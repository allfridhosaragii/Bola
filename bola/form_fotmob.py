"""Time-censored FotMob league form for UEFA clubs outside CSV coverage."""

from __future__ import annotations

import argparse
from datetime import date, datetime
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

from .form import summarize_window, team_rows


WIB = ZoneInfo("Asia/Jakarta")
LEAGUES = {"176": ("Slovakia 1. liga", "SVK", "S. Bratislava", 6019, "Slovan Bratislava"),
           "441": ("Ukraine Premier League", "UKR", "Shakhtar", 9728, "Shakhtar Donetsk"),
           "122": ("Czech 1. Liga", "CZE", "Slavia Praha", 7787, "Slavia Prague"),
           "262": ("Azerbaijan Premier League", "AZE", "Sabah", 951893, "Sabah FK")}
SEASONS = {"2526": "2025/2026", "2627": "2026/2027"}


class NextData(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.reading = False
        self.body = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script" and dict(attrs).get("id") == "__NEXT_DATA__":
            self.reading = True

    def handle_data(self, data: str) -> None:
        if self.reading:
            self.body += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self.reading = False


def read_page(body: bytes, league_id: str, season: str, cutoff: date) -> list[dict]:
    parser = NextData()
    parser.feed(body.decode("utf-8"))
    if not parser.body:
        raise ValueError("FotMob page lacks embedded league data")
    page = json.loads(parser.body)
    if page["page"] != "/leagues/[id]/[tab]/[[...slug]]":
        raise ValueError("Unexpected FotMob page type")
    details = page["props"]["pageProps"]["details"]
    wanted_name, country, _, _, _ = LEAGUES[league_id]
    if (str(details["id"]) != league_id or details["country"] != country or
            details["selectedSeason"] != SEASONS[season] or page["query"]["season"] != SEASONS[season]):
        raise ValueError(f"FotMob league or season identity mismatch: {league_id}_{season}")
    seen_ids = set()
    rows = []
    for fixture in page["props"]["pageProps"]["fixtures"]["allMatches"]:
        match_id = str(fixture["id"])
        if match_id in seen_ids:
            raise ValueError(f"Duplicate FotMob match ID: {match_id}")
        seen_ids.add(match_id)
        state = fixture["status"]
        kickoff = datetime.fromisoformat(state["utcTime"].replace("Z", "+00:00"))
        if kickoff.tzinfo is None:
            raise ValueError(f"FotMob match lacks timezone: {match_id}")
        day = kickoff.astimezone(WIB).date()
        if day >= cutoff or not state.get("finished") or state.get("cancelled") or state.get("awarded"):
            continue
        score = re.fullmatch(r"(\d+) - (\d+)", state.get("scoreStr", ""))
        if not score:
            raise ValueError(f"Completed FotMob match lacks final score: {match_id}")
        home, away = fixture["home"], fixture["away"]
        if int(home["id"]) == int(away["id"]):
            raise ValueError(f"FotMob fixture has same team on both sides: {match_id}")
        rows.append({"HomeTeam": home["name"], "AwayTeam": away["name"],
                     "FTHG": score[1], "FTAG": score[2], "_day": day,
                     "_season": SEASONS[season], "_match_id": match_id,
                     "_home_id": int(home["id"]), "_away_id": int(away["id"])})
    if len(seen_ids) < 100:
        raise ValueError(f"FotMob league fixture list is unexpectedly short: {league_id}_{season}")
    return rows


def report(folder: Path, cutoff: date) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text())
    teams = {}
    for league_id, (league_name, _, official_name, team_id, source_name) in LEAGUES.items():
        all_rows = []
        for season in SEASONS:
            filename = f"{league_id}_{season}.html"
            source = manifest["files"][filename]
            body = (folder / filename).read_bytes()
            if hashlib.sha256(body).hexdigest() != source["sha256"]:
                raise ValueError(f"FotMob snapshot checksum mismatch: {filename}")
            all_rows.extend(read_page(body, league_id, season, cutoff))
        if len({row["_match_id"] for row in all_rows}) != len(all_rows):
            raise ValueError(f"Repeated FotMob match ID across seasons: {league_id}")
        all_rows.sort(key=lambda row: (row["_day"], row["_match_id"]))
        actual_names = {row["HomeTeam"] for row in all_rows if row["_home_id"] == team_id}
        actual_names |= {row["AwayTeam"] for row in all_rows if row["_away_id"] == team_id}
        if actual_names != {source_name}:
            raise ValueError(f"FotMob team ID/name mismatch for {official_name}: {actual_names}")
        normalized = team_rows(all_rows)[source_name]
        if len(normalized) < 20:
            raise ValueError(f"Insufficient domestic history for {official_name}: {len(normalized)}")
        teams[official_name] = {"league": league_name, "source_team_name": source_name,
                                "source_team_id": team_id, "games_before_cutoff": len(normalized),
                                "windows": {str(n): summarize_window(normalized, n) for n in (5, 10, 20)},
                                "last_five_games": normalized[-5:]}
    return {"cutoff_exclusive_date_wib": cutoff.isoformat(), "source": "https://www.fotmob.com/",
            "snapshot_manifest": manifest, "covered_teams": len(teams), "teams": teams,
            "limitations": ["Results are FotMob/enet league-page snapshots, not independent official league score feeds.",
                            "Snapshot retrieval time does not establish when each result first appeared on the source.",
                            "Postponed, abandoned, and awarded fixtures are excluded from played-match form.",
                            "No shots, possession, xG, or post-shot goalkeeper metric is included in these league fixture rows.",
                            "Elo adjusts for results and venue within each league, not cross-league team strength."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(".cache/fotmob_form"))
    parser.add_argument("--cutoff-date-wib", type=date.fromisoformat, required=True)
    parser.add_argument("--output", type=Path, default=Path("reports/current_form_fotmob.json"))
    args = parser.parse_args()
    result = report(args.data_dir, args.cutoff_date_wib)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"covered_teams": result["covered_teams"],
                      "teams": {name: {"games": row["games_before_cutoff"],
                                       "last_five_record": row["windows"]["5"]["record"]}
                                for name, row in result["teams"].items()}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
