import unittest

from bola.xg_transfer import evaluate


class XgTransferTest(unittest.TestCase):
    def test_penalties_are_excluded_from_non_penalty_comparison(self):
        games = [[(0.8, 1, True), (0.2, 0, False)],
                 [(0.6, 1, False)]]
        all_shots = evaluate(games, 0.4, non_penalty=False)
        open_play = evaluate(games, 0.4, non_penalty=True)
        self.assertEqual(all_shots["calibration"]["shots"], 3)
        self.assertEqual(open_play["calibration"]["shots"], 2)
        self.assertAlmostEqual(open_play["brier_xg_minus_constant"], -0.16)


if __name__ == "__main__":
    unittest.main()
