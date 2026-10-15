"""Fetch a pinned community mirror of Understat EPL 2015/16 shots."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen


COMMIT = "87960c218d873b63daabdd851e93adbecab77faa"
SHA256 = "cdde2434aa027d4cbb8e9ead6510143d219a3df3575daa0f14a18937fece8f4e"
URL = ("https://raw.githubusercontent.com/douglasbc/scraping-understat-dataset/"
       f"{COMMIT}/datasets/epl/shots_epl_15-16.csv")
DEST = Path(".cache/understat_epl_2015")


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    path = DEST / "shots.csv"
    if path.exists():
        body = path.read_bytes()
    else:
        with urlopen(URL, timeout=45) as response:
            body = response.read()
        if hashlib.sha256(body).hexdigest() != SHA256:
            raise ValueError("Understat mirror checksum mismatch")
        path.write_bytes(body)
    if hashlib.sha256(body).hexdigest() != SHA256:
        raise ValueError("Cached Understat mirror checksum mismatch")
    manifest = {"source": "Understat community mirror", "url": URL,
                "repository_commit": COMMIT, "sha256": SHA256,
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "bytes": len(body)}
    (DEST / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Verified Understat mirror EPL 2015/16: {len(body)} bytes")


if __name__ == "__main__":
    main()
