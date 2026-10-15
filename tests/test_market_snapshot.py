import unittest

from bola.market_snapshot import compare


class MarketSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.archive = {"generated_at": "2026-10-19T18:00:00Z",
                        "predictions": [{"match_id": "1", "home": "A", "away": "B",
                                         "kickoff": "2026-10-20T19:00:00Z",
                                         "probabilities_h_d_a": {"blend": [0.5, 0.25, 0.25]}}]}
        self.quote = {"match_id": "1", "home": "A", "away": "B", "kickoff": "2026-10-20T19:00:00Z",
                      "market": "1X2_regular_time", "bookmaker": "Example",
                      "observed_at": "2026-10-20T18:55:00Z",
                      "decimal_odds": {"home": 2.0, "draw": 4.0, "away": 4.0},
                      "screenshot_path": "example.png"}

    def test_market_math_and_image_provenance(self):
        report = compare(self.archive, self.quote, b"\x89PNG\r\n\x1a\nimage evidence", "2026-10-20T18:56:00Z")
        self.assertEqual(report["market_overround"], 0)
        self.assertEqual(report["market_normalized_probabilities_h_d_a"], [0.5, 0.25, 0.25])
        self.assertTrue(report["fresh_within_10m"])
        self.assertEqual(len(report["screenshot_sha256"]), 64)
        self.assertFalse(report["ready_for_betting_selection"])

    def test_rejects_late_or_mismatched_quote(self):
        with self.assertRaisesRegex(ValueError, "kicked off"):
            compare(self.archive, self.quote, b"\x89PNG\r\n\x1a\nimage", "2026-10-20T19:01:00Z")
        self.quote["away"] = "C"
        with self.assertRaisesRegex(ValueError, "disagrees"):
            compare(self.archive, self.quote, b"\x89PNG\r\n\x1a\nimage", "2026-10-20T18:56:00Z")
        self.quote["away"] = "B"
        self.quote["decimal_odds"]["draw"] = float("nan")
        with self.assertRaisesRegex(ValueError, "Invalid decimal"):
            compare(self.archive, self.quote, b"\x89PNG\r\n\x1a\nimage", "2026-10-20T18:56:00Z")
        self.quote["decimal_odds"]["draw"] = 4
        with self.assertRaisesRegex(ValueError, "Screenshot evidence"):
            compare(self.archive, self.quote, b"", "2026-10-20T18:56:00Z")


if __name__ == "__main__":
    unittest.main()
