"""Snapshot UEFA league-phase results for chronological cross-league evaluation."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


API = "https://match.uefa.com/v5"
SEASONS = {2025: ("2024-09-01", "2025-02-01", 144),
           2026: ("2025-09-01", "2026-02-01", 144),
           2027: ("2026-09-01", "2026-09-15", 18)}


def get(path: str, parameters: dict) -> tuple[bytes, str]:
    url = f"{API}/{path}?{urlencode(parameters)}"
    with urlopen(url, timeout=25) as response:
        return response.read(), url


def fetch() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    root = Path(".cache/uefa_history") / stamp
    root.mkdir(parents=True)
    manifest = {}
    matches = []
    for season, (start, end, expected) in SEASONS.items():
        body, url = get("match-calendar", {"competitionIds": 1, "startDate": start,
                                           "endDate": end, "phase": "ALL",
                                           "seasonYear": season, "utcOffset": 0})
        calendar_name = f"calendar_{season}.json"
        (root / calendar_name).write_bytes(body)
        manifest[calendar_name] = {"url": url, "sha256": hashlib.sha256(body).hexdigest()}
        days = json.loads(body)["data"]
        if sum(day["numberOfMatches"] for day in days) != expected:
            raise ValueError(f"Unexpected calendar fixture count in {season}")

        def fetch_day(day: dict) -> tuple[str, bytes, str, int]:
            date = day["date"]
            payload, source_url = get("matches", {"competitionId": 1, "fromDate": date,
                                                  "toDate": date, "limit": 50, "offset": 0,
                                                  "order": "ASC", "phase": "ALL",
                                                  "seasonYear": season, "utcOffset": 0})
            return date, payload, source_url, day["numberOfMatches"]

        with ThreadPoolExecutor(max_workers=4) as pool:
            responses = list(pool.map(fetch_day, days))
        for date, payload, source_url, count in responses:
            filename = f"matches_{season}_{date}.json"
            (root / filename).write_bytes(payload)
            manifest[filename] = {"url": source_url, "sha256": hashlib.sha256(payload).hexdigest()}
            rows = json.loads(payload)
            if len(rows) != count:
                raise ValueError(f"UEFA calendar and match list disagree: {date}")
            for row in rows:
                if (row["round"]["metaData"]["name"] != "League Phase" or
                        row["status"] != "FINISHED" or str(row["seasonYear"]) != str(season)):
                    raise ValueError(f"Unexpected phase, status, or season: {row['id']}")
                score = row["score"]["regular"]
                if any(type(score[side]) is not int or score[side] < 0 for side in ("home", "away")):
                    raise ValueError(f"Invalid UEFA score: {row['id']}")
                matches.append({"id": str(row["id"]), "season": season,
                                "kickoff": row["kickOffTime"]["dateTime"],
                                "home_id": row["homeTeam"]["id"],
                                "away_id": row["awayTeam"]["id"],
                                "home": row["homeTeam"]["internationalName"],
                                "away": row["awayTeam"]["internationalName"],
                                "home_goals": score["home"], "away_goals": score["away"]})
        if sum(row["season"] == season for row in matches) != expected:
            raise ValueError(f"Unexpected league-phase total: {season}")
    if len({row["id"] for row in matches}) != len(matches):
        raise ValueError("Duplicate UEFA match ID")
    normalized = json.dumps(matches, ensure_ascii=False, indent=2).encode() + b"\n"
    (root / "matches_normalized.json").write_bytes(normalized)
    manifest["matches_normalized.json"] = {"sha256": hashlib.sha256(normalized).hexdigest()}
    (root / "manifest.json").write_text(json.dumps({"source": API, "retrieved_at": datetime.now(timezone.utc).isoformat(),
                                                    "files": manifest}, indent=2) + "\n")
    return root


if __name__ == "__main__":
    path = fetch()
    print(f"Saved UEFA league-phase source snapshot: {path}")
