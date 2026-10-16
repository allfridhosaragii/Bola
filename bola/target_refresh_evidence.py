"""Assemble one checksum-linked evidence record for a target refresh."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _instant(value: str) -> datetime:
    """Parse an ISO timestamp while accepting the standard trailing ``Z``."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _require_equal(actual: object, expected: object, description: str) -> None:
    if actual != expected:
        raise ValueError(f"Evidence lineage mismatch: {description}")


def validate_lineage(paths: dict[str, Path], data: dict[str, dict]) -> None:
    """Reject a manifest assembled from reports belonging to different runs.

    Checksums in the final record are useful only after the dependent reports
    have proved which exact inputs they consumed.  This keeps a valid-looking
    report from silently mixing a new forecast with a stale squad, schedule,
    recent-statistics, or independent score cross-check.
    """
    forecast_digest = _digest(paths["forecast"])
    form_digest = _digest(paths["form"])
    squad_digest = _digest(paths["squad"])
    schedule_digest = _digest(paths["schedule"])
    recent_digest = _digest(paths["recent"])
    forecast = data["forecast"]
    analyst = data["analyst"]

    _require_equal(data["squad"]["forecast_generated_at"], forecast["generated_at"],
                   "squad forecast timestamp")
    _require_equal(data["schedule"]["forecast_generated_at"], forecast["generated_at"],
                   "schedule forecast timestamp")
    _require_equal(data["schedule"]["target_date_utc"], forecast["target_date_utc"],
                   "schedule target date")
    _require_equal(data["analyst"]["target_date_utc"], forecast["target_date_utc"],
                   "analyst target date")
    _require_equal(data["openfootball"]["primary_crosscheck_sha256"], _digest(paths["crosscheck"]),
                   "OpenFootball primary cross-check checksum")
    _require_equal(Path(data["coverage"]["report_path"]).name, paths["recent"].name,
                   "recent-source coverage report path")

    analyst_inputs = analyst["input_sha256"]
    _require_equal(analyst_inputs["forecast"], forecast_digest, "analyst forecast checksum")
    _require_equal(analyst_inputs["form"], form_digest, "analyst form checksum")
    _require_equal(analyst_inputs["squad"], squad_digest, "analyst squad checksum")
    _require_equal(analyst["schedule_input_sha256"], schedule_digest, "analyst schedule checksum")
    _require_equal(analyst["recent_stats_input_sha256"], recent_digest,
                   "analyst recent-statistics checksum")
    if _instant(analyst["generated_at"]) < _instant(data["squad"]["refreshed_at"]):
        raise ValueError("Evidence lineage mismatch: analyst predates squad snapshot")


def assemble(paths: dict[str, Path]) -> dict:
    required = {"forecast", "squad", "form", "crosscheck", "openfootball", "schedule", "recent", "coverage", "odds", "analyst"}
    if set(paths) != required:
        raise ValueError("Target refresh evidence needs all ten named inputs")
    data = {name: _load(path) for name, path in paths.items()}
    validate_lineage(paths, data)
    forecast, squad, form = data["forecast"], data["squad"], data["form"]
    crosscheck, openfootball, schedule, recent = data["crosscheck"], data["openfootball"], data["schedule"], data["recent"]
    coverage, odds, analyst = data["coverage"], data["odds"], data["analyst"]
    fixtures = squad["fixtures"]
    fixture_pairs = len(fixtures)
    badge_counts = [sum(len(players) for players in (row.get("flagged_players") or {}).values())
                    for row in fixtures]
    return {
        "generated_at": analyst["generated_at"], "target_date_utc": forecast["target_date_utc"],
        "evaluation_type": "Prospective pre-match refresh",
        "forecast": {"path": str(paths["forecast"]), "sha256": _digest(paths["forecast"]),
                     "matches": len(forecast["predictions"]), "generated_at": forecast["generated_at"]},
        "source_report_sha256": {name: _digest(path) for name, path in paths.items() if name != "forecast"},
        "lineage_checks": {
            "analyst_inputs_match_manifest": True,
            "forecast_dependent_reports_match_forecast": True,
            "openfootball_matches_primary_crosscheck": True,
            "recent_coverage_matches_recent_report": True,
        },
        "coverage": {
            "official_fixture_pairs_checked": fixture_pairs,
            "registered_squad_pairs": sum(bool(row["registered_players"]) for row in fixtures),
            "fixtures_with_observed_player_badges": sum(count > 0 for count in badge_counts),
            "observed_player_badges": sum(badge_counts),
            "official_starting_xi": sum(row["official_starting_xi_before_kickoff"] for row in fixtures),
            "domestic_form_teams": form["teams_covered"], "domestic_form_teams_requested": form["teams_requested"],
            "independent_score_matches": crosscheck["independent_matches_checked"],
            "independent_score_teams": crosscheck["independent_teams"],
            "openfootball_independent_score_matches": openfootball["independent_score_matches"],
            "openfootball_requested_score_matches": openfootball["requested_score_matches"],
            "openfootball_independent_full_window_teams": openfootball["independent_full_window_teams"],
            "recent_team_match_observations": recent["summary"]["team_match_observations"],
            "recent_observations_with_stats": recent["summary"]["observations_with_stats"],
            "recent_observations_with_lineups": recent["summary"]["observations_with_lineups"],
            "raw_recent_pages_checked": coverage["raw_pages_checked"],
            "recent_page_audit_anomalies": len(coverage["anomalies"]),
            "teams_with_all_five_stats_pages": recent["summary"]["teams_with_all_five_stats_pages"],
            "teams_with_all_five_lineups": recent["summary"]["teams_with_all_five_lineups"],
            "teams_with_intervening_fixture": schedule["summary"]["teams_with_scheduled_match_before_target"],
            "minimum_projected_rest_hours": schedule["summary"]["minimum_projected_rest_hours"],
        },
        "freshness": {key: analyst["summary"][key] for key in ("form_fresh", "schedule_fresh", "recent_stats_fresh")},
        "decision": {key: analyst["summary"][key] for key in ("eligible_for_review", "no_selection")},
        "external_source_checks": {"checked_at": odds["generated_at"], "urls_checked": len(odds["results"]),
                                   "quotes_observed": odds["quotes_observed"],
                                   "results": [{"url": row["url"], "http_code": row["http_code"],
                                                "status_chain": row["status_chain"],
                                                "curl_exit_code": row["curl_exit_code"]}
                                               for row in odds["results"]]},
        "limitations": [
            "Registered-player lists and badges do not establish injuries, suspensions, or the eventual starting XI.",
            "Recent statistics are descriptive and do not enter the frozen probability model.",
            "A network response is not a timestamped odds quote; quotes remain unavailable unless match, market, three prices, and capture time are recorded.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("forecast", "squad", "form", "crosscheck", "openfootball", "schedule", "recent", "coverage", "odds", "analyst"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = {name: getattr(args, name) for name in ("forecast", "squad", "form", "crosscheck", "openfootball", "schedule", "recent", "coverage", "odds", "analyst")}
    result = assemble(paths)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"matches": result["forecast"]["matches"], "no_selection": result["decision"]["no_selection"],
                      "quotes_observed": result["external_source_checks"]["quotes_observed"]}, indent=2))


if __name__ == "__main__":
    main()
