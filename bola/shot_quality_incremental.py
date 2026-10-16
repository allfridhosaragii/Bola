"""Test whether prior npxG adds value beyond prior goal difference."""

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
from .shot_quality_predict import BETAS as XG_BETAS, non_penalty_shots
from .statsbomb import SOURCE_COMMIT
from .tactic_predict import CUTOFF


GOAL_BETAS = (-0.25, -0.1, -0.05, 0.0, 0.05, 0.1, 0.25)


def feature_rows(matches: list[dict], qualities: dict[int, dict[str, dict]]) -> list[dict]:
    """Build same-season rows from five strictly prior matches per team."""
    matches = sorted(matches, key=lambda row: (row["match_date"], row["match_id"]))
    model = Model()
    recent_xg: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=5))
    recent_goals: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=5))
    rows = []
    for day in sorted({row["match_date"] for row in matches}):
        current = [row for row in matches if row["match_date"] == day]
        pending = []
        for row in current:
            home = str(row["home_team"]["home_team_id"])
            away = str(row["away_team"]["away_team_id"])
            season = str(row.get("season", {}).get("season_name", "unknown"))
            match = Match(season, date.fromisoformat(day), home, away,
                          row["home_score"], row["away_score"], "statsbomb")
            if (len(recent_xg[home]) == len(recent_xg[away]) == 5
                    and len(recent_goals[home]) == len(recent_goals[away]) == 5):
                rows.append({
                    "date": day,
                    "match_id": row["match_id"],
                    "xg_feature": sum(recent_xg[home]) / 5 - sum(recent_xg[away]) / 5,
                    "goal_feature": sum(recent_goals[home]) / 5 - sum(recent_goals[away]) / 5,
                    "elo": model.predict(match)["elo"],
                    "outcome": 0 if match.outcome == "H" else 1 if match.outcome == "D" else 2,
                })
            quality = qualities[row["match_id"]]
            home_xg = float(quality.get(home, {}).get("npxg", 0.0))
            away_xg = float(quality.get(away, {}).get("npxg", 0.0))
            pending.append((match, home, away, home_xg - away_xg,
                            float(row["home_score"] - row["away_score"])))
        # Preserve strict chronology for simultaneous or same-date fixtures.
        for match, home, away, xg_difference, goal_difference in pending:
            model.observe(match)
            recent_xg[home].append(xg_difference)
            recent_xg[away].append(-xg_difference)
            recent_goals[home].append(goal_difference)
            recent_goals[away].append(-goal_difference)
    return rows


def probabilities(row: dict, xg_beta: float, goal_beta: float) -> tuple[float, float, float]:
    weight = xg_beta * row["xg_feature"] + goal_beta * row["goal_feature"]
    values = (row["elo"][0] * math.exp(weight), row["elo"][1], row["elo"][2] * math.exp(-weight))
    total = sum(values)
    return tuple(value / total for value in values)


def metric(rows: list[dict], xg_beta: float, goal_beta: float) -> dict:
    losses = []
    briers = []
    for row in rows:
        forecast = probabilities(row, xg_beta, goal_beta)
        outcome = row["outcome"]
        losses.append(-math.log(max(1e-12, forecast[outcome])))
        briers.append(sum((forecast[i] - int(i == outcome)) ** 2 for i in range(3)))
    return {"n": len(rows), "log_loss": sum(losses) / len(losses), "brier": sum(briers) / len(briers)}


def comparison(rows: list[dict], candidate: tuple[float, float], reference: tuple[float, float]) -> dict:
    by_day: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        candidate_loss = -math.log(probabilities(row, *candidate)[row["outcome"]])
        reference_loss = -math.log(probabilities(row, *reference)[row["outcome"]])
        by_day[row["date"]].append(candidate_loss - reference_loss)
    clusters = list(by_day.values())
    rng = random.Random(20261016)
    replicates = []
    for _ in range(2000):
        sampled = [clusters[rng.randrange(len(clusters))] for _ in clusters]
        replicates.append(sum(sum(group) for group in sampled) / sum(len(group) for group in sampled))
    replicates.sort()
    candidate_metric = metric(rows, *candidate)
    reference_metric = metric(rows, *reference)
    return {
        "log_loss_difference_candidate_minus_reference": (
            candidate_metric["log_loss"] - reference_metric["log_loss"]),
        "match_date_bootstrap_95_ci": [replicates[49], replicates[1949]],
    }


def load_epl(folder: Path) -> tuple[list[dict], dict[int, dict[str, dict]], dict]:
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if manifest["source_commit"] != SOURCE_COMMIT:
        raise ValueError("Unexpected EPL source commit")
    raw = (folder / "matches_2_27.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest["matches_sha256"]:
        raise ValueError("EPL match checksum mismatch")
    matches = json.loads(raw)
    qualities = {}
    event_rows = shots = 0
    for row in matches:
        body = (folder / f"events_{row['match_id']}.json").read_bytes()
        if hashlib.sha256(body).hexdigest() != manifest["events_sha256"][str(row["match_id"])]:
            raise ValueError(f"EPL event checksum mismatch: {row['match_id']}")
        events = json.loads(body)
        quality = non_penalty_shots(events)
        qualities[row["match_id"]] = quality
        event_rows += len(events)
        shots += sum(int(value["shots"]) for value in quality.values())
    if len(matches) != 380 or len(qualities) != 380:
        raise ValueError("Expected complete EPL season")
    return matches, qualities, {"matches": 380, "event_rows": event_rows,
                                "non_penalty_shots": shots, "checksums_verified": 381}


def load_wsl(folder: Path) -> tuple[list[list[dict]], list[dict[int, dict[str, dict]]], dict]:
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if manifest["source_commit"] != SOURCE_COMMIT:
        raise ValueError("Unexpected WSL source commit")
    seasons = []
    season_qualities = []
    event_rows = shots = checksums = 0
    ids = set()
    for spec in manifest["seasons"]:
        raw = (folder / f"matches_{spec['competition_id']}_{spec['season_id']}.json").read_bytes()
        if hashlib.sha256(raw).hexdigest() != spec["matches_sha256"]:
            raise ValueError("WSL match checksum mismatch")
        checksums += 1
        matches = json.loads(raw)
        qualities = {}
        for row in matches:
            match_id = row["match_id"]
            if match_id in ids:
                raise ValueError(f"Duplicate WSL match ID: {match_id}")
            ids.add(match_id)
            body = (folder / f"events_{match_id}.json").read_bytes()
            if hashlib.sha256(body).hexdigest() != manifest["events_sha256"][str(match_id)]:
                raise ValueError(f"WSL event checksum mismatch: {match_id}")
            checksums += 1
            events = json.loads(body)
            quality = non_penalty_shots(events)
            qualities[match_id] = quality
            event_rows += len(events)
            shots += sum(int(value["shots"]) for value in quality.values())
        seasons.append(matches)
        season_qualities.append(qualities)
    if len(ids) != 457:
        raise ValueError("Expected 457 WSL matches")
    return seasons, season_qualities, {"matches": 457, "event_rows": event_rows,
                                      "non_penalty_shots": shots, "checksums_verified": checksums}


def report(epl_folder: Path, wsl_folder: Path) -> dict:
    epl_matches, epl_quality, epl_audit = load_epl(epl_folder)
    epl_rows = feature_rows(epl_matches, epl_quality)
    train = [row for row in epl_rows if row["date"] < CUTOFF]
    epl_holdout = [row for row in epl_rows if row["date"] >= CUTOFF]
    if len(train) != 140 or len(epl_holdout) != 190:
        raise ValueError("Unexpected EPL chronological split")

    goal_beta = min(GOAL_BETAS, key=lambda beta: (metric(train, 0.0, beta)["log_loss"], abs(beta)))
    xg_beta = min(XG_BETAS, key=lambda beta: (metric(train, beta, 0.0)["log_loss"], abs(beta)))
    pairs = [(xg, goals) for xg in XG_BETAS for goals in GOAL_BETAS]
    joint = min(pairs, key=lambda pair: (metric(train, *pair)["log_loss"],
                                         abs(pair[0]) + abs(pair[1]), abs(pair[0])))
    models = {
        "score_only_elo": (0.0, 0.0),
        "elo_plus_goals": (0.0, goal_beta),
        "elo_plus_npxg": (xg_beta, 0.0),
        "elo_plus_goals_and_npxg": joint,
    }

    wsl_seasons, wsl_qualities, wsl_audit = load_wsl(wsl_folder)
    wsl_rows = []
    for matches, qualities in zip(wsl_seasons, wsl_qualities):
        wsl_rows.extend(feature_rows(matches, qualities))
    if len(wsl_rows) != 335:
        raise ValueError("Unexpected number of eligible WSL predictions")

    transfer_metrics = {name: metric(wsl_rows, *coefficient) for name, coefficient in models.items()}
    incremental = comparison(wsl_rows, models["elo_plus_goals_and_npxg"], models["elo_plus_goals"])
    xg_vs_goals = comparison(wsl_rows, models["elo_plus_npxg"], models["elo_plus_goals"])
    joint_vs_elo = comparison(wsl_rows, models["elo_plus_goals_and_npxg"], models["score_only_elo"])
    retained = (incremental["log_loss_difference_candidate_minus_reference"] < 0
                and incremental["match_date_bootstrap_95_ci"][1] < 0)
    return {
        "source": "StatsBomb open-data",
        "commit": SOURCE_COMMIT,
        "input_audit": {"epl": epl_audit, "wsl": wsl_audit},
        "protocol": {
            "features": "Home minus away mean team goal difference and non-penalty xG difference over five prior matches.",
            "training": "All coefficients selected on 140 EPL matches before 2016-01-01.",
            "transfer_test": "Coefficients frozen before evaluation on 335 eligible WSL matches; no WSL tuning.",
            "goal_beta_grid": GOAL_BETAS,
            "npxg_beta_grid": XG_BETAS,
            "selected_coefficients": {name: {"npxg_beta": value[0], "goal_beta": value[1]}
                                      for name, value in models.items()},
            "same_date_rule": "All matches on a date are predicted before results or events from that date are observed.",
        },
        "epl_training_metrics": {name: metric(train, *value) for name, value in models.items()},
        "epl_holdout_metrics": {name: metric(epl_holdout, *value) for name, value in models.items()},
        "wsl_transfer_metrics": transfer_metrics,
        "wsl_comparisons": {
            "joint_vs_score_only_elo": joint_vs_elo,
            "npxg_only_vs_goals_only": xg_vs_goals,
            "joint_vs_goals_only_incremental_npxg": incremental,
        },
        "decision": {
            "rule": "npxG adds incremental value only if the frozen joint model beats goals-only and its entire 95% interval is below zero.",
            "incremental_npxg_retained": retained,
            "result": ("Passed: npxG adds transfer value beyond five-match goal difference."
                       if retained else "Rejected: npxG did not prove transfer value beyond five-match goal difference."),
        },
        "limitations": [
            "EPL selected the feature coefficients and WSL supplied the external transfer test; UEFA men's transfer remains untested.",
            "Both datasets use StatsBomb xG, so the result is not independent of the provider model.",
            "Event data are post-match and do not establish real-time pregame feed availability.",
            "Goal difference includes all official goals while the xG feature excludes penalties.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epl-data-dir", type=Path, default=Path(".cache/statsbomb_epl_2015"))
    parser.add_argument("--wsl-data-dir", type=Path, default=Path(".cache/statsbomb_wsl"))
    parser.add_argument("--output", type=Path, default=Path("reports/shot_quality_incremental.json"))
    args = parser.parse_args()
    result = report(args.epl_data_dir, args.wsl_data_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
