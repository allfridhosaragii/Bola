from datetime import date
import unittest

from bola.backtest import Match
from bola.uefa_extended_backtest import (EXPECTED, classwise_calibration, evaluate_rows,
                                         outcome_reweight_factors, reweight)


class ExtendedUefaBacktestTests(unittest.TestCase):
    def test_complete_sample_and_matchday_holdouts(self):
        rows = []
        counter = 0
        for season, count in EXPECTED.items():
            for index in range(count):
                counter += 1
                if season in ("2025", "2026") and index < 144:
                    stage, day = "League Phase", f"{int(season)-1}-09-{17 + index % 2:02d}"
                elif season == "2027" and index < 18:
                    stage, day = "League Phase", f"2026-09-{9 + index % 2:02d}"
                elif season == "2027" and index < 36:
                    stage, day = "League Phase", f"2026-10-{13 + index % 2:02d}"
                else:
                    stage, day = "Qualifying", f"{int(season)-1}-07-{1 + index % 20:02d}"
                rows.append({"id": str(counter), "season": int(season), "kickoff": day + "T19:00:00Z",
                             "stage": stage, "home_id": str(index % 20),
                             "away_id": str((index + 1) % 20),
                             "home_goals": index % 3, "away_goals": (index + 1) % 2})
        report = evaluate_rows(rows)
        self.assertEqual(report["results"]["2025_league_phase"]["matches"], 144)
        self.assertEqual(report["results"]["2026_league_phase"]["matches"], 144)
        self.assertEqual(report["results"]["2027_md1"]["matches"], 18)
        self.assertEqual(report["results"]["2027_md2"]["matches"], 18)
        self.assertEqual(sum(report["sample"].values()), 1114)
        self.assertIn(report["weight_selection"]["candidate_weight"], (0.0, 0.25, 0.5, 0.75, 1.0))
        self.assertIn(report["weight_selection"]["deployed_weight"], (0.0, 0.25, 0.5, 0.75, 1.0))
        self.assertIn(report["weight_selection"]["decision"], ("candidate_accepted", "incumbent_retained"))
        self.assertEqual(report["weight_selection"]["locked_evaluation_periods"],
                         ["2026_league_phase", "2027_md1", "2027_md2"])
        self.assertIn("deployed_blend_minus_fixed_0_5_log_loss", report["results"]["2027_md2"])
        self.assertEqual(report["results"]["locked_combined"]["matches"], 180)
        calibration = report["results"]["locked_combined"]["blend_classwise_calibration_5_bins"]
        self.assertEqual(sum(row["matches"] for row in calibration["H"]["bins"]), 180)
        self.assertEqual(report["calibration_candidate"]["evaluation_matches"], 36)
        self.assertIn(report["calibration_candidate"]["decision"],
                      ("candidate_accepted", "candidate_rejected"))

    def test_rejects_incomplete_sample(self):
        with self.assertRaisesRegex(ValueError, "Unexpected extended"):
            evaluate_rows([])

    def test_classwise_calibration_counts_every_match_for_every_class(self):
        rows = [(Match("x", date(2026, 1, 1), "a", "b", 1, 0, "x"), (0.7, 0.2, 0.1)),
                (Match("x", date(2026, 1, 2), "b", "a", 1, 1, "x"), (0.4, 0.3, 0.3))]
        report = classwise_calibration(rows)
        for outcome in ("H", "D", "A"):
            self.assertEqual(sum(item["matches"] for item in report[outcome]["bins"]), 2)
            self.assertGreaterEqual(report[outcome]["ece"], 0)

    def test_outcome_reweighting_is_normalized(self):
        rows = [(Match("x", date(2026, 1, 1), "a", "b", 1, 0, "x"), (0.5, 0.3, 0.2)),
                (Match("x", date(2026, 1, 2), "b", "a", 1, 1, "x"), (0.4, 0.3, 0.3)),
                (Match("x", date(2026, 1, 3), "c", "a", 0, 1, "x"), (0.4, 0.3, 0.3))]
        factors = outcome_reweight_factors(rows)
        corrected = reweight((0.5, 0.3, 0.2), factors)
        self.assertAlmostEqual(sum(corrected), 1)
        self.assertTrue(all(value > 0 for value in corrected))


if __name__ == "__main__":
    unittest.main()
