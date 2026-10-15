"""Audit available attacking, defensive, and goalkeeper stats in recent matches."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
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
            if len(pair) != 2 or any(value is None for value in pair):
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


def parse_match(body: bytes, source: dict, cutoff: date | None = None,
                captured_at: datetime | None = None) -> dict:
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
    if ((cutoff and kickoff.astimezone(WIB).date() >= cutoff) or
            (captured_at and kickoff >= captured_at) or not state["finished"] or
            state.get("cancelled") or state.get("awarded") or state["scoreStr"] != source["score"] or
            kickoff != datetime.fromisoformat(source["kickoff"].replace("Z", "+00:00"))):
        raise ValueError(f"FotMob match timing/status/score mismatch: {source['match_id']}")
    side = 0 if teams[0]["id"] == source["team_id"] else 1
    content = payload.get("content") or {}
    stats = content.get("stats") or {}
    period_data = stats.get("Periods") or {}
    result = {}
    for period in PERIODS:
        available = period_stats(period_data[period]) if period in period_data else {}
        result[period] = {name: {"team": pair[side], "opponent": pair[1 - side]}
                          for name, pair in available.items()}
    lineup = content.get("lineup") or {}
    lineup_team = lineup.get("homeTeam" if side == 0 else "awayTeam") or {}
    starters = lineup_team.get("starters") or []
    if starters and (int(lineup_team["id"]) != source["team_id"] or len(starters) != 11 or
                     len({int(player["id"]) for player in starters}) != 11):
        raise ValueError(f"Invalid FotMob starting XI: {source['match_id']}")
    return {"match_id": source["match_id"], "kickoff": source["kickoff"], "team": source["team"],
            "opponent": teams[1 - side]["name"], "venue": "home" if side == 0 else "away",
            "score": source["score"], "stats_available": bool(period_data),
            "lineup_available": bool(starters), "formation": lineup_team.get("formation"),
            "starters": [{"id": str(player["id"]), "name": player["name"]} for player in starters],
            "periods": result}


def report(folder: Path) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text())
    cutoff_text = manifest.get("cutoff_exclusive_date_wib")
    cutoff = date.fromisoformat(cutoff_text) if cutoff_text else None
    captured = datetime.fromisoformat(manifest["captured_at"].replace("Z", "+00:00")) if manifest.get("captured_at") else None
    snapshot = Path(manifest["snapshot_folder"])
    games = []
    for filename, source in manifest["files"].items():
        body = (snapshot / filename).read_bytes()
        if hashlib.sha256(body).hexdigest() != source["sha256"]:
            raise ValueError(f"FotMob recent match checksum mismatch: {filename}")
        games.append(parse_match(body, source, cutoff, captured))
    teams = {}
    for name in sorted({game["team"] for game in games}):
        rows = sorted((game for game in games if game["team"] == name), key=lambda row: row["kickoff"])
        if len(rows) != manifest.get("matches_per_team", 5):
            raise ValueError(f"Unexpected recent match-page count for {name}")
        averages = {}
        for period in PERIODS:
            names = sorted({metric for row in rows for metric in row["periods"][period]})
            averages[period] = {}
            for metric in names:
                observed = [row["periods"][period][metric] for row in rows if metric in row["periods"][period]]
                averages[period][metric] = {"observed_games": len(observed),
                                            "team_mean": round(sum(row["team"] for row in observed) / len(observed), 2),
                                            "opponent_mean": round(sum(row["opponent"] for row in observed) / len(observed), 2)}
        lineup_rows = [row for row in rows if row["lineup_available"]]
        start_counts = {}
        player_names = {}
        for row in lineup_rows:
            for player in row["starters"]:
                start_counts[player["id"]] = start_counts.get(player["id"], 0) + 1
                player_names[player["id"]] = player["name"]
        changes = []
        for previous, current in zip(lineup_rows, lineup_rows[1:]):
            old = {player["id"] for player in previous["starters"]}
            new = {player["id"] for player in current["starters"]}
            changes.append(len(new - old))
        teams[name] = {"games": rows,
                       "stats_available_games": sum(row["stats_available"] for row in rows),
                       "lineup_available_games": len(lineup_rows),
                       "distinct_starters": len(start_counts),
                       "core_starters": [{"id": player_id, "name": player_names[player_id], "starts": starts}
                                         for player_id, starts in sorted(start_counts.items(),
                                                                         key=lambda item: (-item[1], item[0]))
                                         if starts >= 4],
                       "mean_starter_changes": (round(sum(changes) / len(changes), 2) if changes else None),
                       "averages": averages}
    coverage = {}
    for metric in sorted(set(METRICS.values()) | {"pass_accuracy_pct"}):
        counts = {name: row["averages"]["All"].get(metric, {}).get("observed_games", 0)
                  for name, row in teams.items()}
        coverage[metric] = {"teams_with_any": sum(value > 0 for value in counts.values()),
                            "teams_with_all_five": sum(value == manifest.get("matches_per_team", 5)
                                                       for value in counts.values()),
                            "observed_team_games": sum(counts.values())}
    return {"generated_at": datetime.now(timezone.utc).isoformat(),
            "source_retrieved_at_latest": max(item["retrieved_at"] for item in manifest["files"].values()),
            "cutoff_exclusive_date_wib": cutoff.isoformat() if cutoff else None,
            "captured_at": manifest.get("captured_at"), "source": "https://www.fotmob.com/",
            "snapshot_manifest": manifest, "teams": teams,
            "coverage": coverage,
            "summary": {"teams": len(teams), "team_match_observations": len(games),
                        "unique_matches": len({game["match_id"] for game in games}),
                        "observations_with_stats": sum(game["stats_available"] for game in games),
                        "observations_with_lineups": sum(game["lineup_available"] for game in games),
                        "teams_with_at_least_one_stats_page": sum(row["stats_available_games"] > 0
                                                                  for row in teams.values()),
                        "teams_with_all_five_stats_pages": sum(row["stats_available_games"] == 5
                                                               for row in teams.values()),
                        "teams_with_all_five_lineups": sum(row["lineup_available_games"] == 5
                                                           for row in teams.values())},
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
