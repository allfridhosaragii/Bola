import unittest

from bola.uefa_lineup_api import parse


class UefaLineupApiTests(unittest.TestCase):
    def test_eleven_per_team_and_observation_time(self):
        fixture = {"match_id": "1", "home": "A", "away": "B",
                   "kickoff": "2026-10-14T19:00:00Z"}
        match = {"id": "1", "homeTeam": {"id": "10", "internationalName": "A"},
                 "awayTeam": {"id": "20", "internationalName": "B"},
                 "kickOffTime": {"dateTime": "2026-10-14T19:00:00Z"}, "status": "UPCOMING"}
        lineup = {"matchId": "1", "lineupStatus": "INITIAL_AVAILABLE"}
        for side, team_id in (("homeTeam", "10"), ("awayTeam", "20")):
            lineup[side] = {"team": {"id": team_id}, "field": [
                {"player": {"id": f"{team_id}-{n}", "internationalName": str(n)}, "type": "MIDFIELDER"}
                for n in range(11)], "bench": []}
        result = parse(match, lineup, fixture, "2026-10-14T18:00:00Z")
        self.assertTrue(result["official_starting_xi"])
        self.assertTrue(result["before_kickoff_at_retrieval"])
        lineup["awayTeam"]["field"].pop()
        self.assertFalse(parse(match, lineup, fixture, "2026-10-14T19:01:00Z")["official_starting_xi"])
        lineup["awayTeam"]["team"]["id"] = "wrong"
        with self.assertRaises(ValueError):
            parse(match, lineup, fixture, "2026-10-14T18:00:00Z")


if __name__ == "__main__":
    unittest.main()
