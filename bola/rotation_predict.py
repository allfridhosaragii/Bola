"""Held-out test of starting-XI turnover as a pregame 1X2 feature."""

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
from .club_audit import starting_xi
from .statsbomb import SOURCE_COMMIT
from .tactic_predict import adjusted, metric


CUTOFF = "2016-01-01"
BETAS = (-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0)


def report(folder: Path) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text())
    if manifest["source_commit"] != SOURCE_COMMIT:
        raise ValueError("Unexpected StatsBomb source commit")
    raw_matches = (folder / "matches_2_27.json").read_bytes()
    if hashlib.sha256(raw_matches).hexdigest() != manifest["matches_sha256"]:
        raise ValueError("Match metadata checksum mismatch")
    matches = sorted(json.loads(raw_matches), key=lambda row: (row["match_date"], row["match_id"]))
    if len(matches) != 380 or len({row["match_id"] for row in matches}) != 380:
        raise ValueError("Expected complete EPL season")
    if not (matches[189]["match_date"] < CUTOFF <= matches[190]["match_date"]):
        raise ValueError("EPL season no longer splits 190/190 at cutoff")
    games = []
    for row in matches:
        match_id = row["match_id"]
        name = f"events_{match_id}.json"
        body = (folder / name).read_bytes()
        if hashlib.sha256(body).hexdigest() != manifest["events_sha256"][str(match_id)]:
            raise ValueError(f"Event checksum mismatch: {name}")
        home, away = row["home_team"]["home_team_id"], row["away_team"]["away_team_id"]
        lineups = starting_xi(json.loads(body), {home, away})
        games.append((row, lineups))
    model = Model()
    previous = {}
    predictions = []
    for day in sorted({row["match_date"] for row, _ in games}):
        current = [(row, lineups) for row, lineups in games if row["match_date"] == day]
        pending = []
        for row, lineups in current:
            home_id, away_id = row["home_team"]["home_team_id"], row["away_team"]["away_team_id"]
            match = Match("2015-16", date.fromisoformat(day), str(home_id), str(away_id),
                          row["home_score"], row["away_score"], "statsbomb")
            if home_id in previous and away_id in previous:
                changed_home = len(lineups[home_id] - previous[home_id])
                changed_away = len(lineups[away_id] - previous[away_id])
                predictions.append({"date": day, "match_id": row["match_id"],
                                    "feature": changed_away - changed_home,
                                    "elo": model.predict(match)["elo"],
                                    "outcome": 0 if match.outcome == "H" else 1 if match.outcome == "D" else 2})
            pending.append((match, lineups))
        for match, lineups in pending:
            model.observe(match)
            previous.update(lineups)
    train = [row for row in predictions if row["date"] < CUTOFF]
    test = [row for row in predictions if row["date"] >= CUTOFF]
    if len(train) != 180 or len(test) != 190:
        raise ValueError("Unexpected rotation training/test coverage")
    tuned = {str(beta): metric(train, beta) for beta in BETAS}
    beta = min(BETAS, key=lambda item: (tuned[str(item)]["log_loss"], abs(item)))
    baseline = metric(test, 0)
    adjusted_result = metric(test, beta)
    by_day = defaultdict(list)
    for row in test:
        y = row["outcome"]
        by_day[row["date"]].append(-math.log(adjusted(row["elo"], row["feature"], beta)[y]) +
                                   math.log(row["elo"][y]))
    clusters = list(by_day.values())
    rng = random.Random(20261015)
    replicates = []
    for _ in range(2000):
        sample = [clusters[rng.randrange(len(clusters))] for _ in clusters]
        replicates.append(sum(sum(group) for group in sample) / sum(len(group) for group in sample))
    replicates.sort()
    return {"source": "StatsBomb open-data", "commit": SOURCE_COMMIT,
            "feature": "Current starter changes versus each team's previous EPL match; away changes minus home changes.",
            "training": {"period": "Before 2016-01-01", "n": len(train), "beta_grid": BETAS,
                         "training_log_loss": {key: value["log_loss"] for key, value in tuned.items()},
                         "selected_beta": beta},
            "holdout": {"period": "2016-01-01 through season end", "n": len(test),
                        "score_only_elo": baseline, "elo_plus_rotation": adjusted_result,
                        "log_loss_difference_augmented_minus_elo":
                            adjusted_result["log_loss"] - baseline["log_loss"],
                        "match_date_bootstrap_95_ci": [replicates[49], replicates[1949]]},
            "limitations": ["Historical event feed does not prove lineup publication before kickoff.",
                            "Changed starters are not the same as injured or suspended players.",
                            "Opponent, rest, manager decisions, and selection are confounders.",
                            "This single old season cannot validate UEFA player-impact estimates."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(".cache/statsbomb_epl_2015"))
    parser.add_argument("--output", type=Path, default=Path("reports/rotation_predict.json"))
    args = parser.parse_args()
    result = report(args.data_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
