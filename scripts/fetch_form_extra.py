"""Snapshot Football-Data Austria and Norway CSVs for two UEFA candidates."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from urllib.request import urlopen


DATA_DIR = Path(".cache/form_extra")
FILES = {"AUT.csv": "https://www.football-data.co.uk/new/AUT.csv",
         "NOR.csv": "https://www.football-data.co.uk/new/NOR.csv"}


def fetch(item: tuple[str, str], folder: Path) -> tuple[str, dict]:
    name, url = item
    with urlopen(url, timeout=40) as response:
        body = response.read()
    if not body.startswith((b"\xef\xbb\xbfCountry,League,Season,Date,", b"Country,League,Season,Date,")):
        raise ValueError(f"Unexpected extra-league CSV header: {url}")
    (folder / name).write_bytes(body)
    return name, {"url": url, "sha256": hashlib.sha256(body).hexdigest(),
                  "retrieved_at": datetime.now(timezone.utc).isoformat(), "bytes": len(body)}


def main() -> None:
    snapshots = DATA_DIR / "snapshots"
    snapshots.mkdir(parents=True, exist_ok=True)
    old_path = DATA_DIR / "manifest.json"
    if old_path.exists():
        old = json.loads(old_path.read_text())
        old_folder = Path(old["snapshot_folder"]).resolve()
        if not old_folder.is_relative_to(snapshots.resolve()):
            raise ValueError("Previous extra-league snapshot path escaped cache")
        for name, source in old["files"].items():
            if hashlib.sha256((old_folder / name).read_bytes()).hexdigest() != source["sha256"]:
                raise ValueError(f"Previous source snapshot checksum mismatch: {name}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    current = snapshots / stamp
    current.mkdir()
    with ThreadPoolExecutor(max_workers=2) as pool:
        files = dict(pool.map(lambda item: fetch(item, current), FILES.items()))
    manifest = {"snapshot_folder": str(current), "files": files}
    (current / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    for name in files:
        shutil.copy2(current / name, DATA_DIR / name)
    old_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Snapshotted {len(files)} extra-league CSV files")


if __name__ == "__main__":
    main()
