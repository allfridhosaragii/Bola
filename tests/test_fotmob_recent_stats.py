import unittest

from bola.fotmob_recent_stats import period_stats


class RecentStatsTests(unittest.TestCase):
    def test_duplicate_totals_must_agree_and_pass_accuracy_is_parsed(self):
        period = {"stats": [{"stats": [
            {"key": "BallPossesion", "stats": [61, 39]},
            {"key": "total_shots", "stats": [14, 5]},
            {"key": "accurate_passes", "stats": ["400 (84%)", "210 (70%)"]}]},
            {"stats": [{"key": "total_shots", "stats": [14, 5]}]}]}
        result = period_stats(period)
        self.assertEqual(result["pass_accuracy_pct"], [84, 70])
        self.assertEqual(result["shots"], [14, 5])
        period["stats"][1]["stats"][0]["stats"] = [15, 5]
        with self.assertRaises(ValueError):
            period_stats(period)

    def test_possession_and_shot_bounds_are_checked(self):
        period = {"stats": [{"stats": [
            {"key": "BallPossesion", "stats": [61, 40]},
            {"key": "total_shots", "stats": [5, 2]},
            {"key": "ShotsOnTarget", "stats": [6, 1]}]}]}
        with self.assertRaises(ValueError):
            period_stats(period)
        period["stats"][0]["stats"][0]["stats"] = [60, 40]
        with self.assertRaises(ValueError):
            period_stats(period)


if __name__ == "__main__":
    unittest.main()
