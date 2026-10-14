import unittest

from bola.squad import audit_ledger


class SquadTests(unittest.TestCase):
    def setUp(self):
        self.ledger = {"fixture": {"home": "A", "away": "B", "kickoff": "2026-10-14T20:00:00+07:00"},
                       "as_of": "2026-10-14T18:00:00+07:00", "evidence": []}

    def item(self, published, retrieved=None):
        return {"team": "A", "player": "Player 1", "claim": "out_injured", "source_kind": "club",
                "source_url": "https://example.org/team-news", "published_at": published,
                "retrieved_at": retrieved or published}

    def test_future_report_is_excluded(self):
        self.ledger["evidence"] = [self.item("2026-10-14T19:00:00+07:00")]
        result = audit_ledger(self.ledger)
        self.assertEqual(result["accepted_as_of"], 0)
        self.assertEqual(result["excluded_future_rows"], [0])

    def test_partial_lineup_is_not_confirmed(self):
        self.ledger["evidence"] = [{**self.item("2026-10-14T17:00:00+07:00"), "claim": "starting"}]
        result = audit_ledger(self.ledger)
        self.assertFalse(result["teams"]["A"]["official_lineup_complete"])
        self.assertTrue(result["issues"])

    def test_timezone_is_required(self):
        self.ledger["as_of"] = "2026-10-14T18:00:00"
        with self.assertRaises(ValueError):
            audit_ledger(self.ledger)


if __name__ == "__main__":
    unittest.main()
