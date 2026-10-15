import unittest

from bola.pressure_predict import pressure_regains


def event(index, second, kind, team, possession, possession_team):
    return {"index": index, "period": 1, "minute": 0, "second": second,
            "type": {"name": kind}, "team": {"id": team}, "possession": possession,
            "possession_team": {"id": possession_team}}


class PressurePredictTests(unittest.TestCase):
    def test_unique_regain_within_five_seconds(self):
        rows = [event(1, 1, "Pressure", 1, 10, 2),
                event(2, 3, "Ball Recovery", 1, 11, 1),
                event(3, 4, "Pressure", 1, 10, 2),
                event(4, 5, "Pass", 1, 11, 1),
                event(5, 20, "Pressure", 2, 12, 1),
                event(6, 27, "Pass", 2, 13, 2)]
        pressures, regains = pressure_regains(rows)
        self.assertEqual(pressures, {"1": 2, "2": 1})
        self.assertEqual(regains, {"1": 1})

    def test_same_possession_is_not_regain(self):
        rows = [event(1, 1, "Pressure", 1, 10, 2), event(2, 2, "Duel", 1, 10, 1)]
        _, regains = pressure_regains(rows)
        self.assertFalse(regains)


if __name__ == "__main__":
    unittest.main()
