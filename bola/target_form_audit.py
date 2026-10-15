"""Combine verified domestic form windows for a frozen UEFA match list."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from .squad import instant


WIB = ZoneInfo("Asia/Jakarta")


def assemble(archive: dict, sources: list[tuple[str, dict]], as_of: str) -> dict:
    now = instant(as_of)
    if instant(archive["generated_at"]) > now:
        raise ValueError("Forecast is newer than form analysis time")
    cutoff = now.astimezone(WIB).date().isoformat()
    teams = {}
    provenance = {}
    for label, report in sources:
        if report["cutoff_exclusive_date_wib"] != cutoff:
            raise ValueError(f"Domestic form cutoff must equal analysis WIB date: {label}")
        files = report["snapshot_manifest"]["files"]
        if not files or any(instant(item["retrieved_at"]) > now for item in files.values()):
            raise ValueError(f"Domestic form source is not available by analysis time: {label}")
        for name, data in report["teams"].items():
            if name in teams:
                raise ValueError(f"Duplicate team among domestic sources: {name}")
            windows = data["windows"]
            if set(windows) != {"5", "10", "20"} or any(windows[str(n)]["games"] != n for n in (5, 10, 20)):
                raise ValueError(f"Incomplete form windows: {name}")
            teams[name] = data
            provenance[name] = {"source_label": label, "source": report["source"],
                                "retrieved_at_latest": max(item["retrieved_at"] for item in files.values())}
    wanted = {team for row in archive["predictions"] for team in (row["home"], row["away"])}
    if any(instant(row["kickoff"]) <= now for row in archive["predictions"]):
        raise ValueError("At least one fixture has started before form analysis")
    summary = {}
    for team in sorted(wanted & teams.keys()):
        item = teams[team]
        summary[team] = {"league": item["league"], "games_before_cutoff": item["games_before_cutoff"],
                         "source": provenance[team],
                         "windows": {size: {"record": item["windows"][size]["record"],
                                            "from": item["windows"][size]["from"],
                                            "through": item["windows"][size]["through"],
                                            "mean_opponent_elo_before": item["windows"][size]["mean_opponent_elo_before"],
                                            "venue_counts": item["windows"][size]["venue_counts"],
                                            "goals_for_per_game": item["windows"][size]["metrics"]["goals_for"]["mean"],
                                            "goals_against_per_game": item["windows"][size]["metrics"]["goals_against"]["mean"],
                                            "shots_for_observed_games": item["windows"][size]["metrics"]["shots_for"]["observed_games"]}
                                     for size in ("5", "10", "20")}}
    return {"as_of": as_of, "cutoff_exclusive_date_wib": cutoff,
            "target_date_utc": archive["target_date_utc"],
            "teams_requested": len(wanted), "teams_covered": len(summary),
            "teams_missing": sorted(wanted - teams.keys()), "teams": summary,
            "limitations": ["The form is a snapshot at its retrieval time, not the final pre-kickoff form.",
                            "Domestic leagues differ in strength; within-league Elo cannot be read as cross-league strength.",
                            "Shot data availability differs by league. Post-shot xG and current goalkeeper quality are unavailable.",
                            "This report does not add domestic form to UEFA model probabilities."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--forecast", type=Path, required=True)
    parser.add_argument("--form", type=Path, required=True)
    parser.add_argument("--extra-form", type=Path, required=True)
    parser.add_argument("--fotmob-form", type=Path, required=True)
    parser.add_argument("--as-of", default=datetime.now(timezone.utc).isoformat())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Form audit already exists: {args.output}")
    archive = json.loads(args.forecast.read_text(encoding="utf-8"))
    paths = {"football_data": args.form, "football_data_extra": args.extra_form, "fotmob": args.fotmob_form}
    sources = [(label, json.loads(path.read_text(encoding="utf-8"))) for label, path in paths.items()]
    result = assemble(archive, sources, args.as_of)
    result["input_sha256"] = {label: hashlib.sha256(path.read_bytes()).hexdigest() for label, path in paths.items()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
