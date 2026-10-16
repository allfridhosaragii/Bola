import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from bola.target_refresh_evidence import assemble


class TargetRefreshEvidenceTests(unittest.TestCase):
    @staticmethod
    def write_valid_inputs(root: Path) -> dict[str, Path]:
        payloads = {
                "forecast": {"target_date_utc": "2026-10-20", "generated_at": "2026-10-16T00:00:00Z", "predictions": [{}]},
                "squad": {"forecast_generated_at": "2026-10-16T00:00:00Z", "refreshed_at": "2026-10-16T00:00:30Z",
                          "fixtures": [{"registered_players": {"A": 1}, "official_starting_xi_before_kickoff": False}]},
                "form": {"teams_covered": 2, "teams_requested": 2},
                "crosscheck": {"independent_matches_checked": 5, "independent_teams": 1},
                "openfootball": {"primary_crosscheck_sha256": None, "independent_score_matches": 4, "requested_score_matches": 15,
                                 "independent_full_window_teams": 0},
                "schedule": {"forecast_generated_at": "2026-10-16T00:00:00Z", "target_date_utc": "2026-10-20",
                             "summary": {"teams_with_scheduled_match_before_target": 1, "minimum_projected_rest_hours": 72}},
                "recent": {"summary": {"team_match_observations": 10, "observations_with_stats": 9,
                                           "observations_with_lineups": 10, "teams_with_all_five_stats_pages": 1,
                                           "teams_with_all_five_lineups": 2}},
                "coverage": {"report_path": "recent.json", "raw_pages_checked": 10, "anomalies": []},
                "odds": {"generated_at": "2026-10-16T00:00:00Z", "quotes_observed": 0,
                          "results": [{"url": "https://example.test", "http_code": 403, "status_chain": [403], "curl_exit_code": 0}]},
                "analyst": {"target_date_utc": "2026-10-20", "generated_at": "2026-10-16T00:01:00Z", "input_sha256": {},
                            "schedule_input_sha256": None, "recent_stats_input_sha256": None,
                            "summary": {"form_fresh": 1, "schedule_fresh": 1,
                             "recent_stats_fresh": 1, "eligible_for_review": 0, "no_selection": 1}},
        }
        paths = {}
        for name, payload in payloads.items():
            path = root / f"{name}.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            paths[name] = path
        payloads["openfootball"]["primary_crosscheck_sha256"] = hashlib.sha256(paths["crosscheck"].read_bytes()).hexdigest()
        payloads["analyst"]["input_sha256"] = {
            name: hashlib.sha256(paths[name].read_bytes()).hexdigest()
            for name in ("forecast", "form", "squad")
        }
        payloads["analyst"]["schedule_input_sha256"] = hashlib.sha256(paths["schedule"].read_bytes()).hexdigest()
        payloads["analyst"]["recent_stats_input_sha256"] = hashlib.sha256(paths["recent"].read_bytes()).hexdigest()
        for name in ("openfootball", "analyst"):
            paths[name].write_text(json.dumps(payloads[name]), encoding="utf-8")
        return paths

    def test_assemble_uses_input_hashes_and_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self.write_valid_inputs(Path(directory))
            result = assemble(paths)
            self.assertEqual(result["coverage"]["raw_recent_pages_checked"], 10)
            self.assertEqual(result["coverage"]["openfootball_independent_score_matches"], 4)
            self.assertEqual(result["external_source_checks"]["quotes_observed"], 0)
            self.assertEqual(result["source_report_sha256"]["analyst"], hashlib.sha256(paths["analyst"].read_bytes()).hexdigest())
            self.assertTrue(result["lineage_checks"]["analyst_inputs_match_manifest"])

    def test_assemble_rejects_mixed_lineage(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self.write_valid_inputs(Path(directory))
            form = json.loads(paths["form"].read_text(encoding="utf-8"))
            form["teams_covered"] = 1
            paths["form"].write_text(json.dumps(form), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "analyst form checksum"):
                assemble(paths)


if __name__ == "__main__":
    unittest.main()
