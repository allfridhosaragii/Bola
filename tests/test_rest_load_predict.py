import unittest

from bola.rest_load_predict import capped_rest, season_predictions


class RestLoadPredictTests(unittest.TestCase):
    def test_rest_is_capped_and_requires_positive_days(self):
        self.assertEqual(capped_rest(4), 4)
        self.assertEqual(capped_rest(30), 14)
        with self.assertRaises(ValueError):
            capped_rest(0)

    def test_uses_only_previous_dates(self):
        matches = [
            {"match_id": 1, "match_date": "2020-01-01", "season": {"season_name": "test"},
             "home_team": {"home_team_id": 1}, "away_team": {"away_team_id": 2},
             "home_score": 1, "away_score": 0},
            {"match_id": 2, "match_date": "2020-01-05", "season": {"season_name": "test"},
             "home_team": {"home_team_id": 1}, "away_team": {"away_team_id": 2},
             "home_score": 0, "away_score": 0},
        ]
        rows = season_predictions(matches)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["home_rest_days"], 4)
        self.assertEqual(rows[0]["feature"], 0)


if __name__ == "__main__":
    unittest.main()
