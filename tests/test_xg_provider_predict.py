import unittest

from bola.xg_provider_predict import paired_difference


class XgProviderPredictTests(unittest.TestCase):
    def test_zero_candidate_matches_reference(self):
        rows = [{"date": "2020-01-01", "outcome": 0, "elo": (0.4, 0.3, 0.3),
                 "xg_feature": 1.0, "goal_feature": 0.0}]
        result = paired_difference(rows, 0.0)
        self.assertEqual(result["log_loss_difference_candidate_minus_reference"], 0.0)
        self.assertEqual(result["match_date_bootstrap_95_ci"], [0.0, 0.0])


if __name__ == "__main__":
    unittest.main()
