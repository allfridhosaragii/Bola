import unittest
from unittest.mock import patch

from bola.odds_source_audit import audit


class OddsSourceAuditTests(unittest.TestCase):
    @patch("bola.odds_source_audit.probe")
    def test_audit_never_counts_access_as_a_quote(self, probe):
        probe.side_effect = [
            {"url": "https://example.test", "odds_observed": False},
            {"url": "https://example.test/id", "odds_observed": False},
        ]
        result = audit(["https://example.test", "https://example.test/id"])
        self.assertEqual(result["quotes_observed"], 0)
        self.assertEqual(probe.call_count, 2)

    def test_empty_url_list_is_rejected(self):
        with self.assertRaises(ValueError):
            audit([])


if __name__ == "__main__":
    unittest.main()
