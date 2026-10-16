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
        team = {"windows": {str(n): {"record": {"W": n, "D": 0, "L": 0}} for n in (5, 10, 20)}}
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

    def test_invalid_probabilities_are_rejected(self):
        for probabilities in ([float('nan'), .2, .8], [-.1, .5, .6], [True, 0, 0]):
            with self.subTest(probabilities=probabilities):
                self.forecast['predictions'][0]['probabilities_h_d_a']['blend'] = probabilities
                with self.assertRaisesRegex(ValueError, 'Invalid frozen probabilities'):
                    assemble(self.forecast, self.form, self.squad, '2026-10-20T18:45:00Z')

    def test_partial_form_does_not_pass_completeness_gate(self):
        self.form['teams']['A']['windows']['20']['record']['W'] = 19
        report = assemble(self.forecast, self.form, self.squad, '2026-10-20T18:45:00Z')
        self.assertEqual(report['summary']['form_complete'], 0)

    def test_market_freshness_is_recomputed_at_report_time(self):
        market = {'match_id': '1', 'home': 'A', 'away': 'B',
                  'kickoff': '2026-10-20T19:00:00Z',
                  'analyzed_at': '2026-10-20T18:30:00Z',
                  'quote_observed_at_transcribed': '2026-10-20T18:29:00Z',
                  'fresh_within_10m': True, 'screenshot_sha256': 'test-fixture'}
        report = assemble(self.forecast, self.form, self.squad, '2026-10-20T18:45:00Z', [market])
        self.assertEqual(report['summary']['fresh_markets'], 0)
        market['analyzed_at'] = market['quote_observed_at_transcribed'] = '2026-10-20T18:35:00Z'
        report = assemble(self.forecast, self.form, self.squad, '2026-10-20T18:45:00Z', [market])
        self.assertEqual(report['summary']['fresh_markets'], 1)

    def test_schedule_load_is_checked_and_included(self):
        schedule = {"generated_at": "2026-10-20T18:41:00Z",
                    "forecast_generated_at": "2026-10-20T17:00:00Z", "target_date_utc": "2026-10-20",
                    "teams": {"A": {"projected_hours_from_preceding_fixture_to_target": 72},
                              "B": {"projected_hours_from_preceding_fixture_to_target": 80}},
                    "target_fixture_crosscheck": [{"match_id": "1", "home": "A", "away": "B"}]}
        report = assemble(self.forecast, self.form, self.squad, "2026-10-20T18:45:00Z", schedule=schedule)
        row = report["matches"][0]
        self.assertTrue(row["evidence_gates"]["schedule_load_for_both"])
        self.assertEqual(report["summary"]["schedule_load_complete"], 1)
        schedule["target_fixture_crosscheck"][0]["away"] = "C"
        with self.assertRaisesRegex(ValueError, "identity disagree"):
            assemble(self.forecast, self.form, self.squad, "2026-10-20T18:45:00Z", schedule=schedule)

    def test_recent_match_stats_are_time_checked(self):
        recent = {"generated_at": "2026-10-20T18:41:00Z",
                  "source_retrieved_at_latest": "2026-10-20T18:40:00Z",
                  "teams": {"A": {"stats_available_games": 5}, "B": {"stats_available_games": 4}}}
        report = assemble(self.forecast, self.form, self.squad, "2026-10-20T18:45:00Z",
                          recent_stats=recent)
        self.assertTrue(report["matches"][0]["evidence_gates"]["recent_match_stats_for_both"])
        recent["source_retrieved_at_latest"] = "2026-10-20T18:46:00Z"
        with self.assertRaisesRegex(ValueError, "newer"):
            assemble(self.forecast, self.form, self.squad, "2026-10-20T18:45:00Z",
                     recent_stats=recent)


if __name__ == "__main__":
    unittest.main()
