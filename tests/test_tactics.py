import unittest

from bola.tactics import event_summary, infer_directions


def shot(team, period, end_x):
    return {"team": team, "period": period, "time": 1.0, "type": "SHOT", "subtype": "ON TARGET-GOAL",
            "start_x": None, "end_x": end_x}


class TacticsTests(unittest.TestCase):
    def test_attack_direction_switch_changes_progression(self):
        events = [shot("Home", 1, 1.0), shot("Away", 1, 0.0),
                  shot("Home", 2, 0.0), shot("Away", 2, 1.0)]
        events.append({"team": "Home", "period": 1, "time": 2.0, "type": "PASS", "subtype": "",
                       "start_x": .2, "end_x": .4})
        events.append({"team": "Home", "period": 2, "time": 2.0, "type": "PASS", "subtype": "",
                       "start_x": .4, "end_x": .2})
        self.assertEqual(infer_directions(events)["Home", 2], -1)
        summary = event_summary(events)
        self.assertEqual(summary["Home_period_1"]["forward_10m_pass_proxy"], 1)
        self.assertEqual(summary["Home_period_2"]["forward_10m_pass_proxy"], 1)


if __name__ == "__main__":
    unittest.main()
