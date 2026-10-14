"""Time-separated results-only 1X2 benchmark on UEFA league-phase matches."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path

from .backtest import Match, bootstrap_logloss_difference, metrics, mix, run_chronological


SEASON_COUNTS = {"2025": 144, "2026": 144, "2027": 18}


def evaluate(data_dir: Path) -> dict:
    manifest = json.loads((data_dir / "manifest.json").read_text())
    for name, source in manifest["files"].items():
        if hashlib.sha256((data_dir / name).read_bytes()).hexdigest() != source["sha256"]:
            raise ValueError(f"UEFA snapshot checksum mismatch: {name}")
    source = json.loads((data_dir / "matches_normalized.json").read_text())
    counts = {season: sum(str(row["season"]) == season for row in source) for season in SEASON_COUNTS}
    if counts != SEASON_COUNTS or len({row["id"] for row in source}) != len(source):
        raise ValueError(f"Unexpected UEFA match sample: {counts}")
    matches = []
    for row in source:
        kickoff = datetime.fromisoformat(row["kickoff"].replace("Z", "+00:00"))
        if kickoff.tzinfo is None or row["home_id"] == row["away_id"]:
            raise ValueError(f"Invalid UEFA team or kickoff: {row['id']}")
        matches.append(Match(str(row["season"]), kickoff.date(), str(row["home_id"]),
                             str(row["away_id"]), row["home_goals"], row["away_goals"], "uefa_api"))
    records = run_chronological(matches)
    by_season = {}
    for season in ("2026", "2027"):
        rows = {name: [] for name in ("base", "elo", "poisson", "blend")}
        for match, predictions in records:
            if match.season != season:
                continue
            for name in ("base", "elo", "poisson"):
                rows[name].append((match, predictions[name]))
            rows["blend"].append((match, mix(predictions["elo"], predictions["poisson"], 0.5)))
        by_season[season] = {"matches": len(rows["base"]),
                             "metrics": {name: metrics(value) for name, value in rows.items()},
                             "blend_minus_base_log_loss": bootstrap_logloss_difference(rows["blend"], rows["base"])}
    return {"source": "https://match.uefa.com/v5/", "source_snapshot": str(data_dir),
            "source_retrieved_at": manifest["retrieved_at"], "sample": counts,
            "protocol": "2024/25 train; 2025/26 chronological validation; 2026/27 MD1 small later holdout. "
                        "Same UTC-date matches are predicted before any that day's results are observed. "
                        "The 0.5 blend weight came from the separate EPL validation, not this UEFA sample.",
            "results": by_season,
            "limitations": ["This uses UEFA league-phase results only; no domestic strength, xG, odds, or squad information.",
                            "The 2026/27 holdout contains only 18 MD1 matches and cannot establish stable calibration.",
                            "The historical API snapshot lacks first-publication timestamps of match results.",
                            "No current fixture predictions or betting selections are validated by this result."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--output", type=Path, default=Path("reports/uefa_backtest.json"))
    args = parser.parse_args()
    data_dir = args.data_dir or sorted(Path(".cache/uefa_history").glob("*/manifest.json"))[-1].parent
    result = evaluate(data_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
