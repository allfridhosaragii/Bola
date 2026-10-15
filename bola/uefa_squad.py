"""Read UEFA's registered squad rows and availability badges for upcoming matches."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import re
from urllib.request import urlopen

from .uefa import parse_match_page


WRAPPER = re.compile(r'<div class="(?:home|away)-squad-wrapper[^>]*data-squad="([^"]+)"[^>]*>')
ROW = re.compile(r'<pk-table-row class="row--squadlist">(.*?)</pk-table-row>', re.DOTALL)
PLAYER = re.compile(r'<a href="([^"]*/clubs/players/[^\"]+)" title="([^"]+)"')
BADGE = re.compile(r'<pk-badge[^>]*badge-title="([^"]+)"')


def parse_squad_page(body: bytes, url: str, retrieved_at: str) -> dict:
    page = body.decode("utf-8")
    fixture = parse_match_page(body, url, retrieved_at)
    wrappers = list(WRAPPER.finditer(page))
    if len(wrappers) != 2:
        raise ValueError(f"Expected home and away squad sections: {url}")
    teams = {}
    for index, wrapper in enumerate(wrappers):
        section = page[wrapper.end():wrappers[index + 1].start() if index + 1 < len(wrappers) else len(page)]
        players = []
        for row in ROW.findall(section):
            found = PLAYER.search(row)
            if found is None:
                raise ValueError(f"Squad row lacks a player: {url}")
            players.append({"name": html.unescape(found.group(2)),
                            "player_url": "https://www.uefa.com" + found.group(1),
                            "badges": [html.unescape(badge) for badge in BADGE.findall(row)]})
        if not players or len({player["player_url"] for player in players}) != len(players):
            raise ValueError(f"Missing or duplicated squad players: {url}")
        teams[html.unescape(wrapper.group(1))] = {
            "registered_players": len(players),
            "flagged_players": [player for player in players if player["badges"]],
        }
    if set(teams) != {fixture["home"], fixture["away"]}:
        raise ValueError(f"Squad teams disagree with match metadata: {url}")
    return {**fixture, "teams": teams, "official_starting_xi_parsed": False,
            "limitations": ["The visible table is UEFA's registered squad list, not an announced matchday starting XI.",
                            "Badges are page labels observed at retrieval time; this page does not provide their publication timestamps.",
                            "A badge alone does not prove a player is unavailable for this specific fixture."]}


def fetch_squads(fixtures_report: dict, cache_dir: Path) -> dict:
    upcoming = [row for row in fixtures_report["fixtures"] if row["status"] == "Upcoming"]
    cache_dir.mkdir(parents=True, exist_ok=True)
    def fetch(row: dict) -> dict:
        url = row["url"] + "lineups/"
        with urlopen(url, timeout=25) as response:
            body = response.read()
        retrieved_at = datetime.now(timezone.utc).isoformat()
        stamp = datetime.fromisoformat(retrieved_at).strftime("%Y%m%dT%H%M%S%fZ")
        (cache_dir / f"{row['match_id']}_{stamp}_lineups.html").write_bytes(body)
        return parse_squad_page(body, url, retrieved_at)
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(fetch, upcoming))
    return {"source": "https://www.uefa.com/", "upcoming_matches": len(rows), "fixtures": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=Path("reports/uefa_fixtures.json"))
    parser.add_argument("--cache-dir", type=Path, default=Path(".cache/uefa"))
    parser.add_argument("--output", type=Path, default=Path("reports/uefa_squads.json"))
    args = parser.parse_args()
    result = fetch_squads(json.loads(args.fixtures.read_text(encoding="utf-8")), args.cache_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
