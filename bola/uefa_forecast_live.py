"""Freeze a source-backed UEFA 1X2 baseline for any upcoming UTC match date."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from urllib.parse import urlencode

from .backtest import Match, Model, mix
from .squad import instant
from .uefa_lineup_api import fetch_body


API = "https://match.uefa.com/v5"


def url_for(path: str, **params: object) -> str:
    return f"{API}/{path}?{urlencode(params)}"


def match_date_url(day: date, season: int) -> str:
    return url_for("matches", competitionId=1, fromDate=day.isoformat(), limit=50,
                   offset=0, order="ASC", phase="ALL", seasonYear=season,
                   toDate=day.isoformat(), utcOffset=0)


def validate_match(row: dict, season: int) -> tuple[str, datetime]:
    match_id = str(row["id"])
    kickoff = instant(row["kickOffTime"]["dateTime"])
    if str(row["seasonYear"]) != str(season) or row["homeTeam"]["id"] == row["awayTeam"]["id"]:
        raise ValueError(f"Invalid UEFA season or clubs: {match_id}")
    if row["round"]["metaData"]["name"] != "League Phase":
        raise ValueError(f"Match is not UEFA league phase: {match_id}")
    return match_id, kickoff


def completed_match(row: dict, season: int) -> Match:
    mid, kickoff = validate_match(row, season)
    if row["status"] != "FINISHED":
        raise ValueError(f"Previous match lacks final result: {mid}")
    score = row["score"]["regular"]
    if any(type(score[side]) is not int or score[side] < 0 for side in ("home", "away")):
        raise ValueError(f"Invalid UEFA final score: {mid}")
    return Match(str(season), kickoff.date(), str(row["homeTeam"]["id"]),
                 str(row["awayTeam"]["id"]), score["home"], score["away"], "uefa_api")


def build_forecast(history: list[dict], prior_days: dict[str, list[dict]],
                   target_rows: list[dict], target_day: date, season: int,
                   captured: datetime, include_current_history: bool = False) -> dict:
    if captured.tzinfo is None:
        raise ValueError("Capture time must include timezone")
    if len({str(row["id"]) for row in history}) != len(history):
        raise ValueError("Duplicate historical UEFA match ID")
    if len({str(row["id"]) for rows in prior_days.values() for row in rows}) != sum(map(len, prior_days.values())):
        raise ValueError("Duplicate prior UEFA match ID")
    if len({str(row["id"]) for row in target_rows}) != len(target_rows):
        raise ValueError("Duplicate target UEFA match ID")
    if not target_rows:
        raise ValueError("No UEFA matches on target date")
    model = Model()
    appearances = Counter()
    inputs = []
    seen = set()
    for row in history:
        if not include_current_history and str(row["season"]) >= str(season):
            continue  # The current season comes from a freshly captured API snapshot.
        kickoff = instant(row["kickoff"])
        if kickoff >= captured or kickoff.date() >= target_day:
            raise ValueError(f"Historical result comes after capture: {row['id']}")
        mid = str(row["id"])
        seen.add(mid)
        inputs.append((kickoff, mid, Match(str(row["season"]), kickoff.date(), str(row["home_id"]),
                                           str(row["away_id"]), row["home_goals"], row["away_goals"], "uefa_api")))
    excluded_unfinished = []
    for day_string, rows in prior_days.items():
        day = date.fromisoformat(day_string)
        if day >= target_day:
            raise ValueError("Prior match date is not before target")
        for row in rows:
            mid, kickoff = validate_match(row, season)
            if kickoff.date() != day or mid in seen:
                raise ValueError(f"Duplicate or mismatched prior fixture: {mid}")
            seen.add(mid)
            if row["status"] != "FINISHED":
                excluded_unfinished.append(mid)
                continue
            if kickoff >= captured:
                raise ValueError(f"Prior final score occurs after capture: {mid}")
            inputs.append((kickoff, mid, completed_match(row, season)))
    for _, _, match in sorted(inputs, key=lambda item: (item[0], item[1])):
        model.observe(match)
        appearances[match.home] += 1
        appearances[match.away] += 1
    predictions = []
    excluded_target = []
    for row in target_rows:
        mid, kickoff = validate_match(row, season)
        if kickoff.date() != target_day or mid in seen:
            raise ValueError(f"Target fixture date or ID mismatch: {mid}")
        if row["status"] != "UPCOMING" or captured >= kickoff:
            excluded_target.append({"match_id": mid, "status": row["status"]})
            continue
        home, away = str(row["homeTeam"]["id"]), str(row["awayTeam"]["id"])
        candidate = Match(str(season), kickoff.date(), home, away, 0, 0, "unplayed")
        probabilities = model.predict(candidate)
        probabilities["blend"] = mix(probabilities["elo"], probabilities["poisson"], 0.5)
        predictions.append({"match_id": mid, "home": row["homeTeam"]["internationalName"],
                            "away": row["awayTeam"]["internationalName"],
                            "kickoff": row["kickOffTime"]["dateTime"],
                            "historical_uefa_appearances": {"home": appearances[home], "away": appearances[away]},
                            "probabilities_h_d_a": {name: [round(value, 6) for value in values]
                                                    for name, values in probabilities.items()}})
    if not predictions:
        raise ValueError("No unstarted UEFA fixture remains for this date")
    return {"generated_at": captured.isoformat(), "target_date_utc": target_day.isoformat(),
            "season_year": season, "training_matches": model.n,
            "excluded_unfinished_prior_matches": excluded_unfinished,
            "excluded_target_matches": excluded_target,
            "predictions": predictions,
            "protocol": "Results-only UEFA Elo/Poisson blend at fixed 0.5 weight from EPL validation. "
                        "All fixtures on the target UTC date use the same prior-date model state. "
                        "Probability order: home/draw/away.",
            "limitations": ["Exploratory probabilities; not calibrated betting recommendations.",
                            "No live odds, injuries, xG, tactical labels, or player-strength adjustments enter the model.",
                            "Historical API snapshots do not prove first-publication times of older results.",
                            "A team with few UEFA appearances has a weak club-specific prior."]}


def forecast(history_dir: Path, cache_dir: Path, target_day: date, season: int) -> dict:
    if season != 2027:
        raise ValueError("This historical snapshot and validation protocol support UEFA season year 2027 only")
    manifest = json.loads((history_dir / "manifest.json").read_text(encoding="utf-8"))
    normalized = (history_dir / "matches_normalized.json").read_bytes()
    if hashlib.sha256(normalized).hexdigest() != manifest["files"]["matches_normalized.json"]["sha256"]:
        raise ValueError("Historical UEFA source checksum mismatch")
    history = json.loads(normalized)
    if Counter(str(row["season"]) for row in history if int(row["season"]) < season) != {"2025": 144, "2026": 144}:
        raise ValueError("Expected fixed historical UEFA training sample")
    previous_day = target_day - timedelta(days=1)
    calendar_url = url_for("match-calendar", competitionIds=1, startDate=f"{season-1}-09-01",
                           endDate=previous_day.isoformat(), phase="ALL", seasonYear=season, utcOffset=0)
    calendar_body = fetch_body(calendar_url)
    days = json.loads(calendar_body)["data"]
    if len({row["date"] for row in days}) != len(days):
        raise ValueError("Duplicate UEFA calendar date")
    raw = {"calendar.json": (calendar_body, calendar_url)}
    prior = {}
    for day in days:
        date_string = day["date"]
        if date.fromisoformat(date_string) >= target_day:
            raise ValueError("Calendar includes target or future day")
        url = match_date_url(date.fromisoformat(date_string), season)
        body = fetch_body(url)
        rows = json.loads(body)
        if len(rows) != day["numberOfMatches"]:
            raise ValueError(f"UEFA calendar count differs from match feed: {date_string}")
        prior[date_string] = rows
        raw[f"prior_{date_string}.json"] = body, url
    target_url = match_date_url(target_day, season)
    target_body = fetch_body(target_url)
    raw["target.json"] = target_body, target_url
    captured = datetime.now(timezone.utc)
    result = build_forecast(history, prior, json.loads(target_body), target_day, season, captured)
    cache_dir.mkdir(parents=True, exist_ok=True)
    stamp = captured.strftime("%Y%m%dT%H%M%S%fZ")
    snapshot_dir = cache_dir / stamp
    snapshot_dir.mkdir()
    sources = {}
    for name, (body, url) in raw.items():
        (snapshot_dir / name).write_bytes(body)
        sources[name] = {"url": url, "sha256": hashlib.sha256(body).hexdigest(), "snapshot": str(snapshot_dir / name)}
    result["repository_base_commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    result["model_code_sha256"] = {
        name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
        for name in ("uefa_forecast_live.py", "backtest.py")}
    result["source"] = {"historical_snapshot": str(history_dir),
                        "historical_sha256": hashlib.sha256(normalized).hexdigest(),
                        "current_snapshot_files": sources}
    return result


def forecast_extended(history_dir: Path, cache_dir: Path, target_day: date, season: int) -> dict:
    if season != 2027 or target_day != date(2026, 10, 20):
        raise ValueError("The extended snapshot currently supports the 20 October 2026 UTC target only")
    manifest = json.loads((history_dir / "manifest.json").read_text(encoding="utf-8"))
    normalized = (history_dir / "matches_normalized.json").read_bytes()
    if hashlib.sha256(normalized).hexdigest() != manifest["files"]["matches_normalized.json"]["sha256"]:
        raise ValueError("Extended historical UEFA source checksum mismatch")
    history = json.loads(normalized)
    expected = {"2023": 214, "2024": 214, "2025": 279, "2026": 281, "2027": 126}
    if Counter(str(row["season"]) for row in history) != expected:
        raise ValueError("Expected fixed extended UEFA training sample")
    target_url = match_date_url(target_day, season)
    target_body = fetch_body(target_url)
    captured = datetime.now(timezone.utc)
    result = build_forecast(history, {}, json.loads(target_body), target_day, season, captured,
                            include_current_history=True)
    result["history_mode"] = "all_ucl_phases_2022_23_through_2026_10_14"
    result["protocol"] = ("Results-only UEFA Elo/Poisson blend at fixed 0.5 weight from EPL validation. "
                          "Uses all completed Champions League phases from 2022/23 through 14 October 2026. "
                          "All target-date fixtures use the same prior state. Probability order: home/draw/away.")
    cache_dir.mkdir(parents=True, exist_ok=True)
    stamp = captured.strftime("%Y%m%dT%H%M%S%fZ")
    snapshot_dir = cache_dir / stamp
    snapshot_dir.mkdir()
    target_path = snapshot_dir / "target.json"
    target_path.write_bytes(target_body)
    result["repository_base_commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    result["model_code_sha256"] = {
        name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
        for name in ("uefa_forecast_live.py", "backtest.py")}
    result["source"] = {
        "historical_snapshot": str(history_dir),
        "historical_sha256": hashlib.sha256(normalized).hexdigest(),
        "current_snapshot_files": {"target.json": {"url": target_url,
            "sha256": hashlib.sha256(target_body).hexdigest(), "snapshot": str(target_path)}},
    }
    return result


def verify_archive(archive: dict) -> dict:
    """Replay a frozen forecast from its checksummed local source snapshots."""
    historical_path = Path(archive["source"]["historical_snapshot"]) / "matches_normalized.json"
    historical_bytes = historical_path.read_bytes()
    if hashlib.sha256(historical_bytes).hexdigest() != archive["source"]["historical_sha256"]:
        raise ValueError("Archived historical snapshot checksum mismatch")
    bodies = {}
    for name, source in archive["source"]["current_snapshot_files"].items():
        body = Path(source["snapshot"]).read_bytes()
        if hashlib.sha256(body).hexdigest() != source["sha256"]:
            raise ValueError(f"Archived current snapshot checksum mismatch: {name}")
        bodies[name] = json.loads(body)
    code_hashes = archive.get("model_code_sha256", {})
    for name, digest in code_hashes.items():
        if hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Model code differs from archived version: {name}")
    extended = archive.get("history_mode") == "all_ucl_phases_2022_23_through_2026_10_14"
    prior = {name.removeprefix("prior_").removesuffix(".json"): rows
             for name, rows in bodies.items() if name.startswith("prior_")}
    if not extended:
        calendar = bodies["calendar.json"]["data"]
        if {row["date"]: row["numberOfMatches"] for row in calendar} != {
                day: len(rows) for day, rows in prior.items()} or len(calendar) != len(prior):
            raise ValueError("Archived calendar and prior match snapshots disagree")
    replay = build_forecast(json.loads(historical_bytes), prior, bodies["target.json"],
                            date.fromisoformat(archive["target_date_utc"]), archive["season_year"],
                            instant(archive["generated_at"]), include_current_history=extended)
    for field in ("training_matches", "excluded_unfinished_prior_matches",
                  "excluded_target_matches", "predictions"):
        if replay[field] != archive[field]:
            raise ValueError(f"Archived forecast replay mismatch: {field}")
    return {"verified": True, "training_matches": replay["training_matches"],
            "predictions": len(replay["predictions"]), "source_files": len(bodies) + 1}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-date-utc", type=date.fromisoformat)
    parser.add_argument("--season-year", type=int, default=2027)
    parser.add_argument("--history-dir", type=Path)
    parser.add_argument("--extended-history-dir", type=Path)
    parser.add_argument("--cache-dir", type=Path, default=Path(".cache/uefa_forecast"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", type=Path, help="Replay an existing forecast from saved source snapshots")
    args = parser.parse_args()
    if args.verify:
        print(json.dumps(verify_archive(json.loads(args.verify.read_text(encoding="utf-8"))), indent=2))
        return
    if args.target_date_utc is None:
        parser.error("--target-date-utc is required unless --verify is used")
    if args.extended_history_dir and args.history_dir:
        parser.error("Use only one of --history-dir and --extended-history-dir")
    if args.extended_history_dir:
        result = forecast_extended(args.extended_history_dir, args.cache_dir,
                                   args.target_date_utc, args.season_year)
    else:
        history_dir = args.history_dir or sorted(Path(".cache/uefa_history").glob("*/manifest.json"))[-1].parent
        result = forecast(history_dir, args.cache_dir, args.target_date_utc, args.season_year)
    output = args.output or Path("prospective") / ("uefa_" + result["generated_at"].replace(":", "-") + ".json")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(f"Forecast archive already exists: {output}")
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
