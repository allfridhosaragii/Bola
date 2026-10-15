"""Compare StatsBomb and Understat shot xG on the same EPL 2015/16 fixtures."""

from __future__ import annotations

import argparse
import csv
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import random

from .statsbomb import SOURCE_COMMIT


UNDERSTAT_SHA256 = "cdde2434aa027d4cbb8e9ead6510143d219a3df3575daa0f14a18937fece8f4e"
SB_TO_UNDERSTAT = {"AFC Bournemouth": "Bournemouth", "Leicester City": "Leicester",
                   "Norwich City": "Norwich", "Stoke City": "Stoke",
                   "Swansea City": "Swansea", "Tottenham Hotspur": "Tottenham",
                   "West Ham United": "West Ham"}
OUTCOMES = {"BlockedShot", "MissedShots", "SavedShot", "Goal", "ShotOnPost", "OwnGoal"}


def _summary() -> dict:
    return {"shots": [0, 0], "goals": [0, 0], "xg": [0.0, 0.0]}


def understat_rows(folder: Path) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text())
    if manifest["sha256"] != UNDERSTAT_SHA256:
        raise ValueError("Unexpected Understat mirror checksum in manifest")
    body = (folder / "shots.csv").read_bytes()
    if hashlib.sha256(body).hexdigest() != UNDERSTAT_SHA256:
        raise ValueError("Understat mirror source checksum mismatch")
    matches = {}
    seen_shots = set()
    match_ids = {}
    own_goals = 0
    for row in csv.DictReader(body.decode("utf-8-sig").splitlines()):
        shot_id = row["id"]
        if shot_id in seen_shots:
            raise ValueError(f"Duplicate Understat shot ID: {shot_id}")
        seen_shots.add(shot_id)
        pair = row["h_team"], row["a_team"]
        match_id = row["match_id"]
        if match_id in match_ids and match_ids[match_id] != pair:
            raise ValueError(f"Understat match ID changes teams: {match_id}")
        match_ids[match_id] = pair
        score = int(float(row["h_goals"])), int(float(row["a_goals"]))
        day = date.fromisoformat(row["date"][:10])
        entry = matches.setdefault(pair, {"match_id": match_id, "date": day.isoformat(),
                                           "score": score, **_summary()})
        if (entry["match_id"], entry["date"], entry["score"]) != (match_id, day.isoformat(), score):
            raise ValueError(f"Conflicting Understat fixture: {pair}")
        side = {"h": 0, "a": 1}.get(row["h_a"])
        if side is None or row["result"] not in OUTCOMES:
            raise ValueError(f"Unexpected Understat side or outcome: {shot_id}")
        xg = float(row["xG"])
        if not math.isfinite(xg) or not 0 <= xg <= 1:
            raise ValueError(f"Invalid Understat xG: {shot_id}")
        if row["result"] == "OwnGoal":
            if xg != 0:
                raise ValueError(f"Own goal has nonzero shot xG: {shot_id}")
            own_goals += 1
            continue
        entry["shots"][side] += 1
        entry["goals"][side] += row["result"] == "Goal"
        entry["xg"][side] += xg
    if len(matches) != 380 or len(match_ids) != 380 or len(seen_shots) != 9819 or own_goals != 38:
        raise ValueError("Understat mirror does not contain expected complete season")
    return matches


def statsbomb_rows(folder: Path) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text())
    if manifest["source_commit"] != SOURCE_COMMIT:
        raise ValueError("Unexpected StatsBomb source commit")
    body = (folder / "matches_2_27.json").read_bytes()
    if hashlib.sha256(body).hexdigest() != manifest["matches_sha256"]:
        raise ValueError("StatsBomb match metadata checksum mismatch")
    matches = json.loads(body)
    if len(matches) != 380 or len({row["match_id"] for row in matches}) != 380:
        raise ValueError("Expected 380 unique StatsBomb matches")
    rows = {}
    for match in matches:
        names = match["home_team"]["home_team_name"], match["away_team"]["away_team_name"]
        pair = tuple(SB_TO_UNDERSTAT.get(name, name) for name in names)
        if pair in rows:
            raise ValueError(f"Duplicate StatsBomb home-away fixture: {pair}")
        teams = match["home_team"]["home_team_id"], match["away_team"]["away_team_id"]
        entry = {"match_id": match["match_id"], "date": match["match_date"],
                 "score": (match["home_score"], match["away_score"]), **_summary()}
        event_body = (folder / f"events_{match['match_id']}.json").read_bytes()
        if hashlib.sha256(event_body).hexdigest() != manifest["events_sha256"][str(match["match_id"])]:
            raise ValueError(f"StatsBomb event checksum mismatch: {match['match_id']}")
        for event in json.loads(event_body):
            if event["type"]["name"] != "Shot" or event["period"] not in (1, 2, 3, 4):
                continue
            team = event["team"]["id"]
            if team not in teams:
                raise ValueError(f"Shot team not in fixture: {match['match_id']}")
            side = teams.index(team)
            xg = event["shot"]["statsbomb_xg"]
            if not isinstance(xg, (int, float)) or not math.isfinite(xg) or not 0 <= xg <= 1:
                raise ValueError(f"Invalid StatsBomb xG: {event['id']}")
            entry["shots"][side] += 1
            entry["goals"][side] += event["shot"]["outcome"]["name"] == "Goal"
            entry["xg"][side] += xg
        rows[pair] = entry
    if sum(sum(row["shots"]) for row in rows.values()) != 9908:
        raise ValueError("StatsBomb shot sample disagrees with full-season audit")
    return rows


def _correlation(xs: list[float], ys: list[float]) -> float:
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    numerator = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denominator = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return numerator / denominator


def compare(sb: dict, understat: dict) -> dict:
    if sb.keys() != understat.keys() or len(sb) != 380:
        raise ValueError("Providers do not cover the same 380 home-away fixtures")
    rows = []
    for pair in sorted(sb):
        a, b = sb[pair], understat[pair]
        days_apart = abs((date.fromisoformat(a["date"]) - date.fromisoformat(b["date"])).days)
        if a["score"] != b["score"] or days_apart > 1:
            raise ValueError(f"Score or date mismatch between providers: {pair}")
        rows.append({"home": pair[0], "away": pair[1], "statsbomb_match_id": a["match_id"],
                     "understat_match_id": b["match_id"], "statsbomb_date": a["date"],
                     "understat_date": b["date"], "date_difference_days": days_apart,
                     "score": a["score"], "statsbomb": {k: a[k] for k in ("shots", "goals", "xg")},
                     "understat": {k: b[k] for k in ("shots", "goals", "xg")}})
    sx = [v for row in rows for v in row["statsbomb"]["xg"]]
    ux = [v for row in rows for v in row["understat"]["xg"]]
    differences = [x - y for x, y in zip(sx, ux)]
    rng = random.Random(20261015)
    boot = []
    for _ in range(1000):
        picked = [rows[rng.randrange(len(rows))] for _ in rows]
        boot.append(sum(a - b for row in picked for a, b in
                        zip(row["statsbomb"]["xg"], row["understat"]["xg"])) / 760)
    boot.sort()
    counts = {"fixtures_matched": len(rows),
              "date_differed_by_one_day": sum(row["date_difference_days"] == 1 for row in rows),
              "team_game_shot_counts_equal": sum(row["statsbomb"]["shots"][i] == row["understat"]["shots"][i]
                                                 for row in rows for i in (0, 1)),
              "fixture_goal_event_counts_differ": sum(row["statsbomb"]["goals"] != row["understat"]["goals"]
                                                     for row in rows)}
    totals = {provider: {field: sum(sum(row[provider][field]) for row in rows)
                         for field in ("shots", "goals", "xg")}
              for provider in ("statsbomb", "understat")}
    if totals["statsbomb"]["goals"] != 988 or totals["understat"]["goals"] != 988:
        raise ValueError("Goal event count disagrees with known season audit")
    return {"sources": {"statsbomb_commit": SOURCE_COMMIT, "understat_mirror_sha256": UNDERSTAT_SHA256},
            "counts": counts, "totals": totals,
            "team_game_xg": {"n": 760, "pearson_correlation": round(_correlation(sx, ux), 4),
                             "mean_absolute_difference": round(sum(map(abs, differences)) / 760, 4),
                             "mean_statsbomb_minus_understat": round(sum(differences) / 760, 4),
                             "paired_fixture_bootstrap_95": [round(boot[24], 4), round(boot[975], 4)]},
            "matches": rows,
            "limitations": ["The Understat CSV is a public community mirror; source publication times and vendor model training provenance are unknown.",
                            "Shot definitions differ. The comparison matches fixtures and team totals, not individual shots.",
                            "OwnGoal rows in Understat are excluded from shot counts and xG; official final scores still include own goals.",
                            "A 2015/16 EPL comparison does not establish current xG quality for UEFA clubs."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--statsbomb-dir", type=Path, default=Path(".cache/statsbomb_epl_2015"))
    parser.add_argument("--understat-dir", type=Path, default=Path(".cache/understat_epl_2015"))
    parser.add_argument("--output", type=Path, default=Path("reports/xg_provider_compare.json"))
    args = parser.parse_args()
    report = compare(statsbomb_rows(args.statsbomb_dir), understat_rows(args.understat_dir))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("counts", "totals", "team_game_xg")}, indent=2))


if __name__ == "__main__":
    main()
