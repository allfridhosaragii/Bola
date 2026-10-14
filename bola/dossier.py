"""Combine time-stamped fixture, squad, and domestic form evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from .squad import instant


WIB = ZoneInfo("Asia/Jakarta")


def assemble(fixtures: dict, squads: dict, form: dict, as_of: str, lineups: dict | None = None) -> dict:
    now = instant(as_of)
    cutoff = now.astimezone(WIB).date().isoformat()
    if form["cutoff_exclusive_date_wib"] != cutoff:
        raise ValueError("Domestic form cutoff date must equal the as-of WIB calendar date")
    for name, source in form["snapshot_manifest"]["files"].items():
        if instant(source["retrieved_at"]) > now:
            raise ValueError(f"Domestic source appears after as-of time: {name}")
    squads_by_id = {row["match_id"]: row for row in squads["fixtures"]}
    if len(squads_by_id) != len(squads["fixtures"]):
        raise ValueError("Duplicate UEFA squad match ID")
    lineups_by_id = {row["match_id"]: row for row in lineups["fixtures"]} if lineups else {}
    if lineups and len(lineups_by_id) != len(lineups["fixtures"]):
        raise ValueError("Duplicate UEFA API lineup match ID")
    results = []
    for fixture in fixtures["fixtures"]:
        if instant(fixture["retrieved_at"]) > now:
            raise ValueError(f"UEFA fixture source appears after as-of: {fixture['match_id']}")
        squad = squads_by_id.get(fixture["match_id"])
        lineup = lineups_by_id.get(fixture["match_id"])
        if squad and instant(squad["retrieved_at"]) > now:
            raise ValueError(f"UEFA squad source appears after as-of: {fixture['match_id']}")
        if lineup and instant(lineup["retrieved_at"]) > now:
            raise ValueError(f"UEFA lineup source appears after as-of: {fixture['match_id']}")
        if lineup and (lineup["home"] != fixture["home"] or lineup["away"] != fixture["away"] or
                       instant(lineup["kickoff"]) != instant(fixture["kickoff"])):
            raise ValueError(f"UEFA API lineup and fixture metadata disagree: {fixture['match_id']}")
        if squad and (squad.get("home", fixture["home"]) != fixture["home"] or
                      squad.get("away", fixture["away"]) != fixture["away"] or
                      instant(squad.get("kickoff", fixture["kickoff"])) != instant(fixture["kickoff"])):
            raise ValueError(f"UEFA squad and fixture metadata disagree: {fixture['match_id']}")
        kickoff = instant(fixture["kickoff"])
        before_kickoff = now < kickoff
        teams = {}
        for name in (fixture["home"], fixture["away"]):
            source_team = squad["teams"].get(name) if squad else None
            teams[name] = {"domestic_form": form["teams"].get(name),
                           "registered_squad_count": source_team["registered_players"] if source_team else None,
                           "uefa_badge_players": source_team["flagged_players"] if source_team else None}
        gates = {"uefa_fixture_upcoming_at_snapshot": fixture["status"] == "Upcoming",
                 "uefa_fixture_snapshot_within_30m": now - instant(fixture["retrieved_at"]) <= timedelta(minutes=30),
                 "uefa_squad_snapshot_within_30m": bool(squad and now - instant(squad["retrieved_at"]) <= timedelta(minutes=30)),
                 "before_official_kickoff": before_kickoff,
                 "domestic_form_for_both": all(teams[name]["domestic_form"] for name in teams),
                 "uefa_squad_page_for_both": all(teams[name]["registered_squad_count"] for name in teams),
                 "official_starting_xi": bool(lineup and lineup["official_starting_xi"] and
                                              lineup["before_kickoff_at_retrieval"] and
                                              now - instant(lineup["retrieved_at"]) <= timedelta(minutes=30)),
                 "current_odds_with_retrieval_time": False,
                 "validated_cross_league_probability_model": False}
        results.append({"match_id": fixture["match_id"], "home": fixture["home"], "away": fixture["away"],
                        "kickoff_wib": kickoff.astimezone(WIB).isoformat(), "uefa_status_at_snapshot": fixture["status"],
                        "uefa_fixture_url": fixture["url"], "uefa_fixture_retrieved_at": fixture["retrieved_at"],
                        "uefa_squad_url": squad["url"] if squad else None,
                        "uefa_squad_retrieved_at": squad["retrieved_at"] if squad else None,
                        "uefa_lineup_status": lineup["lineup_status"] if lineup else None,
                        "uefa_lineup_retrieved_at": lineup["retrieved_at"] if lineup else None,
                        "uefa_lineup_url": lineup["lineup_url"] if lineup else None,
                        "teams": teams, "evidence_gates": gates,
                        "ready_for_two_predictions": all(gates.values())})
    return {"as_of": as_of, "fixtures": results,
            "limitations": ["Form covers domestic league matches only and is not a cross-league team strength comparison.",
                            "UEFA player badges do not confirm a matchday absence or a starting XI.",
                            "No time-stamped odds for these fixtures or validated cross-league model has been supplied.",
                            "Live match status must be refreshed; snapshot status is not a current live feed."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=Path("reports/uefa_fixtures.json"))
    parser.add_argument("--squads", type=Path, default=Path("reports/uefa_squads.json"))
    parser.add_argument("--form", type=Path, default=Path("reports/current_form.json"))
    parser.add_argument("--lineups", type=Path)
    parser.add_argument("--as-of", default=datetime.now(timezone.utc).isoformat())
    parser.add_argument("--output", type=Path, default=Path("reports/prematch_dossier.json"))
    args = parser.parse_args()
    result = assemble(*(json.loads(path.read_text(encoding="utf-8")) for path in
                        (args.fixtures, args.squads, args.form)), as_of=args.as_of,
                      lineups=json.loads(args.lineups.read_text(encoding="utf-8")) if args.lineups else None)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
