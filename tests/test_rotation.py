import unittest

from bola.rotation import comparison


class RotationTests(unittest.TestCase):
    def test_prior_bench_and_absence_are_distinct(self):
        prior = {"field": [{"player": {"id": str(n)}} for n in range(11)],
                 "bench": [{"player": {"id": "11"}}]}
        current = {"starters": [{"id": str(n)} for n in range(9)] +
                               [{"id": "11"}, {"id": "12"}]}
        result = comparison(prior, current)
        self.assertEqual(result["retained_starters"], 9)
        self.assertEqual(result["new_starters_from_prior_bench"], 1)
        self.assertEqual(result["new_starters_not_in_prior_matchday_list"], 1)


if __name__ == "__main__":
    unittest.main()
