"""Snapshot current and previous domestic seasons for pre-match form audits."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from urllib.request import urlopen


SEASONS = ("2526", "2627")
LEAGUES = ("E0", "F1", "I1", "SP1", "D1", "N1", "P1")
TARGET = Path(".cache/form")


def fetch(item: tuple[str, str], destination: Path) -> tuple[str, dict]:
    season, league = item
    url = f"https://www.football-data.co.uk/mmz4281/{season}/{league}.csv"
    with urlopen(url, timeout=40) as response:
        body = response.read()
    if not body.startswith((b"\xef\xbb\xbfDiv,Date,", b"Div,Date,")):
        raise ValueError(f"Unexpected CSV header: {url}")
    name = f"{season}_{league}.csv"
    (destination / name).write_bytes(body)
    return name, {"url": url, "sha256": hashlib.sha256(body).hexdigest(),
                  "retrieved_at": datetime.now(timezone.utc).isoformat(), "bytes": len(body)}


def main() -> None:
    TARGET.mkdir(parents=True, exist_ok=True)
    snapshot_root = TARGET / "snapshots"
    snapshot_root.mkdir(exist_ok=True)
    old_manifest_path = TARGET / "manifest.json"
    if old_manifest_path.exists():
        old_manifest = json.loads(old_manifest_path.read_text())
        archived = old_manifest.get("snapshot_folder")
        if archived:
            old_folder = Path(archived).resolve()
            if not old_folder.is_relative_to(snapshot_root.resolve()) or not (old_folder / "manifest.json").exists():
                raise ValueError("Previous source snapshot is missing or outside cache")
            for name, row in old_manifest["files"].items():
                if hashlib.sha256((old_folder / name).read_bytes()).hexdigest() != row["sha256"]:
                    raise ValueError(f"Previous source snapshot checksum mismatch: {name}")
        else:
            old_stamp = min(row["retrieved_at"] for row in old_manifest["files"].values())
            old_folder = snapshot_root / old_stamp.replace(":", "-").replace("+", "_")
            with tempfile.TemporaryDirectory(dir=snapshot_root) as temporary:
                staging = Path(temporary)
                for name, row in old_manifest["files"].items():
                    body = (TARGET / name).read_bytes()
                    if hashlib.sha256(body).hexdigest() != row["sha256"]:
                        raise ValueError(f"Cannot archive altered source file: {name}")
                    (staging / name).write_bytes(body)
                shutil.copy2(old_manifest_path, staging / "manifest.json")
                staging.rename(old_folder)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    current_folder = snapshot_root / stamp
    current_folder.mkdir()
    with ThreadPoolExecutor(max_workers=4) as pool:
        items = dict(pool.map(lambda item: fetch(item, current_folder),
                              ((season, league) for season in SEASONS for league in LEAGUES)))
    manifest = {"files": items, "snapshot_folder": str(current_folder)}
    (current_folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    for name in items:
        shutil.copy2(current_folder / name, TARGET / name)
    (TARGET / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Snapshotted {len(items)} Football-Data domestic CSV files")


if __name__ == "__main__":
    main()
