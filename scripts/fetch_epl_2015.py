"""Cache full StatsBomb Premier League 2015/16 event data with pinned hashes."""

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

from fetch_worldcup import COMMIT, fetch


DATA_DIR = Path(".cache/statsbomb_epl_2015")
PINNED_MANIFEST = Path("data/statsbomb_epl_2015_sha256.json")
MATCHES_SHA256 = "e07d6d360b30e0cd17f9aeea0db1502d2a5666d298f1b44b83a2d2f21ba3d21b"


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    pinned = json.loads(PINNED_MANIFEST.read_text())
    if pinned["source_commit"] != COMMIT or pinned["matches_sha256"] != MATCHES_SHA256:
        raise ValueError("Pinned EPL 2015/16 manifest disagrees with source")
    fetch("matches/2/27.json", DATA_DIR / "matches_2_27.json", MATCHES_SHA256)
    matches = json.loads((DATA_DIR / "matches_2_27.json").read_text())
    ids = [row["match_id"] for row in matches]
    if len(ids) != 380 or len(set(ids)) != 380:
        raise ValueError("Expected 380 distinct EPL 2015/16 matches")
    expected = pinned["events_sha256"]
    if set(expected) != {str(match_id) for match_id in ids}:
        raise ValueError("Pinned event hashes do not match match metadata")
    with ThreadPoolExecutor(max_workers=6) as pool:
        files = list(pool.map(lambda match_id: fetch(
            f"events/{match_id}.json", DATA_DIR / f"events_{match_id}.json", expected[str(match_id)]), ids))
    hashes = {name.removeprefix("events_").removesuffix(".json"): digest for name, digest in files}
    if hashes != expected:
        raise ValueError("Downloaded event hashes disagree with pinned manifest")
    (DATA_DIR / "manifest.json").write_text(json.dumps(pinned, indent=2) + "\n")
    print(f"Verified {len(files)} EPL 2015/16 event files at {COMMIT}")


if __name__ == "__main__":
    main()
