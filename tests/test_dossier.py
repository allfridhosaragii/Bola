import unittest

from bola.dossier import assemble


class DossierTests(unittest.TestCase):
    def setUp(self):
        self.fixtures = {"fixtures": [{"match_id": "1", "home": "A", "away": "B",
                                       "kickoff": "2026-10-14T19:00:00+00:00", "status": "Upcoming",
                                       "url": "https://www.uefa.com/match/1",
                                       "retrieved_at": "2026-10-14T17:00:00+00:00"}]}
        self.squads = {"fixtures": [{"match_id": "1", "retrieved_at": "2026-10-14T17:05:00+00:00",
                                     "url": "https://www.uefa.com/match/1/lineups/",
                                     "official_starting_xi_parsed": False,
                                     "teams": {"A": {"registered_players": 25, "flagged_players": []},
                                               "B": {"registered_players": 24, "flagged_players": []}}}]}
        self.form = {"cutoff_exclusive_date_wib": "2026-10-15",
                     "snapshot_manifest": {"files": {"sample.csv": {"retrieved_at": "2026-10-14T17:10:00+00:00"}}},
                     "teams": {"A": {"windows": {}}, "B": {"windows": {}}}}

    def test_report_gates_and_future_source_rejection(self):
        result = assemble(self.fixtures, self.squads, self.form, "2026-10-15T00:20:00+07:00")
        gate = result["fixtures"][0]["evidence_gates"]
        self.assertTrue(gate["domestic_form_for_both"])
        self.form["teams"]["A"]["last_five_games"] = [{"date": "2026-10-10"}]
        result = assemble(self.fixtures, self.squads, self.form, "2026-10-15T00:20:00+07:00")
        self.assertEqual(result["fixtures"][0]["teams"]["A"]["days_since_last_captured_domestic_league_game"], 5)
        self.assertTrue(gate["uefa_fixture_snapshot_within_30m"])
        self.assertFalse(result["fixtures"][0]["ready_for_two_predictions"])
        old = assemble(self.fixtures, self.squads, self.form, "2026-10-15T00:50:00+07:00")
        self.assertFalse(old["fixtures"][0]["evidence_gates"]["uefa_fixture_snapshot_within_30m"])
        with self.assertRaises(ValueError):
            assemble(self.fixtures, self.squads, self.form, "2026-10-15T00:05:00+07:00")
        self.squads["fixtures"][0]["away"] = "C"
        with self.assertRaises(ValueError):
            assemble(self.fixtures, self.squads, self.form, "2026-10-15T00:20:00+07:00")

    def test_lineup_must_be_observed_before_kickoff(self):
        lineup = {"fixtures": [{"match_id": "1", "home": "A", "away": "B",
                                "kickoff": "2026-10-14T19:00:00Z",
                                "retrieved_at": "2026-10-14T17:15:00Z",
                                "official_starting_xi": True, "before_kickoff_at_retrieval": True,
                                "lineup_status": "INITIAL_AVAILABLE", "lineup_url": "https://match.uefa.com/test"}]}
        result = assemble(self.fixtures, self.squads, self.form, "2026-10-14T17:20:00Z", lineup)
        self.assertTrue(result["fixtures"][0]["evidence_gates"]["official_starting_xi"])
        lineup["fixtures"][0]["before_kickoff_at_retrieval"] = False
        result = assemble(self.fixtures, self.squads, self.form, "2026-10-14T17:20:00Z", lineup)
        self.assertFalse(result["fixtures"][0]["evidence_gates"]["official_starting_xi"])

    def test_badge_cross_checked_against_matchday_role(self):
        self.squads["fixtures"][0]["teams"]["A"]["flagged_players"] = [
            {"name": "Player A", "player_url": "https://www.uefa.com/clubs/players/123--player-a/",
             "badges": ["Injured"]}]
        lineup = {"fixtures": [{"match_id": "1", "home": "A", "away": "B",
                                "kickoff": "2026-10-14T19:00:00Z", "retrieved_at": "2026-10-14T17:15:00Z",
                                "official_starting_xi": True, "before_kickoff_at_retrieval": True,
                                "lineup_status": "AVAILABLE", "lineup_url": "https://match.uefa.com/test",
                                "teams": {"A": {"starters": [], "bench": [{"id": "123"}]},
                                          "B": {"starters": [], "bench": []}}}]}
        result = assemble(self.fixtures, self.squads, self.form, "2026-10-14T17:20:00Z", lineup)
        badges = result["fixtures"][0]["teams"]["A"]["badge_players_in_official_matchday_list"]
        self.assertEqual(badges[0]["lineup_role"], "bench")

    def test_extra_form_merges_and_rejects_future_or_duplicate_source(self):
        extra = {"cutoff_exclusive_date_wib": "2026-10-15",
                 "snapshot_manifest": {"files": {"extra.csv": {"retrieved_at": "2026-10-14T17:10:00Z"}}},
                 "teams": {"C": {"last_five_games": [{"date": "2026-10-10"}]}}}
        self.fixtures["fixtures"][0]["away"] = "C"
        self.squads["fixtures"][0]["away"] = "C"
        self.squads["fixtures"][0]["teams"]["C"] = self.squads["fixtures"][0]["teams"].pop("B")
        result = assemble(self.fixtures, self.squads, self.form, "2026-10-14T17:20:00Z", extra_form=extra)
        self.assertTrue(result["fixtures"][0]["evidence_gates"]["domestic_form_for_both"])
        extra["snapshot_manifest"]["files"]["extra.csv"]["retrieved_at"] = "2026-10-14T17:21:00Z"
        with self.assertRaises(ValueError):
            assemble(self.fixtures, self.squads, self.form, "2026-10-14T17:20:00Z", extra_form=extra)
        extra["snapshot_manifest"]["files"]["extra.csv"]["retrieved_at"] = "2026-10-14T17:10:00Z"
        extra["teams"]["A"] = {}
        with self.assertRaises(ValueError):
            assemble(self.fixtures, self.squads, self.form, "2026-10-14T17:20:00Z", extra_form=extra)


if __name__ == "__main__":
    unittest.main()
