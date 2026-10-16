import unittest

from bola.lineup_continuity_transfer import season_predictions


class LineupContinuityTransferTests(unittest.TestCase):
    def test_requires_five_prior_lineups(self):
        matches = []
        lineups = {}
        home_base = set(range(1, 12))
        away_base = set(range(20, 31))
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
            lineups[match_id] = {1: home_base, 2: away_base}
        rows = season_predictions(matches, lineups)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["feature"], 0.0)
        self.assertEqual(rows[0]["home_absence_load"], 0.0)


if __name__ == "__main__":
    unittest.main()
