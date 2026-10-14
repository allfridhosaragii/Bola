"""Descriptive link between recovery location and immediate shots in WC 2022."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import random

from .statsbomb import SOURCE_COMMIT


def clock(event: dict) -> int:
    return 60 * event["minute"] + event["second"]


def summarize_match(events: list[dict], seconds: int = 15) -> dict[str, dict]:
    """Count only the first successful tagged recovery of a team possession."""
    recoveries = {}
    shots = defaultdict(list)
    for index, event in enumerate(events):
        if event["period"] not in (1, 2, 3, 4):
            continue
        key = event["period"], event["possession"], event["team"]["id"]
        kind = event["type"]["name"]
        if (kind == "Ball Recovery" and event.get("location") and
                not event.get("ball_recovery", {}).get("recovery_failure")):
            recoveries.setdefault(key, (index, event))
        elif kind == "Shot":
            shots[key].append((index, event))
    result = {side: {"recoveries": 0, "shot_sequences": 0, "shots": 0, "xg": 0.0}
              for side in ("own_half", "opponent_half")}
    for key, (recovery_index, event) in recoveries.items():
        x = event["location"][0]
        if not 0 <= x <= 120:
            raise ValueError("Recovery coordinate outside StatsBomb pitch")
        side = "opponent_half" if x >= 60 else "own_half"
        bucket = result[side]
        bucket["recoveries"] += 1
        following = [shot for index, shot in shots[key]
                     if index > recovery_index and 0 <= clock(shot) - clock(event) <= seconds]
        bucket["shot_sequences"] += bool(following)
        bucket["shots"] += len(following)
        bucket["xg"] += sum(shot["shot"]["statsbomb_xg"] for shot in following)
    return result


def aggregate(rows: list[dict]) -> dict:
    totals = {side: {key: sum(row[side][key] for row in rows)
                     for key in ("recoveries", "shot_sequences", "shots", "xg")}
              for side in ("own_half", "opponent_half")}
    for values in totals.values():
        count = values["recoveries"]
        values["shot_sequence_rate"] = values["shot_sequences"] / count if count else None
        values["xg_per_100_recoveries"] = 100 * values["xg"] / count if count else None
    return totals


def report(data_dir: Path, seconds: int = 15) -> dict:
    if seconds <= 0:
        raise ValueError("Window must be positive")
    manifest = json.loads((data_dir / "worldcup_sha256.json").read_text())
    if manifest["commit"] != SOURCE_COMMIT:
        raise ValueError("Unexpected source commit")
    matches = json.loads((data_dir / "matches_43_106.json").read_text())
    if len(matches) != 64 or len({row["match_id"] for row in matches}) != 64:
        raise ValueError("Expected 64 unique matches")
    rows = []
    for match in matches:
        name = f"events_{match['match_id']}.json"
        body = (data_dir / name).read_bytes()
        if hashlib.sha256(body).hexdigest() != manifest["files"][name]:
            raise ValueError(f"Event checksum mismatch: {name}")
        rows.append(summarize_match(json.loads(body), seconds))
    totals = aggregate(rows)
    rng = random.Random(20261015)
    differences = []
    for _ in range(1000):
        sample = aggregate([rows[rng.randrange(len(rows))] for _ in rows])
        high = sample["opponent_half"]["shot_sequence_rate"]
        low = sample["own_half"]["shot_sequence_rate"]
        if high is not None and low is not None:
            differences.append(high - low)
    differences.sort()
    return {"source": "https://github.com/statsbomb/open-data", "commit": SOURCE_COMMIT,
            "competition": "2022 FIFA World Cup", "matches": len(matches),
            "shot_window_seconds": seconds, "by_recovery_half": totals,
            "shot_sequence_rate_difference_opponent_minus_own":
                totals["opponent_half"]["shot_sequence_rate"] - totals["own_half"]["shot_sequence_rate"],
            "match_bootstrap_95pct_interval_difference": [differences[25], differences[974]],
            "limitations": [
                "Counts first successful tagged Ball Recovery per team possession; untagged turnovers are absent.",
                "A shot must follow the recovery within the time window in the same team possession and period.",
                "Shot sequence rate is descriptive; field position, score state, and match context can confound it.",
                "Recovery is not identical to a successful press, and data cannot establish tactical intent or causality.",
                "One national-team tournament cannot validate a UEFA club prediction feature.",
            ]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(".cache/statsbomb"))
    parser.add_argument("--seconds", type=int, default=15)
    parser.add_argument("--output", type=Path, default=Path("reports/recovery.json"))
    args = parser.parse_args()
    result = report(args.data_dir, args.seconds)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
