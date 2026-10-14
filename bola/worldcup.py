"""Summarize StatsBomb open-data event and lineup audits for World Cup 2022."""

import argparse
from collections import Counter
import json
import math
from pathlib import Path

from .statsbomb import SOURCE_COMMIT, audit


def shot_calibration(shots: list[tuple[float, int]]) -> dict:
    if not shots:
        raise ValueError("No shots available for calibration")
    bins = [{"count": 0, "predicted_sum": 0.0, "goals": 0} for _ in range(10)]
    brier = 0.0
    log_loss = 0.0
    for xg, goal in shots:
        brier += (xg - goal) ** 2
        clipped = min(max(xg, 1e-15), 1 - 1e-15)
        log_loss -= goal * math.log(clipped) + (1 - goal) * math.log(1 - clipped)
        bucket = bins[min(9, int(xg * 10))]
        bucket["count"] += 1
        bucket["predicted_sum"] += xg
        bucket["goals"] += goal
    n = len(shots)
    goal_rate = sum(goal for _, goal in shots) / n
    calibration_bins = [
        {"range": f"{index / 10:.1f}-{(index + 1) / 10:.1f}", "count": bucket["count"],
         "mean_xg": round(bucket["predicted_sum"] / bucket["count"], 4),
         "goal_rate": round(bucket["goals"] / bucket["count"], 4)}
        for index, bucket in enumerate(bins) if bucket["count"]
    ]
    ece = sum(abs(bucket["predicted_sum"] - bucket["goals"]) for bucket in bins) / n
    return {"shots": n, "goals": sum(goal for _, goal in shots), "mean_xg": round(sum(xg for xg, _ in shots) / n, 4),
            "goal_rate": round(goal_rate, 4), "brier": round(brier / n, 4),
            "constant_goal_rate_brier": round(goal_rate * (1 - goal_rate), 4),
            "log_loss": round(log_loss / n, 4), "ece_10_bins": round(ece, 4),
            "bins": calibration_bins}


def summarize(data_dir: Path) -> dict:
    matches = json.loads((data_dir / "matches_43_106.json").read_text(encoding="utf-8"))
    if len(matches) != 64 or len({m["match_id"] for m in matches}) != 64:
        raise ValueError("Expected 64 unique World Cup matches")
    totals = Counter()
    stages = Counter()
    shots = []
    for match in matches:
        match_id = match["match_id"]
        events = json.loads((data_dir / f"events_{match_id}.json").read_text(encoding="utf-8"))
        lineups = json.loads((data_dir / f"lineups_{match_id}.json").read_text(encoding="utf-8"))
        expected_teams = {match["home_team"]["home_team_name"], match["away_team"]["away_team_name"]}
        if {team["team_name"] for team in lineups} != expected_teams:
            raise ValueError(f"Match {match_id} teams disagree with metadata")
        result = audit(events, lineups, match_id)
        for event in events:
            if event["type"]["name"] == "Shot" and event["period"] in (1, 2, 3, 4):
                shots.append((event["shot"]["statsbomb_xg"], int(event["shot"]["outcome"]["name"] == "Goal")))
        totals["events"] += result["event_rows"]
        totals["shootout_shots_excluded"] += result["shootout_shots_excluded"]
        totals["starting_xis_cross_checked"] += len(result["teams"])
        for team in result["teams"].values():
            for key in ("shots", "penalty_shots", "goals_from_shot_events", "passes_attempted",
                        "passes_completed", "pressure_events", "ball_recovery_events",
                        "xg_including_penalties", "xg_excluding_penalties"):
                totals[key] += team.get(key, 0)
        stages[match["competition_stage"]["name"]] += 1
    calibration = shot_calibration(shots)
    if calibration["shots"] != totals["shots"] or calibration["goals"] != totals["goals_from_shot_events"]:
        raise ValueError("Shot calibration disagrees with event audit totals")
    return {
        "source": "https://github.com/statsbomb/open-data", "commit": SOURCE_COMMIT,
        "competition": "2022 FIFA World Cup", "matches": len(matches),
        "stages": dict(stages),
        "totals": {key: round(value, 4) if key.startswith("xg_") else value for key, value in totals.items()},
        "shot_xg_calibration": calibration,
        "limitations": [
            "Open data was published after matches; it cannot establish pre-match information availability.",
            "This is a single tournament, not a representative sample of club football.",
            "StatsBomb xG model training data are not established here; calibration is descriptive, not an independent holdout validation.",
            "Tagged pressure events do not establish pressing success or tactical intent.",
            "Match score is not necessarily identical to goals from Shot events because own goals are separate.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(".cache/statsbomb"))
    parser.add_argument("--output", type=Path, default=Path("reports/worldcup.json"))
    args = parser.parse_args()
    result = summarize(args.data_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
