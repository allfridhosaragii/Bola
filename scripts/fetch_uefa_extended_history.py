"""Snapshot complete official UEFA Champions League histories through 15 October 2026."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


API = "https://match.uefa.com/v5"
SEASONS = {
    2023: ("2022-06-01", "2023-06-30", 214),
    2024: ("2023-06-01", "2024-06-30", 214),
    2025: ("2024-06-01", "2025-06-30", 279),
    2026: ("2025-06-01", "2026-06-30", 281),
    2027: ("2026-06-01", "2026-10-15", 126),
}


def get(path: str, parameters: dict) -> tuple[bytes, str]:
    url = f"{API}/{path}?{urlencode(parameters)}"
    with urlopen(url, timeout=30) as response:
        return response.read(), url


def fetch() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    root = Path(".cache/uefa_extended_history") / stamp
    root.mkdir(parents=True)
    manifest = {}
    calendars = {}
    for season, (start, end, expected) in SEASONS.items():
        body, url = get("match-calendar", {"competitionIds": 1, "startDate": start,
                                           "endDate": end, "phase": "ALL",
                                           "seasonYear": season, "utcOffset": 0})
        name = f"calendar_{season}.json"
        (root / name).write_bytes(body)
        manifest[name] = {"url": url, "sha256": hashlib.sha256(body).hexdigest()}
        days = json.loads(body)["data"]
        if sum(row["numberOfMatches"] for row in days) != expected:
            raise ValueError(f"Unexpected official UEFA calendar count for {season}")
        calendars[season] = days

    jobs = [(season, row["date"], row["numberOfMatches"])
            for season, days in calendars.items() for row in days]

    def one(job: tuple[int, str, int]) -> tuple[int, str, int, bytes, str]:
        season, day, expected = job
        body, url = get("matches", {"competitionId": 1, "fromDate": day, "toDate": day,
                                    "limit": 50, "offset": 0, "order": "ASC", "phase": "ALL",
                                    "seasonYear": season, "utcOffset": 0})
        return season, day, expected, body, url

    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(one, jobs))
    matches = []
    for season, day, expected, body, url in responses:
        name = f"matches_{season}_{day}.json"
        (root / name).write_bytes(body)
        manifest[name] = {"url": url, "sha256": hashlib.sha256(body).hexdigest()}
        rows = json.loads(body)
        if len(rows) != expected:
            raise ValueError(f"UEFA calendar and match response disagree: {season} {day}")
        for row in rows:
            if row["status"] != "FINISHED" or str(row["seasonYear"]) != str(season):
                raise ValueError(f"Unexpected match status or season: {row['id']}")
            score = row["score"]["regular"]
            if any(type(score[side]) is not int or score[side] < 0 for side in ("home", "away")):
                raise ValueError(f"Invalid final score: {row['id']}")
            matches.append({
                "id": str(row["id"]), "season": season,
                "kickoff": row["kickOffTime"]["dateTime"],
                "stage": row["round"]["metaData"]["name"],
                "round_id": str(row["round"]["id"]),
                "home_id": str(row["homeTeam"]["id"]),
                "away_id": str(row["awayTeam"]["id"]),
                "home": row["homeTeam"]["internationalName"],
                "away": row["awayTeam"]["internationalName"],
                "home_goals": score["home"], "away_goals": score["away"],
            })
    if len(matches) != sum(item[2] for item in SEASONS.values()):
        raise ValueError("Extended UEFA sample count mismatch")
    if len({row["id"] for row in matches}) != len(matches):
        raise ValueError("Duplicate UEFA match ID")
    normalized = json.dumps(matches, ensure_ascii=False, indent=2).encode() + b"\n"
    (root / "matches_normalized.json").write_bytes(normalized)
    manifest["matches_normalized.json"] = {"sha256": hashlib.sha256(normalized).hexdigest()}
    (root / "manifest.json").write_text(json.dumps({
        "source": API, "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "cutoff_inclusive": "2026-10-14", "season_expected_counts":
            {str(season): item[2] for season, item in SEASONS.items()},
        "files": manifest,
    }, indent=2) + "\n", encoding="utf-8")
    return root


if __name__ == "__main__":
    print(fetch())
