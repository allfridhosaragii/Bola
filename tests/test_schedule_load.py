import json
import unittest

from bola.schedule_load import assemble


def fixture(mid, when, team_id, opponent_id, *, finished, tournament="League", home=True):
    own = {"id": team_id, "name": f"Team {team_id}", "score": 1 if finished else None}
    other = {"id": opponent_id, "name": f"Team {opponent_id}", "score": 0 if finished else None}
    return {"id": mid, "home": own if home else other, "away": other if home else own,
            "notStarted": not finished, "tournament": {"name": tournament},
            "status": {"utcTime": when, "finished": finished, "started": finished,
                       "cancelled": False, "awarded": False}}


def page(team_id, fixtures):
    payload = {"props": {"pageProps": {"fallback": {f"team-{team_id}": {
        "details": {"id": team_id}, "fixtures": {"allFixtures": {"fixtures": fixtures}}
    }}}}}
    return '<script id="__NEXT_DATA__" type="application/json">' + json.dumps(payload) + "</script>"


class ScheduleLoadTests(unittest.TestCase):
    def test_real_time_windows_and_pair_crosscheck(self):
        target = "2026-10-20T19:00:00Z"
        archive = {"generated_at": "2026-10-15T12:00:00Z", "target_date_utc": "2026-10-20",
                   "predictions": [{"match_id": "u1", "home": "A", "away": "B", "kickoff": target}]}
        common = fixture(99, target, 1, 2, finished=False)
        pages = {
            "A": page(1, [fixture(10, "2026-10-10T19:00:00Z", 1, 3, finished=True),
                           fixture(11, "2026-10-17T19:00:00Z", 1, 4, finished=False), common]),
            "B": page(2, [fixture(20, "2026-10-01T19:00:00Z", 2, 5, finished=True),
                           fixture(99, target, 1, 2, finished=False)]),
        }
        manifest = {"teams": {
            "A": {"team_id": 1, "retrieved_at": "2026-10-15T12:00:00Z"},
            "B": {"team_id": 2, "retrieved_at": "2026-10-15T12:00:00Z"},
        }}
        report = assemble(archive, manifest, pages)
        self.assertEqual(report["summary"]["target_pairs_agree"], 1)
        self.assertEqual(report["teams"]["A"]["scheduled_matches_before_target"], 1)
        self.assertEqual(report["teams"]["A"]["projected_hours_from_preceding_fixture_to_target"], 72)
        self.assertEqual(report["teams"]["B"]["completed_in_previous_14_days"], 1)

    def test_rejects_target_venue_mismatch(self):
        target = "2026-10-20T19:00:00Z"
        archive = {"generated_at": "2026-10-15T12:00:00Z", "target_date_utc": "2026-10-20",
                   "predictions": [{"match_id": "u1", "home": "A", "away": "B", "kickoff": target}]}
        wrong = fixture(99, target, 1, 2, finished=False, home=False)
        past_a = fixture(10, "2026-10-10T19:00:00Z", 1, 3, finished=True)
        past_b = fixture(20, "2026-10-10T19:00:00Z", 2, 3, finished=True)
        manifest = {"teams": {"A": {"team_id": 1, "retrieved_at": "2026-10-15T12:00:00Z"},
                              "B": {"team_id": 2, "retrieved_at": "2026-10-15T12:00:00Z"}}}
        with self.assertRaisesRegex(ValueError, "venue"):
            assemble(archive, manifest, {"A": page(1, [past_a, wrong]),
                                         "B": page(2, [past_b, wrong])})


if __name__ == "__main__":
    unittest.main()
