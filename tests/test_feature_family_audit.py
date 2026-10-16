import unittest

from bola.feature_family_audit import percentile, summarize_replicates


class FeatureFamilyAuditTests(unittest.TestCase):
    def test_familywise_interval_is_wider_than_nominal(self):
        values = [float(value) for value in range(1000)]
        result = summarize_replicates(-1.0, values, 4)
        nominal = result["nominal_bootstrap_95_ci"]
        adjusted = result["bonferroni_familywise_95_ci"]
        self.assertLessEqual(adjusted[0], nominal[0])
        self.assertGreaterEqual(adjusted[1], nominal[1])

    def test_percentile_rejects_invalid_input(self):
        with self.assertRaises(ValueError):
            percentile([], 0.5)
        with self.assertRaises(ValueError):
            percentile([1.0], 1.1)


if __name__ == "__main__":
    unittest.main()
