import unittest

from bola.analyst_report import assemble


class AnalystReportTests(unittest.TestCase):
    def setUp(self):
        self.forecast = {
            "generated_at": "2026-10-20T17:00:00Z", "target_date_utc": "2026-10-20",
            "predictions": [{"match_id": "1", "home": "A", "away": "B",
                             "kickoff": "2026-10-20T19:00:00Z",
                             "historical_uefa_appearances": {"home": 18, "away": 18},
                             "probabilities_h_d_a": {"blend": [0.5, 0.2, 0.3]}}],
        }
        team = {"windows": {str(n): {"games": n} for n in (5, 10, 20)}}
        self.form = {"as_of": "2026-10-20T18:35:00Z", "teams": {"A": team, "B": team}}
        self.squad = {
            "refreshed_at": "2026-10-20T18:40:00Z",
            "fixtures": [{"match_id": "1", "home": "A", "away": "B",
                          "kickoff": "2026-10-20T19:00:00Z", "status_at_retrieval": "Upcoming",
                          "fixture_retrieved_at": "2026-10-20T18:39:00Z",
                          "lineup_retrieved_at": "2026-10-20T18:40:00Z",
                          "registered_players": {"A": 25, "B": 24},
                          "flagged_players": {"A": [], "B": []},
                          "lineup_status": "AVAILABLE",
                          "official_starting_xi_before_kickoff": True}],
        }

    def test_missing_market_and_validation_force_no_selection(self):
        report = assemble(self.forecast, self.form, self.squad, "2026-10-20T18:45:00Z")
        row = report["matches"][0]
        self.assertEqual(row["selection_status"], "no_selection")
        self.assertIn("fresh_market_screenshot", row["blocking_gates"])
        self.assertIn("validated_current_tactical_evidence", row["blocking_gates"])
        self.assertEqual(report["summary"]["form_complete"], 1)
        self.assertEqual(report["summary"]["official_lineups"], 1)

    def test_rejects_identity_and_future_evidence(self):
        self.squad["fixtures"][0]["away"] = "C"
        with self.assertRaisesRegex(ValueError, "identity disagree"):
            assemble(self.forecast, self.form, self.squad, "2026-10-20T18:45:00Z")
        self.squad["fixtures"][0]["away"] = "B"
        self.form["as_of"] = "2026-10-20T18:46:00Z"
        with self.assertRaisesRegex(ValueError, "after report"):
            assemble(self.forecast, self.form, self.squad, "2026-10-20T18:45:00Z")

    def test_stale_fixture_is_visible_blocker(self):
        self.squad["fixtures"][0]["fixture_retrieved_at"] = "2026-10-20T18:00:00Z"
        report = assemble(self.forecast, self.form, self.squad, "2026-10-20T18:45:00Z")
        self.assertFalse(report["matches"][0]["evidence_gates"]["official_fixture_snapshot_within_30m"])


if __name__ == "__main__":
    unittest.main()
