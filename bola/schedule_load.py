"""Audit target-team fixture load from checksummed FotMob team snapshots."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re

from .squad import instant


NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>')
FRIENDLY_NAMES = {"Club Friendlies", "Friendlies", "International Friendlies"}


def embedded_team(body: str, team_id: int) -> dict:
    match = NEXT_DATA.search(body)
    if not match:
        raise ValueError("FotMob page lacks __NEXT_DATA__")
    root = json.loads(match.group(1))
    try:
        return root["props"]["pageProps"]["fallback"][f"team-{team_id}"]
    except KeyError as exc:
        raise ValueError(f"FotMob page lacks expected team payload: {team_id}") from exc


def analyze_team(name: str, item: dict, payload: dict, prediction: dict) -> dict:
    team_id = int(item["team_id"])
    if int(payload["details"]["id"]) != team_id:
        raise ValueError(f"FotMob team identity mismatch: {name}")
    captured = instant(item["retrieved_at"])
    kickoff = instant(prediction["kickoff"])
    if captured >= kickoff:
        raise ValueError(f"Team schedule was captured after target kickoff: {name}")
    expected_role = "home" if prediction["home"] == name else "away"
    fixtures = payload["fixtures"]["allFixtures"]["fixtures"]
    if len({str(row["id"]) for row in fixtures}) != len(fixtures):
        raise ValueError(f"Duplicate FotMob fixture ID: {name}")

    normalized = []
    target = []
    for row in fixtures:
        when = instant(row["status"]["utcTime"])
        if team_id not in (int(row["home"]["id"]), int(row["away"]["id"])):
            raise ValueError(f"Fixture does not contain team: {name}")
        if abs((when - kickoff).total_seconds()) <= 300:
            if int(row[expected_role]["id"]) != team_id:
                raise ValueError(f"Target venue disagrees with UEFA archive: {name}")
            target.append(row)
        normalized.append((when, row))
    if len(target) != 1 or not target[0]["notStarted"]:
        raise ValueError(f"Expected one upcoming FotMob target fixture: {name}")

    def competitive(row: dict) -> bool:
        status = row["status"]
        return (row["tournament"]["name"] not in FRIENDLY_NAMES and not status["cancelled"]
                and not status.get("awarded", False))

    completed = [(when, row) for when, row in normalized
                 if when < captured and row["status"]["finished"] and competitive(row)]
    scheduled = [(when, row) for when, row in normalized
                 if captured < when < kickoff and row["notStarted"] and competitive(row)]
    if not completed:
        raise ValueError(f"No completed competitive fixture in team page: {name}")
    last_completed = max(completed, key=lambda pair: pair[0])
    preceding = max(completed + scheduled, key=lambda pair: pair[0])

    def compact(pair: tuple[datetime, dict]) -> dict:
        when, row = pair
        return {"match_id": str(row["id"]), "kickoff": when.isoformat(),
                "home": row["home"]["name"], "away": row["away"]["name"],
                "competition": row["tournament"]["name"],
                "status": "finished" if row["status"]["finished"] else "scheduled"}

    return {
        "fotmob_team_id": team_id,
        "source_retrieved_at": item["retrieved_at"],
        "target_fotmob_match_id": str(target[0]["id"]),
        "completed_competitive_matches_before_capture": len(completed),
        "completed_in_previous_14_days": sum(captured - timedelta(days=14) <= when < captured
                                               for when, _ in completed),
        "completed_in_previous_28_days": sum(captured - timedelta(days=28) <= when < captured
                                               for when, _ in completed),
        "last_completed": compact(last_completed),
        "hours_from_last_completed_to_target": round((kickoff - last_completed[0]).total_seconds() / 3600, 2),
        "scheduled_before_target": [compact(pair) for pair in sorted(scheduled, key=lambda pair: pair[0])],
        "scheduled_matches_before_target": len(scheduled),
        "projected_hours_from_preceding_fixture_to_target": round(
            (kickoff - preceding[0]).total_seconds() / 3600, 2),
        "projected_preceding_fixture_status": "scheduled" if preceding in scheduled else "finished",
    }


def assemble(archive: dict, manifest: dict, pages: dict[str, str]) -> dict:
    predictions = archive["predictions"]
    by_team = {name: row for row in predictions for name in (row["home"], row["away"])}
    if set(manifest["teams"]) != set(by_team) or set(pages) != set(by_team):
        raise ValueError("FotMob manifest, pages, and forecast teams disagree")
    teams = {name: analyze_team(name, manifest["teams"][name],
                                embedded_team(pages[name], manifest["teams"][name]["team_id"]),
                                by_team[name]) for name in sorted(by_team)}
    pair_checks = []
    for row in predictions:
        home, away = teams[row["home"]], teams[row["away"]]
        pair_checks.append({"match_id": row["match_id"], "home": row["home"], "away": row["away"],
                            "fotmob_match_id": home["target_fotmob_match_id"],
                            "both_team_pages_agree": home["target_fotmob_match_id"] == away["target_fotmob_match_id"]})
    if not all(row["both_team_pages_agree"] for row in pair_checks):
        raise ValueError("Target match ID differs between FotMob team pages")
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "forecast_generated_at": archive["generated_at"],
        "target_date_utc": archive["target_date_utc"],
        "teams": teams,
        "target_fixture_crosscheck": pair_checks,
        "summary": {
            "teams": len(teams),
            "target_pairs_agree": sum(row["both_team_pages_agree"] for row in pair_checks),
            "teams_with_scheduled_match_before_target": sum(row["scheduled_matches_before_target"] > 0
                                                              for row in teams.values()),
            "minimum_projected_rest_hours": min(row["projected_hours_from_preceding_fixture_to_target"]
                                                 for row in teams.values()),
        },
        "limitations": [
            "The workload snapshot comes from one provider; only the target fixture is cross-checked to the UEFA archive.",
            "A scheduled match may be postponed, cancelled, or played with a rotated lineup after this capture.",
            "Fixture count and elapsed time do not measure player-level minutes, travel, sleep, injury, or fatigue.",
            "Friendly matches are excluded from competitive workload counts.",
        ],
    }


def load(folder: Path, forecast: Path) -> dict:
    manifest_path = folder / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pages = {}
    source_sha256 = {}
    for name, item in manifest["teams"].items():
        body = (folder / item["filename"]).read_bytes()
        digest = hashlib.sha256(body).hexdigest()
        if digest != item["sha256"]:
            raise ValueError(f"FotMob team page checksum mismatch: {name}")
        pages[name] = body.decode("utf-8")
        source_sha256[name] = digest
    archive = json.loads(forecast.read_text(encoding="utf-8"))
    result = assemble(archive, manifest, pages)
    result["source"] = {"snapshot_folder": str(folder), "manifest_sha256": hashlib.sha256(
        manifest_path.read_bytes()).hexdigest(), "team_page_sha256": source_sha256,
        "forecast": str(forecast), "forecast_sha256": hashlib.sha256(forecast.read_bytes()).hexdigest()}
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--forecast", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Schedule-load report already exists: {args.output}")
    folder = args.data_dir or sorted(Path(".cache/fotmob_target_teams").glob("*/manifest.json"))[-1].parent
    report = load(folder, args.forecast)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
