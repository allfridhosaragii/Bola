import unittest

from bola.readiness_audit import gate, section


class ReadinessAuditTests(unittest.TestCase):
    def test_section_requires_five_equal_gates(self):
        gates = [gate(str(i), i < 3, "evidence", "blocked") for i in range(5)]
        result = section("example", gates)
        self.assertEqual(result["passed"], 3)
        self.assertEqual(result["strict_gate_coverage_percent"], 60.0)

    def test_section_rejects_partial_rubric(self):
        with self.assertRaises(ValueError):
            section("example", [gate("one", True, "evidence", "blocked")])


if __name__ == "__main__":
    unittest.main()
