"""Archive an exploratory, pre-kickoff UEFA 1X2 forecast for later scoring."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

from .backtest import Match, Model, mix
from .uefa_lineup_api import fetch_body


API = "https://match.uefa.com/v5"


def date_matches(day: str, season_year: int = 2027) -> tuple[bytes, str]:
    url = (f"{API}/matches?competitionId=1&fromDate={day}&limit=50&offset=0"
           f"&order=ASC&phase=ALL&seasonYear={season_year}&toDate={day}&utcOffset=0")
    return fetch_body(url), url


def from_result(row: dict) -> Match:
    score = row["score"]["regular"]
    return Match(str(row["seasonYear"]),
                 datetime.fromisoformat(row["kickOffTime"]["dateTime"].replace("Z", "+00:00")).date(),
                 str(row["homeTeam"]["id"]), str(row["awayTeam"]["id"]),
                 score["home"], score["away"], "uefa_api")


def forecast(history_dir: Path, cache_dir: Path) -> dict:
    manifest = json.loads((history_dir / "manifest.json").read_text())
    normalized = (history_dir / "matches_normalized.json").read_bytes()
    if hashlib.sha256(normalized).hexdigest() != manifest["files"]["matches_normalized.json"]["sha256"]:
        raise ValueError("Historical UEFA source checksum mismatch")
    historical = json.loads(normalized)
    if Counter(str(row["season"]) for row in historical) != {"2025": 144, "2026": 144, "2027": 18}:
        raise ValueError("Expected fixed UEFA training/validation sample")
    cache_dir.mkdir(parents=True, exist_ok=True)
    prior_body, prior_url = date_matches("2026-10-13")
    current_body, current_url = date_matches("2026-10-14")
    captured = datetime.now(timezone.utc)
    stamp = captured.strftime("%Y%m%dT%H%M%S%fZ")
    for label, body in (("prior", prior_body), ("current", current_body)):
        (cache_dir / f"{stamp}_{label}.json").write_bytes(body)
    prior = json.loads(prior_body)
    current = json.loads(current_body)
    if len(prior) != 9 or any(row["status"] != "FINISHED" for row in prior):
        raise ValueError("Expected nine completed prior matchday fixtures")
    if len(current) != 9 or Counter(row["status"] for row in current) != {"LIVE": 2, "UPCOMING": 7}:
        raise ValueError("Expected two live and seven upcoming fixtures")
    model = Model()
    appearances = Counter()
    combined = []
    for row in historical:
        kickoff = datetime.fromisoformat(row["kickoff"].replace("Z", "+00:00"))
        combined.append((kickoff, Match(str(row["season"]), kickoff.date(), str(row["home_id"]),
                                        str(row["away_id"]), row["home_goals"], row["away_goals"], "uefa_api")))
    combined.extend((datetime.fromisoformat(row["kickOffTime"]["dateTime"].replace("Z", "+00:00")),
                     from_result(row)) for row in prior)
    for _, match in sorted(combined, key=lambda pair: pair[0]):
        model.observe(match)
        appearances[match.home] += 1
        appearances[match.away] += 1
    predictions = []
    for row in current:
        if row["status"] != "UPCOMING":
            continue
        kickoff = datetime.fromisoformat(row["kickOffTime"]["dateTime"].replace("Z", "+00:00"))
        if captured >= kickoff:
            raise ValueError(f"Fixture already kicked off: {row['id']}")
        home, away = str(row["homeTeam"]["id"]), str(row["awayTeam"]["id"])
        candidate = Match("2027", kickoff.date(), home, away, 0, 0, "unplayed")
        probs = model.predict(candidate)
        probs["blend"] = mix(probs["elo"], probs["poisson"], 0.5)
        predictions.append({"match_id": str(row["id"]), "home": row["homeTeam"]["internationalName"],
                            "away": row["awayTeam"]["internationalName"],
                            "kickoff": row["kickOffTime"]["dateTime"],
                            "historical_uefa_appearances": {"home": appearances[home], "away": appearances[away]},
                            "probabilities_h_d_a": {name: [round(x, 6) for x in value]
                                                    for name, value in probs.items()}})
    if len(predictions) != 7:
        raise ValueError("Expected seven pre-kickoff predictions")
    return {"generated_at": captured.isoformat(), "model_code_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True).strip(),
            "source": {"historical_snapshot": str(history_dir),
                       "historical_sha256": hashlib.sha256(normalized).hexdigest(),
                       "prior_url": prior_url, "prior_sha256": hashlib.sha256(prior_body).hexdigest(),
                       "current_url": current_url, "current_sha256": hashlib.sha256(current_body).hexdigest(),
                       "raw_snapshot_prefix": str(cache_dir / stamp)},
            "protocol": "Results-only UEFA Elo/Poisson blend with weight 0.5 frozen from EPL validation. "
                        "Uses 306 completed matches from 2024/25–2025/26, 18 completed MD1 matches, "
                        "and nine completed MD2 matches on 13 October. Two live matches are excluded. "
                        "Probabilities order: home/draw/away.",
            "predictions": predictions,
            "limitations": ["Exploratory predictions, not validated betting selections or two recommended bets.",
                            "No current odds, xG, lineup, injury, or tactical feature enters this model.",
                            "Several clubs have very few UEFA appearances in the training sample.",
                            "Do not revise this archived forecast after results are known; score it prospectively."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history-dir", type=Path)
    parser.add_argument("--cache-dir", type=Path, default=Path(".cache/uefa_forecast"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    history_dir = args.history_dir or sorted(Path(".cache/uefa_history").glob("*/manifest.json"))[-1].parent
    result = forecast(history_dir, args.cache_dir)
    output = args.output or Path("prospective") / ("uefa_" + result["generated_at"].replace(":", "-") + ".json")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(f"Prospective forecast already exists: {output}")
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
