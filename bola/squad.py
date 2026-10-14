"""Validate the timing and completeness of manually verified squad evidence.

This checks a source ledger's structure and chronology. It does not fetch
articles or certify that a URL actually supports a claim.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timedelta
import json
from pathlib import Path
from urllib.parse import urlparse


CLAIMS = {"starting", "bench", "out_injured", "out_suspended", "doubtful", "available"}
OFFICIAL_KINDS = {"club", "league", "competition"}
SOURCE_KINDS = OFFICIAL_KINDS | {"reporter", "data_provider"}


def instant(value: str) -> datetime:
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.utcoffset() is None:
        raise ValueError("Timestamps must include a UTC offset")
    return timestamp


def audit_ledger(ledger: dict) -> dict:
    fixture = ledger["fixture"]
    teams = (fixture["home"], fixture["away"])
    if not all(isinstance(team, str) and team.strip() for team in teams) or teams[0] == teams[1]:
        raise ValueError("Fixture requires two distinct named teams")
    kickoff, as_of = instant(fixture["kickoff"]), instant(ledger["as_of"])
    if as_of >= kickoff:
        raise ValueError("Pre-match squad audit must precede kickoff")
    rows = ledger.get("evidence", [])
    if not isinstance(rows, list):
        raise ValueError("evidence must be a list")
    accepted = []
    excluded_future = []
    for index, row in enumerate(rows):
        if row.get("team") not in teams or not isinstance(row.get("player"), str) or not row["player"].strip():
            raise ValueError(f"Invalid team/player at evidence row {index}")
        if row.get("claim") not in CLAIMS or row.get("source_kind") not in SOURCE_KINDS:
            raise ValueError(f"Invalid claim or source kind at evidence row {index}")
        url = urlparse(row.get("source_url", ""))
        if url.scheme != "https" or not url.hostname:
            raise ValueError(f"Evidence row {index} requires an HTTPS source URL")
        published = instant(row["published_at"])
        retrieved = instant(row["retrieved_at"])
        if retrieved < published:
            raise ValueError(f"Evidence row {index} retrieved before publication")
        item = {**row, "_published": published, "_retrieved": retrieved}
        if published > as_of or retrieved > as_of:
            excluded_future.append(index)
        else:
            accepted.append(item)
    issues = []
    by_team = {}
    for team in teams:
        current = [row for row in accepted if row["team"] == team]
        official_starters = {row["player"] for row in current if row["claim"] == "starting" and row["source_kind"] in OFFICIAL_KINDS}
        official_bench = {row["player"] for row in current if row["claim"] == "bench" and row["source_kind"] in OFFICIAL_KINDS}
        if official_starters and len(official_starters) != 11:
            issues.append(f"{team}: official starting XI incomplete or duplicated ({len(official_starters)}/11)")
        if official_starters & official_bench:
            issues.append(f"{team}: player listed as starter and substitute")
        status_by_player = defaultdict(set)
        for row in current:
            if row["claim"] not in ("starting", "bench") and as_of - row["_published"] <= timedelta(hours=72):
                status_by_player[row["player"]].add(row["claim"])
        conflicts = {player: sorted(claims) for player, claims in status_by_player.items()
                     if "available" in claims and any(claim.startswith("out_") for claim in claims)}
        if conflicts:
            issues.append(f"{team}: conflicting player availability claims require source review")
        by_team[team] = {"accepted_evidence": len(current), "official_starters": len(official_starters),
                         "official_lineup_complete": len(official_starters) == 11 and not bool(official_starters & official_bench),
                         "official_bench": len(official_bench), "fresh_72h_availability_claims": sum(bool(v) for v in status_by_player.values()),
                         "conflicting_players": conflicts}
    return {"fixture": fixture, "as_of": ledger["as_of"], "total_evidence": len(rows),
            "accepted_as_of": len(accepted), "excluded_future_rows": excluded_future,
            "teams": by_team, "issues": issues,
            "limitations": ["Source URLs and source_kind are supplied by the researcher; content was not fetched or authenticated.",
                            "Without a roster universe and verified current reports, availability coverage cannot be scored.",
                            "No player-impact probabilities are inferred from source metadata alone."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit_ledger(json.loads(args.ledger.read_text(encoding="utf-8")))
    formatted = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(formatted, encoding="utf-8")
    print(formatted)


if __name__ == "__main__":
    main()
