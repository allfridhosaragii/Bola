import unittest

from bola.dossier import assemble


class DossierTests(unittest.TestCase):
    def setUp(self):
        self.fixtures = {"fixtures": [{"match_id": "1", "home": "A", "away": "B",
                                       "kickoff": "2026-10-14T19:00:00+00:00", "status": "Upcoming",
                                       "url": "https://www.uefa.com/match/1",
                                       "retrieved_at": "2026-10-14T17:00:00+00:00"}]}
        self.squads = {"fixtures": [{"match_id": "1", "retrieved_at": "2026-10-14T17:05:00+00:00",
                                     "url": "https://www.uefa.com/match/1/lineups/",
                                     "official_starting_xi_parsed": False,
                                     "teams": {"A": {"registered_players": 25, "flagged_players": []},
                                               "B": {"registered_players": 24, "flagged_players": []}}}]}
        self.form = {"cutoff_exclusive_date_wib": "2026-10-15",
                     "snapshot_manifest": {"files": {"sample.csv": {"retrieved_at": "2026-10-14T17:10:00+00:00"}}},
                     "teams": {"A": {"windows": {}}, "B": {"windows": {}}}}

    def test_report_gates_and_future_source_rejection(self):
        result = assemble(self.fixtures, self.squads, self.form, "2026-10-15T00:20:00+07:00")
        gate = result["fixtures"][0]["evidence_gates"]
        self.assertTrue(gate["domestic_form_for_both"])
        self.assertTrue(gate["uefa_fixture_snapshot_within_30m"])
        self.assertFalse(result["fixtures"][0]["ready_for_two_predictions"])
        old = assemble(self.fixtures, self.squads, self.form, "2026-10-15T00:50:00+07:00")
        self.assertFalse(old["fixtures"][0]["evidence_gates"]["uefa_fixture_snapshot_within_30m"])
        with self.assertRaises(ValueError):
            assemble(self.fixtures, self.squads, self.form, "2026-10-15T00:05:00+07:00")
        self.squads["fixtures"][0]["away"] = "C"
        with self.assertRaises(ValueError):
            assemble(self.fixtures, self.squads, self.form, "2026-10-15T00:20:00+07:00")


if __name__ == "__main__":
    unittest.main()
