import math
import unittest

from bola.uefa_score import score


class ScoreTest(unittest.TestCase):
    def setUp(self):
        self.archive = {
            "generated_at": "2026-10-14T18:00:00+00:00",
            "predictions": [{"match_id": "7", "home": "Home", "away": "Away",
                             "kickoff": "2026-10-14T19:00:00Z",
                             "probabilities_h_d_a": {"blend": [0.5, 0.2, 0.3]}}],
        }
        self.results = [{"id": 7, "status": "FINISHED",
                         "kickOffTime": {"dateTime": "2026-10-14T19:00:00Z"},
                         "homeTeam": {"internationalName": "Home"},
                         "awayTeam": {"internationalName": "Away"},
                         "score": {"regular": {"home": 2, "away": 1}}}]

    def test_scores_pregame_final_result(self):
        report = score(self.archive, self.results, "2026-10-14T21:00:00+00:00", "abc")
        self.assertEqual(report["n"], 1)
        self.assertAlmostEqual(report["aggregate"]["blend"]["log_loss"], -math.log(0.5))
        self.assertAlmostEqual(report["aggregate"]["blend"]["brier"], 0.38)

    def test_rejects_unfinished_or_late_forecast(self):
        self.results[0]["status"] = "LIVE"
        with self.assertRaises(ValueError):
            score(self.archive, self.results, "2026-10-14T19:30:00+00:00", "abc")
        self.results[0]["status"] = "FINISHED"
        self.archive["generated_at"] = "2026-10-14T19:01:00+00:00"
        with self.assertRaises(ValueError):
            score(self.archive, self.results, "2026-10-14T21:00:00+00:00", "abc")


if __name__ == "__main__":
    unittest.main()
