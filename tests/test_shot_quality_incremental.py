import unittest

from bola.shot_quality_incremental import feature_rows, probabilities


class ShotQualityIncrementalTests(unittest.TestCase):
    def test_features_use_exactly_five_prior_matches(self):
        matches = []
        qualities = {}
        for index in range(6):
            match_id = index + 1
            matches.append({
                "match_id": match_id,
                "match_date": f"2020-01-{index + 1:02d}",
                "season": {"season_name": "test"},
                "home_team": {"home_team_id": 1},
                "away_team": {"away_team_id": 2},
                "home_score": index + 1,
                "away_score": 1,
            })
            qualities[match_id] = {
                "1": {"shots": 1, "npxg": float(index + 1)},
                "2": {"shots": 1, "npxg": 1.0},
            }
        rows = feature_rows(matches, qualities)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["xg_feature"], 4.0)
        self.assertEqual(rows[0]["goal_feature"], 4.0)

    def test_joint_probability_is_normalized(self):
        row = {"elo": (0.4, 0.25, 0.35), "xg_feature": 1.0, "goal_feature": -0.5}
        forecast = probabilities(row, 0.25, 0.1)
        self.assertAlmostEqual(sum(forecast), 1.0)
        self.assertTrue(all(0 < value < 1 for value in forecast))


if __name__ == "__main__":
    unittest.main()
