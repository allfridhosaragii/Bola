import unittest

from bola.target_form_audit import assemble


class TargetFormAuditTests(unittest.TestCase):
    def test_source_time_and_coverage(self):
        archive = {"generated_at": "2026-10-14T18:00:00Z", "target_date_utc": "2026-10-20",
                   "predictions": [{"home": "A", "away": "B", "kickoff": "2026-10-20T19:00:00Z"}]}
        window = lambda n: {"games": n, "record": {"W": n, "D": 0, "L": 0},
                            "from": "2026-09-01", "through": "2026-10-10",
                            "mean_opponent_elo_before": 1500, "venue_counts": {"home": n, "away": 0},
                            "metrics": {"goals_for": {"mean": 1}, "goals_against": {"mean": 0},
                                        "shots_for": {"observed_games": 0}}}
        form = {"cutoff_exclusive_date_wib": "2026-10-15", "source": "example",
                "snapshot_manifest": {"files": {"a": {"retrieved_at": "2026-10-14T18:01:00Z"}}},
                "teams": {"A": {"league": "X", "games_before_cutoff": 20,
                                "windows": {str(n): window(n) for n in (5, 10, 20)}}}}
        report = assemble(archive, [("first", form)], "2026-10-14T18:02:00Z")
        self.assertEqual(report["teams_covered"], 1)
        self.assertEqual(report["teams_missing"], ["B"])
        form["snapshot_manifest"]["files"]["a"]["retrieved_at"] = "2026-10-14T18:03:00Z"
        with self.assertRaisesRegex(ValueError, "not available"):
            assemble(archive, [("first", form)], "2026-10-14T18:02:00Z")


if __name__ == "__main__":
    unittest.main()
