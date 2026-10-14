import unittest

from bola.worldcup import shot_calibration, shot_origin


class WorldCupTests(unittest.TestCase):
    def test_perfect_and_imperfect_shot_probabilities(self):
        report = shot_calibration([(0.9, 1), (0.1, 0)])
        self.assertEqual(report["brier"], 0.01)
        self.assertEqual(report["constant_goal_rate_brier"], 0.25)
        self.assertEqual(report["ece_10_bins"], 0.1)

    def test_penalty_not_counted_as_general_play_pattern(self):
        event = {"shot": {"type": {"name": "Penalty"}},
                 "play_pattern": {"name": "From Free Kick"}}
        self.assertEqual(shot_origin(event), "Penalty")


if __name__ == "__main__":
    unittest.main()
