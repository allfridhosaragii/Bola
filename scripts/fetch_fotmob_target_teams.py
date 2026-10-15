"""Snapshot FotMob team pages for all clubs in the 20 October UEFA target."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen


TARGETS = {
    "Fenerbahçe": (8695, "fenerbahce"), "Slavia Praha": (7787, "slavia-prague"),
    "Sabah": (951893, "sabah-fk"), "B. Dortmund": (9789, "borussia-dortmund"),
    "Paris": (9847, "paris-saint-germain"), "Barcelona": (8634, "barcelona"),
    "Liverpool": (8650, "liverpool"), "Villarreal": (10205, "villarreal"),
    "Man City": (8456, "manchester-city"), "AEK Athens": (8563, "aek-athens"),
    "Roma": (8686, "roma"), "S. Bratislava": (6019, "slovan-bratislava"),
    "Porto": (9773, "fc-porto"), "PSV": (8640, "psv-eindhoven"),
    "Napoli": (9875, "napoli"), "Bodø/Glimt": (8402, "bodo-glimt"),
    "Stuttgart": (10269, "vfb-stuttgart"), "Atleti": (9906, "atletico-madrid"),
}


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    folder = Path(".cache/fotmob_target_teams") / stamp
    folder.mkdir(parents=True)

    def fetch(item: tuple[str, tuple[int, str]]) -> tuple[str, dict]:
        official, (team_id, slug) = item
        url = f"https://www.fotmob.com/teams/{team_id}/overview/{slug}"
        with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as response:
            body = response.read()
        if b'id="__NEXT_DATA__"' not in body:
            raise ValueError(f"FotMob page lacks embedded data: {official}")
        name = f"{team_id}.html"
        (folder / name).write_bytes(body)
        return official, {"team_id": team_id, "url": url, "filename": name,
                          "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body),
                          "retrieved_at": datetime.now(timezone.utc).isoformat()}

    with ThreadPoolExecutor(max_workers=6) as pool:
        teams = dict(pool.map(fetch, TARGETS.items()))
    (folder / "manifest.json").write_text(json.dumps({"teams": teams}, indent=2) + "\n", encoding="utf-8")
    print(folder)


if __name__ == "__main__":
    main()
