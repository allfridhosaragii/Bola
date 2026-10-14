"""Audit recovery patterns and starting-XI rotation across EPL 2015/16."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
import hashlib
import json
from pathlib import Path
import random

from .backtest import Match, Model
from .recovery import aggregate, summarize_match
from .statsbomb import SOURCE_COMMIT


def starting_xi(events: list[dict], expected: set[int]) -> dict[int, set[int]]:
    lineups = {}
    for event in events:
        if event["type"]["name"] != "Starting XI":
            continue
        team = event["team"]["id"]
        players = [row["player"]["id"] for row in event["tactics"]["lineup"]]
        if team in lineups or len(players) != 11 or len(set(players)) != 11:
            raise ValueError("Duplicate or incomplete starting XI")
        lineups[team] = set(players)
    if set(lineups) != expected:
        raise ValueError("Starting XI teams disagree with match metadata")
    return lineups


def rotation_bucket(changed: int) -> str:
    return "0-2" if changed <= 2 else "3-4" if changed <= 4 else "5-11"


def report(folder: Path) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text())
    if manifest["source_commit"] != SOURCE_COMMIT:
        raise ValueError("Unexpected StatsBomb commit")
    raw_matches = (folder / "matches_2_27.json").read_bytes()
    if hashlib.sha256(raw_matches).hexdigest() != manifest["matches_sha256"]:
        raise ValueError("Match metadata checksum mismatch")
    matches = sorted(json.loads(raw_matches), key=lambda row: (row["match_date"], row["match_id"]))
    if len(matches) != 380 or len({m["match_id"] for m in matches}) != 380:
        raise ValueError("Expected all 380 EPL games")
    recovered = []
    game_rows = []
    previous = {}
    lineup_counts = 0
    for row in matches:
        match_id = row["match_id"]
        name = f"events_{match_id}.json"
        raw = (folder / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != manifest["events_sha256"][str(match_id)]:
            raise ValueError(f"Event checksum mismatch: {name}")
        events = json.loads(raw)
        home, away = row["home_team"]["home_team_id"], row["away_team"]["away_team_id"]
        lineups = starting_xi(events, {home, away})
        recovered.append(summarize_match(events))
        changed = {}
        for team in (home, away):
            changed[team] = len(lineups[team] - previous[team]) if team in previous else None
            previous[team] = lineups[team]
        lineup_counts += 2
        game_rows.append((row, changed))
    model = Model()
    observations = []
    for day in sorted({row["match_date"] for row, _ in game_rows}):
        current = [(row, changes) for row, changes in game_rows if row["match_date"] == day]
        pending = []
        for row, changes in current:
            home, away = row["home_team"]["home_team_id"], row["away_team"]["away_team_id"]
            match = Match("2015-16", date.fromisoformat(day), str(home), str(away),
                          row["home_score"], row["away_score"], "statsbomb")
            probs = model.predict(match)["elo"]
            for team, changed, actual, expected in (
                (home, changes[home], 3 if match.outcome == "H" else 1 if match.outcome == "D" else 0,
                 3 * probs[0] + probs[1]),
                (away, changes[away], 3 if match.outcome == "A" else 1 if match.outcome == "D" else 0,
                 3 * probs[2] + probs[1]),
            ):
                if changed is not None:
                    observations.append({"match_id": row["match_id"], "team_id": team,
                                         "changed_starters": changed, "bucket": rotation_bucket(changed),
                                         "points": actual, "expected_points_score_only": expected,
                                         "points_minus_expectation": actual - expected})
            pending.append(match)
        for match in pending:
            model.observe(match)
    recovery_totals = aggregate(recovered)
    rng = random.Random(20261015)
    differences = []
    for _ in range(2000):
        sampled = aggregate([recovered[rng.randrange(len(recovered))] for _ in recovered])
        differences.append(sampled["opponent_half"]["shot_sequence_rate"] -
                           sampled["own_half"]["shot_sequence_rate"])
    differences.sort()
    by_bucket = defaultdict(list)
    for observation in observations:
        by_bucket[observation["bucket"]].append(observation)
    rotation = {bucket: {"team_matches": len(rows),
                         "mean_changed_starters": sum(r["changed_starters"] for r in rows) / len(rows),
                         "points_per_match": sum(r["points"] for r in rows) / len(rows),
                         "score_only_expected_points_per_match":
                             sum(r["expected_points_score_only"] for r in rows) / len(rows),
                         "mean_points_minus_expectation":
                             sum(r["points_minus_expectation"] for r in rows) / len(rows)}
                for bucket, rows in sorted(by_bucket.items())}
    return {"source": "StatsBomb open-data", "commit": SOURCE_COMMIT, "competition": "EPL 2015/16",
            "matches": len(matches), "starting_xis_checked": lineup_counts,
            "recovery_15_seconds": {"by_half": recovery_totals,
                                    "shot_rate_difference_opponent_minus_own":
                                        recovery_totals["opponent_half"]["shot_sequence_rate"] -
                                        recovery_totals["own_half"]["shot_sequence_rate"],
                                    "match_bootstrap_95_ci": [differences[49], differences[1949]]},
            "rotation_vs_result": {"team_matches_with_prior_xi": len(observations), "by_changed_starters": rotation},
            "limitations": ["Tagged recoveries are not all turnovers or verified successful presses.",
                            "Field position, score state, opponent, and game plan can confound shot rate.",
                            "Starting XI changes have many causes; rotation buckets are descriptive, not causal injury effects.",
                            "The score-only Elo expectation is an exploratory baseline, not a validated player-impact model.",
                            "StatsBomb events were published after matches, so pre-kickoff availability is unproven."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(".cache/statsbomb_epl_2015"))
    parser.add_argument("--output", type=Path, default=Path("reports/club_audit.json"))
    args = parser.parse_args()
    result = report(args.data_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
