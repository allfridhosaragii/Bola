import unittest

from bola.analyst_markdown import render


class AnalystMarkdownTests(unittest.TestCase):
    def test_render_preserves_probabilities_and_blockers(self):
        report = {
            "generated_at": "2026-10-16T12:54:05+00:00",
            "target_date_utc": "2026-10-20",
            "summary": {"matches": 1, "eligible_for_review": 0, "no_selection": 1},
            "matches": [{
                "match_id": "42", "home": "Alpha", "away": "Beta",
                "kickoff": "2026-10-20T18:00:00Z",
                "probabilities_h_d_a_exploratory": [0.5, 0.25, 0.25],
                "selection_status": "no_selection",
                "form": {"Alpha": {"windows": {"5": {"record": {"W": 3, "D": 1, "L": 1},
                                                         "goals_for_per_game": 2.0,
                                                         "goals_against_per_game": 0.8}}}},
                "schedule_load": {}, "recent_match_stats": {},
                "registered_players": {"Alpha": 22, "Beta": 21},
                "flagged_player_counts": {"Alpha": 1, "Beta": 0},
                "lineup_status": "NOT_AVAILABLE", "squad_retrieved_at": "2026-10-16T12:00:00Z",
                "market": None,
                "blocking_gates": ["official_starting_xi_before_kickoff", "fresh_market_screenshot"],
            }],
            "limitations": ["Stats are descriptive.",
                            "Domestic form is descriptive and is not an input to the frozen UEFA probability model."],
            "input_sha256": {"forecast": "abc123"},
            "schedule_input_sha256": "def456",
        }
        output = render(report)
        self.assertIn("50.0% / 25.0% / 25.0%", output)
        self.assertIn("form 5: 3-1-1", output)
        self.assertIn("XI resmi diumumkan sebelum kickoff", output)
        self.assertIn("Bukti odds 1X2 bertimestamp masih segar", output)
        self.assertIn("**no_selection**", output)
        self.assertIn("bersifat eksploratif", output)
        self.assertIn("SHA-256 `abc123`", output)
        self.assertIn("Form domestik bersifat deskriptif", output)
        self.assertIn("Skuad terdaftar: Alpha: 22, Beta: 21", output)
        self.assertNotIn("rekomendasi taruhan", output.split("## Alpha vs Beta", 1)[1].split("## Batasan", 1)[0])

    def test_rejects_missing_matches_list(self):
        with self.assertRaisesRegex(ValueError, "matches list"):
            render({"summary": {}})


if __name__ == "__main__":
    unittest.main()
