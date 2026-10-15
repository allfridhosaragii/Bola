"""Check whether open shot endpoints can support a defensible post-shot proxy."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

from .statsbomb import SOURCE_COMMIT


def summarize(folder: Path) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text())
    if manifest["source_commit"] != SOURCE_COMMIT:
        raise ValueError("Unexpected source commit")
    raw_matches = (folder / "matches_2_27.json").read_bytes()
    if hashlib.sha256(raw_matches).hexdigest() != manifest["matches_sha256"]:
        raise ValueError("Match metadata checksum mismatch")
    matches = json.loads(raw_matches)
    if len(matches) != 380 or len({row["match_id"] for row in matches}) != 380:
        raise ValueError("Expected complete EPL season")
    counts: Counter[str] = Counter()
    outcomes: Counter[str] = Counter()
    keeper_totals: dict[int, dict] = {}
    for match in matches:
        name = f"events_{match['match_id']}.json"
        body = (folder / name).read_bytes()
        if hashlib.sha256(body).hexdigest() != manifest["events_sha256"][str(match["match_id"])]:
            raise ValueError(f"Event checksum mismatch: {name}")
        for event in json.loads(body):
            if event["type"]["name"] != "Shot" or event["period"] not in (1, 2, 3, 4):
                continue
            shot = event["shot"]
            outcome = shot["outcome"]["name"]
            counts["shots"] += 1
            outcomes[outcome] += 1
            counts["psxg_field_present"] += any(key in shot for key in
                                                ("statsbomb_psxg", "post_shot_xg", "psxg"))
            if outcome not in ("Saved", "Goal"):
                continue
            counts["goal_or_saved"] += 1
            endpoint = shot.get("end_location", [])
            if len(endpoint) != 3:
                raise ValueError(f"Missing 3D endpoint on {outcome} event")
            counts[f"{outcome.lower()}_3d"] += 1
            counts[f"{outcome.lower()}_outside_nominal_goal_y"] += endpoint[1] < 36 or endpoint[1] > 44
            visible_keepers = [player for player in shot.get("freeze_frame", [])
                               if not player.get("teammate") and player.get("position", {}).get("name") == "Goalkeeper"]
            counts["one_opponent_keeper_visible"] += len(visible_keepers) == 1
            if len(visible_keepers) == 1:
                keeper = visible_keepers[0]["player"]
                keeper_id = keeper["id"]
                entry = keeper_totals.setdefault(keeper_id, {"player_id": keeper_id,
                                                               "name": keeper["name"], "saved": 0,
                                                               "goals": 0, "pre_shot_xg": 0.0})
                if entry["name"] != keeper["name"]:
                    raise ValueError(f"Goalkeeper ID changed name: {keeper_id}")
                entry["saved" if outcome == "Saved" else "goals"] += 1
                entry["pre_shot_xg"] += shot["statsbomb_xg"]
    if counts["shots"] != 9908 or outcomes["Goal"] != 988:
        raise ValueError("Shot sample disagrees with full-season xG audit")
    keeper_rows = []
    for entry in keeper_totals.values():
        n = entry["saved"] + entry["goals"]
        rate = entry["saved"] / n
        z = 1.96
        denominator = 1 + z * z / n
        midpoint = (rate + z * z / (2 * n)) / denominator
        halfwidth = z * math.sqrt(rate * (1 - rate) / n + z * z / (4 * n * n)) / denominator
        keeper_rows.append({**entry, "pre_shot_xg": round(entry["pre_shot_xg"], 3),
                            "on_target_shots_with_keeper_visible": n,
                            "save_rate": round(rate, 4),
                            "save_rate_wilson_95": [round(midpoint - halfwidth, 4),
                                                    round(midpoint + halfwidth, 4)]})
    keeper_rows.sort(key=lambda row: (-row["on_target_shots_with_keeper_visible"], row["player_id"]))
    if sum(row["on_target_shots_with_keeper_visible"] for row in keeper_rows) != counts["one_opponent_keeper_visible"]:
        raise ValueError("Goalkeeper coverage disagrees with event audit")
    return {"source": "StatsBomb open-data", "commit": SOURCE_COMMIT,
            "competition": "EPL 2015/16", "matches": 380, "counts": dict(counts),
            "outcomes": dict(outcomes), "nominal_goal_lateral_interval": [36, 44],
            "goalkeepers": keeper_rows,
            "interpretation": "At least some saved-shot end locations are not interchangeable with goal crossing points. "
                              "Do not train a post-shot quality proxy from these endpoints without an explicit event definition and validation.",
            "limitations": ["The 36–44 lateral interval is a nominal StatsBomb goal mouth, not a full event-schema audit.",
                            "No vendor post-shot xG field is present in this sample.",
                            "Save rates omit 85 Saved/Goal shots without exactly one opposing goalkeeper in the freeze frame.",
                            "Goalkeeper save rate and faced pre-shot xG are descriptive, not post-shot quality or a validated goals-prevented metric."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(".cache/statsbomb_epl_2015"))
    parser.add_argument("--output", type=Path, default=Path("reports/shot_endpoints.json"))
    args = parser.parse_args()
    report = summarize(args.data_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
