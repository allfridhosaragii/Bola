"""Audit available attacking, defensive, and goalkeeper stats in recent matches."""

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
METRICS = {"BallPossesion": "possession_pct", "total_shots": "shots", "ShotsOnTarget": "shots_on_target",
           "corners": "corners", "big_chance": "big_chances", "touches_opp_box": "touches_opponent_box",
           "keeper_saves": "keeper_saves", "yellow_cards": "yellow_cards", "red_cards": "red_cards",
           "fouls": "fouls", "Offsides": "offsides"}
PERIODS = ("All", "FirstHalf", "SecondHalf")


def period_stats(period: dict) -> dict:
    values = {}
    for group in period["stats"]:
        for stat in group["stats"]:
            key = stat["key"]
            if key not in METRICS and key != "accurate_passes":
                continue
            pair = stat["stats"]
            if len(pair) != 2 or pair == [None, None]:
                continue
            if key == "accurate_passes":
                parsed = []
                for value in pair:
                    match = re.fullmatch(r"\d+ \((\d+)%\)", str(value))
                    if not match:
                        raise ValueError(f"Unexpected FotMob pass accuracy: {value}")
                    parsed.append(int(match[1]))
                pair = parsed
                name = "pass_accuracy_pct"
            else:
                if any(type(value) not in (int, float) or value < 0 for value in pair):
                    raise ValueError(f"Unexpected FotMob numeric metric: {key} {pair}")
                name = METRICS[key]
            if name in values and values[name] != pair:
                raise ValueError(f"Conflicting duplicate FotMob metric: {name}")
            values[name] = pair
    if "possession_pct" in values and sum(values["possession_pct"]) != 100:
        raise ValueError("FotMob possession percentages do not sum to 100")
    if "shots_on_target" in values and "shots" in values:
        if any(a > b for a, b in zip(values["shots_on_target"], values["shots"])):
            raise ValueError("FotMob shots on target exceed all shots")
    return values


def parse_match(body: bytes, source: dict, cutoff: date) -> dict:
    parser = NextData()
    parser.feed(body.decode("utf-8"))
    if not parser.body:
        raise ValueError("FotMob match page lacks embedded data")
    page = json.loads(parser.body)
    if page["page"] != "/matches/[seo]/[h2h]":
        raise ValueError("Unexpected FotMob match page type")
    payload = page["props"]["pageProps"]
    if (str(payload["general"]["matchId"]) != source["match_id"] or
            str(payload["general"].get("parentLeagueId", payload["general"]["leagueId"])) != source["league_id"]):
        raise ValueError(f"FotMob match or league ID mismatch: {source['match_id']}")
    teams = payload["header"]["teams"]
    if len(teams) != 2 or source["team_id"] not in [team["id"] for team in teams]:
        raise ValueError(f"FotMob match teams mismatch: {source['match_id']}")
    state = payload["header"]["status"]
    kickoff = datetime.fromisoformat(state["utcTime"].replace("Z", "+00:00"))
    if (kickoff.astimezone(WIB).date() >= cutoff or not state["finished"] or
            state.get("cancelled") or state.get("awarded") or state["scoreStr"] != source["score"] or
            kickoff != datetime.fromisoformat(source["kickoff"].replace("Z", "+00:00"))):
        raise ValueError(f"FotMob match timing/status/score mismatch: {source['match_id']}")
    side = 0 if teams[0]["id"] == source["team_id"] else 1
    period_data = payload["content"]["stats"]["Periods"]
    result = {}
    for period in PERIODS:
        available = period_stats(period_data[period]) if period in period_data else {}
        result[period] = {name: {"team": pair[side], "opponent": pair[1 - side]}
                          for name, pair in available.items()}
    return {"match_id": source["match_id"], "kickoff": source["kickoff"], "team": source["team"],
            "opponent": teams[1 - side]["name"], "venue": "home" if side == 0 else "away",
            "score": source["score"], "periods": result}


def report(folder: Path) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text())
    cutoff = date.fromisoformat(manifest["cutoff_exclusive_date_wib"])
    snapshot = Path(manifest["snapshot_folder"])
    games = []
    for filename, source in manifest["files"].items():
        body = (snapshot / filename).read_bytes()
        if hashlib.sha256(body).hexdigest() != source["sha256"]:
            raise ValueError(f"FotMob recent match checksum mismatch: {filename}")
        games.append(parse_match(body, source, cutoff))
    teams = {}
    for name in sorted({game["team"] for game in games}):
        rows = sorted((game for game in games if game["team"] == name), key=lambda row: row["kickoff"])
        if len(rows) != 5:
            raise ValueError(f"Expected five domestic match pages for {name}")
        averages = {}
        for period in PERIODS:
            names = sorted({metric for row in rows for metric in row["periods"][period]})
            averages[period] = {}
            for metric in names:
                observed = [row["periods"][period][metric] for row in rows if metric in row["periods"][period]]
                averages[period][metric] = {"observed_games": len(observed),
                                            "team_mean": round(sum(row["team"] for row in observed) / len(observed), 2),
                                            "opponent_mean": round(sum(row["opponent"] for row in observed) / len(observed), 2)}
        teams[name] = {"games": rows, "averages": averages}
    return {"cutoff_exclusive_date_wib": cutoff.isoformat(), "source": "https://www.fotmob.com/",
            "snapshot_manifest": manifest, "teams": teams,
            "limitations": ["These match pages were retrieved after the historical kickoff; pre-match source availability is not established.",
                            "Metrics are reported only when present in each source page. Ukrainian league pages lack xG, big chances, keeper saves, and half-by-half stats in this sample.",
                            "Keeper saves are raw counts, not post-shot expected goals or a quality-adjusted goalkeeper rating.",
                            "The data come from one platform; agreement with independent official match statistics is not established."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(".cache/fotmob_recent"))
    parser.add_argument("--output", type=Path, default=Path("reports/fotmob_recent_stats.json"))
    args = parser.parse_args()
    result = report(args.data_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({name: row["averages"]["All"] for name, row in result["teams"].items()},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
