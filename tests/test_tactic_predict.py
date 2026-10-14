import unittest

from bola.tactic_predict import adjusted, high_recoveries


class TacticPredictTest(unittest.TestCase):
    def test_only_first_successful_recovery_per_possession_counts(self):
        events = [
            {"period": 1, "type": {"name": "Ball Recovery"}, "team": {"id": 1},
             "possession": 4, "location": [40, 30]},
            {"period": 1, "type": {"name": "Ball Recovery"}, "team": {"id": 1},
             "possession": 4, "location": [90, 30]},
            {"period": 1, "type": {"name": "Ball Recovery"}, "team": {"id": 1},
             "possession": 5, "location": [90, 30]},
        ]
        self.assertEqual(high_recoveries(events)["1"], 1)

    def test_zero_coefficient_preserves_elo(self):
        original = (0.4, 0.25, 0.35)
        self.assertEqual(adjusted(original, 12, 0), original)
        self.assertAlmostEqual(sum(adjusted(original, 12, 1)), 1)


if __name__ == "__main__":
    unittest.main()
