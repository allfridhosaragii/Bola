"""Chronological Premier League 1X2 backtest using only match results.

This is deliberately a results-only baseline. It does not infer xG, team news,
odds, or tactical observations from final scores.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
import json
import math
from pathlib import Path
import random
import subprocess
from typing import Iterable


TRAIN = ("2020-21", "2021-22", "2022-23")
VALIDATION = "2023-24"
TEST = ("2024-25", "2025-26")
SEASONS = TRAIN + (VALIDATION,) + TEST
OUTCOMES = ("H", "D", "A")
PINNED_DATA_COMMIT = "e6744429ee395bc86f247348c6184bb08d4eb361"


@dataclass(frozen=True)
class Match:
    season: str
    day: date
    home: str
    away: str
    goals_home: int
    goals_away: int
    score_format: str

    @property
    def outcome(self) -> str:
        return "H" if self.goals_home > self.goals_away else "A" if self.goals_home < self.goals_away else "D"


def load_matches(data_dir: Path, seasons: Iterable[str] = SEASONS, league: str = "en.1") -> tuple[list[Match], dict]:
    matches: list[Match] = []
    audit: dict = {}
    seen: set[tuple[str, str, str]] = set()
    for season in seasons:
        path = data_dir / season / f"{league}.json"
        source = json.loads(path.read_text(encoding="utf-8"))
        counts: Counter[str] = Counter()
        teams: set[str] = set()
        for row in source["matches"]:
            score = row.get("score")
            if isinstance(score, dict) and "ft" in score:
                result, score_format = score["ft"], "score.ft"
            elif isinstance(score, list):
                result, score_format = score, "score_list"
            else:
                counts["missing_score"] += 1
                continue
            if not (isinstance(result, list) and len(result) == 2 and all(type(x) is int and x >= 0 for x in result)):
                raise ValueError(f"Invalid full-time score in {path}: {row!r}")
            home, away = row["team1"], row["team2"]
            day = date.fromisoformat(row["date"])
            if home == away:
                raise ValueError(f"Team plays itself in {path}: {row!r}")
            key = season, home, away
            if key in seen:
                raise ValueError(f"Duplicate home-away fixture in {path}: {key!r}")
            seen.add(key)
            teams.update((home, away))
            matches.append(Match(season, day, home, away, *result, score_format))
            counts[score_format] += 1
        expected = len(teams) * (len(teams) - 1)
        counts["teams"] = len(teams)
        counts["scored_matches"] = counts["score.ft"] + counts["score_list"]
        counts["expected_home_away_fixtures"] = expected
        if len(source["matches"]) != expected or counts["scored_matches"] != expected:
            raise ValueError(f"Incomplete or duplicate season {season}: {dict(counts)}")
        audit[season] = dict(counts)
    return sorted(matches, key=lambda m: (m.day, m.home, m.away)), audit


def normalize(values: Iterable[float]) -> tuple[float, float, float]:
    numbers = tuple(max(1e-12, x) for x in values)
    total = sum(numbers)
    return tuple(x / total for x in numbers)  # type: ignore[return-value]


def poisson_probs(rate_home: float, rate_away: float) -> tuple[float, float, float]:
    def pmf(rate: float) -> list[float]:
        values = [math.exp(-rate)]
        for k in range(1, 16):
            values.append(values[-1] * rate / k)
        return values

    home, away = pmf(rate_home), pmf(rate_away)
    win = draw = loss = 0.0
    for h, ph in enumerate(home):
        for a, pa in enumerate(away):
            mass = ph * pa
            if h > a:
                win += mass
            elif h == a:
                draw += mass
            else:
                loss += mass
    return normalize((win, draw, loss))


class Model:
    def __init__(self) -> None:
        self.elo: dict[str, float] = defaultdict(lambda: 1500.0)
        self.outcomes: Counter[str] = Counter()
        self.goals = [0, 0]
        self.n = 0
        self.home_for: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        self.home_against: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        self.away_for: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        self.away_against: dict[str, list[int]] = defaultdict(lambda: [0, 0])

    def predict(self, match: Match) -> dict[str, tuple[float, float, float]]:
        # Prior observations only. The draw rate is estimated from completed games.
        base = normalize((self.outcomes["H"] + 1, self.outcomes["D"] + 1, self.outcomes["A"] + 1))
        diff = self.elo[match.home] + 65 - self.elo[match.away]
        conditional_home_win = 1 / (1 + 10 ** (-diff / 400))
        p_draw = (self.outcomes["D"] + 25) / (self.n + 100)
        p_draw *= math.exp(-abs(diff) / 1200)
        # Elo's expected *points* cannot be converted to 1X2 by subtracting
        # half the draw probability: for strong favourites that can force the
        # underdog probability to zero. Split non-draw mass instead.
        p_home = (1 - p_draw) * conditional_home_win
        elo = normalize((p_home, p_draw, (1 - p_draw) * (1 - conditional_home_win)))

        # Venue-specific attack and defence, shrunk toward prior league rates.
        mean_home = (self.goals[0] + 15) / (self.n + 10)
        mean_away = (self.goals[1] + 12) / (self.n + 10)

        def shrunk(stats: list[int], prior: float) -> float:
            return (stats[0] + 8 * prior) / (stats[1] + 8)

        rate_home = shrunk(self.home_for[match.home], mean_home) * shrunk(self.away_against[match.away], mean_home) / mean_home
        rate_away = shrunk(self.away_for[match.away], mean_away) * shrunk(self.home_against[match.home], mean_away) / mean_away
        poisson = poisson_probs(min(5, rate_home), min(5, rate_away))
        return {"base": base, "elo": elo, "poisson": poisson}

    def observe(self, match: Match) -> None:
        prediction = 1 / (1 + 10 ** (-(self.elo[match.home] + 65 - self.elo[match.away]) / 400))
        result = 1.0 if match.outcome == "H" else 0.0 if match.outcome == "A" else 0.5
        change = 20 * (result - prediction)
        self.elo[match.home] += change
        self.elo[match.away] -= change
        self.outcomes[match.outcome] += 1
        self.n += 1
        self.goals[0] += match.goals_home
        self.goals[1] += match.goals_away
        for table, team, goals in (
            (self.home_for, match.home, match.goals_home),
            (self.home_against, match.home, match.goals_away),
            (self.away_for, match.away, match.goals_away),
            (self.away_against, match.away, match.goals_home),
        ):
            table[team][0] += goals
            table[team][1] += 1


def run_chronological(matches: list[Match]) -> list[tuple[Match, dict[str, tuple[float, float, float]]]]:
    model = Model()
    predictions = []
    for day in sorted({m.day for m in matches}):
        # Predict all matches on a date from the same prior state. Match times
        # are not trusted as a universally consistent timezone in this source.
        games = [m for m in matches if m.day == day]
        predictions.extend((m, model.predict(m)) for m in games)
        for match in games:
            model.observe(match)
    return predictions


def mix(a: tuple[float, float, float], b: tuple[float, float, float], alpha: float) -> tuple[float, float, float]:
    return normalize(alpha * x + (1 - alpha) * y for x, y in zip(a, b))


def metrics(rows: list[tuple[Match, tuple[float, float, float]]]) -> dict[str, float | int]:
    n = len(rows)
    if not n:
        raise ValueError("Cannot evaluate zero matches")
    brier = logloss = rps = correct = 0.0
    bins = defaultdict(list)
    for match, probs in rows:
        index = OUTCOMES.index(match.outcome)
        actual = tuple(float(i == index) for i in range(3))
        brier += sum((p - y) ** 2 for p, y in zip(probs, actual))
        logloss -= math.log(max(probs[index], 1e-12))
        rps += ((probs[0] - actual[0]) ** 2 + (probs[0] + probs[1] - actual[0] - actual[1]) ** 2) / 2
        pick = max(range(3), key=probs.__getitem__)
        correct += pick == index
        bins[min(9, int(10 * probs[pick]))].append((probs[pick], float(pick == index)))
    ece = sum(len(v) / n * abs(sum(p for p, _ in v) / len(v) - sum(y for _, y in v) / len(v)) for v in bins.values())
    return {"n": n, "accuracy": correct / n, "brier": brier / n, "log_loss": logloss / n, "rps": rps / n, "top_label_ece_10_bins": ece}


def evaluate(records, seasons, model, alpha=0.0):
    rows = []
    for match, predictions in records:
        if match.season in seasons:
            probs = mix(predictions["elo"], predictions["poisson"], alpha) if model == "blend" else predictions[model]
            rows.append((match, probs))
    return rows


def bootstrap_logloss_difference(a, b, seed=2026, repetitions=1000):
    # Paired date-block resampling preserves fixtures from the same matchday.
    grouped = defaultdict(list)
    for (match, pa), (_, pb) in zip(a, b):
        grouped[match.day].append(math.log(max(pb[OUTCOMES.index(match.outcome)], 1e-12)) - math.log(max(pa[OUTCOMES.index(match.outcome)], 1e-12)))
    blocks = list(grouped.values())
    rng = random.Random(seed)
    samples = []
    for _ in range(repetitions):
        selected = [rng.choice(blocks) for _ in blocks]
        samples.append(sum(sum(block) for block in selected) / sum(map(len, selected)))
    samples.sort()
    return {"difference_a_minus_b": sum(sum(block) for block in blocks) / sum(map(len, blocks)), "ci95": [samples[int(.025 * repetitions)], samples[int(.975 * repetitions)]]}


def data_commit(data_dir: Path) -> str | None:
    result = subprocess.run(["git", "-C", str(data_dir), "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(".cache/openfootball"))
    parser.add_argument("--output", type=Path, default=Path("reports/backtest.json"))
    parser.add_argument("--league", default="en.1", choices=("en.1", "de.1", "nl.1"))
    parser.add_argument("--test-seasons", nargs="+", default=list(TEST))
    parser.add_argument("--fixed-poisson-weight", type=float, choices=(0, .25, .5, .75, 1))
    args = parser.parse_args()
    if len(set(args.test_seasons)) != len(args.test_seasons) or any(season in TRAIN + (VALIDATION,) for season in args.test_seasons):
        parser.error("test seasons must be unique and separate from train/validation")
    matches, audit = load_matches(args.data_dir, seasons=TRAIN + (VALIDATION,) + tuple(args.test_seasons), league=args.league)
    records = run_chronological(matches)
    validation = {str(a): metrics(evaluate(records, {VALIDATION}, "blend", a)) for a in (0, .25, .5, .75, 1)}
    best_alpha = args.fixed_poisson_weight if args.fixed_poisson_weight is not None else min((0, .25, .5, .75, 1), key=lambda a: validation[str(a)]["log_loss"])
    seasons = set(args.test_seasons)
    all_test = {name: metrics(evaluate(records, seasons, name, best_alpha)) for name in ("base", "elo", "poisson", "blend")}
    by_season = {season: {name: metrics(evaluate(records, {season}, name, best_alpha)) for name in ("base", "elo", "poisson", "blend")} for season in args.test_seasons}
    paired = bootstrap_logloss_difference(evaluate(records, seasons, "elo"), evaluate(records, seasons, "blend", best_alpha))
    report = {"dataset": {"source": "https://github.com/openfootball/football.json", "commit": data_commit(args.data_dir), "league": args.league, "season_audit": audit}, "split": {"train": TRAIN, "validation": VALIDATION, "test": args.test_seasons, "same_date_predictions_share_prior_state": True}, "validation_blend_log_loss": {a: round(x["log_loss"], 6) for a, x in validation.items()}, "selected_poisson_weight": best_alpha, "weight_selected_on_this_league": args.fixed_poisson_weight is None, "test": all_test, "test_by_season": by_season, "paired_bootstrap_elo_minus_blend_log_loss": paired, "limitations": ["Results-only model: no xG, odds, squad, video, or tracking data.", "Current source snapshot has no historical publication timestamps; strict as-of-source availability cannot be proven.", "Bootstrap interval is descriptive and cannot establish future performance."]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
