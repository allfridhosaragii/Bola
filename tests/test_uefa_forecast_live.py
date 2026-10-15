import unittest
from datetime import date, datetime, timezone

from bola.uefa_forecast_live import build_forecast


def fixture(mid, day, status="UPCOMING", home=1, away=2, score=None):
    return {"id": mid, "seasonYear": 2027, "status": status,
            "round": {"metaData": {"name": "League Phase"}},
            "kickOffTime": {"dateTime": f"{day}T19:00:00Z"},
            "homeTeam": {"id": home, "internationalName": f"Team {home}"},
            "awayTeam": {"id": away, "internationalName": f"Team {away}"},
            "score": {"regular": {"home": score[0], "away": score[1]}} if score else None}


class ForecastLiveTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 19, 12, tzinfo=timezone.utc)
        self.prior = {"2026-10-18": [fixture(1, "2026-10-18", "FINISHED", score=(2, 0))]}
        self.target = [fixture(2, "2026-10-20")]

    def test_prior_result_and_same_day_exclusion(self):
        result = build_forecast([], self.prior, self.target, date(2026, 10, 20), 2027, self.now)
        self.assertEqual(result["training_matches"], 1)
        self.assertEqual(len(result["predictions"]), 1)
        self.assertAlmostEqual(sum(result["predictions"][0]["probabilities_h_d_a"]["blend"]), 1, places=5)
        same_day_finished = fixture(3, "2026-10-20", "FINISHED", score=(6, 0))
        altered = build_forecast([], self.prior, [same_day_finished, *self.target],
                                 date(2026, 10, 20), 2027, self.now)
        self.assertEqual(altered["training_matches"], 1)
        self.assertEqual(altered["predictions"], result["predictions"])
        self.assertEqual(altered["excluded_target_matches"], [{"match_id": "3", "status": "FINISHED"}])

    def test_rejects_kicked_off_duplicate_and_wrong_date(self):
        with self.assertRaisesRegex(ValueError, "No unstarted"):
            build_forecast([], self.prior, self.target, date(2026, 10, 20), 2027,
                           datetime(2026, 10, 20, 20, tzinfo=timezone.utc))
        with self.assertRaisesRegex(ValueError, "Duplicate target"):
            build_forecast([], self.prior, self.target * 2, date(2026, 10, 20), 2027, self.now)
        with self.assertRaisesRegex(ValueError, "date or ID mismatch"):
            build_forecast([], self.prior, [fixture(2, "2026-10-21")],
                           date(2026, 10, 20), 2027, self.now)
        with self.assertRaisesRegex(ValueError, "timezone"):
            build_forecast([], self.prior, self.target, date(2026, 10, 20), 2027,
                           datetime(2026, 10, 19, 12))

    def test_excludes_unfinished_prior_without_using_score(self):
        pending = fixture(4, "2026-10-18", "UPCOMING")
        result = build_forecast([], {"2026-10-18": [pending]}, self.target,
                                date(2026, 10, 20), 2027, self.now)
        self.assertEqual(result["training_matches"], 0)
        self.assertEqual(result["excluded_unfinished_prior_matches"], ["4"])

    def test_extended_mode_includes_completed_current_season_history(self):
        historical = [{"id": "9", "season": 2027, "kickoff": "2026-10-18T19:00:00Z",
                       "home_id": "1", "away_id": "2", "home_goals": 3, "away_goals": 0}]
        result = build_forecast(historical, {}, self.target, date(2026, 10, 20), 2027, self.now,
                                include_current_history=True)
        self.assertEqual(result["training_matches"], 1)
        self.assertEqual(result["predictions"][0]["historical_uefa_appearances"], {"home": 1, "away": 1})


if __name__ == "__main__":
    unittest.main()
