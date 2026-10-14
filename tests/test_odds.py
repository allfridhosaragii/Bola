import unittest

from bola.odds import market_probs


class OddsTests(unittest.TestCase):
    def test_overround_removed_and_bad_price_rejected(self):
        row = {"AvgCH": "2", "AvgCD": "4", "AvgCA": "4"}
        self.assertEqual(market_probs(row, "C"), ((0.5, 0.25, 0.25), 0.0))
        row["AvgCA"] = "1"
        with self.assertRaises(ValueError):
            market_probs(row, "C")


if __name__ == "__main__":
    unittest.main()
