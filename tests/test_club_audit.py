import unittest

from bola.club_audit import rotation_bucket, starting_xi


def event(team, players):
    return {"type": {"name": "Starting XI"}, "team": {"id": team},
            "tactics": {"lineup": [{"player": {"id": player}} for player in players]}}


class ClubAuditTest(unittest.TestCase):
    def test_starting_xi_matches_teams_and_has_unique_eleven(self):
        events = [event(1, range(11)), event(2, range(11, 22))]
        self.assertEqual(len(starting_xi(events, {1, 2})[1]), 11)
        with self.assertRaises(ValueError):
            starting_xi([event(1, [0] * 11), events[1]], {1, 2})
        with self.assertRaises(ValueError):
            starting_xi(events, {1, 3})

    def test_rotation_buckets_are_disjoint(self):
        self.assertEqual([rotation_bucket(n) for n in (0, 2, 3, 4, 5, 11)],
                         ["0-2", "0-2", "3-4", "3-4", "5-11", "5-11"])


if __name__ == "__main__":
    unittest.main()
