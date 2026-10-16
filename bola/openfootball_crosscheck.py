"""Audit an independent OpenFootball score source for the target form window.

The audit is deliberately conservative: a source only counts as a complete
independent team cross-check when all five primary recent results are present
as final scores. Missing or stale season files remain explicit blockers.
"""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unicodedata


DATE_HEADER = re.compile(r"^\s*[A-Z][a-z]{2} ([A-Z][a-z]{2}) (\d{1,2})(?: (\d{4}))?\s*$")
MATCH = re.compile(
    r"^\s+(?:(?:\d{1,2}:\d{2})\s+)?(.+?)\s+(\d+)-(\d+)"
    r"(?:\s+\([^)]*\))?\s+(.+?)\s*$"
)
MONTHS = {name: number for number, name in enumerate(
    ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), 1
)}

TEAM_SOURCES = {
    "Slavia Praha": {
        "relative_path": "czech-republic/2026-27_cz1.txt",
        "aliases": ("Slavia Praha", "Slavia Prague"),
    },
    "Sabah": {
        "relative_path": "azerbaijan/2026-27_az1.txt",
        "aliases": ("Sabah", "Sabah FK"),
    },
    "S. Bratislava": {
        "relative_path": "slovakia/2026-27_sk1.txt",
        "aliases": ("Slovan Bratislava", "S. Bratislava"),
    },
}


def _clean_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def parse_matches(body: str, cutoff: date) -> list[dict]:
    """Parse final-score rows from an OpenFootball season text file."""
    current_day: date | None = None
    rows: list[dict] = []
    for line in body.splitlines():
        header = DATE_HEADER.fullmatch(line)
        if header:
            month = MONTHS[header[1]]
            year = int(header[3]) if header[3] else (2026 if month >= 7 else 2027)
            current_day = date(year, month, int(header[2]))
            continue
        if current_day is None or current_day >= cutoff:
            continue
        match = MATCH.fullmatch(line)
        if not match:
            continue
        rows.append({"date": current_day.isoformat(), "home": match[1].strip(),
                     "away": match[4].strip(), "goals_home": int(match[2]),
                     "goals_away": int(match[3])})
    return rows


def _team_in_row(row: dict, aliases: tuple[str, ...]) -> tuple[bool, bool]:
    aliases_clean = {_clean_name(alias) for alias in aliases}
    home = _clean_name(row["home"]) in aliases_clean
    away = _clean_name(row["away"]) in aliases_clean
    return home, away


def _match_primary(primary: dict, source_rows: list[dict], aliases: tuple[str, ...]) -> dict | None:
    source_day = date.fromisoformat(primary["source_date"])
    score = primary.get("score")
    goals_for = primary.get("goals_for", score[0] if score else None)
    goals_against = primary.get("goals_against", score[1] if score else None)
    if goals_for is None or goals_against is None:
        raise ValueError("Primary result lacks a score")
    candidates = []
    for row in source_rows:
        home, away = _team_in_row(row, aliases)
        if not (home or away) or home == away:
            continue
        venue = "home" if home else "away"
        row_goals_for = row["goals_home"] if home else row["goals_away"]
        row_goals_against = row["goals_away"] if home else row["goals_home"]
        if venue != primary["venue"] or row_goals_for != goals_for or row_goals_against != goals_against:
            continue
        if abs((date.fromisoformat(row["date"]) - source_day).days) <= 1:
            candidates.append(row)
    return candidates[0] if len(candidates) == 1 else None


def _repository_commit(source_root: Path) -> str | None:
    try:
        return subprocess.run(["git", "-C", str(source_root), "rev-parse", "HEAD"],
                              check=True, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def audit(source_root: Path, primary_report: dict, cutoff: date) -> dict:
    if primary_report.get("cutoff_exclusive_date_wib") != cutoff.isoformat():
        raise ValueError("Primary form cutoff does not match OpenFootball cutoff")
    teams = {}
    for official, config in TEAM_SOURCES.items():
        path = source_root / config["relative_path"]
        primary = primary_report["teams"].get(official)
        if primary is None:
            raise ValueError(f"Primary form report missing target team: {official}")
        if not path.exists():
            teams[official] = {
                "source_status": "missing_current_season_file",
                "source_path": config["relative_path"], "matches_checked": 0,
                "matches_matched": 0, "all_scores_agree": False,
                "blocker": "Current-season OpenFootball file is unavailable.",
            }
            continue
        body = path.read_text(encoding="utf-8")
        rows = parse_matches(body, cutoff)
        matches = []
        for item in primary["matches"]:
            found = _match_primary(item, rows, config["aliases"])
            primary_score = item["score"] if "score" in item else [item["goals_for"], item["goals_against"]]
            matches.append({"source_date": item["source_date"], "venue": item["venue"],
                            "score": primary_score,
                            "openfootball": found})
        matched = sum(item["openfootball"] is not None for item in matches)
        teams[official] = {
            "source_status": "verified_complete" if matched == len(matches) else "verified_partial",
            "source_path": config["relative_path"], "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "matches_checked": len(matches), "matches_matched": matched,
            "all_scores_agree": matched == len(matches), "matches": matches,
            "blocker": None if matched == len(matches) else "At least one primary result is not present as a final score.",
        }
    return {
        "cutoff_exclusive_date_wib": cutoff.isoformat(),
        "source_repository": "https://github.com/openfootball/europe.git",
        "repository_commit": _repository_commit(source_root),
        "teams": teams,
        "teams_checked": len(teams),
        "independent_full_window_teams": sum(item["all_scores_agree"] for item in teams.values()),
        "independent_score_matches": sum(item["matches_matched"] for item in teams.values()),
        "requested_score_matches": sum(len(primary_report["teams"][official]["matches"])
                                       for official in TEAM_SOURCES),
        "limitations": [
            "A one-day date tolerance is allowed because source dates can differ by timezone.",
            "Only final scores are checked; advanced event and shot data are not inferred.",
            "A missing or partial current-season file does not pass the independent full-window gate.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--primary-crosscheck", type=Path, required=True)
    parser.add_argument("--cutoff-date-wib", type=date.fromisoformat, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.source_root, json.loads(args.primary_crosscheck.read_text(encoding="utf-8")), args.cutoff_date_wib)
    result["primary_crosscheck_sha256"] = hashlib.sha256(args.primary_crosscheck.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("teams_checked", "independent_full_window_teams", "independent_score_matches", "requested_score_matches")}, indent=2))


if __name__ == "__main__":
    main()
