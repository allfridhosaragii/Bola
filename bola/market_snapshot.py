"""Audit a manually transcribed 1X2 screenshot against a frozen match forecast."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

from .squad import instant


OUTCOMES = ("home", "draw", "away")


def compare(archive: dict, quote: dict, image: bytes, as_of: str) -> dict:
    now = instant(as_of)
    observed = instant(quote["observed_at"])
    generated = instant(archive["generated_at"])
    if observed > now or generated > now:
        raise ValueError("Quote or forecast timestamp is after analysis time")
    predictions = [row for row in archive["predictions"] if row["match_id"] == quote["match_id"]]
    if len(predictions) != 1:
        raise ValueError("Quote match ID is not unique in forecast")
    prediction = predictions[0]
    kickoff = instant(prediction["kickoff"])
    if now >= kickoff or observed >= kickoff or generated >= kickoff:
        raise ValueError("Match has kicked off before forecast, quote, or analysis")
    for field in ("home", "away"):
        if quote.get(field) != prediction[field]:
            raise ValueError(f"Quote {field} disagrees with official UEFA fixture")
    if instant(quote["kickoff"]) != kickoff:
        raise ValueError("Quote kickoff disagrees with official UEFA fixture")
    if quote.get("market") != "1X2_regular_time" or not isinstance(quote.get("bookmaker"), str) or not quote["bookmaker"].strip():
        raise ValueError("Expected a named bookmaker and regular-time 1X2 market")
    prices = quote.get("decimal_odds")
    if not isinstance(prices, dict) or set(prices) != set(OUTCOMES):
        raise ValueError("Quote needs exactly home, draw, and away decimal odds")
    if any(type(prices[outcome]) not in (int, float) or not math.isfinite(prices[outcome]) or
           prices[outcome] <= 1 for outcome in OUTCOMES):
        raise ValueError("Invalid decimal odds")
    if image.startswith(b"\x89PNG\r\n\x1a\n"):
        image_format = "png"
    elif image.startswith(b"\xff\xd8\xff"):
        image_format = "jpeg"
    elif image.startswith(b"RIFF") and image[8:12] == b"WEBP":
        image_format = "webp"
    else:
        raise ValueError("Screenshot evidence must be PNG, JPEG, or WebP")
    inverse = [1 / prices[outcome] for outcome in OUTCOMES]
    total = sum(inverse)
    fair = [round(value / total, 6) for value in inverse]
    baseline = prediction["probabilities_h_d_a"]["blend"]
    if len(baseline) != 3 or any(not 0 <= value <= 1 for value in baseline) or abs(sum(baseline) - 1) > 2e-6:
        raise ValueError("Frozen model probabilities are invalid")
    return {"match_id": quote["match_id"], "home": prediction["home"], "away": prediction["away"],
            "kickoff": prediction["kickoff"], "forecast_generated_at": archive["generated_at"],
            "bookmaker": quote["bookmaker"], "market": quote["market"],
            "quote_observed_at_transcribed": quote["observed_at"], "analyzed_at": as_of,
            "screenshot_sha256": hashlib.sha256(image).hexdigest(),
            "screenshot_bytes": len(image), "screenshot_format": image_format,
            "screenshot_path": quote.get("screenshot_path"),
            "decimal_odds": prices, "market_overround": round(total - 1, 6),
            "market_normalized_probabilities_h_d_a": fair,
            "frozen_baseline_probabilities_h_d_a": baseline,
            "baseline_minus_market_h_d_a": [round(model - market, 6) for model, market in zip(baseline, fair)],
            "quote_age_seconds": round((now - observed).total_seconds(), 1),
            "fresh_within_10m": (now - observed).total_seconds() <= 600,
            "ready_for_betting_selection": False,
            "limitations": ["Screenshot text and capture time are transcribed manually; the file hash proves only which image was supplied.",
                            "A screenshot does not establish that the odds were executable at the analysis time.",
                            "The UEFA baseline has not shown stable market-beating calibration; a model-market difference is not a validated edge.",
                            "No injury, lineup, tactics, or current domestic form enters this baseline."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--forecast", type=Path, required=True)
    parser.add_argument("--quote", type=Path, required=True, help="JSON transcription with screenshot_path")
    parser.add_argument("--as-of", default=datetime.now(timezone.utc).isoformat())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Market comparison already exists: {args.output}")
    quote = json.loads(args.quote.read_text(encoding="utf-8"))
    image = Path(quote["screenshot_path"]).read_bytes()
    result = compare(json.loads(args.forecast.read_text(encoding="utf-8")), quote, image, args.as_of)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
