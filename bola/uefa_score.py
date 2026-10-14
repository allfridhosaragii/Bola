"""Score an archived pre-kickoff UEFA forecast against completed official results."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

from .uefa_forecast import date_matches


OUTCOMES = ("home", "draw", "away")


def score(archive: dict, results: list[dict], retrieved_at: str, result_sha256: str) -> dict:
    by_id = {str(row["id"]): row for row in results}
    if len(by_id) != len(results):
        raise ValueError("Duplicate UEFA match IDs in result feed")
    forecast_time = datetime.fromisoformat(archive["generated_at"])
    if forecast_time.tzinfo is None:
        raise ValueError("Forecast timestamp lacks timezone")
    games = []
    for prediction in archive["predictions"]:
        match_id = prediction["match_id"]
        row = by_id.get(match_id)
        if row is None or row.get("status") != "FINISHED":
            raise ValueError(f"Official final result unavailable for {match_id}")
        kickoff = datetime.fromisoformat(prediction["kickoff"].replace("Z", "+00:00"))
        if not forecast_time < kickoff or row["kickOffTime"]["dateTime"] != prediction["kickoff"]:
            raise ValueError(f"Forecast timing or fixture mismatch for {match_id}")
        if (row["homeTeam"]["internationalName"] != prediction["home"] or
                row["awayTeam"]["internationalName"] != prediction["away"]):
            raise ValueError(f"Teams changed in result {match_id}")
        regular = row["score"]["regular"]
        home, away = regular["home"], regular["away"]
        if not all(type(x) is int and x >= 0 for x in (home, away)):
            raise ValueError(f"Invalid final score for {match_id}")
        outcome = 0 if home > away else 1 if home == away else 2
        metrics = {}
        for model, probabilities in prediction["probabilities_h_d_a"].items():
            if len(probabilities) != 3 or any(not 0 <= p <= 1 for p in probabilities) or abs(sum(probabilities) - 1) > 2e-6:
                raise ValueError(f"Invalid probabilities for {match_id}, {model}")
            metrics[model] = {"log_loss": -math.log(max(1e-12, probabilities[outcome])),
                              "brier": sum((p - int(i == outcome)) ** 2 for i, p in enumerate(probabilities)),
                              "correct_top_probability": probabilities.index(max(probabilities)) == outcome}
        games.append({"match_id": match_id, "home": prediction["home"], "away": prediction["away"],
                      "goals": [home, away], "outcome": OUTCOMES[outcome], "metrics": metrics})
    models = games[0]["metrics"].keys() if games else ()
    aggregate = {model: {name: sum(game["metrics"][model][name] for game in games) / len(games)
                         for name in ("log_loss", "brier", "correct_top_probability")} for model in models}
    return {"forecast_generated_at": archive["generated_at"], "scored_at": retrieved_at,
            "result_sha256": result_sha256, "n": len(games), "aggregate": aggregate,
            "games": games, "warning": "Seven matches are a small prospective sample; do not infer calibration or betting value."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--results-json", type=Path, help="Use a saved raw UEFA API response")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Score report already exists: {args.output}")
    archive = json.loads(args.archive.read_text(encoding="utf-8"))
    if args.results_json:
        raw = args.results_json.read_bytes()
    else:
        raw, _ = date_matches("2026-10-14")
    retrieved_at = datetime.now(timezone.utc).isoformat()
    report = score(archive, json.loads(raw), retrieved_at, hashlib.sha256(raw).hexdigest())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
