"""Snapshot five recent competitive match pages for all 18 UEFA target teams."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bola.schedule_load import FRIENDLY_NAMES, embedded_team
from bola.squad import instant


SOURCE = Path(".cache/fotmob_target_teams")
DEST = Path(".cache/fotmob_target_recent")


def selected_fixtures(folder: Path) -> tuple[list[dict], dict]:
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    selected = []
    for official, item in manifest["teams"].items():
        body = (folder / item["filename"]).read_bytes()
        if hashlib.sha256(body).hexdigest() != item["sha256"]:
            raise ValueError(f"Team-page checksum mismatch: {official}")
        payload = embedded_team(body.decode("utf-8"), int(item["team_id"]))
        captured = instant(item["retrieved_at"])
        matches = []
        for fixture in payload["fixtures"]["allFixtures"]["fixtures"]:
            status = fixture["status"]
            kickoff = instant(status["utcTime"])
            if (kickoff >= captured or not status["finished"] or status.get("cancelled") or
                    status.get("awarded") or fixture["tournament"]["name"] in FRIENDLY_NAMES):
                continue
            if int(item["team_id"]) not in (int(fixture["home"]["id"]), int(fixture["away"]["id"])):
                raise ValueError(f"Fixture does not contain target team: {official}")
            matches.append(fixture)
        matches.sort(key=lambda fixture: fixture["status"]["utcTime"])
        if len(matches) < 5:
            raise ValueError(f"Insufficient recent competitive fixtures: {official}")
        for fixture in matches[-5:]:
            selected.append({"team": official, "team_id": int(item["team_id"]),
                             "league_id": str(fixture["tournament"]["leagueId"]),
                             "match_id": str(fixture["id"]), "kickoff": fixture["status"]["utcTime"],
                             "score": fixture["status"]["scoreStr"],
                             "url": "https://www.fotmob.com" + fixture["pageUrl"].split("#", 1)[0],
                             "team_page_retrieved_at": item["retrieved_at"]})
    if len(selected) != 90 or len({(row["team_id"], row["match_id"]) for row in selected}) != 90:
        raise ValueError("Expected five unique fixtures for each of 18 teams")
    return selected, manifest


def fetch_group(group: tuple[str, list[dict]], folder: Path) -> list[tuple[str, dict]]:
    url, fixtures = group
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=35) as response:
        body = response.read()
    if b'id="__NEXT_DATA__"' not in body:
        raise ValueError(f"FotMob match page lacks embedded data: {url}")
    result = []
    retrieved = datetime.now(timezone.utc).isoformat()
    digest = hashlib.sha256(body).hexdigest()
    for fixture in fixtures:
        filename = f"{fixture['team_id']}_{fixture['match_id']}.html"
        (folder / filename).write_bytes(body)
        result.append((filename, {**fixture, "sha256": digest,
                                  "retrieved_at": retrieved, "bytes": len(body)}))
    return result


def main() -> None:
    source_manifest = sorted(SOURCE.glob("*/manifest.json"))[-1]
    fixtures, team_manifest = selected_fixtures(source_manifest.parent)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    folder = DEST / stamp
    folder.mkdir(parents=True)
    grouped = {}
    for fixture in fixtures:
        grouped.setdefault(fixture["url"], []).append(fixture)
    with ThreadPoolExecutor(max_workers=8) as pool:
        batches = pool.map(lambda group: fetch_group(group, folder), grouped.items())
        files = dict(item for batch in batches for item in batch)
    captured = max(item["retrieved_at"] for item in team_manifest["teams"].values())
    manifest = {"captured_at": captured, "matches_per_team": 5,
                "team_snapshot": str(source_manifest.parent),
                "team_manifest_sha256": hashlib.sha256(source_manifest.read_bytes()).hexdigest(),
                "snapshot_folder": str(folder), "files": files}
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                           encoding="utf-8")
    print(folder)


if __name__ == "__main__":
    main()
