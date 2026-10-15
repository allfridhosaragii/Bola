"""Snapshot FotMob domestic league pages for four UEFA clubs."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from urllib.request import urlopen


DATA_DIR = Path(".cache/fotmob_form")
LEAGUES = {"176": "1-liga", "441": "premier-league",
           "122": "1-liga", "262": "premier-league"}
SEASONS = {"2526": "2025%2F2026", "2627": "2026%2F2027"}


def fetch(item: tuple[str, str, str], folder: Path) -> tuple[str, dict]:
    league_id, slug, season = item
    filename = f"{league_id}_{season}.html"
    url = f"https://www.fotmob.com/leagues/{league_id}/overview/{slug}?season={SEASONS[season]}"
    with urlopen(url, timeout=40) as response:
        body = response.read()
    if b'id="__NEXT_DATA__"' not in body or len(body) < 200_000:
        raise ValueError(f"FotMob league page lacks embedded data: {url}")
    (folder / filename).write_bytes(body)
    return filename, {"url": url, "sha256": hashlib.sha256(body).hexdigest(),
                      "retrieved_at": datetime.now(timezone.utc).isoformat(), "bytes": len(body)}


def main() -> None:
    snapshots = DATA_DIR / "snapshots"
    snapshots.mkdir(parents=True, exist_ok=True)
    old_path = DATA_DIR / "manifest.json"
    if old_path.exists():
        old = json.loads(old_path.read_text())
        old_folder = Path(old["snapshot_folder"]).resolve()
        if not old_folder.is_relative_to(snapshots.resolve()):
            raise ValueError("Previous FotMob snapshot path escaped cache")
        for filename, source in old["files"].items():
            if hashlib.sha256((old_folder / filename).read_bytes()).hexdigest() != source["sha256"]:
                raise ValueError(f"Previous FotMob snapshot checksum mismatch: {filename}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    current = snapshots / stamp
    current.mkdir()
    items = ((league_id, slug, season) for league_id, slug in LEAGUES.items() for season in SEASONS)
    with ThreadPoolExecutor(max_workers=4) as pool:
        files = dict(pool.map(lambda item: fetch(item, current), items))
    manifest = {"snapshot_folder": str(current), "files": files}
    (current / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    for name in files:
        shutil.copy2(current / name, DATA_DIR / name)
    old_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Snapshotted {len(files)} FotMob league pages")


if __name__ == "__main__":
    main()
