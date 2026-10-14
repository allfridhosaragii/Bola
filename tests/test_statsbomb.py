import unittest

from bola.statsbomb import audit


class StatsBombTests(unittest.TestCase):
    def test_shootout_shot_excluded_and_starting_xi_cross_checked(self):
        lineups = []
        events = []
        for team in ("A", "B"):
            players = [{"player_id": i, "positions": [{"start_reason": "Starting XI"}]} for i in range(1, 12)]
            lineups.append({"team_name": team, "lineup": players})
            events.append({"team": {"name": team}, "type": {"name": "Starting XI"}, "period": 1,
                           "tactics": {"lineup": [{"player": {"id": i}} for i in range(1, 12)]}})
        events.append({"id": "shootout", "team": {"name": "A"}, "type": {"name": "Shot"}, "period": 5,
                       "shot": {"statsbomb_xg": .9, "type": {"name": "Penalty"}, "outcome": {"name": "Goal"}}})
        report = audit(events, lineups)
        self.assertEqual(report["shootout_shots_excluded"], 1)
        self.assertNotIn("shots", report["teams"]["A"])
        self.assertEqual(report["teams"]["A"]["starters_cross_checked"], 11)


if __name__ == "__main__":
    unittest.main()
