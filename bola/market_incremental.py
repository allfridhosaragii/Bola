"""Test whether the internal model adds value beyond opening market probabilities."""

from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import json
import math
from pathlib import Path
import random

from .backtest import (Match, OUTCOMES, PINNED_DATA_COMMIT, SEASONS,
                       data_commit, load_matches, metrics, mix, run_chronological)
from .odds import alias, market_probs, read_odds
from .odds_multi import CONFIG


TRAIN_SEASON = "2024-25"
HOLDOUT_SEASON = "2025-26"
LEAGUES = ("en.1", "de.1", "nl.1")
MODEL_WEIGHTS = (0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0)
EXPECTED_SHA256 = {
    "2425_E0.csv": "d0c8ce4a96d886cf60cf101f570f4a3893844226f91c7bd769eb568c49edbfa4",
    "2526_E0.csv": "3e3a8352f9ada6789c508d6ca184424421fed56a30400904a4a327c583407e62",
    "2425_D1.csv": "a295c58033cfe6393cbbc28f7db85671839b960c5f1153fd3678e20ad2adb92e",
    "2526_D1.csv": "618301a4b39918225a8ccc57f0f839d675e1abd92fa3a3ccd9a67acd7c79dd7f",
    "2425_N1.csv": "7f97f0a7fd1f9b2cff6ac09588cdc14fd07f19950cb75e821fa58ab41e541d0a",
}


@dataclass(frozen=True)
class MarketRecord:
    league: str
    match: Match
    market_open: tuple[float, float, float]
    market_close: tuple[float, float, float]
    internal_model: tuple[float, float, float]


def verify_market_files(odds_dir: Path) -> dict[str, str]:
    observed = {}
    for filename, expected in EXPECTED_SHA256.items():
        digest = hashlib.sha256((odds_dir / filename).read_bytes()).hexdigest()
        if digest != expected:
            raise ValueError(f"Market checksum mismatch: {filename}")
        observed[filename] = digest
    return observed


def _multi_odds(odds_dir: Path, league: str) -> dict[tuple[str, str, str], dict]:
    config = CONFIG[league]
    rows = {}
    for season, filename in config["files"].items():
        with (odds_dir / filename).open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                if row.get("Div") != config["division"]:
                    raise ValueError(f"Wrong market division in {filename}")
                key = season, row["HomeTeam"], row["AwayTeam"]
                if key in rows:
                    raise ValueError(f"Duplicate market fixture: {key}")
                rows[key] = row
    return rows


def load_market_records(scores_dir: Path, odds_dir: Path, league: str) -> list[MarketRecord]:
    if league not in LEAGUES:
        raise ValueError(f"Unsupported league: {league}")
    if league == "en.1":
        odds = read_odds(odds_dir)
        market_seasons = (TRAIN_SEASON, HOLDOUT_SEASON)
        team_name = alias
    else:
        config = CONFIG[league]
        odds = _multi_odds(odds_dir, league)
        market_seasons = tuple(config["files"])
        team_name = config["aliases"].__getitem__
    last_season = market_seasons[-1]
    source_seasons = SEASONS[:SEASONS.index(last_season) + 1]
    matches, _ = load_matches(scores_dir, seasons=source_seasons, league=league)
    records = []
    used = set()
    for match, predictions in run_chronological(matches):
        if match.season not in market_seasons:
            continue
        key = match.season, team_name(match.home), team_name(match.away)
        source = odds.get(key)
        if source is None or key in used:
            raise ValueError(f"Missing or duplicate market match: {key}")
        used.add(key)
        source_day = datetime.strptime(source["Date"], "%d/%m/%Y").date()
        source_score = int(source["FTHG"]), int(source["FTAG"])
        if source_day != match.day or source_score != (match.goals_home, match.goals_away):
            raise ValueError(f"Market date or score disagrees with results: {key}")
        records.append(MarketRecord(
            league=league,
            match=match,
            market_open=market_probs(source, "")[0],
            market_close=market_probs(source, "C")[0],
            internal_model=mix(predictions["elo"], predictions["poisson"], 0.5),
        ))
    if used != set(odds):
        raise ValueError(f"Unmatched market fixtures for {league}: {len(set(odds) - used)}")
    return records


def model_market_mix(row: MarketRecord, model_weight: float) -> tuple[float, float, float]:
    if not 0 <= model_weight <= 1:
        raise ValueError("Model weight must be between zero and one")
    if model_weight == 0:
        return row.market_open
    if model_weight == 1:
        return row.internal_model
    return mix(row.internal_model, row.market_open, model_weight)


def score(records: list[MarketRecord], model_weight: float) -> dict:
    return metrics([(row.match, model_market_mix(row, model_weight)) for row in records])


def paired_block_difference(records: list[MarketRecord], model_weight: float,
                            repetitions: int = 10000, seed: int = 20261016) -> dict:
    """Bootstrap candidate minus opening-market log loss by league and date."""
    if not records or repetitions < 100:
        raise ValueError("Paired bootstrap needs records and at least 100 repetitions")
    blocks: dict[tuple[str, date], list[float]] = defaultdict(list)
    for row in records:
        outcome = OUTCOMES.index(row.match.outcome)
        candidate = model_market_mix(row, model_weight)
        delta = -math.log(candidate[outcome]) + math.log(row.market_open[outcome])
        blocks[(row.league, row.match.day)].append(delta)
    groups = list(blocks.values())
    difference = sum(map(sum, groups)) / sum(map(len, groups))
    rng = random.Random(seed)
    samples = []
    for _ in range(repetitions):
        selected = [groups[rng.randrange(len(groups))] for _ in groups]
        samples.append(sum(map(sum, selected)) / sum(map(len, selected)))
    samples.sort()
    return {
        "difference_candidate_minus_market_open": difference,
        "league_date_blocks": len(groups),
        "ci95": [samples[int(0.025 * repetitions)], samples[int(0.975 * repetitions) - 1]],
    }


def report(scores_dir: Path, odds_dir: Path) -> dict:
    results_commit = data_commit(scores_dir)
    if results_commit != PINNED_DATA_COMMIT:
        raise ValueError(f"Unexpected OpenFootball commit: {results_commit}")
    checksums = verify_market_files(odds_dir)
    records = [row for league in LEAGUES for row in load_market_records(scores_dir, odds_dir, league)]
    training = [row for row in records if row.match.season == TRAIN_SEASON]
    holdout = [row for row in records if row.match.season == HOLDOUT_SEASON]
    if len(training) != 992 or len(holdout) != 686:
        raise ValueError(f"Unexpected train/holdout counts: {len(training)}/{len(holdout)}")
    training_grid = {str(weight): score(training, weight)["log_loss"] for weight in MODEL_WEIGHTS}
    selected_weight = min(MODEL_WEIGHTS, key=lambda value: (training_grid[str(value)], value))
    holdout_grid = {str(weight): score(holdout, weight)["log_loss"] for weight in MODEL_WEIGHTS}
    comparison = paired_block_difference(holdout, selected_weight)
    retained = selected_weight > 0 and comparison["ci95"][1] < 0

    def direct_metrics(rows: list[MarketRecord], attribute: str) -> dict:
        return metrics([(row.match, getattr(row, attribute)) for row in rows])

    by_league = {}
    for league in ("en.1", "de.1"):
        subset = [row for row in holdout if row.league == league]
        by_league[league] = {
            "matches": len(subset),
            "market_open_log_loss": direct_metrics(subset, "market_open")["log_loss"],
            "selected_mix_log_loss": score(subset, selected_weight)["log_loss"],
            "internal_model_log_loss": direct_metrics(subset, "internal_model")["log_loss"],
        }
    return {
        "source": {
            "market": "Football-Data average bookmaker 1X2 odds",
            "results": "OpenFootball football.json",
            "results_commit": results_commit,
            "market_file_sha256": checksums,
        },
        "protocol": {
            "internal_model": "Fixed 0.5 Elo and 0.5 Poisson blend using prior results only.",
            "candidate": "Linear pool of the internal model and normalized average opening market probabilities.",
            "model_weight_grid": MODEL_WEIGHTS,
            "selection_season": TRAIN_SEASON,
            "holdout_season": HOLDOUT_SEASON,
            "selection_leagues": LEAGUES,
            "holdout_leagues": ("en.1", "de.1"),
            "deployment_rule": "Retain only if training selects a positive model weight and the holdout paired 95% interval is wholly below zero.",
        },
        "sample": {
            "total_matches": len(records),
            "selection_matches": len(training),
            "holdout_matches": len(holdout),
            "selection_by_league": {league: sum(row.league == league for row in training) for league in LEAGUES},
            "holdout_by_league": {league: sum(row.league == league for row in holdout) for league in ("en.1", "de.1")},
        },
        "selection": {
            "log_loss_by_model_weight": training_grid,
            "selected_model_weight": selected_weight,
        },
        "holdout": {
            "log_loss_by_model_weight": holdout_grid,
            "market_open": direct_metrics(holdout, "market_open"),
            "market_close": direct_metrics(holdout, "market_close"),
            "internal_model": direct_metrics(holdout, "internal_model"),
            "selected_mix": score(holdout, selected_weight),
            "selected_mix_minus_market_open": comparison,
            "by_league": by_league,
        },
        "decision": {
            "retained": retained,
            "result": ("Internal model retained as an addition to opening market probabilities."
                       if retained else "Rejected: the internal model did not add validated information to opening market probabilities."),
        },
        "limitations": [
            "These seasons were already inspected in earlier model development and benchmarks; this is retrospective reuse, not an untouched holdout.",
            "Football-Data labels average opening and closing odds but does not provide a timestamp for each quote.",
            "The experiment is a historical information benchmark, not evidence that a quoted price was available to this system before kickoff.",
            "The holdout covers two men's domestic leagues and does not establish incremental value in UEFA competition.",
            "Closing odds are reported only as a benchmark and are never used to select the model weight.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scores-dir", type=Path, default=Path(".cache/openfootball"))
    parser.add_argument("--odds-dir", type=Path, default=Path(".cache/odds"))
    parser.add_argument("--output", type=Path, default=Path("reports/market_incremental.json"))
    args = parser.parse_args()
    result = report(args.scores_dir, args.odds_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
