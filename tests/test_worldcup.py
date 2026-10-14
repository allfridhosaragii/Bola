import unittest

from bola.worldcup import shot_calibration


class WorldCupTests(unittest.TestCase):
    def test_perfect_and_imperfect_shot_probabilities(self):
        report = shot_calibration([(0.9, 1), (0.1, 0)])
        self.assertEqual(report["brier"], 0.01)
        self.assertEqual(report["constant_goal_rate_brier"], 0.25)
        self.assertEqual(report["ece_10_bins"], 0.1)


if __name__ == "__main__":
    unittest.main()
