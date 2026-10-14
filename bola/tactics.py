"""Observed event and tracking summaries for Metrica's anonymous sample game.

These are descriptive proxies, not a validated xT, pitch-control or pressing
model. The source does not identify the clubs or supply match video.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import json
import math
from pathlib import Path
import statistics


SOURCE_COMMIT = "e706dd506b360d69d9d123d5b8026e7294b13996"


def number(value: str) -> float | None:
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def read_events(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    events = []
    for index, row in enumerate(rows):
        if row["Team"] not in ("Home", "Away") or row["Period"] not in ("1", "2"):
            raise ValueError(f"Unexpected team or period at event {index}")
        at = number(row["Start Time [s]"])
        if at is None or at < 0:
            raise ValueError(f"Invalid event time at row {index}")
        events.append({"team": row["Team"], "period": int(row["Period"]), "time": at,
                       "type": row["Type"], "subtype": row["Subtype"],
                       "start_x": number(row["Start X"]), "end_x": number(row["End X"])})
    return sorted(events, key=lambda e: (e["period"], e["time"]))


def infer_directions(events: list[dict]) -> dict[tuple[str, int], int]:
    """Infer attack direction from observed shot destinations in each half."""
    shots = defaultdict(list)
    for event in events:
        if event["type"] == "SHOT" and event["end_x"] is not None:
            shots[event["team"], event["period"]].append(event["end_x"])
    directions = {}
    for team in ("Home", "Away"):
        for period in (1, 2):
            values = shots[team, period]
            if not values:
                raise ValueError(f"Cannot infer attack direction: no shots for {team}, period {period}")
            median = statistics.median(values)
            if 0.4 <= median <= 0.6:
                raise ValueError(f"Ambiguous attack direction for {team}, period {period}")
            directions[team, period] = 1 if median > 0.5 else -1
    for period in (1, 2):
        if directions["Home", period] == directions["Away", period]:
            raise ValueError(f"Both teams appear to attack the same goal in period {period}")
    return directions


def event_summary(events: list[dict]) -> dict:
    directions = infer_directions(events)
    result = {}
    for team in ("Home", "Away"):
        for period in (1, 2):
            current = [e for e in events if e["team"] == team and e["period"] == period]
            direction = directions[team, period]
            passes = [e for e in current if e["type"] == "PASS"]
            valid_passes = [e for e in passes if e["start_x"] is not None and e["end_x"] is not None
                            and 0 <= e["start_x"] <= 1 and 0 <= e["end_x"] <= 1]
            progressive = sum((e["end_x"] - e["start_x"]) * direction >= 10 / 105 for e in valid_passes)
            recoveries = [e for e in current if e["type"] == "RECOVERY"]
            high_recoveries = sum(e["start_x"] is not None and 0 <= e["start_x"] <= 1
                                  and (e["start_x"] - 0.5) * direction > 0 for e in recoveries)
            losses = [e for e in current if e["type"] == "BALL LOST"]
            own_half_losses = sum(e["start_x"] is not None and 0 <= e["start_x"] <= 1
                                  and (e["start_x"] - 0.5) * direction < 0 for e in losses)
            shots = [e for e in current if e["type"] == "SHOT"]
            key = f"{team}_period_{period}"
            result[key] = {"attack_direction": "right" if direction == 1 else "left",
                           "events": len(current), "passes": len(passes), "passes_with_valid_x": len(valid_passes),
                           "forward_10m_pass_proxy": progressive, "shots": len(shots),
                           "shots_on_target": sum("ON TARGET" in e["subtype"] for e in shots),
                           "goals": sum("GOAL" in e["subtype"] for e in shots),
                           "recoveries": len(recoveries), "opponent_half_recoveries": high_recoveries,
                           "ball_losses": len(losses), "own_half_ball_losses": own_half_losses,
                           "corners": sum(e["type"] == "SET PIECE" and e["subtype"] == "CORNER KICK" for e in current)}
    return result


def tracking_summary(path: Path, stride: int = 25) -> dict:
    """Sample one of every 25 25-Hz frames, including players visible in each."""
    if stride < 1:
        raise ValueError("stride must be positive")
    totals = defaultdict(lambda: defaultdict(float))
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        next(reader)
        next(reader)
        header = next(reader)
        if header[:3] != ["Period", "Frame", "Time [s]"] or header[-2:] != ["Ball", ""]:
            raise ValueError(f"Unexpected tracking header in {path}")
        player_columns = list(range(3, len(header) - 2, 2))
        for row in reader:
            period, frame = int(row[0]), int(row[1])
            if frame % stride != 1:
                continue
            if period not in (1, 2):
                continue
            players = []
            for column in player_columns:
                x, y = number(row[column]), number(row[column + 1])
                if x is not None and y is not None and 0 <= x <= 1 and 0 <= y <= 1:
                    players.append((x, y))
            if not players:
                continue
            group = totals[period]
            group["sampled_frames"] += 1
            group["visible_players_total"] += len(players)
            group["team_x_span_m_total"] += (max(x for x, _ in players) - min(x for x, _ in players)) * 105
            group["team_y_span_m_total"] += (max(y for _, y in players) - min(y for _, y in players)) * 68
            ball_x, ball_y = number(row[-2]), number(row[-1])
            if ball_x is not None and ball_y is not None and 0 <= ball_x <= 1 and 0 <= ball_y <= 1:
                group["valid_ball_frames"] += 1
                group["nearest_player_ball_distance_m_total"] += min(math.hypot((x - ball_x) * 105, (y - ball_y) * 68) for x, y in players)
    return {str(period): {"sampled_frames": int(values["sampled_frames"]),
                          "mean_visible_players": values["visible_players_total"] / values["sampled_frames"],
                          "mean_team_x_span_m": values["team_x_span_m_total"] / values["sampled_frames"],
                          "mean_team_y_span_m": values["team_y_span_m_total"] / values["sampled_frames"],
                          "frames_with_ball": int(values["valid_ball_frames"]),
                          "mean_nearest_player_ball_m": values["nearest_player_ball_distance_m_total"] / values["valid_ball_frames"] if values["valid_ball_frames"] else None}
            for period, values in totals.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(".cache/metrica"))
    parser.add_argument("--output", type=Path, default=Path("reports/tactics.json"))
    parser.add_argument("--game", type=int, choices=(1, 2), default=1)
    args = parser.parse_args()
    game = f"Sample_Game_{args.game}"
    folder = args.data_dir / "data" / game
    event_path = folder / f"{game}_RawEventsData.csv"
    events = read_events(event_path)
    report = {"source": "https://github.com/metrica-sports/sample-data", "commit": SOURCE_COMMIT,
              "game": game, "anonymous_teams": True, "event_rows": len(events),
              "event_types": dict(Counter(e["type"] for e in events)), "by_team_and_period": event_summary(events),
              "tracking_1hz": {team: tracking_summary(folder / f"{game}_RawTrackingData_{team}_Team.csv")
                               for team in ("Home", "Away")},
              "limitations": ["Only one anonymous game; no generalisation to a named team.",
                              "Forward-pass and spatial-span metrics are descriptive proxies, not validated tactical labels.",
                              "No video, xT, pitch-control or causal pressing estimate is calculated."]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
