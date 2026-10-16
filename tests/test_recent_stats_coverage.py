import json
import tempfile
import unittest
from pathlib import Path

from bola.recent_stats_coverage import audit


class RecentStatsCoverageTests(unittest.TestCase):
    def test_raw_null_fields_are_reported_and_checksums_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            body = json.dumps({"props": {"pageProps": {"content": {"stats": None, "lineup": None}}}}).encode()
            page = root / "1_1.html"
            page.write_bytes(b'<script id="__NEXT_DATA__">' + body + b"</script>")
            import hashlib
            digest = hashlib.sha256(page.read_bytes()).hexdigest()
            report = {
                "snapshot_manifest": {"snapshot_folder": str(root), "captured_at": "2026-10-16T08:00:00Z",
                                      "files": {"1_1.html": {"match_id": "1", "team": "A", "sha256": digest}}},
                "teams": {"A": {"games": [{"match_id": "1", "kickoff": "2026-10-10T00:00:00Z",
                                               "stats_available": False, "lineup_available": False}]}}
            }
            report_path = root / "report.json"
            report_path.write_text(json.dumps(report), encoding="utf-8")
            result = audit(report_path)
            self.assertEqual(result["raw_pages_checked"], 1)
            self.assertEqual(result["stats_missing_reasons"], {"stats_null": 1})
            self.assertEqual(result["lineup_missing_reasons"], {"lineup_null": 1})
            self.assertEqual(result["anomalies"], [])


if __name__ == "__main__":
    unittest.main()
