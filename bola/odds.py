"""Benchmark chronological Premier League models against historical market odds."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import json
import math
from pathlib import Path

from .backtest import (SEASONS, TEST, bootstrap_logloss_difference, load_matches,
                       metrics, mix, normalize, run_chronological)


FILES = {"2024-25": "2425_E0.csv", "2025-26": "2526_E0.csv"}
ALIASES = {
    "AFC Bournemouth": "Bournemouth", "Brighton & Hove Albion FC": "Brighton",
    "Ipswich Town FC": "Ipswich", "Leicester City FC": "Leicester",
    "Manchester City FC": "Man City", "Manchester United FC": "Man United",
    "Newcastle United FC": "Newcastle", "Nottingham Forest FC": "Nott'm Forest",
    "Tottenham Hotspur FC": "Tottenham", "West Ham United FC": "West Ham",
    "Wolverhampton Wanderers FC": "Wolves", "Leeds United FC": "Leeds",
    "Sunderland AFC": "Sunderland",
}


def market_probs(row: dict, prefix: str) -> tuple[tuple[float, float, float], float]:
    columns = (f"Avg{prefix}H", f"Avg{prefix}D", f"Avg{prefix}A")
    prices = [float(row[key]) for key in columns]
    if any(not math.isfinite(price) or price <= 1 for price in prices):
        raise ValueError(f"Invalid average 1X2 odds: {columns}")
    inverses = [1 / price for price in prices]
    return normalize(inverses), sum(inverses) - 1


def alias(name: str) -> str:
    return ALIASES.get(name, name.removesuffix(" FC"))


def read_odds(data_dir: Path) -> dict[tuple[str, str, str], dict]:
    rows = {}
    for season, filename in FILES.items():
        with (data_dir / filename).open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                if row.get("Div") != "E0":
                    continue
                key = season, row["HomeTeam"], row["AwayTeam"]
                if key in rows:
                    raise ValueError(f"Duplicate market fixture: {key}")
                rows[key] = row
    if len(rows) != 760:
        raise ValueError(f"Expected 760 EPL market rows, found {len(rows)}")
    return rows


def benchmark(scores_dir: Path, odds_dir: Path) -> dict:
    matches, _ = load_matches(scores_dir, seasons=SEASONS)
    records = run_chronological(matches)
    odds = read_odds(odds_dir)
    rows = {name: [] for name in ("market_open", "market_close", "elo", "poisson", "blend")}
    margins = []
    used = set()
    for match, predictions in records:
        if match.season not in TEST:
            continue
        key = match.season, alias(match.home), alias(match.away)
        source = odds.get(key)
        if source is None or key in used:
            raise ValueError(f"Missing or duplicate market match: {key}")
        used.add(key)
        if (datetime.strptime(source["Date"], "%d/%m/%Y").date() != match.day or
                (int(source["FTHG"]), int(source["FTAG"])) != (match.goals_home, match.goals_away)):
            raise ValueError(f"Market date or score disagrees with OpenFootball: {key}")
        open_probs, _ = market_probs(source, "")
        close_probs, margin = market_probs(source, "C")
        margins.append(margin)
        rows["market_open"].append((match, open_probs))
        rows["market_close"].append((match, close_probs))
        rows["elo"].append((match, predictions["elo"]))
        rows["poisson"].append((match, predictions["poisson"]))
        rows["blend"].append((match, mix(predictions["elo"], predictions["poisson"], 0.5)))
    if used != set(odds):
        raise ValueError(f"Unmatched market fixtures: {len(set(odds) - used)}")
    return {
        "market_source": "https://www.football-data.co.uk/englandm.php",
        "market_files": FILES,
        "scores_source": "https://github.com/openfootball/football.json",
        "matched_fixtures": len(used),
        "probability_method": "Normalize reciprocal average bookmaker 1X2 odds by their sum",
        "mean_closing_overround": sum(margins) / len(margins),
        "metrics": {name: metrics(value) for name, value in rows.items()},
        "metrics_by_season": {
            season: {name: metrics([item for item in value if item[0].season == season])
                     for name, value in rows.items()}
            for season in TEST
        },
        "elo_minus_market_close_log_loss": bootstrap_logloss_difference(rows["elo"], rows["market_close"]),
        "blend_minus_market_close_log_loss": bootstrap_logloss_difference(rows["blend"], rows["market_close"]),
        "limitations": [
            "Football-Data lists opening and closing average odds but does not supply per-quote publication timestamps in these CSV files.",
            "Closing odds may reflect information unavailable to the results-only model at its date-level cutoff; this is a benchmark, not a trading backtest.",
            "Market probabilities remove aggregate overround and cannot be treated as guaranteed fair prices.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scores-dir", type=Path, default=Path(".cache/openfootball"))
    parser.add_argument("--odds-dir", type=Path, default=Path(".cache/odds"))
    parser.add_argument("--output", type=Path, default=Path("reports/odds_benchmark.json"))
    args = parser.parse_args()
    result = benchmark(args.scores_dir, args.odds_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
