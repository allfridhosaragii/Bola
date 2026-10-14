"""Fetch official UEFA match API lineups with source and retrieval timestamps."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.request import urlopen

from .squad import instant


API = "https://match.uefa.com/v5"


def fetch_body(url: str) -> bytes:
    for attempt in range(3):
        try:
            with urlopen(url, timeout=25) as response:
                return response.read()
        except HTTPError as error:
            if error.code not in (429, 502, 503, 504) or attempt == 2:
                raise
            time.sleep(2 ** attempt)
    raise AssertionError("Unreachable UEFA API retry state")


def parse(match: dict, lineup: dict, fixture: dict, retrieved_at: str) -> dict:
    mid = fixture["match_id"]
    if str(match["id"]) != mid or str(lineup["matchId"]) != mid:
        raise ValueError(f"UEFA match ID disagreement: {mid}")
    if (match["homeTeam"]["internationalName"] != fixture["home"] or
            match["awayTeam"]["internationalName"] != fixture["away"] or
            instant(match["kickOffTime"]["dateTime"]) != instant(fixture["kickoff"])):
        raise ValueError(f"UEFA fixture metadata disagreement: {mid}")
    teams = {}
    complete = True
    for side, name in (("homeTeam", fixture["home"]), ("awayTeam", fixture["away"])):
        source = lineup.get(side)
        if source is None:
            complete = False
            teams[name] = {"starters": [], "bench_count": 0}
            continue
        if source["team"]["id"] != match[side]["id"]:
            raise ValueError(f"UEFA lineup team ID disagreement: {mid} {name}")
        field = source["field"]
        bench = source.get("bench", [])
        ids = [row["player"]["id"] for row in field + bench]
        if len(ids) != len(set(ids)) or len(field) > 11:
            raise ValueError(f"Duplicate players or more than eleven starters: {mid} {name}")
        def player(record: dict) -> dict:
            return {"id": record["player"]["id"], "name": record["player"]["internationalName"],
                    "jersey_number": record.get("jerseyNumber"),
                    "position": record["player"].get("fieldPosition")}
        starters = [player(row) for row in field]
        complete &= len(starters) == 11
        teams[name] = {"team_id": source["team"]["id"],
                       "starters": starters, "bench": [player(row) for row in bench],
                       "bench_count": len(bench)}
    observed = instant(retrieved_at)
    return {"match_id": mid, "home": fixture["home"], "away": fixture["away"],
            "kickoff": fixture["kickoff"], "api_match_status": match["status"],
            "lineup_status": lineup["lineupStatus"], "retrieved_at": retrieved_at,
            "before_kickoff_at_retrieval": observed < instant(fixture["kickoff"]),
            "official_starting_xi": bool(complete), "teams": teams,
            "match_url": f"{API}/matches?matchId={mid}",
            "lineup_url": f"{API}/matches/{mid}/lineups"}


def fetch(fixtures: dict, cache_dir: Path) -> dict:
    cache_dir.mkdir(parents=True, exist_ok=True)

    def one(fixture: dict) -> dict:
        mid = fixture["match_id"]
        urls = (f"{API}/matches?matchId={mid}", f"{API}/matches/{mid}/lineups")
        bodies = []
        for url in urls:
            bodies.append(fetch_body(url))
        retrieved_at = datetime.now(timezone.utc).isoformat()
        stamp = datetime.fromisoformat(retrieved_at).strftime("%Y%m%dT%H%M%S%fZ")
        saved_files = {}
        for label, body in zip(("match", "lineup"), bodies):
            path = cache_dir / f"{mid}_{stamp}_{label}.json"
            path.write_bytes(body)
            saved_files[label] = str(path)
        matches = json.loads(bodies[0])
        if not isinstance(matches, list) or len(matches) != 1:
            raise ValueError(f"Expected one UEFA match: {mid}")
        result = parse(matches[0], json.loads(bodies[1]), fixture, retrieved_at)
        result["source_sha256"] = {label: hashlib.sha256(body).hexdigest()
                                   for label, body in zip(("match", "lineup"), bodies)}
        result["source_files"] = saved_files
        return result

    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(one, fixtures["fixtures"]))
    return {"source": API, "fixtures": rows,
            "limitations": ["The API response does not identify the original announcement time of each lineup.",
                            "A lineup observed after kickoff cannot establish what was known before kickoff.",
                            "A pregame lineup can change; refresh close to the decision time."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=Path("reports/uefa_fixtures.json"))
    parser.add_argument("--cache-dir", type=Path, default=Path(".cache/uefa/api"))
    parser.add_argument("--output", type=Path, default=Path("reports/uefa_lineups.json"))
    args = parser.parse_args()
    result = fetch(json.loads(args.fixtures.read_text(encoding="utf-8")), args.cache_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
