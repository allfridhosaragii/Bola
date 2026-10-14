import unittest

from bola.fixtures import audit_candidates


class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.payload = {"source_kind": "user_reported", "fixtures": [
            {"home": "A", "away": "B", "competition": "Cup", "kickoff": "2026-10-14T23:45:00+07:00"},
            {"home": "C", "away": "D", "competition": "Cup", "kickoff": "2026-10-15T02:00:00+07:00"},
        ]}

    def test_kickoff_gate_and_source_limit(self):
        report = audit_candidates(self.payload, "2026-10-14T23:47:00+07:00")
        self.assertEqual([f["time_status"] for f in report["fixtures"]],
                         ["kickoff_passed", "before_reported_kickoff"])
        self.assertTrue(all(not f["prematch_analysis_ready"] for f in report["fixtures"]))

    def test_timezone_required(self):
        self.payload["fixtures"][0]["kickoff"] = "2026-10-14T23:45:00"
        with self.assertRaises(ValueError):
            audit_candidates(self.payload, "2026-10-14T23:47:00+07:00")


if __name__ == "__main__":
    unittest.main()
