"""Cross-check target-team recent league scores against FotMob team pages."""

from __future__ import annotations

import argparse
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

from .form_fotmob import NextData


WIB = ZoneInfo("Asia/Jakarta")


def read_team_page(body: bytes, team_id: int, cutoff: date) -> tuple[dict, list[dict]]:
    parser = NextData()
    parser.feed(body.decode("utf-8"))
    page = json.loads(parser.body)
    payload = page["props"]["pageProps"]["fallback"][f"team-{team_id}"]
    details = payload["details"]
    if details["id"] != team_id or not details.get("primaryLeagueId"):
        raise ValueError(f"FotMob team identity or primary league missing: {team_id}")
    rows = []
    for fixture in payload["fixtures"]["allFixtures"]["fixtures"]:
        status = fixture["status"]
        if (fixture["tournament"]["leagueId"] != details["primaryLeagueId"] or
                not status.get("finished") or status.get("cancelled") or status.get("awarded")):
            continue
        kickoff = datetime.fromisoformat(status["utcTime"].replace("Z", "+00:00"))
        day = kickoff.astimezone(WIB).date()
        if day >= cutoff:
            continue
        score = re.fullmatch(r"(\d+) - (\d+)", status.get("scoreStr", ""))
        if not score:
            raise ValueError(f"FotMob completed fixture lacks score: {fixture['id']}")
        home, away = fixture["home"], fixture["away"]
        if team_id not in (home["id"], away["id"]):
            raise ValueError(f"FotMob team fixture identity mismatch: {fixture['id']}")
        is_home = home["id"] == team_id
        goals_home, goals_away = int(score[1]), int(score[2])
        rows.append({"match_id": str(fixture["id"]), "date_wib": day.isoformat(),
                     "venue": "home" if is_home else "away",
                     "opponent": away["name"] if is_home else home["name"],
                     "goals_for": goals_home if is_home else goals_away,
                     "goals_against": goals_away if is_home else goals_home})
    rows.sort(key=lambda row: (row["date_wib"], row["match_id"]))
    return details, rows


def compare(folder: Path, sources: list[tuple[str, dict]], cutoff: date) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    source_teams = {}
    source_labels = {}
    for label, report in sources:
        if report["cutoff_exclusive_date_wib"] != cutoff.isoformat():
            raise ValueError(f"Form source cutoff mismatch: {label}")
        for name, team in report["teams"].items():
            if name in source_teams:
                raise ValueError(f"Duplicate source team: {name}")
            source_teams[name] = team
            source_labels[name] = (label, report["source"])
    results = {}
    for official, item in manifest["teams"].items():
        body = (folder / item["filename"]).read_bytes()
        if hashlib.sha256(body).hexdigest() != item["sha256"]:
            raise ValueError(f"FotMob team page checksum mismatch: {official}")
        details, fotmob = read_team_page(body, item["team_id"], cutoff)
        primary = source_teams.get(official)
        if primary is None:
            raise ValueError(f"Target form source missing team: {official}")
        wanted = primary["last_five_games"]
        matches = []
        used = set()
        for row in wanted:
            source_day = date.fromisoformat(row["date"])
            candidates = [candidate for candidate in fotmob
                          if candidate["match_id"] not in used and candidate["venue"] == row["venue"]
                          and candidate["goals_for"] == row["goals_for"]
                          and candidate["goals_against"] == row["goals_against"]
                          and abs((date.fromisoformat(candidate["date_wib"]) - source_day).days) <= 1]
            if len(candidates) != 1:
                raise ValueError(f"Could not uniquely cross-check recent result: {official} {row['date']}")
            found = candidates[0]
            used.add(found["match_id"])
            matches.append({"source_date": row["date"], "fotmob_date_wib": found["date_wib"],
                            "venue": row["venue"], "score": [row["goals_for"], row["goals_against"]],
                            "source_opponent": row["opponent"], "fotmob_opponent": found["opponent"],
                            "fotmob_match_id": found["match_id"]})
        label, source_url = source_labels[official]
        independent = "fotmob.com" not in source_url
        results[official] = {"primary_source_label": label, "primary_source": source_url,
                             "fotmob_team_id": item["team_id"], "fotmob_name": details["name"],
                             "primary_league_id": details["primaryLeagueId"],
                             "matches_checked": len(matches), "all_scores_agree": len(matches) == 5,
                             "independent_provider": independent, "matches": matches}
    return {"cutoff_exclusive_date_wib": cutoff.isoformat(), "teams": results,
            "teams_checked": len(results),
            "independent_teams": sum(row["independent_provider"] for row in results.values()),
            "same_provider_teams": sum(not row["independent_provider"] for row in results.values()),
            "independent_matches_checked": sum(row["matches_checked"] for row in results.values()
                                               if row["independent_provider"]),
            "limitations": [
                "Matching permits a one-day date difference because source dates may be local while FotMob is converted to WIB.",
                "Opponent names are retained from both providers but are not required to be text-identical.",
                "FotMob comparisons for teams whose primary form also uses FotMob are marked same-provider, not independent.",
                "This verifies dates, venues, and final scores for five recent league games, not every advanced statistic.",
            ]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--form", type=Path, required=True)
    parser.add_argument("--extra-form", type=Path, required=True)
    parser.add_argument("--fotmob-form", type=Path, required=True)
    parser.add_argument("--cutoff-date-wib", type=date.fromisoformat, required=True)
    parser.add_argument("--output", type=Path, default=Path("reports/form_crosscheck.json"))
    args = parser.parse_args()
    folder = args.data_dir or sorted(Path(".cache/fotmob_target_teams").glob("*/manifest.json"))[-1].parent
    paths = (("football_data", args.form), ("football_data_extra", args.extra_form),
             ("fotmob", args.fotmob_form))
    result = compare(folder, [(label, json.loads(path.read_text(encoding="utf-8")))
                              for label, path in paths], args.cutoff_date_wib)
    result["source_snapshot"] = str(folder)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("teams_checked", "independent_teams",
                                                    "same_provider_teams", "independent_matches_checked")}, indent=2))


if __name__ == "__main__":
    main()
