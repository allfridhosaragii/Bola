"""Test whether prior high recoveries add held-out 1X2 value to score-only Elo."""

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


BETAS = (-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0)
CUTOFF = "2016-01-01"


def high_recoveries(events: list[dict]) -> Counter[str]:
    seen = set()
    counts: Counter[str] = Counter()
    for event in events:
        if event["period"] not in (1, 2, 3, 4) or event["type"]["name"] != "Ball Recovery":
            continue
        if event.get("ball_recovery", {}).get("recovery_failure") or not event.get("location"):
            continue
        team = str(event["team"]["id"])
        key = event["period"], event["possession"], team
        if key in seen:
            continue
        seen.add(key)
        x = event["location"][0]
        if not 0 <= x <= 120:
            raise ValueError("Recovery coordinate outside StatsBomb pitch")
        counts[team] += int(x >= 60)
    return counts


def adjusted(elo: tuple[float, float, float], feature: float, beta: float) -> tuple[float, float, float]:
    weight = beta * feature / 10
    values = (elo[0] * math.exp(weight), elo[1], elo[2] * math.exp(-weight))
    return tuple(x / sum(values) for x in values)


def metric(rows: list[dict], beta: float) -> dict:
    losses = []
    briers = []
    for row in rows:
        p = adjusted(row["elo"], row["feature"], beta)
        y = row["outcome"]
        losses.append(-math.log(max(1e-12, p[y])))
        briers.append(sum((p[i] - int(i == y)) ** 2 for i in range(3)))
    return {"n": len(rows), "log_loss": sum(losses) / len(losses), "brier": sum(briers) / len(briers)}


def report(folder: Path) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text())
    if manifest["source_commit"] != SOURCE_COMMIT:
        raise ValueError("Unexpected source commit")
    raw = (folder / "matches_2_27.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest["matches_sha256"]:
        raise ValueError("Match metadata checksum mismatch")
    matches = sorted(json.loads(raw), key=lambda row: (row["match_date"], row["match_id"]))
    if len(matches) != 380 or len({row["match_id"] for row in matches}) != 380:
        raise ValueError("Expected complete EPL season")
    if not (matches[189]["match_date"] < CUTOFF <= matches[190]["match_date"]):
        raise ValueError("Historical season does not split 190/190 at cutoff")
    games = []
    for row in matches:
        name = f"events_{row['match_id']}.json"
        body = (folder / name).read_bytes()
        if hashlib.sha256(body).hexdigest() != manifest["events_sha256"][str(row["match_id"])]:
            raise ValueError(f"Event checksum mismatch: {name}")
        events = json.loads(body)
        games.append((row, high_recoveries(events)))
    model = Model()
    recovery_totals: Counter[str] = Counter()
    games_seen: Counter[str] = Counter()
    predictions = []
    for day in sorted({row["match_date"] for row, _ in games}):
        current = [(row, counts) for row, counts in games if row["match_date"] == day]
        pending = []
        for row, counts in current:
            home = str(row["home_team"]["home_team_id"])
            away = str(row["away_team"]["away_team_id"])
            match = Match("2015-16", date.fromisoformat(day), home, away,
                          row["home_score"], row["away_score"], "statsbomb")
            if games_seen[home] >= 5 and games_seen[away] >= 5:
                feature = recovery_totals[home] / games_seen[home] - recovery_totals[away] / games_seen[away]
                predictions.append({"date": day, "match_id": row["match_id"], "feature": feature,
                                    "elo": model.predict(match)["elo"],
                                    "outcome": 0 if match.outcome == "H" else 1 if match.outcome == "D" else 2})
            pending.append((match, counts))
        for match, counts in pending:
            model.observe(match)
            for team in (match.home, match.away):
                recovery_totals[team] += counts[team]
                games_seen[team] += 1
    train = [row for row in predictions if row["date"] < CUTOFF]
    test = [row for row in predictions if row["date"] >= CUTOFF]
    if len(test) != 190 or len(train) < 100:
        raise ValueError("Insufficient chronological train/test predictions")
    trained = {str(beta): metric(train, beta) for beta in BETAS}
    beta = min(BETAS, key=lambda item: (trained[str(item)]["log_loss"], abs(item)))
    baseline = metric(test, 0)
    augmented = metric(test, beta)
    by_day = defaultdict(list)
    for row in test:
        a = -math.log(adjusted(row["elo"], row["feature"], beta)[row["outcome"]])
        b = -math.log(row["elo"][row["outcome"]])
        by_day[row["date"]].append(a - b)
    clusters = list(by_day.values())
    rng = random.Random(20261015)
    replicates = []
    for _ in range(2000):
        selected = [clusters[rng.randrange(len(clusters))] for _ in clusters]
        replicates.append(sum(sum(group) for group in selected) / sum(len(group) for group in selected))
    replicates.sort()
    return {"source": "StatsBomb open-data", "commit": SOURCE_COMMIT,
            "feature": "Difference in mean tagged opponent-half recoveries per prior game; minimum five prior matches per team.",
            "tuning": {"period": "Before 2016-01-01", "n": len(train), "beta_grid": BETAS,
                       "training_log_loss": {key: value["log_loss"] for key, value in trained.items()},
                       "selected_beta": beta},
            "holdout": {"period": "2016-01-01 through season end", "n": len(test),
                        "score_only_elo": baseline, "elo_plus_recoveries": augmented,
                        "log_loss_difference_augmented_minus_elo": augmented["log_loss"] - baseline["log_loss"],
                        "match_date_bootstrap_95_ci": [replicates[49], replicates[1949]]},
            "limitations": ["Event files were published after matches; actual pregame availability is unverified.",
                            "Recovery tags miss other turnovers and do not prove successful pressing.",
                            "One older EPL season is inadequate to validate transfer to UEFA or future seasons.",
                            "A selected coefficient may exploit training noise; interpret the holdout result without causal claims."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(".cache/statsbomb_epl_2015"))
    parser.add_argument("--output", type=Path, default=Path("reports/tactic_predict.json"))
    args = parser.parse_args()
    result = report(args.data_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
