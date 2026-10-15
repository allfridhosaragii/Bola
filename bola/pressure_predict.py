"""Held-out test of pressure-led possession regains as a pre-match 1X2 feature."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import random

from .backtest import Match, Model
from .statsbomb import SOURCE_COMMIT
from .tactic_predict import BETAS, CUTOFF, adjusted, metric


def event_seconds(event: dict) -> float:
    return event["minute"] * 60 + event["second"]


def pressure_regains(events: list[dict], seconds: float = 5) -> tuple[Counter[str], Counter[str]]:
    pressures: Counter[str] = Counter()
    regained: Counter[str] = Counter()
    counted = set()
    ordered = sorted(events, key=lambda row: (row["period"], row["minute"], row["second"], row["index"]))
    for index, event in enumerate(ordered):
        if event["type"]["name"] != "Pressure" or event["period"] not in (1, 2, 3, 4):
            continue
        team = str(event["team"]["id"])
        pressures[team] += 1
        start = event_seconds(event)
        old_possession = event.get("possession")
        for later in ordered[index + 1:]:
            if later["period"] != event["period"] or event_seconds(later) - start > seconds:
                break
            possession_team = str(later.get("possession_team", {}).get("id", ""))
            possession = later.get("possession")
            key = event["period"], possession, team
            if possession_team == team and possession != old_possession and key not in counted:
                regained[team] += 1
                counted.add(key)
                break
    return pressures, regained


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
    pressure_total = Counter()
    regain_total = Counter()
    for row in matches:
        name = f"events_{row['match_id']}.json"
        body = (folder / name).read_bytes()
        if hashlib.sha256(body).hexdigest() != manifest["events_sha256"][str(row["match_id"])]:
            raise ValueError(f"Event checksum mismatch: {name}")
        pressures, regains = pressure_regains(json.loads(body))
        pressure_total.update(pressures)
        regain_total.update(regains)
        games.append((row, pressures, regains))
    model = Model()
    prior_regains = Counter()
    prior_games = Counter()
    predictions = []
    for day in sorted({row["match_date"] for row, _, _ in games}):
        current = [game for game in games if game[0]["match_date"] == day]
        pending = []
        for row, pressures, regains in current:
            home = str(row["home_team"]["home_team_id"])
            away = str(row["away_team"]["away_team_id"])
            match = Match("2015-16", date.fromisoformat(day), home, away,
                          row["home_score"], row["away_score"], "statsbomb")
            if prior_games[home] >= 5 and prior_games[away] >= 5:
                feature = prior_regains[home] / prior_games[home] - prior_regains[away] / prior_games[away]
                predictions.append({"date": day, "match_id": row["match_id"], "feature": feature,
                                    "elo": model.predict(match)["elo"],
                                    "outcome": 0 if match.outcome == "H" else 1 if match.outcome == "D" else 2})
            pending.append((match, regains))
        for match, regains in pending:
            model.observe(match)
            for team in (match.home, match.away):
                prior_regains[team] += regains[team]
                prior_games[team] += 1
    train = [row for row in predictions if row["date"] < CUTOFF]
    test = [row for row in predictions if row["date"] >= CUTOFF]
    if len(test) != 190 or len(train) < 100:
        raise ValueError("Insufficient pressure feature train/test coverage")
    tuned = {str(beta): metric(train, beta) for beta in BETAS}
    beta = min(BETAS, key=lambda item: (tuned[str(item)]["log_loss"], abs(item)))
    baseline = metric(test, 0)
    augmented = metric(test, beta)
    by_day = defaultdict(list)
    for row in test:
        outcome = row["outcome"]
        delta = (-math.log(adjusted(row["elo"], row["feature"], beta)[outcome]) +
                 math.log(row["elo"][outcome]))
        by_day[row["date"]].append(delta)
    clusters = list(by_day.values())
    rng = random.Random(20261015)
    bootstrap = []
    for _ in range(2000):
        sample = [clusters[rng.randrange(len(clusters))] for _ in clusters]
        bootstrap.append(sum(sum(group) for group in sample) / sum(len(group) for group in sample))
    bootstrap.sort()
    return {
        "source": "StatsBomb open-data", "commit": SOURCE_COMMIT,
        "feature": "Difference in mean prior-match unique possessions regained within five seconds of a tagged pressure.",
        "event_counts": {"pressures": sum(pressure_total.values()),
                         "unique_pressure_led_regains": sum(regain_total.values())},
        "training": {"period": "Before 2016-01-01", "n": len(train), "beta_grid": BETAS,
                     "selected_beta": beta,
                     "training_log_loss": {key: value["log_loss"] for key, value in tuned.items()}},
        "holdout": {"period": "2016-01-01 through season end", "n": len(test),
                    "score_only_elo": baseline, "elo_plus_pressure_regains": augmented,
                    "log_loss_difference_augmented_minus_elo": augmented["log_loss"] - baseline["log_loss"],
                    "match_date_bootstrap_95_ci": [bootstrap[49], bootstrap[1949]]},
        "limitations": [
            "StatsBomb pressure tags and possession segmentation are provider definitions, not independent video labels.",
            "A possession change after pressure is an association and does not establish sole causation by that pressure.",
            "Event files were published after matches, so historical pre-kickoff availability is unverified.",
            "One older EPL season cannot establish transfer to current UEFA teams.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(".cache/statsbomb_epl_2015"))
    parser.add_argument("--output", type=Path, default=Path("reports/pressure_predict.json"))
    args = parser.parse_args()
    result = report(args.data_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
