"""Audit user-reported fixture times before any pre-match analysis."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path

from .squad import instant


def audit_candidates(payload: dict, as_of: str) -> dict:
    now = instant(as_of)
    if payload.get("source_kind") != "user_reported":
        raise ValueError("Candidate list must identify its source as user_reported")
    fixtures = payload.get("fixtures")
    if not isinstance(fixtures, list) or not fixtures:
        raise ValueError("fixtures must be a nonempty list")
    seen = set()
    results = []
    for index, row in enumerate(fixtures):
        home, away = row.get("home"), row.get("away")
        if not all(isinstance(team, str) and team.strip() for team in (home, away)) or home == away:
            raise ValueError(f"Fixture {index} needs two distinct teams")
        if not isinstance(row.get("competition"), str) or not row["competition"].strip():
            raise ValueError(f"Fixture {index} needs a competition")
        kickoff = instant(row["kickoff"])
        key = (home.casefold(), away.casefold(), kickoff)
        if key in seen:
            raise ValueError(f"Duplicate fixture {index}")
        seen.add(key)
        results.append({
            "home": home, "away": away, "competition_reported": row["competition"],
            "kickoff_reported": row["kickoff"],
            "time_status": "kickoff_passed" if now >= kickoff else "before_reported_kickoff",
            "schedule_verification": "unverified",
            "prematch_analysis_ready": False,
        })
    return {
        "as_of": as_of, "source_kind": "user_reported", "fixtures": results,
        "limitations": [
            "Kickoff and competition were supplied by the user and have not been checked against a live fixture source.",
            "Time status does not establish whether a match is live, postponed, cancelled, or completed.",
            "No lineup, injury, odds, or match prediction is authorized by this schedule audit alone.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidates", type=Path)
    parser.add_argument("--as-of", default=datetime.now().astimezone().isoformat())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit_candidates(json.loads(args.candidates.read_text(encoding="utf-8")), args.as_of)
    formatted = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(formatted, encoding="utf-8")
    print(formatted)


if __name__ == "__main__":
    main()
