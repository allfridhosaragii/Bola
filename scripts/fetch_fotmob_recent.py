"""Snapshot the last five pre-cutoff domestic matches for two FotMob teams."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
import sys
from urllib.request import urlopen
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bola.form_fotmob import LEAGUES, NextData


SOURCE = Path(".cache/fotmob_form")
DEST = Path(".cache/fotmob_recent")
CUTOFF = date(2026, 10, 15)
WIB = ZoneInfo("Asia/Jakarta")


def selected_fixtures() -> tuple[list[dict], dict]:
    source_manifest = json.loads((SOURCE / "manifest.json").read_text())
    selected = []
    for league_id, (_, _, official, team_id, _) in LEAGUES.items():
        filename = f"{league_id}_2627.html"
        body = (SOURCE / filename).read_bytes()
        if hashlib.sha256(body).hexdigest() != source_manifest["files"][filename]["sha256"]:
            raise ValueError(f"League snapshot checksum mismatch: {filename}")
        parser = NextData()
        parser.feed(body.decode("utf-8"))
        page = json.loads(parser.body)
        matches = []
        for fixture in page["props"]["pageProps"]["fixtures"]["allMatches"]:
            status = fixture["status"]
            day = datetime.fromisoformat(status["utcTime"].replace("Z", "+00:00")).astimezone(WIB).date()
            if (team_id not in (int(fixture["home"]["id"]), int(fixture["away"]["id"])) or
                    day >= CUTOFF or not status.get("finished") or status.get("cancelled") or status.get("awarded")):
                continue
            matches.append(fixture)
        matches.sort(key=lambda fixture: fixture["status"]["utcTime"])
        if len(matches) < 5:
            raise ValueError(f"Insufficient recent domestic fixtures for {official}")
        for fixture in matches[-5:]:
            url = "https://www.fotmob.com" + fixture["pageUrl"].split("#", 1)[0]
            selected.append({"team": official, "team_id": team_id, "league_id": league_id,
                             "match_id": str(fixture["id"]), "kickoff": fixture["status"]["utcTime"],
                             "score": fixture["status"]["scoreStr"], "url": url})
    if len({row["match_id"] for row in selected}) != 10:
        raise ValueError("Recent match selection contains duplicate IDs")
    return selected, source_manifest


def fetch(fixture: dict, folder: Path) -> tuple[str, dict]:
    with urlopen(fixture["url"], timeout=35) as response:
        body = response.read()
    if b'id="__NEXT_DATA__"' not in body:
        raise ValueError(f"FotMob match page lacks embedded data: {fixture['match_id']}")
    filename = fixture["match_id"] + ".html"
    (folder / filename).write_bytes(body)
    return filename, {**fixture, "sha256": hashlib.sha256(body).hexdigest(),
                      "retrieved_at": datetime.now(WIB).isoformat(), "bytes": len(body)}


def main() -> None:
    fixtures, source_manifest = selected_fixtures()
    snapshots = DEST / "snapshots"
    snapshots.mkdir(parents=True, exist_ok=True)
    old_path = DEST / "manifest.json"
    if old_path.exists():
        old = json.loads(old_path.read_text())
        old_folder = Path(old["snapshot_folder"]).resolve()
        if not old_folder.is_relative_to(snapshots.resolve()):
            raise ValueError("Previous FotMob match snapshot path escaped cache")
        for filename, source in old["files"].items():
            if hashlib.sha256((old_folder / filename).read_bytes()).hexdigest() != source["sha256"]:
                raise ValueError(f"Previous FotMob match checksum mismatch: {filename}")
    stamp = datetime.now(WIB).strftime("%Y%m%dT%H%M%S%f%z")
    folder = snapshots / stamp
    folder.mkdir()
    with ThreadPoolExecutor(max_workers=4) as pool:
        files = dict(pool.map(lambda item: fetch(item, folder), fixtures))
    manifest = {"cutoff_exclusive_date_wib": CUTOFF.isoformat(),
                "league_snapshot": source_manifest["snapshot_folder"],
                "league_source_sha256": {filename: source_manifest["files"][filename]["sha256"]
                                         for filename in ("176_2627.html", "441_2627.html")},
                "snapshot_folder": str(folder), "files": files}
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    (DEST / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(f"Snapshotted {len(files)} FotMob recent match pages")


if __name__ == "__main__":
    main()
