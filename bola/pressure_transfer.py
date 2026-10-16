"""Train pressure-regain form on early WSL seasons and test 2023/24."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import random

from .backtest import Match, Model
from .pressure_predict import pressure_regains
from .statsbomb import SOURCE_COMMIT
from .tactic_predict import BETAS, adjusted, metric


HOLDOUT_SEASON = "2023/2024"


def season_predictions(matches: list[dict], regains: dict[int, Counter[str]]) -> list[dict]:
    """Create predictions from exactly five earlier same-season matches."""
    matches = sorted(matches, key=lambda row: (row["match_date"], row["match_id"]))
    model = Model()
    recent: dict[str, deque[int]] = defaultdict(lambda: deque(maxlen=5))
    predictions = []
    for day in sorted({row["match_date"] for row in matches}):
        current = [row for row in matches if row["match_date"] == day]
        pending = []
        for row in current:
            home = str(row["home_team"]["home_team_id"])
            away = str(row["away_team"]["away_team_id"])
            match = Match(str(row["season"]["season_name"]), date.fromisoformat(day), home, away,
                          row["home_score"], row["away_score"], "statsbomb")
            if len(recent[home]) == len(recent[away]) == 5:
                predictions.append({
                    "date": day,
                    "match_id": row["match_id"],
                    "feature": sum(recent[home]) / 5 - sum(recent[away]) / 5,
                    "elo": model.predict(match)["elo"],
                    "outcome": 0 if match.outcome == "H" else 1 if match.outcome == "D" else 2,
                })
            pending.append((match, regains[row["match_id"]]))
        # Same-date events and results are not visible to other predictions that day.
        for match, counts in pending:
            model.observe(match)
            recent[match.home].append(counts[match.home])
            recent[match.away].append(counts[match.away])
    return predictions


def report(folder: Path) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if manifest["source_commit"] != SOURCE_COMMIT:
        raise ValueError("Unexpected StatsBomb source commit")
    training_rows = []
    holdout_rows = []
    season_reports = []
    total_pressures: Counter[str] = Counter()
    total_regains: Counter[str] = Counter()
    event_rows = checksums = 0
    match_ids = set()
    for spec in manifest["seasons"]:
        path = folder / f"matches_{spec['competition_id']}_{spec['season_id']}.json"
        body = path.read_bytes()
        if hashlib.sha256(body).hexdigest() != spec["matches_sha256"]:
            raise ValueError(f"Match metadata checksum mismatch: {path.name}")
        checksums += 1
        matches = json.loads(body)
        season_name = matches[0]["season"]["season_name"]
        regains = {}
        season_pressures = Counter()
        season_regains = Counter()
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
            pressures, match_regains = pressure_regains(events)
            regains[match_id] = match_regains
            season_pressures.update(pressures)
            season_regains.update(match_regains)
        rows = season_predictions(matches, regains)
        destination = holdout_rows if season_name == HOLDOUT_SEASON else training_rows
        destination.extend(rows)
        total_pressures.update(season_pressures)
        total_regains.update(season_regains)
        season_reports.append({
            "season": season_name,
            "matches": len(matches),
            "eligible_predictions": len(rows),
            "pressure_events": sum(season_pressures.values()),
            "unique_pressure_led_regains": sum(season_regains.values()),
        })
    if len(match_ids) != 457 or len(training_rows) != 233 or len(holdout_rows) != 102:
        raise ValueError("Unexpected WSL pressure coverage")

    trained = {str(beta): metric(training_rows, beta) for beta in BETAS}
    beta = min(BETAS, key=lambda item: (trained[str(item)]["log_loss"], abs(item)))
    baseline = metric(holdout_rows, 0.0)
    augmented = metric(holdout_rows, beta)
    by_day: dict[str, list[float]] = defaultdict(list)
    for row in holdout_rows:
        outcome = row["outcome"]
        by_day[row["date"]].append(
            -math.log(adjusted(row["elo"], row["feature"], beta)[outcome])
            + math.log(row["elo"][outcome]))
    clusters = list(by_day.values())
    rng = random.Random(20261016)
    bootstrap = []
    for _ in range(2000):
        sample = [clusters[rng.randrange(len(clusters))] for _ in clusters]
        bootstrap.append(sum(sum(group) for group in sample) / sum(len(group) for group in sample))
    bootstrap.sort()
    difference = augmented["log_loss"] - baseline["log_loss"]
    retained = beta != 0 and difference < 0 and bootstrap[1949] < 0
    return {
        "source": "StatsBomb open-data",
        "commit": SOURCE_COMMIT,
        "input_audit": {
            "matches": len(match_ids),
            "event_rows": event_rows,
            "pressure_events": sum(total_pressures.values()),
            "unique_pressure_led_regains": sum(total_regains.values()),
            "checksums_verified": checksums,
        },
        "protocol": {
            "feature": "Home minus away mean unique pressure-led regains over exactly five prior same-season matches.",
            "training_seasons": [row["season"] for row in season_reports if row["season"] != HOLDOUT_SEASON],
            "holdout_season": HOLDOUT_SEASON,
            "beta_grid": BETAS,
            "same_date_rule": "All matches on a date are predicted before events or results from that date are observed.",
            "epl_reference_selected_beta": 0.0,
        },
        "by_season": season_reports,
        "training": {
            "n": len(training_rows),
            "selected_beta": beta,
            "training_log_loss": {key: value["log_loss"] for key, value in trained.items()},
        },
        "holdout": {
            "n": len(holdout_rows),
            "score_only_elo": baseline,
            "elo_plus_pressure_regains": augmented,
            "log_loss_difference_augmented_minus_elo": difference,
            "match_date_bootstrap_95_ci": [bootstrap[49], bootstrap[1949]],
        },
        "decision": {
            "rule": "Retain only if training selects a nonzero coefficient and holdout improvement has an interval fully below zero.",
            "retained": retained,
            "result": ("Retained for further transfer review."
                       if retained else "Rejected: pressure-led regains did not pass the WSL holdout gate."),
        },
        "limitations": [
            "Pressure and possession labels are StatsBomb definitions rather than independent video annotations.",
            "A possession change within five seconds is associated with pressure but does not prove causation.",
            "The 2023/24 holdout is one season from one competition and has already been used for other feature audits.",
            "Event files are post-match data and do not establish pregame feed availability for UEFA targets.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(".cache/statsbomb_wsl"))
    parser.add_argument("--output", type=Path, default=Path("reports/pressure_transfer.json"))
    args = parser.parse_args()
    result = report(args.data_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
