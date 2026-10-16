"""Verify why recent FotMob statistics and lineups are unavailable."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from .form_fotmob import NextData


def _page_payload(body: bytes) -> dict:
    parser = NextData()
    parser.feed(body.decode("utf-8"))
    if not parser.body:
        raise ValueError("Recent match page lacks embedded Next.js data")
    page = json.loads(parser.body)
    return page["props"]["pageProps"]


def _missing_reason(payload: dict, field: str) -> str | None:
    content = payload.get("content") or {}
    if field == "stats":
        value = content.get("stats")
        if value is None:
            return "stats_null"
        if not (value.get("Periods") or {}):
            return "stats_periods_empty"
        return None
    value = content.get("lineup")
    if value is None:
        return "lineup_null"
    if value.get("lineupType") == "unavailable":
        return "lineup_unavailable"
    if not any((value.get(key) or {}).get("starters") for key in ("homeTeam", "awayTeam")):
        return "lineup_without_starters"
    return None


def audit(report_path: Path) -> dict:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    manifest = report["snapshot_manifest"]
    snapshot = Path(manifest["snapshot_folder"])
    source_files = manifest["files"]
    rows = []
    anomalies = []
    stats_reasons: dict[str, int] = {}
    lineup_reasons: dict[str, int] = {}
    for team, team_data in report["teams"].items():
        for game in team_data["games"]:
            filename = f"{game['match_id']}"
            candidates = [name for name, source in source_files.items()
                          if source["match_id"] == game["match_id"] and source["team"] == team]
            if len(candidates) != 1:
                raise ValueError(f"Manifest does not uniquely identify {team} {filename}")
            filename = candidates[0]
            source = source_files[filename]
            body = (snapshot / filename).read_bytes()
            digest = hashlib.sha256(body).hexdigest()
            if digest != source["sha256"]:
                raise ValueError(f"Recent match page checksum mismatch: {filename}")
            payload = _page_payload(body)
            stats_reason = _missing_reason(payload, "stats")
            lineup_reason = _missing_reason(payload, "lineup")
            if bool(stats_reason) == bool(game["stats_available"]):
                anomalies.append({"team": team, "match_id": game["match_id"],
                                  "field": "stats", "report_value": game["stats_available"],
                                  "raw_reason": stats_reason})
            if bool(lineup_reason) == bool(game["lineup_available"]):
                anomalies.append({"team": team, "match_id": game["match_id"],
                                  "field": "lineup", "report_value": game["lineup_available"],
                                  "raw_reason": lineup_reason})
            if stats_reason:
                stats_reasons[stats_reason] = stats_reasons.get(stats_reason, 0) + 1
            if lineup_reason:
                lineup_reasons[lineup_reason] = lineup_reasons.get(lineup_reason, 0) + 1
            rows.append({"team": team, "match_id": game["match_id"], "kickoff": game["kickoff"],
                         "stats_available": game["stats_available"], "lineup_available": game["lineup_available"],
                         "stats_missing_reason": stats_reason, "lineup_missing_reason": lineup_reason,
                         "source_file": filename, "source_sha256": digest})
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report_path": str(report_path),
        "captured_at": manifest.get("captured_at"),
        "raw_pages_checked": len(rows), "anomalies": anomalies,
        "stats_missing_reasons": stats_reasons, "lineup_missing_reasons": lineup_reasons,
        "stats_available": sum(row["stats_available"] for row in rows),
        "lineups_available": sum(row["lineup_available"] for row in rows),
        "limitations": [
            "This verifies source-page fields and checksums; it does not create missing statistics or lineups.",
            "A source page can be internally consistent while still lacking an independent provider cross-check.",
        ],
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("raw_pages_checked", "stats_available", "lineups_available", "anomalies")}, indent=2))


if __name__ == "__main__":
    main()
