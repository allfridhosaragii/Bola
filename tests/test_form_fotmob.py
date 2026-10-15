import json
import unittest
from datetime import date

from bola.form_fotmob import read_page


class FotMobFormTests(unittest.TestCase):
    def page(self):
        fixtures = []
        for n in range(100):
            time = "2026-10-14T16:59:00Z"
            status = {"utcTime": time, "finished": True, "cancelled": False,
                      "awarded": False, "scoreStr": "2 - 1"}
            if n == 1:
                status["utcTime"] = "2026-10-14T17:00:00Z"  # Exactly midnight WIB.
            if n == 2:
                status["cancelled"] = True
            if n == 3:
                status["awarded"] = True
            fixtures.append({"id": n, "home": {"id": 6019, "name": "Slovan Bratislava"},
                             "away": {"id": 6022, "name": "Žilina"}, "status": status})
        payload = {"page": "/leagues/[id]/[tab]/[[...slug]]",
                   "query": {"season": "2026/2027"},
                   "props": {"pageProps": {"details": {"id": 176, "country": "SVK",
                                                        "selectedSeason": "2026/2027"},
                                           "fixtures": {"allMatches": fixtures}}}}
        return ('<script id="__NEXT_DATA__" type="application/json">' + json.dumps(payload) + '</script>').encode()

    def test_wib_midnight_and_unplayed_results_are_excluded(self):
        rows = read_page(self.page(), "176", "2627", date(2026, 10, 15))
        self.assertEqual(len(rows), 97)
        self.assertEqual(rows[0]["_day"], date(2026, 10, 14))

    def test_wrong_league_identity_is_rejected(self):
        with self.assertRaises(ValueError):
            read_page(self.page(), "441", "2627", date(2026, 10, 15))


if __name__ == "__main__":
    unittest.main()
