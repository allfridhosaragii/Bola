"""Cache all 64 World Cup 2018 StatsBomb event files from the pinned commit."""

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

from fetch_worldcup import COMMIT, fetch


DATA_DIR = Path(".cache/statsbomb_2018")
PINNED_MANIFEST = Path("data/statsbomb_2018_sha256.json")
MATCHES_SHA256 = "f89dbd4aedcaf9c9e4ec9d8e745d5d54596500ec357d7489c914a2f126805adf"


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = DATA_DIR / "manifest.json"
    pinned = json.loads(PINNED_MANIFEST.read_text())
    if pinned["source_commit"] != COMMIT or pinned["matches_sha256"] != MATCHES_SHA256:
        raise ValueError("Pinned World Cup 2018 manifest disagrees with source")
    fetch("matches/43/3.json", DATA_DIR / "matches_43_3.json", MATCHES_SHA256)
    matches = json.loads((DATA_DIR / "matches_43_3.json").read_text())
    ids = [row["match_id"] for row in matches]
    if len(ids) != 64 or len(set(ids)) != 64:
        raise ValueError("Expected 64 distinct World Cup 2018 matches")
    expected = pinned["events_sha256"]
    if set(expected) != {str(match_id) for match_id in ids}:
        raise ValueError("Pinned event hashes do not match match metadata")
    with ThreadPoolExecutor(max_workers=4) as pool:
        files = list(pool.map(lambda match_id: fetch(
            f"events/{match_id}.json", DATA_DIR / f"events_{match_id}.json", expected.get(str(match_id))), ids))
    hashes = {name.removeprefix("events_").removesuffix(".json"): digest for name, digest in files}
    if set(hashes) != {str(match_id) for match_id in ids}:
        raise ValueError("Event manifest does not cover all matches")
    if hashes != expected:
        raise ValueError("Downloaded event hashes disagree with pinned manifest")
    manifest_path.write_text(json.dumps({"source_commit": COMMIT, "matches_sha256": MATCHES_SHA256,
                                         "events_sha256": hashes}, indent=2) + "\n")
    print(f"Verified {len(files)} World Cup 2018 event files at {COMMIT}")


if __name__ == "__main__":
    main()
