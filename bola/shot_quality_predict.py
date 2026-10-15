"""Test whether prior five-match non-penalty xG adds held-out 1X2 value."""

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
from .statsbomb import SOURCE_COMMIT
from .tactic_predict import CUTOFF


BETAS = (-1.0, -0.5, -0.25, 0.0, 0.25, 0.5, 1.0)


def non_penalty_shots(events: list[dict]) -> dict[str, dict[str, float | int]]:
    """Return non-penalty shot count and StatsBomb xG by team."""
    result: dict[str, dict[str, float | int]] = defaultdict(lambda: {"shots": 0, "npxg": 0.0})
    for event in events:
        if event.get("period") not in (1, 2, 3, 4) or event.get("type", {}).get("name") != "Shot":
            continue
        shot = event.get("shot", {})
        xg = shot.get("statsbomb_xg")
        if not isinstance(xg, (int, float)) or isinstance(xg, bool) or not math.isfinite(xg) or not 0 <= xg <= 1:
            raise ValueError(f"Shot lacks valid xG: {event.get('id', '<unknown>')}")
        if shot.get("type", {}).get("name") == "Penalty":
            continue
        team = str(event["team"]["id"])
        result[team]["shots"] += 1
        result[team]["npxg"] += xg
    return dict(result)


def adjusted(elo: tuple[float, float, float], feature: float, beta: float) -> tuple[float, float, float]:
    """Shift win/loss log weights using a prior-match xG-difference feature."""
    weight = beta * feature
    values = (elo[0] * math.exp(weight), elo[1], elo[2] * math.exp(-weight))
    total = sum(values)
    return tuple(value / total for value in values)


def metric(rows: list[dict], beta: float) -> dict:
    losses = []
    briers = []
    for row in rows:
        probabilities = adjusted(row["elo"], row["feature"], beta)
        outcome = row["outcome"]
        losses.append(-math.log(max(1e-12, probabilities[outcome])))
        briers.append(sum((probabilities[i] - int(i == outcome)) ** 2 for i in range(3)))
    return {"n": len(rows), "log_loss": sum(losses) / len(losses), "brier": sum(briers) / len(briers)}


def report(folder: Path) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
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
    total_event_rows = 0
    total_non_penalty_shots = 0
    total_non_penalty_xg = 0.0
    for row in matches:
        name = f"events_{row['match_id']}.json"
        body = (folder / name).read_bytes()
        if hashlib.sha256(body).hexdigest() != manifest["events_sha256"][str(row["match_id"])]:
            raise ValueError(f"Event checksum mismatch: {name}")
        events = json.loads(body)
        quality = non_penalty_shots(events)
        total_event_rows += len(events)
        total_non_penalty_shots += sum(int(value["shots"]) for value in quality.values())
        total_non_penalty_xg += sum(float(value["npxg"]) for value in quality.values())
        games.append((row, quality))

    model = Model()
    recent: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=5))
    predictions = []
    for day in sorted({row["match_date"] for row, _ in games}):
        current = [(row, quality) for row, quality in games if row["match_date"] == day]
        pending = []
        for row, quality in current:
            home = str(row["home_team"]["home_team_id"])
            away = str(row["away_team"]["away_team_id"])
            match = Match("2015-16", date.fromisoformat(day), home, away,
                          row["home_score"], row["away_score"], "statsbomb")
            if len(recent[home]) == 5 and len(recent[away]) == 5:
                home_mean = sum(recent[home]) / 5
                away_mean = sum(recent[away]) / 5
                predictions.append({"date": day, "match_id": row["match_id"],
                                    "feature": home_mean - away_mean,
                                    "home_prior_five_npxg_difference": home_mean,
                                    "away_prior_five_npxg_difference": away_mean,
                                    "elo": model.predict(match)["elo"],
                                    "outcome": 0 if match.outcome == "H" else 1 if match.outcome == "D" else 2})
            home_npxg = float(quality.get(home, {}).get("npxg", 0.0))
            away_npxg = float(quality.get(away, {}).get("npxg", 0.0))
            pending.append((match, home, away, home_npxg - away_npxg))
        # All games on a date are predicted before any result or xG from that date is observed.
        for match, home, away, difference in pending:
            model.observe(match)
            recent[home].append(difference)
            recent[away].append(-difference)

    train = [row for row in predictions if row["date"] < CUTOFF]
    test = [row for row in predictions if row["date"] >= CUTOFF]
    if len(test) != 190 or len(train) < 100:
        raise ValueError("Insufficient chronological train/test predictions")
    trained = {str(beta): metric(train, beta) for beta in BETAS}
    beta = min(BETAS, key=lambda item: (trained[str(item)]["log_loss"], abs(item)))
    baseline = metric(test, 0.0)
    augmented = metric(test, beta)

    by_day: dict[str, list[float]] = defaultdict(list)
    for row in test:
        augmented_loss = -math.log(adjusted(row["elo"], row["feature"], beta)[row["outcome"]])
        baseline_loss = -math.log(row["elo"][row["outcome"]])
        by_day[row["date"]].append(augmented_loss - baseline_loss)
    clusters = list(by_day.values())
    rng = random.Random(20261015)
    replicates = []
    for _ in range(2000):
        selected = [clusters[rng.randrange(len(clusters))] for _ in clusters]
        replicates.append(sum(sum(group) for group in selected) / sum(len(group) for group in selected))
    replicates.sort()

    return {
        "source": "StatsBomb open-data",
        "commit": SOURCE_COMMIT,
        "input_audit": {
            "matches": len(matches),
            "event_rows": total_event_rows,
            "non_penalty_shots": total_non_penalty_shots,
            "non_penalty_xg": round(total_non_penalty_xg, 6),
            "checksums_verified": len(matches) + 1,
        },
        "feature": "Home minus away mean non-penalty xG difference over exactly five prior matches.",
        "chronology": "All matches on the same date are predicted before any result or event from that date is observed.",
        "tuning": {
            "period": "Before 2016-01-01",
            "n": len(train),
            "beta_grid": BETAS,
            "training_log_loss": {key: value["log_loss"] for key, value in trained.items()},
            "selected_beta": beta,
        },
        "holdout": {
            "period": "2016-01-01 through season end",
            "n": len(test),
            "score_only_elo": baseline,
            "elo_plus_prior_five_npxg": augmented,
            "log_loss_difference_augmented_minus_elo": augmented["log_loss"] - baseline["log_loss"],
            "match_date_bootstrap_95_ci": [replicates[49], replicates[1949]],
        },
        "decision": {
            "rule": "Retain only if holdout log loss improves and the entire bootstrap interval is below zero.",
            "retained": augmented["log_loss"] < baseline["log_loss"] and replicates[1949] < 0,
            "result": ("Retained: the prespecified holdout and uncertainty rule passed."
                       if augmented["log_loss"] < baseline["log_loss"] and replicates[1949] < 0
                       else "Rejected: the 95% interval includes zero, so the feature is not added to the UEFA model."),
        },
        "limitations": [
            "StatsBomb xG is a provider model whose training history is not independently known here.",
            "Event files were published after matches; actual pregame availability is unverified.",
            "A single older EPL season is inadequate to establish transfer to UEFA or future seasons.",
            "The feature summarizes shot quality and does not identify tactics, injuries, or player availability.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(".cache/statsbomb_epl_2015"))
    parser.add_argument("--output", type=Path, default=Path("reports/shot_quality_predict.json"))
    args = parser.parse_args()
    result = report(args.data_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
