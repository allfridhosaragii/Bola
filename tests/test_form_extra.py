import unittest
from datetime import date

from bola.form_extra import read_rows


class ExtraFormTest(unittest.TestCase):
    def test_season_cutoff_and_score_agreement(self):
        body = ("Country,League,Season,Date,Home,Away,HG,AG,Res\n"
                "Norway,Eliteserien,2026,10/10/2026,Bodo/Glimt,A,2,1,H\n"
                "Norway,Eliteserien,2026,15/10/2026,Bodo/Glimt,B,5,0,H\n").encode()
        rows = read_rows(body, "Norway", "Eliteserien", {"2026"}, date(2026, 10, 15))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["FTHG"], "2")
        with self.assertRaises(ValueError):
            read_rows(body.replace(b"2,1,H", b"2,1,A"), "Norway", "Eliteserien", {"2026"},
                      date(2026, 10, 15))


if __name__ == "__main__":
    unittest.main()
