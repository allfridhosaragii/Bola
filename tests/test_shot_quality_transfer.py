import unittest

from bola.shot_quality_transfer import season_predictions


class ShotQualityTransferTests(unittest.TestCase):
    def test_exactly_five_prior_matches_are_required(self):
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
                "home_score": 1,
                "away_score": 0,
            })
            qualities[match_id] = {
                "1": {"shots": 1, "npxg": float(index + 1)},
                "2": {"shots": 1, "npxg": 1.0},
            }
        predictions = season_predictions(matches, qualities)
        self.assertEqual(len(predictions), 1)
        # Prior home differences are 0, 1, 2, 3, 4; away differences are their inverse.
        self.assertEqual(predictions[0]["feature"], 4.0)

    def test_same_date_events_do_not_leak_between_predictions(self):
        matches = []
        qualities = {}
        for index in range(7):
            match_id = index + 1
            day = index + 1 if index < 5 else 6
            matches.append({
                "match_id": match_id,
                "match_date": f"2020-01-{day:02d}",
                "season": {"season_name": "test"},
                "home_team": {"home_team_id": 1},
                "away_team": {"away_team_id": 2},
                "home_score": 1,
                "away_score": 0,
            })
            qualities[match_id] = {
                "1": {"shots": 1, "npxg": 100.0 if index == 5 else 2.0},
                "2": {"shots": 1, "npxg": 1.0},
            }
        predictions = season_predictions(matches, qualities)
        self.assertEqual([row["feature"] for row in predictions], [2.0, 2.0])


if __name__ == "__main__":
    unittest.main()
