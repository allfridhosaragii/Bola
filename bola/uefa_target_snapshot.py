"""Refresh official UEFA fixture, squad, and lineup evidence for an archived target date."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.request import urlopen
import xml.etree.ElementTree as ET

from .squad import instant
from .uefa import SITEMAP_NS, SITEMAP_URL, parse_match_page
from .uefa_lineup_api import fetch as fetch_lineups
from .uefa_squad import fetch_squads


def target_urls(sitemap: bytes, ids: set[str]) -> dict[str, str]:
    root = ET.fromstring(sitemap)
    urls = {}
    for node in root.findall("s:url", SITEMAP_NS):
        url = node.findtext("s:loc", namespaces=SITEMAP_NS)
        found = re.search(r"/match/(\d+)--", url or "")
        if found and found.group(1) in ids:
            if found.group(1) in urls:
                raise ValueError(f"Repeated match ID in UEFA sitemap: {found.group(1)}")
            urls[found.group(1)] = url
    if set(urls) != ids:
        raise ValueError(f"UEFA sitemap missing target match IDs: {sorted(ids - set(urls))}")
    return urls


def check_fixtures(archive: dict, fixtures: list[dict]) -> None:
    expected = {row["match_id"]: row for row in archive["predictions"]}
    if len(expected) != len(archive["predictions"]) or len(fixtures) != len(expected):
        raise ValueError("Archived predictions or refreshed fixtures are duplicated")
    for fixture in fixtures:
        mid = str(fixture["match_id"])
        row = expected.get(mid)
        if row is None or (row["home"], row["away"]) != (fixture["home"], fixture["away"]):
            raise ValueError(f"Refreshed fixture team identity mismatch: {mid}")
        if instant(row["kickoff"]) != instant(fixture["kickoff"]):
            raise ValueError(f"Refreshed fixture kickoff mismatch: {mid}")


def refresh(archive: dict, cache_root: Path) -> dict:
    cache_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    folder = cache_root / stamp
    folder.mkdir()
    with urlopen(SITEMAP_URL, timeout=25) as response:
        sitemap = response.read()
    (folder / "ucl_sitemap.xml").write_bytes(sitemap)
    ids = {row["match_id"] for row in archive["predictions"]}
    urls = target_urls(sitemap, ids)

    def fetch_page(row: dict) -> dict:
        mid = row["match_id"]
        with urlopen(urls[mid], timeout=25) as response:
            body = response.read()
        retrieved = datetime.now(timezone.utc).isoformat()
        (folder / f"{mid}.html").write_bytes(body)
        return parse_match_page(body, urls[mid], retrieved)

    with ThreadPoolExecutor(max_workers=4) as pool:
        fixtures = list(pool.map(fetch_page, archive["predictions"]))
    check_fixtures(archive, fixtures)
    fixture_report = {"source": SITEMAP_URL, "fixtures": fixtures}
    squads = fetch_squads(fixture_report, folder / "squad")
    lineups = fetch_lineups(fixture_report, folder / "lineup")
    by_squad = {row["match_id"]: row for row in squads["fixtures"]}
    by_lineup = {row["match_id"]: row for row in lineups["fixtures"]}
    rows = []
    for fixture in fixtures:
        mid = fixture["match_id"]
        squad = by_squad.get(mid)
        lineup = by_lineup[mid]
        rows.append({"match_id": mid, "home": fixture["home"], "away": fixture["away"],
                     "kickoff": fixture["kickoff"], "status_at_retrieval": fixture["status"],
                     "fixture_url": fixture["url"], "fixture_retrieved_at": fixture["retrieved_at"],
                     "fixture_html_sha256": fixture["html_sha256"],
                     "squad_retrieved_at": squad["retrieved_at"] if squad else None,
                     "registered_players": {team: item["registered_players"]
                                            for team, item in squad["teams"].items()} if squad else None,
                     "flagged_players": {team: item["flagged_players"]
                                         for team, item in squad["teams"].items()} if squad else None,
                     "lineup_retrieved_at": lineup["retrieved_at"],
                     "lineup_status": lineup["lineup_status"],
                     "official_starting_xi_before_kickoff": bool(lineup["official_starting_xi"] and
                                                                 lineup["before_kickoff_at_retrieval"]),
                     "lineup_source_sha256": lineup["source_sha256"]})
    return {"refreshed_at": datetime.now(timezone.utc).isoformat(),
            "forecast_generated_at": archive["generated_at"],
            "sitemap_sha256": hashlib.sha256(sitemap).hexdigest(),
            "snapshot_folder": str(folder), "fixtures": rows,
            "limitations": ["A registered squad or player badge does not establish fitness or selection for this fixture.",
                            "The UEFA pages do not provide first-publication times of individual player badges.",
                            "Refresh lineups and injury news near kickoff; this snapshot is time-specific."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--forecast", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, default=Path(".cache/uefa_target"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Target snapshot already exists: {args.output}")
    result = refresh(json.loads(args.forecast.read_text(encoding="utf-8")), args.cache_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
