import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from bola.target_refresh_evidence import assemble


class TargetRefreshEvidenceTests(unittest.TestCase):
    def test_assemble_uses_input_hashes_and_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payloads = {
                "forecast": {"target_date_utc": "2026-10-20", "generated_at": "2026-10-16T00:00:00Z", "predictions": [{}]},
                "squad": {"fixtures": [{"registered_players": {"A": 1}, "official_starting_xi_before_kickoff": False}]},
                "form": {"teams_covered": 2, "teams_requested": 2},
                "crosscheck": {"independent_matches_checked": 5, "independent_teams": 1},
                "openfootball": {"independent_score_matches": 4, "requested_score_matches": 15,
                                 "independent_full_window_teams": 0},
                "schedule": {"summary": {"teams_with_scheduled_match_before_target": 1, "minimum_projected_rest_hours": 72}},
                "recent": {"summary": {"team_match_observations": 10, "observations_with_stats": 9,
                                           "observations_with_lineups": 10, "teams_with_all_five_stats_pages": 1,
                                           "teams_with_all_five_lineups": 2}},
                "coverage": {"raw_pages_checked": 10, "anomalies": []},
                "odds": {"generated_at": "2026-10-16T00:00:00Z", "quotes_observed": 0,
                          "results": [{"url": "https://example.test", "http_code": 403, "status_chain": [403], "curl_exit_code": 0}]},
                "analyst": {"generated_at": "2026-10-16T00:01:00Z", "summary": {"form_fresh": 1, "schedule_fresh": 1,
                             "recent_stats_fresh": 1, "eligible_for_review": 0, "no_selection": 1}},
            }
            paths = {}
            for name, payload in payloads.items():
                path = root / f"{name}.json"
                path.write_text(json.dumps(payload), encoding="utf-8")
                paths[name] = path
            result = assemble(paths)
            self.assertEqual(result["coverage"]["raw_recent_pages_checked"], 10)
            self.assertEqual(result["coverage"]["openfootball_independent_score_matches"], 4)
            self.assertEqual(result["external_source_checks"]["quotes_observed"], 0)
            self.assertEqual(result["source_report_sha256"]["analyst"], hashlib.sha256(paths["analyst"].read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
