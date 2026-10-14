import json
from pathlib import Path
import tempfile
import unittest

from bola.backtest import Match, Model, load_matches, metrics, poisson_probs, run_chronological
from datetime import date


class DataTests(unittest.TestCase):
    def test_both_full_time_score_shapes_are_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "sample"
            folder.mkdir()
            (folder / "en.1.json").write_text(json.dumps({"matches": [
                {"date": "2025-08-01", "team1": "A", "team2": "B", "score": {"ft": [2, 1]}},
                {"date": "2025-08-08", "team1": "B", "team2": "A", "score": [0, 0]},
            ]}))
            matches, audit = load_matches(Path(tmp), ["sample"])
            self.assertEqual([m.outcome for m in matches], ["H", "D"])
            self.assertEqual(audit["sample"]["score_list"], 1)

    def test_same_day_order_does_not_change_predictions(self):
        first = Match("s", date(2025, 1, 1), "A", "B", 3, 0, "score.ft")
        second = Match("s", date(2025, 1, 1), "C", "D", 0, 1, "score.ft")
        forward = {m.home: pred for m, pred in run_chronological([first, second])}
        backward = {m.home: pred for m, pred in run_chronological([second, first])}
        self.assertEqual(forward, backward)

    def test_probabilities_and_metrics(self):
        probs = poisson_probs(1.4, 1.0)
        self.assertAlmostEqual(sum(probs), 1)
        match = Match("s", date(2025, 1, 1), "A", "B", 1, 0, "score.ft")
        self.assertEqual(metrics([(match, probs)])["n"], 1)

    def test_strong_favourite_does_not_zero_underdog_probability(self):
        model = Model()
        model.elo["A"] = 2000
        model.elo["B"] = 1200
        match = Match("s", date(2025, 1, 1), "A", "B", 0, 1, "score.ft")
        p = model.predict(match)["elo"]
        self.assertGreater(p[2], 0.001)
        self.assertAlmostEqual(sum(p), 1)


if __name__ == "__main__":
    unittest.main()
