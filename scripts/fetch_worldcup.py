"""Fetch all 64 World Cup 2022 match files from a pinned StatsBomb commit."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import tempfile
from urllib.request import urlopen


COMMIT = "4b73468fc5b0f1950f9f66fada70ad3a4f9327cb"
BASE = f"https://raw.githubusercontent.com/statsbomb/open-data/{COMMIT}/data"
MATCHES_SHA256 = "b9d7516dc9919a825f04c204ca85487958c8a2431e84140a48e944934661efc7"
DATA_DIR = Path(".cache/statsbomb")


def fetch(remote: str, target: Path, expected_sha: str | None = None) -> tuple[str, str]:
    if target.exists():
        content = target.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        if expected_sha is None or digest == expected_sha:
            try:
                if isinstance(json.loads(content), list):
                    return target.name, digest
            except json.JSONDecodeError:
                pass
    else:
        content = None
    error = None
    for _ in range(3):
        try:
            with urlopen(f"{BASE}/{remote}", timeout=90) as response:
                content = response.read()
            digest = hashlib.sha256(content).hexdigest()
            if expected_sha is not None and digest != expected_sha:
                raise ValueError(f"Checksum mismatch: {remote}")
            if not isinstance(json.loads(content), list):
                raise ValueError(f"Expected a JSON list: {remote}")
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as tmp:
                tmp.write(content)
                temporary = Path(tmp.name)
            temporary.replace(target)
            return target.name, digest
        except Exception as exc:
            error = exc
    raise RuntimeError(f"Failed to fetch {remote}: {error}")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = DATA_DIR / "worldcup_sha256.json"
    previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    if previous and previous.get("commit") != COMMIT:
        raise ValueError("Existing checksum manifest uses a different commit")
    expected_files = previous.get("files", {})
    name, digest = fetch("matches/43/106.json", DATA_DIR / "matches_43_106.json", MATCHES_SHA256)
    matches = json.loads((DATA_DIR / name).read_text(encoding="utf-8"))
    if len(matches) != 64 or len({m["match_id"] for m in matches}) != 64:
        raise ValueError("Expected exactly 64 unique World Cup 2022 matches")
    checksums = {name: digest}
    futures = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for match in matches:
            match_id = match["match_id"]
            for kind in ("events", "lineups"):
                filename = f"{kind}_{match_id}.json"
                futures.append(pool.submit(fetch, f"{kind}/{match_id}.json", DATA_DIR / filename,
                                           expected_files.get(filename)))
        for future in as_completed(futures):
            name, digest = future.result()
            checksums[name] = digest
    manifest_path.write_text(json.dumps({"commit": COMMIT, "files": checksums}, indent=2) + "\n")
    print(f"Verified {len(matches)} matches and {len(checksums)} files from StatsBomb commit {COMMIT}")


if __name__ == "__main__":
    main()
