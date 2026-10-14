import unittest

from bola.recovery import summarize_match


def event(kind, minute, second, team=1, possession=1, period=1, **extra):
    return {"type": {"name": kind}, "minute": minute, "second": second,
            "team": {"id": team}, "possession": possession, "period": period, **extra}


class RecoveryTests(unittest.TestCase):
    def test_first_recovery_and_same_possession_forward_window(self):
        rows = [event("Ball Recovery", 1, 0, location=[80, 30]),
                event("Ball Recovery", 1, 3, location=[30, 30]),
                event("Shot", 1, 10, shot={"statsbomb_xg": 0.2}),
                event("Shot", 1, 12, team=2, shot={"statsbomb_xg": 0.3}),
                event("Shot", 1, 20, shot={"statsbomb_xg": 0.4}),
                event("Shot", 1, 11, period=2, shot={"statsbomb_xg": 0.5}),
                event("Ball Recovery", 2, 0, possession=2, location=[20, 30],
                      ball_recovery={"recovery_failure": True})]
        result = summarize_match(rows, 15)
        self.assertEqual(result["opponent_half"]["recoveries"], 1)
        self.assertEqual(result["opponent_half"]["shot_sequences"], 1)
        self.assertEqual(result["opponent_half"]["shots"], 1)
        self.assertEqual(result["own_half"]["recoveries"], 0)


if __name__ == "__main__":
    unittest.main()
