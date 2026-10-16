"""Transfer the frozen EPL lineup-continuity feature to four WSL datasets."""

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
from .club_audit import starting_xi
from .lineup_continuity_predict import absence_load
from .statsbomb import SOURCE_COMMIT
from .tactic_predict import adjusted, metric


FROZEN_EPL_BETA = 1.0
EPL_HOLDOUT_DIFFERENCE = 0.01462953963410496
EPL_HOLDOUT_CI = (-0.008335411416120828, 0.03708788273904114)


def season_predictions(matches: list[dict], lineups: dict[int, dict[int, set[int]]]) -> list[dict]:
    """Create strict same-season predictions after five previous XIs per team."""
    matches = sorted(matches, key=lambda row: (row["match_date"], row["match_id"]))
    model = Model()
    history: dict[int, deque[set[int]]] = defaultdict(lambda: deque(maxlen=5))
    predictions = []
    for day in sorted({row["match_date"] for row in matches}):
        current = [row for row in matches if row["match_date"] == day]
        pending = []
        for row in current:
            home_id = row["home_team"]["home_team_id"]
            away_id = row["away_team"]["away_team_id"]
            match = Match(str(row["season"]["season_name"]), date.fromisoformat(day),
                          str(home_id), str(away_id), row["home_score"], row["away_score"], "statsbomb")
            match_lineups = lineups[row["match_id"]]
            if len(history[home_id]) == len(history[away_id]) == 5:
                home_absence = absence_load(list(history[home_id]), match_lineups[home_id])
                away_absence = absence_load(list(history[away_id]), match_lineups[away_id])
                predictions.append({
                    "date": day,
                    "match_id": row["match_id"],
                    "feature": away_absence - home_absence,
                    "home_absence_load": home_absence,
                    "away_absence_load": away_absence,
                    "elo": model.predict(match)["elo"],
                    "outcome": 0 if match.outcome == "H" else 1 if match.outcome == "D" else 2,
                })
            pending.append((match, match_lineups))
        # Same-date lineups and results are invisible to every prediction on that date.
        for match, match_lineups in pending:
            model.observe(match)
            for team_id, lineup in match_lineups.items():
                history[team_id].append(lineup)
    return predictions


def report(folder: Path) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if manifest["source_commit"] != SOURCE_COMMIT:
        raise ValueError("Unexpected StatsBomb source commit")
    predictions = []
    season_reports = []
    checksums = starting_xis = event_rows = 0
    match_ids = set()
    for spec in manifest["seasons"]:
        path = folder / f"matches_{spec['competition_id']}_{spec['season_id']}.json"
        body = path.read_bytes()
        if hashlib.sha256(body).hexdigest() != spec["matches_sha256"]:
            raise ValueError(f"Match metadata checksum mismatch: {path.name}")
        checksums += 1
        matches = json.loads(body)
        lineups = {}
        for row in matches:
            match_id = row["match_id"]
            if match_id in match_ids:
                raise ValueError(f"Duplicate match ID: {match_id}")
            match_ids.add(match_id)
            event_body = (folder / f"events_{match_id}.json").read_bytes()
            if hashlib.sha256(event_body).hexdigest() != manifest["events_sha256"][str(match_id)]:
                raise ValueError(f"Event checksum mismatch: {match_id}")
            checksums += 1
            events = json.loads(event_body)
            event_rows += len(events)
            teams = {row["home_team"]["home_team_id"], row["away_team"]["away_team_id"]}
            lineups[match_id] = starting_xi(events, teams)
            starting_xis += 2
        rows = season_predictions(matches, lineups)
        predictions.extend(rows)
        season_reports.append({
            "season": matches[0]["season"]["season_name"],
            "matches": len(matches),
            "eligible_predictions": len(rows),
            "score_only_elo": metric(rows, 0.0),
            "elo_plus_frozen_continuity": metric(rows, FROZEN_EPL_BETA),
        })
    if len(match_ids) != 457 or len(predictions) != 335 or starting_xis != 914:
        raise ValueError("Unexpected WSL lineup coverage")

    baseline = metric(predictions, 0.0)
    augmented = metric(predictions, FROZEN_EPL_BETA)
    by_day: dict[str, list[float]] = defaultdict(list)
    for row in predictions:
        outcome = row["outcome"]
        by_day[row["date"]].append(
            -math.log(adjusted(row["elo"], row["feature"], FROZEN_EPL_BETA)[outcome])
            + math.log(row["elo"][outcome]))
    clusters = list(by_day.values())
    rng = random.Random(20261016)
    bootstrap = []
    for _ in range(2000):
        sample = [clusters[rng.randrange(len(clusters))] for _ in clusters]
        bootstrap.append(sum(sum(group) for group in sample) / sum(len(group) for group in sample))
    bootstrap.sort()
    difference = augmented["log_loss"] - baseline["log_loss"]
    transfer_passed = difference < 0 and bootstrap[1949] < 0
    implementation_passed = (transfer_passed and EPL_HOLDOUT_DIFFERENCE < 0
                             and EPL_HOLDOUT_CI[1] < 0)
    return {
        "source": "StatsBomb open-data",
        "commit": SOURCE_COMMIT,
        "input_audit": {
            "matches": len(match_ids),
            "event_rows": event_rows,
            "starting_xis_verified": starting_xis,
            "checksums_verified": checksums,
        },
        "protocol": {
            "feature": "Away minus home absence load; missing players weighted by start share in five prior same-season matches.",
            "frozen_epl_beta": FROZEN_EPL_BETA,
            "wsl_tuning": False,
            "history_reset": "Elo and lineup history reset at the start of each dataset season.",
            "same_date_rule": "All matches on a date are predicted before lineups or results from that date are observed.",
        },
        "by_season": season_reports,
        "wsl_transfer": {
            "score_only_elo": baseline,
            "elo_plus_frozen_continuity": augmented,
            "log_loss_difference_augmented_minus_elo": difference,
            "match_date_bootstrap_95_ci": [bootstrap[49], bootstrap[1949]],
            "mean_home_absence_load": sum(row["home_absence_load"] for row in predictions) / len(predictions),
            "mean_away_absence_load": sum(row["away_absence_load"] for row in predictions) / len(predictions),
        },
        "decision": {
            "original_epl_holdout": {
                "log_loss_difference": EPL_HOLDOUT_DIFFERENCE,
                "bootstrap_95_ci": EPL_HOLDOUT_CI,
                "passed": EPL_HOLDOUT_DIFFERENCE < 0 and EPL_HOLDOUT_CI[1] < 0,
            },
            "transfer_gate_passed": transfer_passed,
            "implementation_gate_passed": implementation_passed,
            "rule": "Implementation requires improvement in both the original EPL holdout and frozen WSL transfer.",
            "result": ("Retained for further implementation review."
                       if implementation_passed
                       else "Rejected: the feature does not pass both independent holdout gates."),
        },
        "limitations": [
            "A missing regular starter can reflect tactics, transfer, suspension, rotation, or injury.",
            "Player weights use starts rather than minutes, position, opponent, or independently estimated ability.",
            "Event lineups are post-match records and do not establish public availability before kickoff.",
            "WSL transfer does not establish player-impact validity for current UEFA men's teams.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(".cache/statsbomb_wsl"))
    parser.add_argument("--output", type=Path, default=Path("reports/lineup_continuity_transfer.json"))
    args = parser.parse_args()
    result = report(args.data_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
