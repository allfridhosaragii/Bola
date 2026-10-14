"""Strict market benchmark for Bundesliga and Eredivisie holdout matches."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import json
from pathlib import Path

from .backtest import (SEASONS, bootstrap_logloss_difference, load_matches,
                       metrics, mix, run_chronological)
from .odds import market_probs


CONFIG = {
    "de.1": {"division": "D1", "seasons": ("2024-25", "2025-26"),
             "files": {"2024-25": "2425_D1.csv", "2025-26": "2526_D1.csv"},
             "aliases": {
                 "1. FC Heidenheim 1846": "Heidenheim", "1. FC Köln": "FC Koln",
                 "1. FC Union Berlin": "Union Berlin", "1. FSV Mainz 05": "Mainz",
                 "Bayer 04 Leverkusen": "Leverkusen", "Borussia Dortmund": "Dortmund",
                 "Borussia Mönchengladbach": "M'gladbach", "Eintracht Frankfurt": "Ein Frankfurt",
                 "FC Augsburg": "Augsburg", "FC Bayern München": "Bayern Munich",
                 "FC St. Pauli 1910": "St Pauli", "Hamburger SV": "Hamburg",
                 "Holstein Kiel": "Holstein Kiel", "RB Leipzig": "RB Leipzig",
                 "SC Freiburg": "Freiburg", "SV Werder Bremen": "Werder Bremen",
                 "TSG 1899 Hoffenheim": "Hoffenheim", "VfB Stuttgart": "Stuttgart",
                 "VfL Bochum 1848": "Bochum", "VfL Wolfsburg": "Wolfsburg"}},
    "nl.1": {"division": "N1", "seasons": ("2024-25",),
             "files": {"2024-25": "2425_N1.csv"},
             "aliases": {
                 "AFC Ajax": "Ajax", "AZ": "AZ Alkmaar", "Almere City FC": "Almere City",
                 "FC Groningen": "Groningen", "FC Twente '65": "Twente",
                 "FC Utrecht": "Utrecht", "Feyenoord Rotterdam": "Feyenoord",
                 "Fortuna Sittard": "For Sittard", "Go Ahead Eagles": "Go Ahead Eagles",
                 "Heracles Almelo": "Heracles", "NAC Breda": "NAC Breda",
                 "NEC": "Nijmegen", "PEC Zwolle": "Zwolle", "PSV": "PSV Eindhoven",
                 "RKC Waalwijk": "Waalwijk", "SC Heerenveen": "Heerenveen",
                 "Sparta Rotterdam": "Sparta Rotterdam", "Willem II Tilburg": "Willem II"}},
}


def benchmark(scores_dir: Path, odds_dir: Path, league: str) -> dict:
    config = CONFIG[league]
    selected_seasons = SEASONS[:SEASONS.index(config["seasons"][-1]) + 1]
    matches, _ = load_matches(scores_dir, seasons=selected_seasons, league=league)
    records = run_chronological(matches)
    odds = {}
    for season, filename in config["files"].items():
        with (odds_dir / filename).open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                if row.get("Div") != config["division"]:
                    raise ValueError(f"Wrong market division in {filename}")
                key = season, row["HomeTeam"], row["AwayTeam"]
                if key in odds:
                    raise ValueError(f"Duplicate market fixture: {key}")
                odds[key] = row
    expected = 306 * len(config["seasons"])
    if len(odds) != expected:
        raise ValueError(f"Expected {expected} market rows, found {len(odds)}")
    rows = {name: [] for name in ("market_open", "market_close", "elo", "poisson", "blend")}
    used = set()
    for match, prediction in records:
        if match.season not in config["seasons"]:
            continue
        key = (match.season, config["aliases"][match.home], config["aliases"][match.away])
        source = odds.get(key)
        if source is None or key in used:
            raise ValueError(f"Missing or duplicated market fixture: {key}")
        used.add(key)
        if (datetime.strptime(source["Date"], "%d/%m/%Y").date() != match.day or
                (int(source["FTHG"]), int(source["FTAG"])) != (match.goals_home, match.goals_away)):
            raise ValueError(f"Market date or score disagrees with OpenFootball: {key}")
        rows["market_open"].append((match, market_probs(source, "")[0]))
        rows["market_close"].append((match, market_probs(source, "C")[0]))
        rows["elo"].append((match, prediction["elo"]))
        rows["poisson"].append((match, prediction["poisson"]))
        rows["blend"].append((match, mix(prediction["elo"], prediction["poisson"], 0.5)))
    if used != set(odds):
        raise ValueError(f"Unmatched market rows: {len(set(odds) - used)}")
    return {"market_source": "https://www.football-data.co.uk/", "division": config["division"],
            "market_files": config["files"], "matched_fixtures": len(used),
            "metrics": {name: metrics(values) for name, values in rows.items()},
            "metrics_by_season": {season: {name: metrics([item for item in values if item[0].season == season])
                                           for name, values in rows.items()}
                                  for season in config["seasons"]},
            "elo_minus_market_close_log_loss": bootstrap_logloss_difference(rows["elo"], rows["market_close"]),
            "blend_minus_market_close_log_loss": bootstrap_logloss_difference(rows["blend"], rows["market_close"]),
            "limitations": ["Average opening and closing odds lack per-quote publication timestamps.",
                            "Closing market data may include information the date-level model could not use.",
                            "The Bundesliga model was revised after inspection of Bundesliga results; its comparison is exploratory."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", choices=CONFIG, required=True)
    parser.add_argument("--scores-dir", type=Path, default=Path(".cache/openfootball"))
    parser.add_argument("--odds-dir", type=Path, default=Path(".cache/odds"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = benchmark(args.scores_dir, args.odds_dir, args.league)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
