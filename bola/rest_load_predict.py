"""Test whether pre-match rest-day differences improve WSL 1X2 forecasts."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import random

from .backtest import Match, Model
from .statsbomb import SOURCE_COMMIT
from .tactic_predict import BETAS, adjusted, metric


HOLDOUT_SEASON = "2023/2024"
REST_CAP_DAYS = 14


def capped_rest(days: int) -> int:
    if days < 1:
        raise ValueError("Rest must be at least one calendar day")
    return min(days, REST_CAP_DAYS)


def season_predictions(matches: list[dict]) -> list[dict]:
    """Build forecasts from rest known before each same-season match."""
    matches = sorted(matches, key=lambda row: (row["match_date"], row["match_id"]))
    model = Model()
    last_played: dict[str, date] = {}
    predictions = []
    for day_text in sorted({row["match_date"] for row in matches}):
        day = date.fromisoformat(day_text)
        current = [row for row in matches if row["match_date"] == day_text]
        pending = []
        for row in current:
            home = str(row["home_team"]["home_team_id"])
            away = str(row["away_team"]["away_team_id"])
            match = Match(str(row["season"]["season_name"]), day, home, away,
                          row["home_score"], row["away_score"], "statsbomb")
            if home in last_played and away in last_played:
                home_rest = (day - last_played[home]).days
                away_rest = (day - last_played[away]).days
                predictions.append({
                    "date": day_text,
                    "match_id": row["match_id"],
                    "feature": capped_rest(home_rest) - capped_rest(away_rest),
                    "home_rest_days": home_rest,
                    "away_rest_days": away_rest,
                    "home_capped_rest_days": capped_rest(home_rest),
                    "away_capped_rest_days": capped_rest(away_rest),
                    "elo": model.predict(match)["elo"],
                    "outcome": 0 if match.outcome == "H" else 1 if match.outcome == "D" else 2,
                })
            pending.append(match)
        # Every fixture on a date sees the same pre-date history.
        for match in pending:
            model.observe(match)
            last_played[match.home] = day
            last_played[match.away] = day
    return predictions


def report(folder: Path) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if manifest["source_commit"] != SOURCE_COMMIT:
        raise ValueError("Unexpected StatsBomb source commit")
    training_rows = []
    holdout_rows = []
    season_reports = []
    checksums = 0
    match_ids = set()
    for spec in manifest["seasons"]:
        path = folder / f"matches_{spec['competition_id']}_{spec['season_id']}.json"
        body = path.read_bytes()
        if hashlib.sha256(body).hexdigest() != spec["matches_sha256"]:
            raise ValueError(f"Match metadata checksum mismatch: {path.name}")
        checksums += 1
        matches = json.loads(body)
        ids = {row["match_id"] for row in matches}
        if len(ids) != len(matches) or match_ids.intersection(ids):
            raise ValueError("Duplicate WSL match ID")
        match_ids.update(ids)
        season_name = matches[0]["season"]["season_name"]
        rows = season_predictions(matches)
        destination = holdout_rows if season_name == HOLDOUT_SEASON else training_rows
        destination.extend(rows)
        season_reports.append({"season": season_name, "matches": len(matches),
                               "eligible_predictions": len(rows)})
    if len(match_ids) != 457 or len(training_rows) < 280 or len(holdout_rows) < 110:
        raise ValueError("Unexpected WSL rest-day coverage")

    trained = {str(beta): metric(training_rows, beta) for beta in BETAS}
    beta = min(BETAS, key=lambda item: (trained[str(item)]["log_loss"], abs(item)))
    baseline = metric(holdout_rows, 0.0)
    augmented = metric(holdout_rows, beta)
    by_day: dict[str, list[float]] = defaultdict(list)
    for row in holdout_rows:
        outcome = row["outcome"]
        by_day[row["date"]].append(
            -math.log(adjusted(row["elo"], row["feature"], beta)[outcome])
            + math.log(row["elo"][outcome]))
    clusters = list(by_day.values())
    rng = random.Random(20261016)
    bootstrap = []
    for _ in range(2000):
        sample = [clusters[rng.randrange(len(clusters))] for _ in clusters]
        bootstrap.append(sum(sum(group) for group in sample) / sum(len(group) for group in sample))
    bootstrap.sort()
    difference = augmented["log_loss"] - baseline["log_loss"]
    retained = beta != 0 and difference < 0 and bootstrap[1949] < 0
    all_rows = training_rows + holdout_rows
    rest_values = [row[key] for row in all_rows for key in ("home_rest_days", "away_rest_days")]
    return {
        "source": "StatsBomb open-data",
        "commit": SOURCE_COMMIT,
        "input_audit": {"matches": len(match_ids), "metadata_checksums_verified": checksums,
                        "eligible_predictions": len(all_rows), "team_rest_observations": len(rest_values)},
        "protocol": {
            "feature": "Home capped rest days minus away capped rest days before the match.",
            "rest_cap_days": REST_CAP_DAYS,
            "training_seasons": [row["season"] for row in season_reports if row["season"] != HOLDOUT_SEASON],
            "holdout_season": HOLDOUT_SEASON,
            "beta_grid": BETAS,
            "same_date_rule": "All matches on a date are predicted before that date updates team history.",
            "history_reset": "Rest history and Elo reset at each dataset season.",
        },
        "by_season": season_reports,
        "rest_distribution": {
            "minimum_days": min(rest_values),
            "maximum_days": max(rest_values),
            "mean_days": sum(rest_values) / len(rest_values),
            "team_matches_with_three_or_fewer_rest_days": sum(value <= 3 for value in rest_values),
        },
        "training": {"n": len(training_rows), "selected_beta": beta,
                     "training_log_loss": {key: value["log_loss"] for key, value in trained.items()}},
        "holdout": {
            "n": len(holdout_rows),
            "score_only_elo": baseline,
            "elo_plus_rest_difference": augmented,
            "log_loss_difference_augmented_minus_elo": difference,
            "match_date_bootstrap_95_ci": [bootstrap[49], bootstrap[1949]],
            "mean_home_rest_days": sum(row["home_rest_days"] for row in holdout_rows) / len(holdout_rows),
            "mean_away_rest_days": sum(row["away_rest_days"] for row in holdout_rows) / len(holdout_rows),
        },
        "decision": {
            "rule": "Retain only if training selects a nonzero coefficient and holdout improvement has an interval fully below zero.",
            "retained": retained,
            "result": ("Retained for further transfer review."
                       if retained else "Rejected: rest-day difference did not pass the WSL holdout gate."),
        },
        "limitations": [
            "Calendar-day rest does not measure player minutes, travel, sleep, training load, or squad rotation.",
            "The cap limits long breaks but is a prespecified modeling choice rather than an estimated fatigue threshold.",
            "Only league fixtures contained in each StatsBomb season dataset contribute to rest history.",
            "One WSL holdout does not establish workload effects for current UEFA men's clubs.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(".cache/statsbomb_wsl"))
    parser.add_argument("--output", type=Path, default=Path("reports/rest_load_predict.json"))
    args = parser.parse_args()
    result = report(args.data_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
