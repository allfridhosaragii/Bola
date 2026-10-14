"""Compare StatsBomb shot xG in the 2018 and 2022 men's World Cups."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random

from .worldcup import shot_calibration


COMMIT = "4b73468fc5b0f1950f9f66fada70ad3a4f9327cb"


def load_games(folder: Path, competition: str) -> list[list[tuple[float, int, bool]]]:
    if competition not in ("wc_2018", "wc_2022", "epl_2015_16"):
        raise ValueError(f"Unknown competition: {competition}")
    is_2022 = competition == "wc_2022"
    manifest = json.loads((folder / ("worldcup_sha256.json" if is_2022 else "manifest.json")).read_text())
    if manifest["commit" if is_2022 else "source_commit"] != COMMIT:
        raise ValueError(f"Wrong source commit for {competition}")
    match_name = {"wc_2018": "matches_43_3.json", "wc_2022": "matches_43_106.json",
                  "epl_2015_16": "matches_2_27.json"}[competition]
    match_bytes = (folder / match_name).read_bytes()
    expected = manifest["files"][match_name] if is_2022 else manifest["matches_sha256"]
    if hashlib.sha256(match_bytes).hexdigest() != expected:
        raise ValueError(f"Match metadata checksum mismatch for {competition}")
    matches = sorted(json.loads(match_bytes), key=lambda row: (row["match_date"], row["match_id"]))
    expected_count = 380 if competition == "epl_2015_16" else 64
    if len(matches) != expected_count or len({row["match_id"] for row in matches}) != expected_count:
        raise ValueError(f"Expected {expected_count} unique matches for {competition}")
    if competition == "epl_2015_16" and not (matches[189]["match_date"] < "2016-01-01" <= matches[190]["match_date"]):
        raise ValueError("EPL chronological training/test cutoff no longer matches 190 games each")
    games = []
    for row in matches:
        match_id = row["match_id"]
        name = f"events_{match_id}.json"
        raw = (folder / name).read_bytes()
        expected = manifest["files"][name] if is_2022 else manifest["events_sha256"][str(match_id)]
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError(f"Event checksum mismatch: {name}")
        shots = []
        for event in json.loads(raw):
            if event["type"]["name"] != "Shot" or event["period"] not in (1, 2, 3, 4):
                continue
            data = event["shot"]
            xg = data["statsbomb_xg"]
            if not isinstance(xg, (float, int)) or not 0 <= xg <= 1:
                raise ValueError(f"Invalid shot xG in {name}")
            shots.append((xg, int(data["outcome"]["name"] == "Goal"), data["type"]["name"] == "Penalty"))
        games.append(shots)
    return games


def evaluate(games: list[list[tuple[float, int, bool]]], baseline: float, *, non_penalty: bool) -> dict:
    grouped = [[(xg, goal) for xg, goal, penalty in game if not non_penalty or not penalty]
               for game in games]
    shots = [shot for game in grouped for shot in game]
    calibration = shot_calibration(shots)
    moments = [(len(game), sum((xg - goal) ** 2 - (baseline - goal) ** 2 for xg, goal in game))
               for game in grouped]
    def difference(sample: list[tuple[int, float]]) -> float:
        return sum(delta for _, delta in sample) / sum(count for count, _ in sample)
    rng = random.Random(20261015)
    replicates = sorted(difference([moments[rng.randrange(len(moments))] for _ in moments])
                        for _ in range(2000))
    return {"calibration": calibration, "baseline_goal_rate": round(baseline, 6),
            "brier_xg_minus_constant": round(difference(moments), 6),
            "match_bootstrap_95_ci": [round(replicates[49], 6), round(replicates[1949], 6)]}


def summarize(folder_2018: Path, folder_2022: Path, folder_epl: Path) -> dict:
    earlier = load_games(folder_2018, "wc_2018")
    later = load_games(folder_2022, "wc_2022")
    club = load_games(folder_epl, "epl_2015_16")
    sections = {}
    for name, non_penalty in (("all_shots", False), ("non_penalty_shots", True)):
        earlier_shots = [(xg, goal) for game in earlier for xg, goal, penalty in game
                         if not non_penalty or not penalty]
        baseline = sum(goal for _, goal in earlier_shots) / len(earlier_shots)
        sections[name] = {"2018": shot_calibration(earlier_shots),
                          "2022_vs_2018_constant": evaluate(later, baseline, non_penalty=non_penalty)}
        club_train = club[:190]
        club_test = club[190:]
        train_shots = [(xg, goal) for game in club_train for xg, goal, penalty in game
                       if not non_penalty or not penalty]
        club_baseline = sum(goal for _, goal in train_shots) / len(train_shots)
        sections[name]["epl_2015_16"] = {
            "all_matches": shot_calibration([(xg, goal) for game in club for xg, goal, penalty in game
                                             if not non_penalty or not penalty]),
            "second_half_vs_first_half_constant": evaluate(club_test, club_baseline,
                                                            non_penalty=non_penalty)}
    return {"source": "StatsBomb open-data", "commit": COMMIT,
            "matches_per_world_cup": 64, "epl_matches": 380, "sections": sections,
            "limitations": ["xG model training provenance is unknown; 2022 is not a confirmed independent model holdout.",
                            "The club sample is a complete older EPL season; neither sample establishes future UEFA performance.",
                            "The 2018 constant baseline uses 2018 outcomes; 2022 comparison is chronological.",
                            "The EPL constant baseline uses matches before 2016-01-01; test matches are on or after that date.",
                            "Bootstrap interval resamples matches and measures uncertainty for this sample, not general transfer performance."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-2018", type=Path, default=Path(".cache/statsbomb_2018"))
    parser.add_argument("--data-2022", type=Path, default=Path(".cache/statsbomb"))
    parser.add_argument("--data-epl", type=Path, default=Path(".cache/statsbomb_epl_2015"))
    parser.add_argument("--output", type=Path, default=Path("reports/xg_transfer.json"))
    args = parser.parse_args()
    report = summarize(args.data_2018, args.data_2022, args.data_epl)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["sections"], indent=2))


if __name__ == "__main__":
    main()
