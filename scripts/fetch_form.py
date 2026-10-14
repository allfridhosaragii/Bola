"""Snapshot current and previous domestic seasons for pre-match form audits."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen


SEASONS = ("2526", "2627")
LEAGUES = ("E0", "F1", "I1", "SP1", "D1", "N1", "P1")
TARGET = Path(".cache/form")


def fetch(item: tuple[str, str]) -> tuple[str, dict]:
    season, league = item
    url = f"https://www.football-data.co.uk/mmz4281/{season}/{league}.csv"
    with urlopen(url, timeout=40) as response:
        body = response.read()
    if not body.startswith((b"\xef\xbb\xbfDiv,Date,", b"Div,Date,")):
        raise ValueError(f"Unexpected CSV header: {url}")
    name = f"{season}_{league}.csv"
    (TARGET / name).write_bytes(body)
    return name, {"url": url, "sha256": hashlib.sha256(body).hexdigest(),
                  "retrieved_at": datetime.now(timezone.utc).isoformat(), "bytes": len(body)}


def main() -> None:
    TARGET.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        items = dict(pool.map(fetch, ((season, league) for season in SEASONS for league in LEAGUES)))
    (TARGET / "manifest.json").write_text(json.dumps({"files": items}, indent=2) + "\n")
    print(f"Snapshotted {len(items)} Football-Data domestic CSV files")


if __name__ == "__main__":
    main()
