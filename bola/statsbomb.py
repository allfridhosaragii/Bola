"""Audit xG, events, and historical starting XIs in a StatsBomb match."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path


MATCH_ID = 3869685  # Argentina vs France, World Cup final, 18 Dec 2022
SOURCE_COMMIT = "4b73468fc5b0f1950f9f66fada70ad3a4f9327cb"


def audit(events: list[dict], lineups: list[dict], match_id: int = MATCH_ID) -> dict:
    teams = {team["team_name"] for team in lineups}
    if len(teams) != 2:
        raise ValueError("Expected two teams in lineup data")
    summary = {team: defaultdict(float) for team in teams}
    starting_from_events = {}
    for event in events:
        name = event["team"]["name"]
        if name not in teams:
            raise ValueError(f"Event team missing from lineups: {name}")
        kind = event["type"]["name"]
        if kind == "Starting XI":
            if name in starting_from_events:
                raise ValueError(f"Duplicate Starting XI for {name}")
            starting_from_events[name] = {player["player"]["id"] for player in event["tactics"]["lineup"]}
        # Period 5 is the penalty shootout and not part of the 3-3 match score.
        if event["period"] not in (1, 2, 3, 4):
            continue
        stats = summary[name]
        if kind == "Pass":
            stats["passes_attempted"] += 1
            if "outcome" not in event["pass"]:
                stats["passes_completed"] += 1
        elif kind == "Pressure":
            stats["pressure_events"] += 1
        elif kind == "Ball Recovery":
            stats["ball_recovery_events"] += 1
        elif kind == "Shot":
            stats["shots"] += 1
            xg = event["shot"].get("statsbomb_xg")
            if not isinstance(xg, (int, float)) or not math.isfinite(xg) or not 0 <= xg <= 1:
                raise ValueError(f"Shot lacks valid xG: {event['id']}")
            stats["xg_including_penalties"] += xg
            if event["shot"]["type"]["name"] == "Penalty":
                stats["penalty_shots"] += 1
            else:
                stats["xg_excluding_penalties"] += xg
            if event["shot"]["outcome"]["name"] == "Goal":
                stats["goals_from_shot_events"] += 1
    result = {}
    for team in lineups:
        name = team["team_name"]
        roster = team["lineup"]
        from_lineups = {player["player_id"] for player in roster
                        if any(position.get("start_reason") == "Starting XI" for position in player["positions"])}
        from_events = starting_from_events.get(name, set())
        if len(from_lineups) != 11 or from_events != from_lineups:
            raise ValueError(f"Starting XI mismatch for {name}: lineup={len(from_lineups)}, events={len(from_events)}")
        stats = dict(summary[name])
        result[name] = {"roster_entries": len(roster), "starters_cross_checked": 11,
                        "substitutes_used": sum(any(p.get("start_reason", "").startswith("Substitution - On")
                                                    for p in player["positions"]) for player in roster),
                        **{key: int(value) if key not in ("xg_including_penalties", "xg_excluding_penalties") else round(value, 4)
                           for key, value in stats.items()}}
    return {"match_id": match_id, "source": "https://github.com/statsbomb/open-data", "commit": SOURCE_COMMIT,
            "event_rows": len(events), "teams": result,
            "shootout_shots_excluded": sum(event["period"] == 5 and event["type"]["name"] == "Shot" for event in events),
            "limitations": ["Post-match dataset; not proof these lineups were available before kickoff.",
                            "Pressure events count tagged actions, not pressing success or tactical intent.",
                            "This World Cup match is not a validated predictor for club fixtures."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(".cache/statsbomb"))
    parser.add_argument("--output", type=Path, default=Path("reports/statsbomb.json"))
    args = parser.parse_args()
    events = json.loads((args.data_dir / f"events_{MATCH_ID}.json").read_text(encoding="utf-8"))
    lineups = json.loads((args.data_dir / f"lineups_{MATCH_ID}.json").read_text(encoding="utf-8"))
    report = audit(events, lineups)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
