"""Time-censored domestic form summaries for teams on the UEFA candidate list."""

from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from datetime import date, datetime
import hashlib
import json
from pathlib import Path


TEAMS = {
    "Feyenoord": ("N1", "Feyenoord"), "Como": ("I1", "Como"),
    "Liverpool": ("E0", "Liverpool"), "Real Betis": ("SP1", "Betis"),
    "Porto": ("P1", "Porto"), "Roma": ("I1", "Roma"),
    "Real Madrid": ("SP1", "Real Madrid"), "Stuttgart": ("D1", "Stuttgart"),
    "Aston Villa": ("E0", "Aston Villa"), "Man City": ("E0", "Man City"),
    "Paris": ("F1", "Paris SG"), "B. Dortmund": ("D1", "Dortmund"),
    "Fenerbahçe": ("T1", "Fenerbahce"), "AEK Athens": ("G1", "AEK"),
}
UNSUPPORTED = ("LASK", "Shakhtar", "S. Bratislava", "Bodø/Glimt")
SEASONS = ("2526", "2627")
FIELDS = ("goals_for", "goals_against", "shots_for", "shots_against", "shots_on_target_for",
          "shots_on_target_against", "corners_for", "corners_against", "yellow_for", "yellow_against",
          "red_for", "red_against", "first_half_goals_for", "first_half_goals_against",
          "second_half_goals_for", "second_half_goals_against", "xg_for", "xg_against",
          "elo_result_surplus")


def read_league(data_dir: Path, manifest: dict, league: str, cutoff: date) -> list[dict]:
    matches = []
    seen = set()
    for season in SEASONS:
        filename = f"{season}_{league}.csv"
        body = (data_dir / filename).read_bytes()
        if hashlib.sha256(body).hexdigest() != manifest["files"][filename]["sha256"]:
            raise ValueError(f"Snapshot checksum mismatch: {filename}")
        for row in csv.DictReader(body.decode("utf-8-sig").splitlines()):
            if row.get("Div") != league or not row.get("FTHG") or not row.get("FTAG"):
                continue
            day = datetime.strptime(row["Date"], "%d/%m/%Y").date()
            if day >= cutoff:
                continue
            key = season, day, row["HomeTeam"], row["AwayTeam"]
            if key in seen:
                raise ValueError(f"Duplicate domestic fixture: {key}")
            seen.add(key)
            row["_day"] = day
            row["_season"] = season
            matches.append(row)
    return sorted(matches, key=lambda r: (r["_day"], r["HomeTeam"], r["AwayTeam"]))


def number(row: dict, field: str) -> int | None:
    value = row.get(field)
    return int(value) if value not in (None, "") else None


def decimal(row: dict, field: str) -> float | None:
    value = row.get(field)
    return float(value) if value not in (None, "") else None


def team_rows(matches: list[dict]) -> dict[str, list[dict]]:
    ratings = defaultdict(lambda: 1500.0)
    by_team = defaultdict(list)
    for day in sorted({row["_day"] for row in matches}):
        games = [row for row in matches if row["_day"] == day]
        updates = []
        for row in games:
            home, away = row["HomeTeam"], row["AwayTeam"]
            goals_home, goals_away = int(row["FTHG"]), int(row["FTAG"])
            expected_home = 1 / (1 + 10 ** (-(ratings[home] + 65 - ratings[away]) / 400))
            actual_home = 1 if goals_home > goals_away else 0 if goals_home < goals_away else 0.5
            updates.append((home, away, 20 * (actual_home - expected_home)))
            for team, opponent, is_home in ((home, away, True), (away, home, False)):
                prefix, other = ("H", "A") if is_home else ("A", "H")
                gf, ga = (goals_home, goals_away) if is_home else (goals_away, goals_home)
                # Football-Data half-time columns are HTHG and HTAG.
                htg = number(row, "HTHG" if is_home else "HTAG")
                hta = number(row, "HTAG" if is_home else "HTHG")
                expected = expected_home if is_home else 1 - expected_home
                actual = actual_home if is_home else 1 - actual_home
                by_team[team].append({
                    "date": row["_day"].isoformat(), "season": row["_season"],
                    "venue": "home" if is_home else "away", "opponent": opponent,
                    "result": "W" if gf > ga else "L" if gf < ga else "D",
                    "opponent_elo_before": round(ratings[opponent], 1),
                    "goals_for": gf, "goals_against": ga,
                    "shots_for": number(row, prefix + "S"), "shots_against": number(row, other + "S"),
                    "shots_on_target_for": number(row, prefix + "ST"),
                    "shots_on_target_against": number(row, other + "ST"),
                    "corners_for": number(row, prefix + "C"), "corners_against": number(row, other + "C"),
                    "yellow_for": number(row, prefix + "Y"), "yellow_against": number(row, other + "Y"),
                    "red_for": number(row, prefix + "R"), "red_against": number(row, other + "R"),
                    "first_half_goals_for": htg, "first_half_goals_against": hta,
                    "second_half_goals_for": gf - htg if htg is not None else None,
                    "second_half_goals_against": ga - hta if hta is not None else None,
                    "xg_for": decimal(row, "HxG" if is_home else "AxG"),
                    "xg_against": decimal(row, "AxG" if is_home else "HxG"),
                    "elo_result_surplus": round(actual - expected, 4),
                })
        for home, away, change in updates:
            ratings[home] += change
            ratings[away] -= change
    return by_team


def summarize_window(rows: list[dict], n: int) -> dict:
    current = rows[-n:]
    if len(current) < n:
        raise ValueError(f"Need {n} completed games, found {len(current)}")
    weights = [0.5 ** (age / 5) for age in range(n - 1, -1, -1)]
    metrics = {}
    for field in FIELDS:
        available = [(row.get(field), weight) for row, weight in zip(current, weights) if row.get(field) is not None]
        metrics[field] = {"observed_games": len(available),
                          "mean": round(sum(value for value, _ in available) / len(available), 3) if available else None,
                          "recency_weighted_mean": round(sum(value * weight for value, weight in available) /
                                                         sum(weight for _, weight in available), 3) if available else None}
    return {"games": n, "from": current[0]["date"], "through": current[-1]["date"],
            "season_counts": {season: sum(row["season"] == season for row in current)
                              for season in sorted({row["season"] for row in current})},
            "record": {result: sum(row["result"] == result for row in current) for result in "WDL"},
            "btts_rate": round(sum(row["goals_for"] > 0 and row["goals_against"] > 0 for row in current) / n, 3),
            "over_2_5_rate": round(sum(row["goals_for"] + row["goals_against"] > 2 for row in current) / n, 3),
            "clean_sheet_rate": round(sum(row["goals_against"] == 0 for row in current) / n, 3),
            "venue_counts": {venue: sum(row["venue"] == venue for row in current) for venue in ("home", "away")},
            "mean_opponent_elo_before": round(sum(row["opponent_elo_before"] for row in current) / n, 1),
            "metrics": metrics}


def report(data_dir: Path, cutoff: date) -> dict:
    manifest = json.loads((data_dir / "manifest.json").read_text())
    leagues = {league for league, _ in TEAMS.values()}
    summaries = {}
    for league in sorted(leagues):
        rows = team_rows(read_league(data_dir, manifest, league, cutoff))
        for official_name, (wanted_league, source_name) in TEAMS.items():
            if wanted_league != league:
                continue
            games = rows[source_name]
            if len(games) < 20:
                raise ValueError(f"Insufficient domestic history for {official_name}: {len(games)}")
            summaries[official_name] = {"league": league, "source_team_name": source_name,
                                        "games_before_cutoff": len(games),
                                        "windows": {str(n): summarize_window(games, n) for n in (5, 10, 20)},
                                        "last_five_games": games[-5:]}
    return {"cutoff_exclusive_date_wib": cutoff.isoformat(), "source": "https://www.football-data.co.uk/",
            "snapshot_manifest": manifest, "covered_teams": len(summaries), "teams": summaries,
            "unsupported_uefa_teams": UNSUPPORTED,
            "limitations": ["Domestic league matches only; UEFA, cups, and national-team games are absent.",
                            "The current-season CSV is a source snapshot, not a historical feed of publication timestamps.",
                            "Elo surplus adjusts for opponent rating and venue within each league but is not comparable across leagues or a calibrated win probability.",
                            "Only some Turkish and Greek rows include xG; its provider and training provenance are unknown. Big chances, goalkeeper post-shot quality, and possession are unavailable."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(".cache/form"))
    parser.add_argument("--cutoff-date-wib", type=date.fromisoformat, required=True)
    parser.add_argument("--output", type=Path, default=Path("reports/current_form.json"))
    args = parser.parse_args()
    result = report(args.data_dir, args.cutoff_date_wib)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
