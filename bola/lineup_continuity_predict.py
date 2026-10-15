"""Held-out test of missing regular starters as a pre-match 1X2 feature."""

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
from .statsbomb import SOURCE_COMMIT
from .tactic_predict import BETAS, CUTOFF, adjusted, metric


def absence_load(history: list[set[int]], current: set[int]) -> float:
    if not history:
        raise ValueError("Lineup history is empty")
    counts = defaultdict(int)
    for lineup in history:
        if len(lineup) != 11:
            raise ValueError("Historical lineup must contain eleven players")
        for player in lineup:
            counts[player] += 1
    return sum(starts / len(history) for player, starts in counts.items() if player not in current)


def report(folder: Path) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if manifest["source_commit"] != SOURCE_COMMIT:
        raise ValueError("Unexpected StatsBomb source commit")
    match_body = (folder / "matches_2_27.json").read_bytes()
    if hashlib.sha256(match_body).hexdigest() != manifest["matches_sha256"]:
        raise ValueError("Match metadata checksum mismatch")
    matches = sorted(json.loads(match_body), key=lambda row: (row["match_date"], row["match_id"]))
    if len(matches) != 380 or len({row["match_id"] for row in matches}) != 380:
        raise ValueError("Expected complete EPL season")
    games = []
    for row in matches:
        name = f"events_{row['match_id']}.json"
        body = (folder / name).read_bytes()
        if hashlib.sha256(body).hexdigest() != manifest["events_sha256"][str(row["match_id"])]:
            raise ValueError(f"Event checksum mismatch: {name}")
        home = row["home_team"]["home_team_id"]
        away = row["away_team"]["away_team_id"]
        games.append((row, starting_xi(json.loads(body), {home, away})))
    model = Model()
    history = defaultdict(lambda: deque(maxlen=5))
    predictions = []
    for day in sorted({row["match_date"] for row, _ in games}):
        current = [game for game in games if game[0]["match_date"] == day]
        pending = []
        for row, lineups in current:
            home_id = row["home_team"]["home_team_id"]
            away_id = row["away_team"]["away_team_id"]
            home, away = str(home_id), str(away_id)
            match = Match("2015-16", date.fromisoformat(day), home, away,
                          row["home_score"], row["away_score"], "statsbomb")
            if len(history[home_id]) == 5 and len(history[away_id]) == 5:
                home_absence = absence_load(list(history[home_id]), lineups[home_id])
                away_absence = absence_load(list(history[away_id]), lineups[away_id])
                predictions.append({"date": day, "match_id": row["match_id"],
                                    "feature": away_absence - home_absence,
                                    "home_absence_load": home_absence, "away_absence_load": away_absence,
                                    "elo": model.predict(match)["elo"],
                                    "outcome": 0 if match.outcome == "H" else 1 if match.outcome == "D" else 2})
            pending.append((match, lineups))
        for match, lineups in pending:
            model.observe(match)
            for team_id, lineup in lineups.items():
                history[team_id].append(lineup)
    train = [row for row in predictions if row["date"] < CUTOFF]
    test = [row for row in predictions if row["date"] >= CUTOFF]
    if len(test) != 190 or len(train) < 100:
        raise ValueError("Insufficient lineup continuity train/test coverage")
    tuned = {str(beta): metric(train, beta) for beta in BETAS}
    beta = min(BETAS, key=lambda item: (tuned[str(item)]["log_loss"], abs(item)))
    baseline = metric(test, 0)
    augmented = metric(test, beta)
    by_day = defaultdict(list)
    for row in test:
        outcome = row["outcome"]
        by_day[row["date"]].append(
            -math.log(adjusted(row["elo"], row["feature"], beta)[outcome]) + math.log(row["elo"][outcome]))
    clusters = list(by_day.values())
    rng = random.Random(20261015)
    bootstrap = []
    for _ in range(2000):
        sample = [clusters[rng.randrange(len(clusters))] for _ in clusters]
        bootstrap.append(sum(sum(group) for group in sample) / sum(len(group) for group in sample))
    bootstrap.sort()
    return {
        "source": "StatsBomb open-data", "commit": SOURCE_COMMIT,
        "feature": "Away minus home absence load. Absence load sums each missing player's start share over five prior league matches.",
        "training": {"period": "Before 2016-01-01", "n": len(train), "beta_grid": BETAS,
                     "selected_beta": beta,
                     "training_log_loss": {key: value["log_loss"] for key, value in tuned.items()}},
        "holdout": {"period": "2016-01-01 through season end", "n": len(test),
                    "score_only_elo": baseline, "elo_plus_lineup_continuity": augmented,
                    "log_loss_difference_augmented_minus_elo": augmented["log_loss"] - baseline["log_loss"],
                    "match_date_bootstrap_95_ci": [bootstrap[49], bootstrap[1949]],
                    "mean_home_absence_load": sum(row["home_absence_load"] for row in test) / len(test),
                    "mean_away_absence_load": sum(row["away_absence_load"] for row in test) / len(test)},
        "limitations": [
            "A missing recent starter may reflect tactics, transfer, suspension, rotation, or injury.",
            "All players are weighted by recent starts, not position, minutes, or independently estimated ability.",
            "Historical event files do not establish that lineups were publicly available before kickoff.",
            "One older EPL season cannot validate player-impact estimates for current UEFA teams.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(".cache/statsbomb_epl_2015"))
    parser.add_argument("--output", type=Path, default=Path("reports/lineup_continuity_predict.json"))
    args = parser.parse_args()
    result = report(args.data_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
