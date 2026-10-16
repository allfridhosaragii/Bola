import unittest
from collections import Counter

from bola.pressure_transfer import season_predictions


class PressureTransferTests(unittest.TestCase):
    def test_uses_exactly_five_prior_matches(self):
        matches = []
        regains = {}
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
            regains[match_id] = Counter({"1": index + 1, "2": 1})
        rows = season_predictions(matches, regains)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["feature"], 2.0)


if __name__ == "__main__":
    unittest.main()
