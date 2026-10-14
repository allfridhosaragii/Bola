import unittest

from bola.uefa import compare_candidates, parse_match_page
from bola.uefa_squad import parse_squad_page


def page(kickoff="2026-10-14T19:00:00+00:00"):
    return (f'<script>var trackVars = {{"competition":"ucl","matchID":"123",'
            f'"matchName":"Shakhtar-AEK Athens","matchDay":"MD2"}};</script>'
            f'<div data-name="match-header" data-options=\'{{"match":{{"id":"123",'
            f'"status":"Upcoming","kickOffTime":{{"dateTime":"{kickoff}"}}}}}}\'></div>')


class UefaTests(unittest.TestCase):
    def test_official_kickoff_and_matchday_discrepancy(self):
        official = parse_match_page(page().encode(), "https://www.uefa.com/match/123", "2026-10-14T17:00:00+00:00")
        reported = {"fixtures": [{"home": "Shakhtar", "away": "AEK Athena",
                                  "kickoff": "2026-10-15T02:00:00+07:00", "competition": "UCL matchday 3"}]}
        mapping = [{"user_home": "Shakhtar", "user_away": "AEK Athena", "match_id": "123",
                    "official_home": "Shakhtar", "official_away": "AEK Athens"}]
        result = compare_candidates(reported, mapping, [official])
        self.assertEqual(result["verified_fixtures"], 1)
        self.assertEqual(result["matchday_disagreements"], 1)
        reported["fixtures"][0]["kickoff"] = "2026-10-15T03:00:00+07:00"
        with self.assertRaises(ValueError):
            compare_candidates(reported, mapping, [official])

    def test_squad_badges_are_not_starting_xi(self):
        body = page() + (
            '<div class="home-squad-wrapper squad-wrapper" data-squad="Shakhtar">'
            '<pk-table-row class="row--squadlist"><a href="/uefachampionsleague/clubs/players/1" title="A">'
            '<pk-badge badge-title="Injured"></pk-badge></a></pk-table-row></div>'
            '<div class="away-squad-wrapper squad-wrapper hidden" data-squad="AEK Athens">'
            '<pk-table-row class="row--squadlist"><a href="/uefachampionsleague/clubs/players/2" title="B">'
            '</a></pk-table-row></div>')
        report = parse_squad_page(body.encode(), "https://www.uefa.com/match/123/lineups/",
                                  "2026-10-14T17:00:00+00:00")
        self.assertEqual(report["teams"]["Shakhtar"]["flagged_players"][0]["badges"], ["Injured"])
        self.assertFalse(report["official_starting_xi_parsed"])


if __name__ == "__main__":
    unittest.main()
