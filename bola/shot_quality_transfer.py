"""Test a frozen EPL prior-xG coefficient on four WSL seasons."""

from __future__ import annotations

import argparse
from collections import defaultdict, deque
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import random

from .backtest import Match, Model
from .shot_quality_predict import adjusted, metric, non_penalty_shots
from .statsbomb import SOURCE_COMMIT


FROZEN_BETA = 0.25
EXPECTED_MATCHES = 457


def season_predictions(matches: list[dict], qualities: dict[int, dict[str, dict]]) -> list[dict]:
    """Build predictions using only the current season's five prior games."""
    matches = sorted(matches, key=lambda row: (row["match_date"], row["match_id"]))
    model = Model()
    recent: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=5))
    predictions = []
    for day in sorted({row["match_date"] for row in matches}):
        current = [row for row in matches if row["match_date"] == day]
        pending = []
        for row in current:
            home = str(row["home_team"]["home_team_id"])
            away = str(row["away_team"]["away_team_id"])
            match = Match(str(row["season"]["season_name"]), date.fromisoformat(day), home, away,
                          row["home_score"], row["away_score"], "statsbomb")
            if len(recent[home]) == 5 and len(recent[away]) == 5:
                predictions.append({
                    "date": day,
                    "match_id": row["match_id"],
                    "feature": sum(recent[home]) / 5 - sum(recent[away]) / 5,
                    "elo": model.predict(match)["elo"],
                    "outcome": 0 if match.outcome == "H" else 1 if match.outcome == "D" else 2,
                })
            quality = qualities[row["match_id"]]
            home_xg = float(quality.get(home, {}).get("npxg", 0.0))
            away_xg = float(quality.get(away, {}).get("npxg", 0.0))
            pending.append((match, home, away, home_xg - away_xg))
        # Same-date matches cannot update the model or rolling feature for each other.
        for match, home, away, difference in pending:
            model.observe(match)
            recent[home].append(difference)
            recent[away].append(-difference)
    return predictions


def report(folder: Path) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if manifest["source_commit"] != SOURCE_COMMIT:
        raise ValueError("Unexpected source commit")
    all_predictions = []
    season_reports = []
    total_events = 0
    total_shots = 0
    total_npxg = 0.0
    checksums = 0
    all_ids = set()
    for spec in manifest["seasons"]:
        path = folder / f"matches_{spec['competition_id']}_{spec['season_id']}.json"
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != spec["matches_sha256"]:
            raise ValueError(f"Match metadata checksum mismatch: {path.name}")
        checksums += 1
        matches = json.loads(raw)
        if len(matches) != spec["matches"]:
            raise ValueError("Season match count mismatch")
        qualities = {}
        for row in matches:
            match_id = row["match_id"]
            if match_id in all_ids:
                raise ValueError(f"Duplicate match ID: {match_id}")
            all_ids.add(match_id)
            body = (folder / f"events_{match_id}.json").read_bytes()
            if hashlib.sha256(body).hexdigest() != manifest["events_sha256"][str(match_id)]:
                raise ValueError(f"Event checksum mismatch: {match_id}")
            checksums += 1
            events = json.loads(body)
            quality = non_penalty_shots(events)
            qualities[match_id] = quality
            total_events += len(events)
            total_shots += sum(int(value["shots"]) for value in quality.values())
            total_npxg += sum(float(value["npxg"]) for value in quality.values())
        predictions = season_predictions(matches, qualities)
        all_predictions.extend(predictions)
        season_reports.append({
            "season": matches[0]["season"]["season_name"],
            "matches": len(matches),
            "eligible_predictions": len(predictions),
            "date_range": [min(row["match_date"] for row in matches), max(row["match_date"] for row in matches)],
            "score_only_elo": metric(predictions, 0.0),
            "elo_plus_frozen_npxg": metric(predictions, FROZEN_BETA),
        })
    if len(all_ids) != EXPECTED_MATCHES:
        raise ValueError(f"Expected {EXPECTED_MATCHES} distinct matches")

    baseline = metric(all_predictions, 0.0)
    augmented = metric(all_predictions, FROZEN_BETA)
    by_day: dict[str, list[float]] = defaultdict(list)
    for row in all_predictions:
        augmented_loss = -math.log(adjusted(row["elo"], row["feature"], FROZEN_BETA)[row["outcome"]])
        baseline_loss = -math.log(row["elo"][row["outcome"]])
        by_day[row["date"]].append(augmented_loss - baseline_loss)
    clusters = list(by_day.values())
    rng = random.Random(20261015)
    replicates = []
    for _ in range(2000):
        sampled = [clusters[rng.randrange(len(clusters))] for _ in clusters]
        replicates.append(sum(sum(group) for group in sampled) / sum(len(group) for group in sampled))
    replicates.sort()
    difference = augmented["log_loss"] - baseline["log_loss"]
    retained = difference < 0 and replicates[1949] < 0
    return {
        "source": "StatsBomb open-data",
        "commit": SOURCE_COMMIT,
        "input_audit": {
            "competition": "FA Women's Super League",
            "seasons": len(season_reports),
            "matches": len(all_ids),
            "event_rows": total_events,
            "non_penalty_shots": total_shots,
            "non_penalty_xg": round(total_npxg, 6),
            "checksums_verified": checksums,
        },
        "transfer_protocol": {
            "coefficient_source": "Selected on 140 EPL 2015/16 matches before 2016-01-01.",
            "frozen_beta": FROZEN_BETA,
            "wsl_tuning": False,
            "history": "Exactly five earlier matches in the same season; Elo and xG history reset each season.",
            "same_date_rule": "Every match on a date is predicted before any match on that date is observed.",
        },
        "by_season": season_reports,
        "combined_transfer_test": {
            "score_only_elo": baseline,
            "elo_plus_frozen_npxg": augmented,
            "log_loss_difference_augmented_minus_elo": difference,
            "match_date_bootstrap_95_ci": [replicates[49], replicates[1949]],
        },
        "decision": {
            "rule": "Retain only if combined log loss improves and the entire bootstrap interval is below zero.",
            "retained": retained,
            "result": ("Retained for further implementation review; the transfer gate passed."
                       if retained else "Rejected: the frozen feature did not pass the transfer gate."),
        },
        "limitations": [
            "This tests transfer from one men's league season to a women's league, not to UEFA men's competitions.",
            "StatsBomb supplies xG in both samples, so provider-model independence is not established.",
            "The open event files are post-match data and do not establish historical pregame publication timing.",
            "Four seasons from one competition cannot establish stability in current or future competitions.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(".cache/statsbomb_wsl"))
    parser.add_argument("--output", type=Path, default=Path("reports/shot_quality_transfer.json"))
    args = parser.parse_args()
    result = report(args.data_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
