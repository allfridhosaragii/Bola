import json
import tempfile
import unittest
from pathlib import Path

from bola.readiness_audit import gate, latest_refresh_path, section


class ReadinessAuditTests(unittest.TestCase):
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
                    json.dumps({"generated_at": generated_at}), encoding="utf-8")
            self.assertEqual(latest_refresh_path(root).name, "target_refresh_evidence_new.json")

    def test_latest_refresh_path_requires_a_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                latest_refresh_path(Path(directory))


if __name__ == "__main__":
    unittest.main()
