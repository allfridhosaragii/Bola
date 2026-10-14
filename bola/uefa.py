"""Compare user-reported fixtures with UEFA match pages and sitemap."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.request import urlopen
import xml.etree.ElementTree as ET

from .squad import instant


SITEMAP_URL = "https://www.uefa.com/sitemap/matches/uefachampionsleague.xml"
SITEMAP_NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}


class MatchParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.match: dict | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("data-name") == "match-header":
            self.match = json.loads(html.unescape(values["data-options"]))["match"]


def parse_match_page(body: bytes, url: str, retrieved_at: str) -> dict:
    page = body.decode("utf-8")
    parser = MatchParser()
    parser.feed(page)
    track = re.search(r"var trackVars = (\{.*?\});", page)
    if parser.match is None or track is None:
        raise ValueError(f"UEFA match metadata missing: {url}")
    metadata = json.loads(track.group(1))
    match = parser.match
    if metadata.get("competition") != "ucl" or metadata.get("matchID") != match.get("id"):
        raise ValueError(f"UEFA competition or match ID mismatch: {url}")
    teams = metadata["matchName"].split("-", 1)
    if len(teams) != 2:
        raise ValueError(f"UEFA team names not parseable: {url}")
    return {"match_id": match["id"], "home": teams[0], "away": teams[1],
            "kickoff": match["kickOffTime"]["dateTime"], "status": match["status"],
            "matchday": metadata["matchDay"], "competition": "UEFA Champions League",
            "url": url, "retrieved_at": retrieved_at, "html_sha256": hashlib.sha256(body).hexdigest()}


def compare_candidates(payload: dict, mappings: list[dict], official: list[dict]) -> dict:
    by_pair = {(row["user_home"], row["user_away"]): row for row in mappings}
    by_id = {row["match_id"]: row for row in official}
    candidates = payload["fixtures"]
    if len(by_pair) != len(mappings) or len(by_id) != len(official) or len(candidates) != len(mappings):
        raise ValueError("Candidate, mapping, and official match counts disagree")
    rows = []
    for user in candidates:
        pair = (user["home"], user["away"])
        mapping = by_pair[pair]
        source = by_id[mapping["match_id"]]
        if (source["home"], source["away"]) != (mapping["official_home"], mapping["official_away"]):
            raise ValueError(f"UEFA team names disagree with mapping for {pair}")
        if instant(user["kickoff"]) != instant(source["kickoff"]):
            raise ValueError(f"Reported kickoff disagrees with UEFA for {pair}")
        reported_day = re.search(r"matchday (\d+)", user["competition"], re.IGNORECASE)
        official_day = int(source["matchday"].removeprefix("MD"))
        rows.append({"user_home": pair[0], "user_away": pair[1], **source,
                     "reported_matchday": int(reported_day.group(1)) if reported_day else None,
                     "matchday_agrees": bool(reported_day and int(reported_day.group(1)) == official_day)})
    return {"source": SITEMAP_URL, "verified_fixtures": len(rows),
            "matchday_disagreements": sum(not row["matchday_agrees"] for row in rows),
            "fixtures": rows,
            "limitations": ["UEFA status and page contents reflect their retrieval times; they can change.",
                            "A verified fixture does not establish player availability, lineups, odds, or a match prediction."]}


def fetch_and_compare(candidates_path: Path, mappings_path: Path, cache_dir: Path) -> dict:
    payload = json.loads(candidates_path.read_text(encoding="utf-8"))
    mappings = json.loads(mappings_path.read_text(encoding="utf-8"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    with urlopen(SITEMAP_URL, timeout=25) as response:
        sitemap = response.read()
    (cache_dir / "ucl_sitemap.xml").write_bytes(sitemap)
    root = ET.fromstring(sitemap)
    urls = [node.find("s:loc", SITEMAP_NS).text for node in root.findall("s:url", SITEMAP_NS)]
    match_urls = {}
    for url in urls:
        found = re.search(r"/match/(\d+)--", url)
        if found:
            match_urls[found.group(1)] = url
    def fetch(mapping: dict) -> dict:
        match_id = mapping["match_id"]
        url = match_urls[match_id]
        with urlopen(url, timeout=25) as response:
            body = response.read()
        retrieved_at = datetime.now(timezone.utc).isoformat()
        (cache_dir / f"{match_id}.html").write_bytes(body)
        return parse_match_page(body, url, retrieved_at)
    with ThreadPoolExecutor(max_workers=4) as pool:
        official = list(pool.map(fetch, mappings))
    return compare_candidates(payload, mappings, official)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, default=Path("examples/candidate_fixtures_2026-10-14.json"))
    parser.add_argument("--match-ids", type=Path, default=Path("examples/uefa_match_ids_2026-10-14.json"))
    parser.add_argument("--cache-dir", type=Path, default=Path(".cache/uefa"))
    parser.add_argument("--output", type=Path, default=Path("reports/uefa_fixtures.json"))
    args = parser.parse_args()
    result = fetch_and_compare(args.candidates, args.match_ids, args.cache_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
