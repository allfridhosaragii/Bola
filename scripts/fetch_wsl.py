"""Cache four Women's Super League season datasets with pinned hashes."""

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

from fetch_worldcup import COMMIT, fetch


DATA_DIR = Path(".cache/statsbomb_wsl")
PINNED_MANIFEST = Path("data/statsbomb_wsl_sha256.json")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    pinned = json.loads(PINNED_MANIFEST.read_text(encoding="utf-8"))
    if pinned["source_commit"] != COMMIT:
        raise ValueError("Pinned WSL manifest disagrees with source commit")
    match_ids = []
    for season in pinned["seasons"]:
        competition_id = season["competition_id"]
        season_id = season["season_id"]
        path = DATA_DIR / f"matches_{competition_id}_{season_id}.json"
        fetch(f"matches/{competition_id}/{season_id}.json", path, season["matches_sha256"])
        rows = json.loads(path.read_text(encoding="utf-8"))
        ids = [row["match_id"] for row in rows]
        if len(ids) != season["matches"] or len(set(ids)) != len(ids):
            raise ValueError(f"Unexpected match count for season {season_id}")
        match_ids.extend(ids)
    if len(match_ids) != 457 or len(set(match_ids)) != 457:
        raise ValueError("Expected 457 distinct WSL matches")
    expected = pinned["events_sha256"]
    if set(expected) != {str(match_id) for match_id in match_ids}:
        raise ValueError("Pinned event hashes do not match WSL metadata")
    with ThreadPoolExecutor(max_workers=6) as pool:
        files = list(pool.map(lambda match_id: fetch(
            f"events/{match_id}.json", DATA_DIR / f"events_{match_id}.json",
            expected[str(match_id)]), match_ids))
    hashes = {name.removeprefix("events_").removesuffix(".json"): digest for name, digest in files}
    if hashes != expected:
        raise ValueError("Downloaded WSL event hashes disagree with pinned manifest")
    (DATA_DIR / "manifest.json").write_text(json.dumps(pinned, indent=2) + "\n", encoding="utf-8")
    print(f"Verified {len(files)} WSL event files at {COMMIT}")


if __name__ == "__main__":
    main()
