import json
import tempfile
import unittest
from pathlib import Path

from bola.readiness_audit import (gate, latest_refresh_path, manifest_provenance,
                                  section, validate_refresh_manifest)


class ReadinessAuditTests(unittest.TestCase):
    @staticmethod
    def refresh(generated_at: str, *, lineage: bool = True) -> dict:
        return {
            "generated_at": generated_at,
            "evaluation_type": "Prospective pre-match refresh",
            "source_report_sha256": {name: "a" * 64 for name in
                                     ("analyst", "coverage", "crosscheck", "form", "odds", "openfootball", "recent", "schedule", "squad")},
            "lineage_checks": {
                "analyst_inputs_match_manifest": lineage,
                "forecast_dependent_reports_match_forecast": True,
                "openfootball_matches_primary_crosscheck": True,
                "recent_coverage_matches_recent_report": True,
            },
            "coverage": {}, "external_source_checks": {},
        }

    def test_section_requires_five_equal_gates(self):
        gates = [gate(str(i), i < 3, "evidence", "blocked") for i in range(5)]
        result = section("example", gates)
        self.assertEqual(result["passed"], 3)
        self.assertEqual(result["strict_gate_coverage_percent"], 60.0)

    def test_section_rejects_partial_rubric(self):
        with self.assertRaises(ValueError):
            section("example", [gate("one", True, "evidence", "blocked")])

    def test_latest_refresh_path_uses_manifest_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for suffix, generated_at in (("old", "2026-10-16T09:00:00+00:00"),
                                         ("new", "2026-10-16T10:00:00+00:00")):
                (root / f"target_refresh_evidence_{suffix}.json").write_text(
                    json.dumps(self.refresh(generated_at)), encoding="utf-8")
            self.assertEqual(latest_refresh_path(root).name, "target_refresh_evidence_new.json")

    def test_latest_refresh_path_requires_a_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                latest_refresh_path(Path(directory))

    def test_latest_refresh_path_rejects_newest_failed_lineage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "target_refresh_evidence_old.json").write_text(
                json.dumps(self.refresh("2026-10-16T09:00:00+00:00")), encoding="utf-8")
            (root / "target_refresh_evidence_new.json").write_text(
                json.dumps(self.refresh("2026-10-16T10:00:00+00:00", lineage=False)), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "lineage"):
                latest_refresh_path(root)

    def test_manifest_requires_complete_source_contract(self):
        refresh = self.refresh("2026-10-16T10:00:00+00:00")
        del refresh["source_report_sha256"]["odds"]
        with self.assertRaisesRegex(ValueError, "source-report"):
            validate_refresh_manifest(refresh)

    def test_manifest_provenance_records_exact_file_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "target_refresh_evidence_example.json"
            path.write_bytes(b"exact evidence")
            result = manifest_provenance(path, self.refresh("2026-10-16T10:00:00+00:00"))
            self.assertEqual(result["path"], path.name)
            self.assertEqual(result["sha256"], "f3483f1fe3825d30b7f4df4670e88edcadacd13e17c96fd2baa0009f9ecef2ae")
            self.assertEqual(result["generated_at"], "2026-10-16T10:00:00+00:00")


if __name__ == "__main__":
    unittest.main()
