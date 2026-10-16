import tempfile
import unittest
from datetime import date
from pathlib import Path

from bola.openfootball_crosscheck import audit, parse_matches


class OpenFootballCrosscheckTests(unittest.TestCase):
    def test_parser_uses_season_year_and_skips_unscored_rows(self):
        body = """Sat Sep 20 2026\n  20:00   Slavia Praha  2-1 (1-0)  Viktoria Plzeň\nFri Oct 9\n  18:00   FC Fastav Zlín  v  Slavia Praha\n"""
        rows = parse_matches(body, date(2026, 10, 16))
        self.assertEqual(rows[0]["date"], "2026-09-20")
        self.assertEqual(len(rows), 1)

    def test_audit_marks_missing_and_partial_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "czech-republic/2026-27_cz1.txt"
            path.parent.mkdir(parents=True)
            path.write_text("Sat Sep 20 2026\n  20:00   Slavia Praha  2-1  Viktoria Plzeň\n", encoding="utf-8")
            report = {"cutoff_exclusive_date_wib": "2026-10-16", "teams": {
                "Slavia Praha": {"matches": [{"source_date": "2026-09-20", "venue": "home", "goals_for": 2, "goals_against": 1}]},
                "Sabah": {"matches": []}, "S. Bratislava": {"matches": []},
            }}
            result = audit(root, report, date(2026, 10, 16))
            self.assertEqual(result["teams"]["Slavia Praha"]["source_status"], "verified_complete")
            self.assertEqual(result["teams"]["Sabah"]["source_status"], "missing_current_season_file")
            self.assertEqual(result["independent_full_window_teams"], 1)


if __name__ == "__main__":
    unittest.main()
