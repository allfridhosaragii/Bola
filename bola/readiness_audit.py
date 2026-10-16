"""Compute a reproducible strict evidence-gate coverage report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SECTIONS = ("statistik", "taktik", "kondisi_skuad", "probabilitas", "validasi_historis")


def gate(name: str, passed: bool, evidence: str, blocker: str) -> dict:
    return {"name": name, "passed": bool(passed), "evidence": evidence,
            "blocker": None if passed else blocker}


def section(name: str, gates: list[dict]) -> dict:
    if len(gates) != 5:
        raise ValueError("Every section must define exactly five equal gates")
    passed = sum(item["passed"] for item in gates)
    return {"section": name, "gates": gates, "passed": passed, "total": len(gates),
            "strict_gate_coverage_percent": 100 * passed / len(gates)}


def load(folder: Path, filename: str) -> dict:
    return json.loads((folder / filename).read_text(encoding="utf-8"))


def latest_refresh_path(folder: Path) -> Path:
    """Return the newest checksum-linked refresh manifest in an evidence folder."""
    candidates = list(folder.glob("target_refresh_evidence_*.json"))
    if not candidates:
        raise FileNotFoundError("No checksum-linked target refresh manifest was found")
    return max(candidates, key=lambda path: (json.loads(path.read_text(encoding="utf-8"))["generated_at"], path.name))


def audit(folder: Path, refresh_path: Path | None = None) -> dict:
    refresh_path = refresh_path or latest_refresh_path(folder)
    refresh = json.loads(refresh_path.read_text(encoding="utf-8"))
    xg = load(folder, "shot_quality_incremental_epl_wsl.json")
    provider = load(folder, "xg_provider_predict_epl_2015.json")
    pressure = load(folder, "pressure_transfer_wsl.json")
    lineup = load(folder, "lineup_continuity_transfer_wsl.json")
    market = load(folder, "market_incremental_holdout.json")
    uefa = load(folder, "uefa_extended_backtest_2026-10-15.json")
    coverage = refresh["coverage"]
    odds_sources = refresh["external_source_checks"]

    sections = {
        "statistik": section("statistik", [
            gate("target_form_coverage", coverage["domestic_form_teams"] == coverage["domestic_form_teams_requested"],
                 "18/18 target teams have a form snapshot", "A target team is missing a complete form snapshot."),
            gate("independent_score_crosscheck", coverage["independent_score_teams"] == coverage["domestic_form_teams_requested"],
                 f"{coverage['independent_score_teams']}/{coverage['domestic_form_teams_requested']} primary target teams cross-checked independently; OpenFootball attempt {coverage['openfootball_independent_score_matches']}/{coverage['openfootball_requested_score_matches']} scores",
                 "Independent score verification does not cover every target team; the OpenFootball attempt is partial or unavailable for the remaining teams."),
            gate("recent_stats_complete", coverage["recent_observations_with_stats"] == coverage["recent_team_match_observations"],
                 f"{coverage['recent_observations_with_stats']}/{coverage['recent_team_match_observations']} observations have stats; raw-page audit {coverage['raw_recent_pages_checked']} pages, anomalies {coverage['recent_page_audit_anomalies']}",
                 "At least one recent team-match observation lacks statistics; raw pages confirm source-level missing fields."),
            gate("npxg_transfer_gate", xg["decision"]["incremental_npxg_retained"],
                 "Frozen npxG transfer gate passed on WSL", "The npxG transfer gate did not pass."),
            gate("provider_robustness", provider["decision"]["provider_robustness_passed"],
                 "Independent provider npxG passes its uncertainty gate", "Provider robustness did not pass."),
        ]),
        "taktik": section("taktik", [
            gate("audited_event_input", pressure["input_audit"]["pressure_events"] > 0,
                 f"{pressure['input_audit']['pressure_events']} pressure events audited", "No audited pressure event input exists."),
            gate("pressure_predictive_gate", pressure["decision"]["retained"],
                 "Pressure feature passed a frozen holdout", "Pressure feature was rejected by its holdout gate."),
            gate("target_tactical_feed", False, "No target pre-kickoff tactical event feed", "Target tactical event/video evidence is unavailable."),
            gate("inter_analyst_labels", False, "No independently labelled target tactical sample", "Inter-analyst tactical labels are missing."),
            gate("pre_kickoff_tactical_validation", False, "No current target tactical feature has a validated holdout", "Current tactical evidence is descriptive only."),
        ]),
        "kondisi_skuad": section("kondisi_skuad", [
            gate("registered_squads", coverage["registered_squad_pairs"] == coverage["official_fixture_pairs_checked"],
                 f"{coverage['registered_squad_pairs']}/{coverage['official_fixture_pairs_checked']} registered-squad pairs", "A target fixture lacks a complete registered squad pair."),
            gate("target_starting_xi", coverage["official_starting_xi"] == coverage["official_fixture_pairs_checked"],
                 f"{coverage['official_starting_xi']}/{coverage['official_fixture_pairs_checked']} official target XIs", "Official target starting XIs are not available for every fixture."),
            gate("recent_lineups_complete", coverage["recent_observations_with_lineups"] == coverage["recent_team_match_observations"],
                 f"{coverage['recent_observations_with_lineups']}/{coverage['recent_team_match_observations']} recent observations have lineups", "Recent lineup coverage is incomplete."),
            gate("current_availability_status", False, "Registered lists are present but injury/suspension status is unverified", "Match-specific player availability is missing."),
            gate("player_impact_holdout", lineup["decision"]["implementation_gate_passed"], "Lineup impact feature passes both holdouts", "Lineup impact feature failed its holdout gates."),
        ]),
        "probabilitas": section("probabilitas", [
            gate("uefa_metrics", bool(uefa["results"].get("locked_combined")), "UEFA locked-period metrics are recorded", "Locked UEFA metrics are missing."),
            gate("classwise_calibration", "blend_classwise_calibration_5_bins" in uefa["results"]["locked_combined"], "Classwise calibration is recorded", "Classwise calibration is missing."),
            gate("market_incremental_value", market["decision"]["retained"], "Internal model adds validated value above opening market", "Internal model was rejected as a market addition."),
            gate("timestamped_uefa_odds", odds_sources["quotes_observed"] > 0,
                 f"{odds_sources['quotes_observed']} timestamped odds quotes observed across {odds_sources['urls_checked']} supplied URLs",
                 "Supplied URLs returned no usable timestamped odds quote."),
            gate("current_market_validation", False, "Current target model-market gate is closed", "The current target model has no validated market edge."),
        ]),
        "validasi_historis": section("validasi_historis", [
            gate("chronological_holdouts", bool(uefa["protocol"]), "Chronological UEFA and transfer protocols are recorded", "A chronological holdout protocol is missing."),
            gate("source_checksums", bool(refresh["source_report_sha256"]) and all(refresh.get("lineage_checks", {}).values()),
                 "Refresh source hashes and lineage checks are recorded", "Source hashes or lineage checks are missing or failed."),
            gate("multi_league_sample", market["sample"]["total_matches"] == 1678, "1,678 domestic market-matched fixtures audited", "The multi-league sample is incomplete."),
            gate("untouched_prospective_scoring", False, "Latest target archive has no final results yet", "A sufficiently sized untouched prospective score is unavailable."),
            gate("publication_timestamps", False, "Historical source publication times are not captured", "First-publication timestamps are missing."),
        ]),
    }
    overall = sum(item["strict_gate_coverage_percent"] for item in sections.values()) / len(sections)
    return {
        "rubric": {
            "meaning": "Strict evidence-gate coverage, not prediction accuracy or probability of winning.",
            "gates_per_section": 5,
            "gate_weight_percent": 20,
            "ninety_five_percent_rule": "A section reaches 95% only when all five mandatory gates pass; partial gates are reported for transparency.",
        },
        "sections": sections,
        "overall_strict_gate_coverage_percent": overall,
        "decision": "No section reaches the 95% evidence threshold.",
        "source_evidence": [
            refresh_path.name, "shot_quality_incremental_epl_wsl.json",
            "xg_provider_predict_epl_2015.json", "pressure_transfer_wsl.json",
            "lineup_continuity_transfer_wsl.json", "market_incremental_holdout.json",
            "uefa_extended_backtest_2026-10-15.json",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, default=Path("evidence"))
    parser.add_argument("--refresh", type=Path,
                        help="Checksum-linked target-refresh manifest; defaults to the newest one in --evidence-dir")
    parser.add_argument("--output", type=Path, default=Path("reports/readiness_audit.json"))
    args = parser.parse_args()
    result = audit(args.evidence_dir, args.refresh)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
