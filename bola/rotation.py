"""Compare official UEFA MD1 and MD2 starting lineups without inferring causes."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from .uefa_lineup_api import fetch_body


def comparison(prior: dict, current: dict) -> dict:
    old = {str(row["player"]["id"]) for row in prior["field"]}
    bench = {str(row["player"]["id"]) for row in prior.get("bench", [])}
    new = {str(row["id"]) for row in current["starters"]}
    if len(old) != 11 or len(new) != 11:
        raise ValueError("Both official lineups must have eleven unique starters")
    return {"retained_starters": len(old & new),
            "changed_starters": len(new - old),
            "new_starters_from_prior_bench": len((new - old) & bench),
            "new_starters_not_in_prior_matchday_list": len((new - old) - bench)}


def report(lineups: dict, history_dir: Path, cache_dir: Path) -> dict:
    history_manifest = json.loads((history_dir / "manifest.json").read_text())
    normalized = (history_dir / "matches_normalized.json").read_bytes()
    if hashlib.sha256(normalized).hexdigest() != history_manifest["files"]["matches_normalized.json"]["sha256"]:
        raise ValueError("UEFA history checksum mismatch")
    md1 = [row for row in json.loads(normalized) if str(row["season"]) == "2027"]
    by_team = {}
    for row in md1:
        for side in ("home", "away"):
            team_id = row[f"{side}_id"]
            if team_id in by_team:
                raise ValueError(f"Team has more than one UEFA MD1 match: {team_id}")
            by_team[team_id] = row["id"]
    eligible = [row for row in lineups["fixtures"] if row["before_kickoff_at_retrieval"]
                and row["official_starting_xi"]]
    ids = {by_team[team["team_id"]] for fixture in eligible for team in fixture["teams"].values()}
    cache_dir.mkdir(parents=True, exist_ok=True)

    def get(mid: str) -> tuple[str, dict, str, str]:
        url = f"https://match.uefa.com/v5/matches/{mid}/lineups"
        body = fetch_body(url)
        retrieved = datetime.now(timezone.utc).isoformat()
        stamp = datetime.fromisoformat(retrieved).strftime("%Y%m%dT%H%M%S%fZ")
        (cache_dir / f"{mid}_{stamp}.json").write_bytes(body)
        return mid, json.loads(body), hashlib.sha256(body).hexdigest(), retrieved

    with ThreadPoolExecutor(max_workers=4) as pool:
        old = {mid: (source, checksum, retrieved) for mid, source, checksum, retrieved in pool.map(get, sorted(ids))}
    results = []
    for fixture in eligible:
        teams = {}
        for name, current in fixture["teams"].items():
            mid = by_team[current["team_id"]]
            source, checksum, retrieved = old[mid]
            if str(source["matchId"]) != mid:
                raise ValueError(f"UEFA MD1 lineup ID mismatch: {mid}")
            prior = next((source[side] for side in ("homeTeam", "awayTeam")
                          if source[side]["team"]["id"] == current["team_id"]), None)
            if prior is None:
                raise ValueError(f"UEFA MD1 team ID mismatch: {mid} {name}")
            teams[name] = {"md1_match_id": mid, "md1_lineup_url": f"https://match.uefa.com/v5/matches/{mid}/lineups",
                           "md1_source_sha256": checksum, "md1_retrieved_at": retrieved,
                           **comparison(prior, current)}
        results.append({"match_id": fixture["match_id"], "home": fixture["home"],
                        "away": fixture["away"], "current_lineup_retrieved_at": fixture["retrieved_at"],
                        "teams": teams})
    return {"fixtures": results,
            "limitations": ["This counts lineup changes from UEFA MD1, not all intervening domestic or cup matches.",
                            "A lineup change alone does not identify injury, suspension, tactical choice, or fatigue.",
                            "Historical MD1 lineups were retrieved retrospectively and lack announcement timestamps."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lineups", type=Path, default=Path("reports/uefa_lineups.json"))
    parser.add_argument("--history-dir", type=Path)
    parser.add_argument("--cache-dir", type=Path, default=Path(".cache/uefa/rotation"))
    parser.add_argument("--output", type=Path, default=Path("reports/uefa_rotation.json"))
    args = parser.parse_args()
    history_dir = args.history_dir or sorted(Path(".cache/uefa_history").glob("*/manifest.json"))[-1].parent
    result = report(json.loads(args.lineups.read_text()), history_dir, args.cache_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
