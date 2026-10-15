import unittest

from bola.shot_quality_predict import adjusted, non_penalty_shots


class ShotQualityPredictTest(unittest.TestCase):
    def test_excludes_penalties_and_shootout(self):
        events = [
            {"id": "open", "period": 1, "type": {"name": "Shot"}, "team": {"id": 1},
             "shot": {"statsbomb_xg": 0.2, "type": {"name": "Open Play"}}},
            {"id": "penalty", "period": 2, "type": {"name": "Shot"}, "team": {"id": 1},
             "shot": {"statsbomb_xg": 0.76, "type": {"name": "Penalty"}}},
            {"id": "shootout", "period": 5, "type": {"name": "Shot"}, "team": {"id": 2},
             "shot": {"statsbomb_xg": 0.76, "type": {"name": "Penalty"}}},
        ]
        self.assertEqual(non_penalty_shots(events), {"1": {"shots": 1, "npxg": 0.2}})

    def test_rejects_invalid_xg(self):
        event = {"id": "bad", "period": 1, "type": {"name": "Shot"}, "team": {"id": 1},
                 "shot": {"statsbomb_xg": 1.2, "type": {"name": "Open Play"}}}
        with self.assertRaises(ValueError):
            non_penalty_shots([event])

    def test_zero_coefficient_preserves_elo(self):
        original = (0.4, 0.25, 0.35)
        self.assertEqual(adjusted(original, 1.5, 0), original)
        shifted = adjusted(original, 1.5, 0.5)
        self.assertAlmostEqual(sum(shifted), 1)
        self.assertGreater(shifted[0], original[0])


if __name__ == "__main__":
    unittest.main()
