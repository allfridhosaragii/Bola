"""Assemble one auditable pre-match analyst report from frozen evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path

from .squad import instant


OUTCOMES = ("home", "draw", "away")


def complete_form(team: dict | None) -> bool:
    if not team:
        return False
    for size in (5, 10, 20):
        window = team.get("windows", {}).get(str(size), {})
        record = window.get("record", {})
        counts = [record.get(key) for key in ("W", "D", "L")]
        if not all(type(value) is int and value >= 0 for value in counts):
            return False
        if sum(counts) != size:
            return False
    return True


def assemble(forecast: dict, form: dict, squad: dict, as_of: str,
             markets: list[dict] | None = None, schedule: dict | None = None,
             recent_stats: dict | None = None) -> dict:
    now = instant(as_of)
    generated = instant(forecast["generated_at"])
    if generated > now:
        raise ValueError("Forecast was generated after report time")
    if form["as_of"] and instant(form["as_of"]) > now:
        raise ValueError("Form audit was generated after report time")
    if instant(squad["refreshed_at"]) > now:
        raise ValueError("UEFA target snapshot was generated after report time")
    if schedule and instant(schedule["generated_at"]) > now:
        raise ValueError("Schedule-load audit was generated after report time")
    if schedule and (instant(schedule["forecast_generated_at"]) != generated or
                     schedule["target_date_utc"] != forecast["target_date_utc"]):
        raise ValueError("Schedule-load audit belongs to a different forecast")
    if recent_stats and (instant(recent_stats["generated_at"]) > now or
                         instant(recent_stats["source_retrieved_at_latest"]) > now):
        raise ValueError("Recent-match statistics are newer than report time")

    predictions = {row["match_id"]: row for row in forecast["predictions"]}
    fixtures = {row["match_id"]: row for row in squad["fixtures"]}
    if len(predictions) != len(forecast["predictions"]) or len(fixtures) != len(squad["fixtures"]):
        raise ValueError("Duplicate match ID in forecast or UEFA snapshot")
    if set(predictions) != set(fixtures):
        raise ValueError("Forecast and UEFA snapshot match sets disagree")

    market_by_id = {}
    for market in markets or []:
        mid = market["match_id"]
        if mid in market_by_id:
            raise ValueError(f"Duplicate market snapshot for match: {mid}")
        market_by_id[mid] = market
    if set(market_by_id) - set(predictions):
        raise ValueError("Market snapshot contains a match outside the forecast")
    schedule_teams = schedule["teams"] if schedule else {}
    recent_teams = recent_stats["teams"] if recent_stats else {}
    schedule_matches = {row["match_id"]: row for row in schedule.get("target_fixture_crosscheck", [])} if schedule else {}
    if schedule and set(schedule_matches) != set(predictions):
        raise ValueError("Schedule-load and forecast match sets disagree")

    rows = []
    for mid, prediction in predictions.items():
        fixture = fixtures[mid]
        if ((prediction["home"], prediction["away"]) != (fixture["home"], fixture["away"]) or
                instant(prediction["kickoff"]) != instant(fixture["kickoff"])):
            raise ValueError(f"Forecast and official fixture identity disagree: {mid}")
        kickoff = instant(prediction["kickoff"])
        before_kickoff = now < kickoff
        fixture_time = instant(fixture["fixture_retrieved_at"])
        lineup_time = instant(fixture["lineup_retrieved_at"])
        if fixture_time > now or lineup_time > now:
            raise ValueError(f"UEFA evidence is newer than report time: {mid}")
        registered = fixture.get("registered_players") or {}
        team_form = {name: form["teams"].get(name) for name in (prediction["home"], prediction["away"])}
        team_schedule = {name: schedule_teams.get(name) for name in (prediction["home"], prediction["away"])}
        team_recent = {}
        for name in (prediction["home"], prediction["away"]):
            recent = recent_teams.get(name)
            team_recent[name] = ({key: recent.get(key) for key in
                                  ("stats_available_games", "lineup_available_games", "distinct_starters",
                                   "core_starters", "mean_starter_changes", "averages")}
                                 if recent else None)
        if schedule:
            check = schedule_matches[mid]
            if (check["home"], check["away"]) != (prediction["home"], prediction["away"]):
                raise ValueError(f"Schedule-load and forecast identity disagree: {mid}")
        market = market_by_id.get(mid)
        market_valid = False
        if market:
            if ((market["home"], market["away"]) != (prediction["home"], prediction["away"]) or
                    instant(market["kickoff"]) != kickoff):
                raise ValueError(f"Market and forecast fixture identity disagree: {mid}")
            if instant(market["analyzed_at"]) > now:
                raise ValueError(f"Market report is newer than analyst report: {mid}")
            observed = instant(market["quote_observed_at_transcribed"])
            if observed > instant(market["analyzed_at"]) or observed >= kickoff:
                raise ValueError(f"Invalid market observation time: {mid}")
            market_valid = bool(now - observed <= timedelta(minutes=10)
                                and market["screenshot_sha256"])
        probabilities = prediction["probabilities_h_d_a"]["blend"]
        if (len(probabilities) != 3 or
                any(type(value) not in (int, float) or not math.isfinite(value)
                    or not 0 <= value <= 1 for value in probabilities) or
                abs(sum(probabilities) - 1) > 2e-6):
            raise ValueError(f"Invalid frozen probabilities: {mid}")
        gates = {
            "before_kickoff": before_kickoff,
            "official_fixture_upcoming": fixture["status_at_retrieval"] == "Upcoming",
            "official_fixture_snapshot_within_30m": now - fixture_time <= timedelta(minutes=30),
            "domestic_form_5_10_20_for_both": all(complete_form(team) for team in team_form.values()),
            "schedule_load_for_both": all(team_schedule.values()),
            "recent_match_stats_for_both": all(row and row.get("stats_available_games", 0) > 0
                                                for row in team_recent.values()),
            "registered_squad_for_both": set(registered) == {prediction["home"], prediction["away"]}
                                                and all(registered.values()),
            "official_starting_xi_before_kickoff": bool(fixture["official_starting_xi_before_kickoff"]),
            "fresh_market_screenshot": market_valid,
            "validated_current_tactical_evidence": False,
            "model_validated_against_current_market": False,
        }
        blocking = [name for name, passed in gates.items() if not passed]
        rows.append({
            "match_id": mid, "home": prediction["home"], "away": prediction["away"],
            "kickoff": prediction["kickoff"],
            "probabilities_h_d_a_exploratory": probabilities,
            "top_probability": {"outcome": OUTCOMES[probabilities.index(max(probabilities))],
                                "probability": max(probabilities)},
            "historical_uefa_appearances": prediction["historical_uefa_appearances"],
            "form": team_form,
            "schedule_load": team_schedule,
            "recent_match_stats": team_recent,
            "registered_players": registered,
            "flagged_players": fixture.get("flagged_players"),
            "lineup_status": fixture["lineup_status"],
            "market": market,
            "evidence_gates": gates,
            "blocking_gates": blocking,
            "selection_status": "eligible_for_review" if not blocking else "no_selection",
        })
    return {
        "generated_at": as_of,
        "target_date_utc": forecast["target_date_utc"],
        "matches": rows,
        "summary": {
            "matches": len(rows),
            "eligible_for_review": sum(row["selection_status"] == "eligible_for_review" for row in rows),
            "no_selection": sum(row["selection_status"] == "no_selection" for row in rows),
            "form_complete": sum(row["evidence_gates"]["domestic_form_5_10_20_for_both"] for row in rows),
            "schedule_load_complete": sum(row["evidence_gates"]["schedule_load_for_both"] for row in rows),
            "recent_match_stats_complete": sum(row["evidence_gates"]["recent_match_stats_for_both"] for row in rows),
            "official_lineups": sum(row["evidence_gates"]["official_starting_xi_before_kickoff"] for row in rows),
            "fresh_markets": sum(row["evidence_gates"]["fresh_market_screenshot"] for row in rows),
        },
        "decision_rule": "A match remains no_selection while any evidence gate is false. "
                         "Exploratory probabilities are recorded for prospective scoring, not treated as selections.",
        "limitations": [
            "Domestic form is descriptive and is not an input to the frozen UEFA probability model.",
            "Player badges do not prove match-specific absence, injury severity, or starting status.",
            "Schedule load counts team fixtures but does not measure player minutes, travel, sleep, or fatigue.",
            "Recent match statistics are descriptive, come from one provider, and are not a validated tactical model.",
            "No current tactical feature has passed a predictive holdout test.",
            "The results-only UEFA model has not demonstrated a stable edge over current market prices.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--forecast", type=Path, required=True)
    parser.add_argument("--form", type=Path, required=True)
    parser.add_argument("--squad", type=Path, required=True)
    parser.add_argument("--market", type=Path, action="append", default=[])
    parser.add_argument("--schedule", type=Path)
    parser.add_argument("--recent-stats", type=Path)
    parser.add_argument("--as-of", default=datetime.now(timezone.utc).isoformat())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Analyst report already exists: {args.output}")
    inputs = {"forecast": args.forecast, "form": args.form, "squad": args.squad}
    forecast, form, squad = (json.loads(path.read_text(encoding="utf-8")) for path in inputs.values())
    markets = [json.loads(path.read_text(encoding="utf-8")) for path in args.market]
    schedule = json.loads(args.schedule.read_text(encoding="utf-8")) if args.schedule else None
    recent_stats = json.loads(args.recent_stats.read_text(encoding="utf-8")) if args.recent_stats else None
    result = assemble(forecast, form, squad, args.as_of, markets, schedule, recent_stats)
    result["input_sha256"] = {name: hashlib.sha256(path.read_bytes()).hexdigest()
                              for name, path in inputs.items()}
    result["market_input_sha256"] = [hashlib.sha256(path.read_bytes()).hexdigest() for path in args.market]
    result["schedule_input_sha256"] = hashlib.sha256(args.schedule.read_bytes()).hexdigest() if args.schedule else None
    result["recent_stats_input_sha256"] = (hashlib.sha256(args.recent_stats.read_bytes()).hexdigest()
                                           if args.recent_stats else None)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
