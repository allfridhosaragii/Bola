"""Time-censored domestic form for LASK and Bodø/Glimt from extra leagues."""

from __future__ import annotations

import argparse
import csv
from datetime import date, datetime
import hashlib
import json
from pathlib import Path

from .form import summarize_window, team_rows


TARGETS = {"LASK": ("AUT.csv", "Austria", "Bundesliga", "LASK", {"2025/2026", "2026/2027"}),
           "Bodø/Glimt": ("NOR.csv", "Norway", "Eliteserien", "Bodo/Glimt", {"2025", "2026"})}


def read_rows(body: bytes, country: str, league: str, seasons: set[str], cutoff: date) -> list[dict]:
    rows = []
    seen = set()
    for source in csv.DictReader(body.decode("utf-8-sig").splitlines()):
        if source["Country"] != country or source["League"] != league or source["Season"] not in seasons:
            continue
        if source["HG"] in (None, "") or source["AG"] in (None, ""):
            continue
        day = datetime.strptime(source["Date"], "%d/%m/%Y").date()
        if day >= cutoff:
            continue
        home, away = source["Home"], source["Away"]
        key = day, home, away
        if key in seen:
            raise ValueError(f"Duplicate extra-league fixture: {key}")
        seen.add(key)
        goals_home, goals_away = int(source["HG"]), int(source["AG"])
        expected_result = "H" if goals_home > goals_away else "A" if goals_home < goals_away else "D"
        if source["Res"] != expected_result:
            raise ValueError(f"Result disagrees with score: {key}")
        rows.append({"HomeTeam": home, "AwayTeam": away, "FTHG": str(goals_home),
                     "FTAG": str(goals_away), "_day": day, "_season": source["Season"]})
    return sorted(rows, key=lambda row: (row["_day"], row["HomeTeam"], row["AwayTeam"]))


def report(folder: Path, cutoff: date) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text())
    bodies = {}
    for name, source in manifest["files"].items():
        body = (folder / name).read_bytes()
        if hashlib.sha256(body).hexdigest() != source["sha256"]:
            raise ValueError(f"Extra-league snapshot checksum mismatch: {name}")
        bodies[name] = body
    teams = {}
    for official, (filename, country, league, source_name, seasons) in TARGETS.items():
        rows = team_rows(read_rows(bodies[filename], country, league, seasons, cutoff))[source_name]
        if len(rows) < 20:
            raise ValueError(f"Insufficient domestic form for {official}: {len(rows)}")
        teams[official] = {"league": f"{country} {league}", "source_team_name": source_name,
                           "games_before_cutoff": len(rows),
                           "windows": {str(n): summarize_window(rows, n) for n in (5, 10, 20)},
                           "last_five_games": rows[-5:]}
    return {"cutoff_exclusive_date_wib": cutoff.isoformat(), "source": "https://www.football-data.co.uk/new/",
            "snapshot_manifest": manifest, "covered_teams": len(teams), "teams": teams,
            "limitations": ["Extra-league CSVs cover domestic league scores and archived odds, not shot or xG fields.",
                            "The source snapshot does not establish first-publication times of each result.",
                            "Elo is within each league and cannot calibrate cross-league team strength."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(".cache/form_extra"))
    parser.add_argument("--cutoff-date-wib", type=date.fromisoformat, required=True)
    parser.add_argument("--output", type=Path, default=Path("reports/current_form_extra.json"))
    args = parser.parse_args()
    result = report(args.data_dir, args.cutoff_date_wib)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
