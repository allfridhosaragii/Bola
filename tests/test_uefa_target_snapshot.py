import unittest

from bola.uefa_target_snapshot import check_fixtures, target_urls


class TargetSnapshotTests(unittest.TestCase):
    def test_sitemap_mapping_and_identity(self):
        sitemap = b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://www.uefa.com/match/7--a-vs-b/</loc></url></urlset>'
        self.assertEqual(target_urls(sitemap, {"7"})["7"], "https://www.uefa.com/match/7--a-vs-b/")
        with self.assertRaisesRegex(ValueError, "missing"):
            target_urls(sitemap, {"8"})
        archive = {"predictions": [{"match_id": "7", "home": "A", "away": "B",
                                    "kickoff": "2026-10-20T19:00:00Z"}]}
        fixture = {"match_id": "7", "home": "A", "away": "B", "kickoff": "2026-10-20T19:00:00+00:00"}
        check_fixtures(archive, [fixture])
        fixture["away"] = "C"
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            check_fixtures(archive, [fixture])


if __name__ == "__main__":
    unittest.main()
