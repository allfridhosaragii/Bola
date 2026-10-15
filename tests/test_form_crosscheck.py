import json
import unittest

from bola.form_crosscheck import read_team_page


class FormCrosscheckTests(unittest.TestCase):
    def test_primary_league_and_cutoff(self):
        payload = {"props": {"pageProps": {"fallback": {"team-7": {
            "details": {"id": 7, "name": "Team", "primaryLeagueId": 10},
            "fixtures": {"allFixtures": {"fixtures": [
                {"id": 1, "tournament": {"leagueId": 10},
                 "home": {"id": 7, "name": "Team"}, "away": {"id": 8, "name": "Other"},
                 "status": {"utcTime": "2026-10-10T12:00:00Z", "finished": True,
                            "cancelled": False, "awarded": False, "scoreStr": "2 - 1"}},
                {"id": 2, "tournament": {"leagueId": 11},
                 "home": {"id": 7, "name": "Team"}, "away": {"id": 9, "name": "Cup"},
                 "status": {"utcTime": "2026-10-11T12:00:00Z", "finished": True,
                            "cancelled": False, "awarded": False, "scoreStr": "3 - 0"}},
            ]}}}}}}}
        body = ("<script id=\"__NEXT_DATA__\" type=\"application/json\">" + json.dumps(payload) + "</script>").encode()
        details, rows = read_team_page(body, 7, __import__("datetime").date(2026, 10, 15))
        self.assertEqual(details["primaryLeagueId"], 10)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["goals_for"], 2)


if __name__ == "__main__":
    unittest.main()
