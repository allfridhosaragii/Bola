"""Test a frozen StatsBomb npxG coefficient with independent Understat xG."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import random

from .shot_quality_incremental import feature_rows, metric, probabilities
from .shot_quality_predict import BETAS
from .statsbomb import SOURCE_COMMIT
from .tactic_predict import CUTOFF
from .xg_provider_compare import SB_TO_UNDERSTAT, statsbomb_rows, understat_rows


FROZEN_STATSBOMB_BETA = 0.25


def paired_difference(rows: list[dict], candidate_beta: float, reference_beta: float = 0.0) -> dict:
    by_day: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        candidate = -math.log(probabilities(row, candidate_beta, 0.0)[row["outcome"]])
        reference = -math.log(probabilities(row, reference_beta, 0.0)[row["outcome"]])
        by_day[row["date"]].append(candidate - reference)
    clusters = list(by_day.values())
    rng = random.Random(20261016)
    replicates = []
    for _ in range(2000):
        sampled = [clusters[rng.randrange(len(clusters))] for _ in clusters]
        replicates.append(sum(sum(group) for group in sampled) / sum(len(group) for group in sampled))
    replicates.sort()
    candidate_metric = metric(rows, candidate_beta, 0.0)
    reference_metric = metric(rows, reference_beta, 0.0)
    return {
        "log_loss_difference_candidate_minus_reference": (
            candidate_metric["log_loss"] - reference_metric["log_loss"]),
        "match_date_bootstrap_95_ci": [replicates[49], replicates[1949]],
    }


def report(statsbomb_folder: Path, understat_folder: Path) -> dict:
    sb = statsbomb_rows(statsbomb_folder)
    understat = understat_rows(understat_folder)
    if sb.keys() != understat.keys() or len(sb) != 380:
        raise ValueError("Providers do not cover the same fixtures")
    manifest = json.loads((statsbomb_folder / "manifest.json").read_text(encoding="utf-8"))
    if manifest["source_commit"] != SOURCE_COMMIT:
        raise ValueError("Unexpected StatsBomb source commit")
    body = (statsbomb_folder / "matches_2_27.json").read_bytes()
    if hashlib.sha256(body).hexdigest() != manifest["matches_sha256"]:
        raise ValueError("StatsBomb match metadata checksum mismatch")
    matches = json.loads(body)
    understat_quality = {}
    statsbomb_quality = {}
    date_differences = 0
    for match in matches:
        names = match["home_team"]["home_team_name"], match["away_team"]["away_team_name"]
        pair = tuple(SB_TO_UNDERSTAT.get(name, name) for name in names)
        a, b = sb[pair], understat[pair]
        if a["score"] != b["score"]:
            raise ValueError(f"Provider score mismatch: {pair}")
        date_gap = abs((date.fromisoformat(a["date"]) - date.fromisoformat(b["date"])).days)
        if date_gap > 1:
            raise ValueError(f"Provider date mismatch: {pair}")
        date_differences += date_gap == 1
        home = str(match["home_team"]["home_team_id"])
        away = str(match["away_team"]["away_team_id"])
        understat_quality[match["match_id"]] = {
            home: {"npxg": b["npxg"][0]}, away: {"npxg": b["npxg"][1]}}
        statsbomb_quality[match["match_id"]] = {
            home: {"npxg": a["npxg"][0]}, away: {"npxg": a["npxg"][1]}}

    understat_features = feature_rows(matches, understat_quality)
    statsbomb_features = feature_rows(matches, statsbomb_quality)
    if [row["match_id"] for row in understat_features] != [row["match_id"] for row in statsbomb_features]:
        raise ValueError("Provider prediction rows do not align")
    train = [row for row in understat_features if row["date"] < CUTOFF]
    test = [row for row in understat_features if row["date"] >= CUTOFF]
    sb_test = [row for row in statsbomb_features if row["date"] >= CUTOFF]
    if len(train) != 140 or len(test) != 190 or len(sb_test) != 190:
        raise ValueError("Unexpected chronological split")
    understat_beta = min(BETAS, key=lambda beta: (metric(train, beta, 0.0)["log_loss"], abs(beta)))
    baseline = metric(test, 0.0, 0.0)
    frozen = metric(test, FROZEN_STATSBOMB_BETA, 0.0)
    retuned = metric(test, understat_beta, 0.0)
    sb_frozen = metric(sb_test, FROZEN_STATSBOMB_BETA, 0.0)
    feature_differences = [a["xg_feature"] - b["xg_feature"]
                           for a, b in zip(sb_test, test)]
    frozen_comparison = paired_difference(test, FROZEN_STATSBOMB_BETA)
    retained = (frozen_comparison["log_loss_difference_candidate_minus_reference"] < 0
                and frozen_comparison["match_date_bootstrap_95_ci"][1] < 0)
    return {
        "sources": {
            "statsbomb_commit": SOURCE_COMMIT,
            "understat_sha256": json.loads((understat_folder / "manifest.json").read_text())["sha256"],
        },
        "input_audit": {
            "fixtures_matched": len(matches),
            "date_differed_by_one_day": date_differences,
            "understat_non_penalty_shots": sum(sum(row["non_penalty_shots"]) for row in understat.values()),
            "statsbomb_non_penalty_shots": sum(sum(row["non_penalty_shots"]) for row in sb.values()),
        },
        "protocol": {
            "frozen_statsbomb_beta": FROZEN_STATSBOMB_BETA,
            "understat_tuning_period": "Before 2016-01-01; reported as sensitivity, not the primary test.",
            "understat_selected_beta": understat_beta,
            "primary_test": "Apply the StatsBomb-selected coefficient to Understat five-match npxG on the 190-match holdout.",
            "same_date_rule": "All matches on a date are predicted before results or xG from that date are observed.",
        },
        "holdout": {
            "score_only_elo": baseline,
            "understat_npxg_frozen_statsbomb_beta": frozen,
            "understat_npxg_retuned_beta_sensitivity": retuned,
            "statsbomb_npxg_frozen_beta_reference": sb_frozen,
            "frozen_understat_vs_elo": frozen_comparison,
            "mean_absolute_statsbomb_understat_feature_difference": (
                sum(map(abs, feature_differences)) / len(feature_differences)),
        },
        "decision": {
            "rule": "Provider robustness passes only if frozen Understat npxG improves holdout log loss and the entire interval is below zero.",
            "provider_robustness_passed": retained,
            "result": ("Passed: the frozen coefficient remains effective with Understat npxG."
                       if retained else "Not passed: independent-provider npxG did not clear the uncertainty gate."),
        },
        "limitations": [
            "The providers are independent measurements, but the same EPL outcomes are used in both feature audits.",
            "Understat data come from a pinned community mirror; original publication timestamps and model training history are unavailable.",
            "Fixture-level npxG is matched; individual shots are not reconciled one by one.",
            "One historical EPL season does not establish current UEFA transfer or pregame availability.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--statsbomb-dir", type=Path, default=Path(".cache/statsbomb_epl_2015"))
    parser.add_argument("--understat-dir", type=Path, default=Path(".cache/understat_epl_2015"))
    parser.add_argument("--output", type=Path, default=Path("reports/xg_provider_predict.json"))
    args = parser.parse_args()
    result = report(args.statsbomb_dir, args.understat_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
