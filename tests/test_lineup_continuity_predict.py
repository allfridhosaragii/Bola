import unittest

from bola.lineup_continuity_predict import absence_load


class LineupContinuityTests(unittest.TestCase):
    def test_weights_missing_players_by_recent_start_share(self):
        history = [{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11},
                   {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12}]
        current = {1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 13}
        self.assertEqual(absence_load(history, current), 1.5)

    def test_rejects_empty_or_partial_history(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            absence_load([], set())
        with self.assertRaisesRegex(ValueError, "eleven"):
            absence_load([{1, 2}], {1, 2})


if __name__ == "__main__":
    unittest.main()
