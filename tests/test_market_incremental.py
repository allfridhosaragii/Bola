import unittest
from datetime import date

from bola.backtest import Match
from bola.market_incremental import MarketRecord, model_market_mix, paired_block_difference


class MarketIncrementalTests(unittest.TestCase):
    def row(self, market, model, score=(1, 0)):
        return MarketRecord(
            "test.league",
            Match("test", date(2026, 1, 1), "home", "away", *score, "test"),
            market,
            market,
            model,
        )

    def test_zero_weight_exactly_preserves_market(self):
        row = self.row((0.5, 0.3, 0.2), (0.2, 0.3, 0.5))
        self.assertEqual(model_market_mix(row, 0), row.market_open)
        comparison = paired_block_difference([row], 0, repetitions=100)
        self.assertEqual(comparison["difference_candidate_minus_market_open"], 0)
        self.assertEqual(comparison["ci95"], [0, 0])
        with self.assertRaises(ValueError):
            model_market_mix(row, 1.1)

    def test_paired_difference_has_expected_direction(self):
        row = self.row((0.4, 0.3, 0.3), (0.8, 0.1, 0.1))
        result = paired_block_difference([row], 1.0, repetitions=100)
        self.assertLess(result["difference_candidate_minus_market_open"], 0)
        self.assertLess(result["ci95"][1], 0)


if __name__ == "__main__":
    unittest.main()
