"""Audit four WSL feature tests with family-wise bootstrap intervals."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import random

from .club_audit import starting_xi
from .lineup_continuity_transfer import season_predictions as lineup_predictions
from .pressure_predict import pressure_regains
from .pressure_transfer import season_predictions as pressure_predictions
from .shot_quality_incremental import feature_rows, probabilities
from .shot_quality_predict import non_penalty_shots
from .statsbomb import SOURCE_COMMIT
from .tactic_predict import adjusted


FEATURES = ("five_match_goals", "five_match_npxg", "pressure_regains", "lineup_continuity")
REPLICATES = 8000


def percentile(values: list[float], probability: float) -> float:
    if not values or not 0 <= probability <= 1:
        raise ValueError("Invalid percentile input")
    ordered = sorted(values)
    return ordered[int(probability * (len(ordered) - 1))]


def summarize_replicates(point: float, replicates: list[float], family_size: int) -> dict:
    alpha = 0.05
    adjusted_tail = alpha / (2 * family_size)
    nominal = [percentile(replicates, alpha / 2), percentile(replicates, 1 - alpha / 2)]
    adjusted_ci = [percentile(replicates, adjusted_tail),
                   percentile(replicates, 1 - adjusted_tail)]
    return {
        "log_loss_difference_candidate_minus_elo": point,
        "nominal_bootstrap_95_ci": nominal,
        "bonferroni_familywise_95_ci": adjusted_ci,
        "passes_familywise_gate": point < 0 and adjusted_ci[1] < 0,
    }


def report(folder: Path) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if manifest["source_commit"] != SOURCE_COMMIT:
        raise ValueError("Unexpected StatsBomb source commit")
    spec = next((row for row in manifest["seasons"] if row["season_id"] == 281), None)
    if spec is None:
        raise ValueError("WSL 2023/24 metadata missing")
    path = folder / f"matches_{spec['competition_id']}_{spec['season_id']}.json"
    body = path.read_bytes()
    if hashlib.sha256(body).hexdigest() != spec["matches_sha256"]:
        raise ValueError("WSL holdout metadata checksum mismatch")
    matches = json.loads(body)
    if len(matches) != 132 or matches[0]["season"]["season_name"] != "2023/2024":
        raise ValueError("Unexpected WSL holdout identity")

    qualities = {}
    lineups = {}
    regains = {}
    event_rows = pressure_events = pressure_led_regains = 0
    for row in matches:
        match_id = row["match_id"]
        event_body = (folder / f"events_{match_id}.json").read_bytes()
        if hashlib.sha256(event_body).hexdigest() != manifest["events_sha256"][str(match_id)]:
            raise ValueError(f"Event checksum mismatch: {match_id}")
        events = json.loads(event_body)
        event_rows += len(events)
        qualities[match_id] = non_penalty_shots(events)
        teams = {row["home_team"]["home_team_id"], row["away_team"]["away_team_id"]}
        lineups[match_id] = starting_xi(events, teams)
        pressures, match_regains = pressure_regains(events)
        regains[match_id] = match_regains
        pressure_events += sum(pressures.values())
        pressure_led_regains += sum(match_regains.values())

    base_rows = feature_rows(matches, qualities)
    pressure_rows = pressure_predictions(matches, regains)
    lineup_rows = lineup_predictions(matches, lineups)
    ids = [row["match_id"] for row in base_rows]
    if (len(ids) != 102 or ids != [row["match_id"] for row in pressure_rows]
            or ids != [row["match_id"] for row in lineup_rows]):
        raise ValueError("Feature rows do not align on the same 102 matches")

    rows = []
    for base, pressure, lineup in zip(base_rows, pressure_rows, lineup_rows):
        if base["elo"] != pressure["elo"] or base["elo"] != lineup["elo"] or (
                base["outcome"] != pressure["outcome"] or base["outcome"] != lineup["outcome"]):
            raise ValueError("Baseline forecast or outcome mismatch")
        forecasts = {
            "five_match_goals": probabilities(base, 0.0, 0.1),
            "five_match_npxg": probabilities(base, 0.25, 0.0),
            "pressure_regains": adjusted(pressure["elo"], pressure["feature"], 0.5),
            "lineup_continuity": adjusted(lineup["elo"], lineup["feature"], 1.0),
        }
        outcome = base["outcome"]
        baseline_loss = -math.log(base["elo"][outcome])
        rows.append({
            "date": base["date"],
            "match_id": base["match_id"],
            "outcome": outcome,
            "elo": base["elo"],
            "forecasts": forecasts,
            "loss_differences": {name: -math.log(forecast[outcome]) - baseline_loss
                                  for name, forecast in forecasts.items()},
        })

    metrics = {}
    for name in FEATURES:
        losses = [-math.log(row["forecasts"][name][row["outcome"]]) for row in rows]
        briers = [sum((row["forecasts"][name][i] - int(i == row["outcome"])) ** 2
                      for i in range(3)) for row in rows]
        metrics[name] = {"n": len(rows), "log_loss": sum(losses) / len(losses),
                         "brier": sum(briers) / len(briers)}
    baseline_losses = [-math.log(row["elo"][row["outcome"]]) for row in rows]
    baseline_briers = [sum((row["elo"][i] - int(i == row["outcome"])) ** 2 for i in range(3))
                       for row in rows]
    baseline_metric = {"n": len(rows), "log_loss": sum(baseline_losses) / len(rows),
                       "brier": sum(baseline_briers) / len(rows)}

    by_day: dict[str, list[dict[str, float]]] = defaultdict(list)
    for row in rows:
        by_day[row["date"]].append(row["loss_differences"])
    clusters = list(by_day.values())
    rng = random.Random(20261016)
    bootstrap = {name: [] for name in FEATURES}
    for _ in range(REPLICATES):
        sample = [clusters[rng.randrange(len(clusters))] for _ in clusters]
        denominator = sum(len(group) for group in sample)
        for name in FEATURES:
            bootstrap[name].append(
                sum(item[name] for group in sample for item in group) / denominator)
    comparisons = {}
    for name in FEATURES:
        point = metrics[name]["log_loss"] - baseline_metric["log_loss"]
        comparisons[name] = summarize_replicates(point, bootstrap[name], len(FEATURES))

    retained = [name for name in FEATURES if comparisons[name]["passes_familywise_gate"]]
    if len(retained) == 1:
        decision_text = f"Only {retained[0]} survives the four-feature family-wise correction."
    elif retained:
        decision_text = f"Only {', '.join(retained)} survive the four-feature family-wise correction."
    else:
        decision_text = "No feature survives the four-feature family-wise correction."
    return {
        "source": "StatsBomb open-data",
        "commit": SOURCE_COMMIT,
        "input_audit": {
            "competition": "FA Women's Super League 2023/24",
            "matches": len(matches),
            "eligible_predictions": len(rows),
            "event_rows": event_rows,
            "starting_xis_verified": len(matches) * 2,
            "pressure_events": pressure_events,
            "pressure_led_regains": pressure_led_regains,
            "checksums_verified": len(matches) + 1,
        },
        "protocol": {
            "family": FEATURES,
            "family_size": len(FEATURES),
            "bootstrap_replicates": REPLICATES,
            "resampling_unit": "match date",
            "nominal_interval": 0.95,
            "bonferroni_individual_interval_for_familywise_95": 1 - 0.05 / len(FEATURES),
            "coefficients": {"five_match_goals": 0.1, "five_match_npxg": 0.25,
                             "pressure_regains": 0.5, "lineup_continuity": 1.0},
        },
        "score_only_elo": baseline_metric,
        "feature_metrics": metrics,
        "comparisons_vs_elo": comparisons,
        "decision": {
            "features_passing_familywise_gate": retained,
            "result": decision_text,
            "implementation": "This retrospective audit does not activate any UEFA feature.",
        },
        "limitations": [
            "The WSL 2023/24 outcomes were already inspected in earlier feature reports; this is multiplicity correction, not a new holdout.",
            "Bonferroni controls this declared four-feature family but not every exploratory analysis ever performed in the project.",
            "All advanced event features use StatsBomb provider definitions and post-match files.",
            "A WSL result does not establish transfer to current UEFA men's fixtures or value against betting markets.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(".cache/statsbomb_wsl"))
    parser.add_argument("--output", type=Path, default=Path("reports/feature_family_audit.json"))
    args = parser.parse_args()
    result = report(args.data_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
