import hashlib
from datetime import date
from pathlib import Path
import tempfile
import unittest

from bola.form import read_league, summarize_window, team_rows


class FormTests(unittest.TestCase):
    def test_cutoff_and_half_time_split(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            files = {}
            for season, rows in (("2526", "E0,01/09/2025,A,B,2,1,1,0,8,7,4,2,5,3,1,2,0,0\n"),
                                 ("2627", "E0,15/10/2026,A,B,9,0,9,0,20,1,10,0,10,0,2,0,0,0\n")):
                body = ("Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,HTHG,HTAG,HS,AS,HST,AST,HC,AC,HY,AY,HR,AR\n" + rows).encode()
                filename = f"{season}_E0.csv"
                (root / filename).write_bytes(body)
                files[filename] = {"sha256": hashlib.sha256(body).hexdigest()}
            matches = read_league(root, {"files": files}, "E0", date(2026, 10, 15))
            self.assertEqual(len(matches), 1)
            home = team_rows(matches)["A"][0]
            self.assertEqual(home["first_half_goals_for"], 1)
            self.assertEqual(home["second_half_goals_for"], 1)
            self.assertGreater(home["elo_result_surplus"], 0)
            (root / "2627_E0.csv").write_text("changed")
            with self.assertRaises(ValueError):
                read_league(root, {"files": files}, "E0", date(2026, 10, 15))

    def test_recent_games_receive_more_weight(self):
        row = {name: 0 for name in ("goals_for", "goals_against", "shots_for", "shots_against",
                                      "shots_on_target_for", "shots_on_target_against", "corners_for",
                                      "corners_against", "yellow_for", "yellow_against", "red_for",
                                      "red_against", "first_half_goals_for", "first_half_goals_against",
                                      "second_half_goals_for", "second_half_goals_against", "elo_result_surplus")}
        rows = [{**row, "date": f"2026-10-{day:02d}", "season": "2627", "result": "D", "venue": "home",
                 "opponent_elo_before": 1500, "goals_for": 5 if day == 5 else 0} for day in range(1, 6)]
        result = summarize_window(rows, 5)
        self.assertEqual(result["metrics"]["goals_for"]["mean"], 1)
        self.assertGreater(result["metrics"]["goals_for"]["recency_weighted_mean"], 1)


if __name__ == "__main__":
    unittest.main()
