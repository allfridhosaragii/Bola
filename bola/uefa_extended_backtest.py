"""Evaluate a results-only model using complete UEFA Champions League histories."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path

from .backtest import Match, OUTCOMES, bootstrap_logloss_difference, metrics, mix, normalize, run_chronological


EXPECTED = {"2023": 214, "2024": 214, "2025": 279, "2026": 281, "2027": 126}
WEIGHT_CANDIDATES = (0.0, 0.25, 0.5, 0.75, 1.0)


def classwise_calibration(rows: list[tuple[Match, tuple[float, float, float]]], bins: int = 5) -> dict:
    """Return transparent one-vs-rest reliability bins for each 1X2 class."""
    if not rows or bins < 2:
        raise ValueError("Calibration needs matches and at least two bins")
    report = {}
    for index, outcome in enumerate(OUTCOMES):
        grouped = [[] for _ in range(bins)]
        for match, probabilities in rows:
            probability = probabilities[index]
            grouped[min(bins - 1, int(probability * bins))].append(
                (probability, float(match.outcome == outcome)))
        table = []
        ece = 0.0
        for bin_index, values in enumerate(grouped):
            if not values:
                continue
            mean_probability = sum(value[0] for value in values) / len(values)
            observed_rate = sum(value[1] for value in values) / len(values)
            ece += len(values) / len(rows) * abs(mean_probability - observed_rate)
            table.append({"lower": bin_index / bins, "upper": (bin_index + 1) / bins,
                          "matches": len(values), "mean_probability": mean_probability,
                          "observed_rate": observed_rate,
                          "gap": observed_rate - mean_probability})
        report[outcome] = {"ece": ece, "bins": table}
    return report


def outcome_reweight_factors(rows: list[tuple[Match, tuple[float, float, float]]]) -> tuple[float, float, float]:
    """Fit a simple class-frequency correction without using later outcomes."""
    if not rows:
        raise ValueError("Outcome reweighting needs matches")
    actual = [sum(match.outcome == outcome for match, _ in rows) for outcome in OUTCOMES]
    expected = [sum(probabilities[index] for _, probabilities in rows) for index in range(3)]
    return tuple(observed / predicted for observed, predicted in zip(actual, expected))


def reweight(probabilities: tuple[float, float, float], factors: tuple[float, float, float]):
    return normalize(probability * factor for probability, factor in zip(probabilities, factors))


def evaluate_rows(source: list[dict]) -> dict:
    counts = Counter(str(row["season"]) for row in source)
    if dict(counts) != EXPECTED or len({row["id"] for row in source}) != len(source):
        raise ValueError(f"Unexpected extended UEFA sample: {dict(counts)}")
    matches = []
    metadata = {}
    for row in source:
        kickoff = datetime.fromisoformat(row["kickoff"].replace("Z", "+00:00"))
        if kickoff.tzinfo is None or row["home_id"] == row["away_id"]:
            raise ValueError(f"Invalid UEFA fixture: {row['id']}")
        match = Match(str(row["season"]), kickoff.date(), str(row["home_id"]), str(row["away_id"]),
                      row["home_goals"], row["away_goals"], "uefa_api_extended")
        matches.append(match)
        metadata[(match.season, match.day, match.home, match.away)] = row
    records = run_chronological(matches)
    periods = {
        "2025_league_phase": lambda row: str(row["season"]) == "2025" and row["stage"] == "League Phase",
        "2026_league_phase": lambda row: str(row["season"]) == "2026" and row["stage"] == "League Phase",
        "2027_md1": lambda row: str(row["season"]) == "2027" and row["stage"] == "League Phase"
                       and row["kickoff"][:10] <= "2026-09-10",
        "2027_md2": lambda row: str(row["season"]) == "2027" and row["stage"] == "League Phase"
                       and "2026-10-13" <= row["kickoff"][:10] <= "2026-10-14",
    }
    period_records = {}
    for label, predicate in periods.items():
        period_records[label] = [(match, predictions) for match, predictions in records
                                 if predicate(metadata[(match.season, match.day, match.home, match.away)])]
        if not period_records[label]:
            raise ValueError(f"No evaluation matches: {label}")
    period_records["locked_combined"] = (period_records["2026_league_phase"]
                                          + period_records["2027_md1"] + period_records["2027_md2"])

    # A candidate is selected once on the earliest league-phase sample. The
    # deployment gate below decides which weight is locked for later periods.
    tuning = {
        str(weight): metrics([(match, mix(predictions["elo"], predictions["poisson"], weight))
                              for match, predictions in period_records["2025_league_phase"]])
        for weight in WEIGHT_CANDIDATES
    }
    candidate_weight = min(WEIGHT_CANDIDATES, key=lambda weight: tuning[str(weight)]["log_loss"])
    tuning_period = period_records["2025_league_phase"]
    candidate_rows = [(match, mix(predictions["elo"], predictions["poisson"], candidate_weight))
                      for match, predictions in tuning_period]
    incumbent_rows = [(match, mix(predictions["elo"], predictions["poisson"], 0.5))
                      for match, predictions in tuning_period]
    candidate_comparison = bootstrap_logloss_difference(candidate_rows, incumbent_rows)
    # Avoid replacing an incumbent for a tiny grid-search win. The candidate
    # must beat it throughout the paired 95% bootstrap interval.
    candidate_accepted = candidate_weight != 0.5 and candidate_comparison["ci95"][1] < 0
    deployed_weight = candidate_weight if candidate_accepted else 0.5

    calibration_train = [(match, mix(predictions["elo"], predictions["poisson"], deployed_weight))
                         for match, predictions in period_records["2026_league_phase"]]
    calibration_test = [(match, mix(predictions["elo"], predictions["poisson"], deployed_weight))
                        for label in ("2027_md1", "2027_md2")
                        for match, predictions in period_records[label]]
    calibration_factors = outcome_reweight_factors(calibration_train)
    corrected_test = [(match, reweight(probabilities, calibration_factors))
                      for match, probabilities in calibration_test]
    calibration_comparison = bootstrap_logloss_difference(corrected_test, calibration_test, repetitions=10000)
    calibration_accepted = calibration_comparison["ci95"][1] < 0

    evaluations = {}
    for label, period in period_records.items():
        selected = {name: [] for name in ("base", "elo", "poisson", "blend")}
        fixed_half = []
        for match, predictions in period:
            for name in ("base", "elo", "poisson"):
                selected[name].append((match, predictions[name]))
            selected["blend"].append((match, mix(predictions["elo"], predictions["poisson"], deployed_weight)))
            fixed_half.append((match, mix(predictions["elo"], predictions["poisson"], 0.5)))
        evaluations[label] = {
            "matches": len(selected["base"]),
            "metrics": {name: metrics(rows) for name, rows in selected.items()},
            "blend_classwise_calibration_5_bins": classwise_calibration(selected["blend"]),
            "blend_minus_base_log_loss": bootstrap_logloss_difference(selected["blend"], selected["base"]),
            "deployed_blend_minus_fixed_0_5_log_loss": bootstrap_logloss_difference(selected["blend"], fixed_half),
        }
    appearances = Counter()
    for row in source:
        if row["kickoff"][:10] <= "2026-10-14":
            appearances[str(row["home_id"])] += 1
            appearances[str(row["away_id"])] += 1
    return {
        "sample": dict(counts),
        "stages": dict(Counter(row["stage"] for row in source)),
        "protocol": "All completed UCL qualifying, league/group, and knockout matches from 2022/23 onward update the model. "
                    "Only named league-phase periods are scored. Matches sharing a UTC date are predicted before any "
                    "result from that date is observed. A candidate Elo weight is selected on 2024/25 but replaces "
                    "the incumbent only when its paired bootstrap interval is wholly below zero.",
        "weight_selection": {
            "meaning": "Elo probability weight; the remainder is Poisson",
            "selection_period": "2025_league_phase",
            "candidate_weights": list(WEIGHT_CANDIDATES),
            "validation_log_loss": {weight: value["log_loss"] for weight, value in tuning.items()},
            "candidate_weight": candidate_weight,
            "candidate_minus_incumbent_log_loss": candidate_comparison,
            "deployment_rule": "Deploy the candidate only if the upper endpoint of the paired date-block bootstrap "
                               "95% interval is below zero.",
            "deployed_weight": deployed_weight,
            "decision": "candidate_accepted" if candidate_accepted else "incumbent_retained",
            "locked_evaluation_periods": ["2026_league_phase", "2027_md1", "2027_md2"],
            "combined_locked_period": "locked_combined",
        },
        "calibration_candidate": {
            "method": "Multiply home/draw/away probabilities by observed-to-expected class ratios, then renormalize.",
            "fit_period": "2026_league_phase",
            "factors_h_d_a": list(calibration_factors),
            "evaluation_periods": ["2027_md1", "2027_md2"],
            "evaluation_matches": len(calibration_test),
            "uncorrected_metrics": metrics(calibration_test),
            "corrected_metrics": metrics(corrected_test),
            "corrected_minus_uncorrected_log_loss": calibration_comparison,
            "deployment_rule": "Deploy only if the upper endpoint of the paired date-block bootstrap 95% interval is below zero.",
            "decision": "candidate_accepted" if calibration_accepted else "candidate_rejected",
            "applied_to_target_forecast": calibration_accepted,
        },
        "results": evaluations,
        "appearances_through_2026_10_14": dict(appearances),
        "limitations": [
            "Qualifying strength is connected through match results only; there is no domestic-league or club-coefficient prior.",
            "The source snapshot does not reveal first-publication timestamps for historical results.",
            "The candidate-selection protocol was implemented after all reported periods had completed; later periods are "
            "untouched by optimization but remain retrospective evidence rather than a preregistered prospective trial.",
            "The class-reweighting candidate is fitted on 2025/26 and checked on 36 later matches, but remains rejected "
            "because its paired bootstrap interval includes zero.",
            "No odds, xG, lineup, injury, or tactical variable enters this model.",
        ],
    }


def evaluate(folder: Path) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    for name, item in manifest["files"].items():
        if hashlib.sha256((folder / name).read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"Extended UEFA source checksum mismatch: {name}")
    result = evaluate_rows(json.loads((folder / "matches_normalized.json").read_text(encoding="utf-8")))
    result.update({"source": manifest["source"], "source_snapshot": str(folder),
                   "source_retrieved_at": manifest["retrieved_at"]})
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--output", type=Path, default=Path("reports/uefa_extended_backtest.json"))
    args = parser.parse_args()
    folder = args.data_dir or sorted(Path(".cache/uefa_extended_history").glob("*/manifest.json"))[-1].parent
    result = evaluate(folder)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
