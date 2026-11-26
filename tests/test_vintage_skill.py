"""Offline checks for the CSV helper shipped with the vintage skill."""
import csv
import importlib.util
from io import StringIO
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "skills/reconstruct-a-vintage/asof.py"
spec = importlib.util.spec_from_file_location("asof", path)
asof = importlib.util.module_from_spec(spec)
spec.loader.exec_module(asof)


class VintageTests(unittest.TestCase):
    def rows(self, lines, cutoff="2026-01-04"):
        reader = csv.DictReader(StringIO("station,round,issued,seen,rev,state,n\n" + lines))
        result = asof.select(reader, ["station", "round"], "seen",
                             asof.instant(cutoff, end_of_day=True),
                             [asof.ordering("issued:date"), asof.ordering("rev:int")],
                             ("state", "withdrawn"))
        return [(row["station"], row["round"], row["n"]) for row in result]

    def test_future_revision_excluded_and_withdrawal_applies_after_selection(self):
        rows = ("A,1,2026-01-01,2026-01-02,1,live,4\n"
                "A,1,2026-01-03,2026-01-05,2,live,6\n"
                "B,1,2026-01-01,2026-01-01,1,live,7\n"
                "B,1,2026-01-03,2026-01-04,2,withdrawn,\n"
                "B,2,2026-01-03,2026-01-04,1,live,0\n")
        self.assertEqual(self.rows(rows), [("A", "1", "4"), ("B", "2", "0")])
        self.assertEqual(self.rows(rows, "2026-01-05")[0][-1], "6")

    def test_numeric_tiebreak_and_utc_date_boundary(self):
        rows = ("A,1,2026-01-01,2026-01-04,2,live,4\n"
                "A,1,2026-01-01,2026-01-05T01:00:00+02:00,10,live,9\n"
                "A,1,2026-01-02,2026-01-05T00:00:00Z,11,live,13\n")
        self.assertEqual(self.rows(rows), [("A", "1", "9")])

    def test_ambiguous_latest_rejected_but_resolved_old_tie_is_harmless(self):
        rows = ("A,1,2026-01-01,2026-01-02,1,live,4\n"
                "A,1,2026-01-01,2026-01-02,1,live,8\n")
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            self.rows(rows)
        self.assertEqual(self.rows(rows + "A,1,2026-01-02,2026-01-03,2,live,7\n"), [("A", "1", "7")])

    def test_integer_availability_uses_numeric_order(self):
        rows = csv.DictReader(StringIO("id,week,samples\nA,2,7\nA,10,6\nA,12,4\n"))
        result = list(asof.select(rows, ["id"], "week", 10, [("week", int)], clock=int))
        self.assertEqual([row["samples"] for row in result], ["6"])

    def test_bad_headers_timestamps_and_keys_fail_clearly(self):
        with self.assertRaisesRegex(ValueError, "Missing columns"):
            list(asof.select(csv.DictReader(StringIO("x\n1\n")), ["k"], "date", None, []))
        with self.assertRaisesRegex(ValueError, "UTC offset"):
            self.rows("A,1,2026-01-01,2026-01-03T03:00:00,1,live,4\n")
        with self.assertRaisesRegex(ValueError, "empty grouping key"):
            self.rows("A,,2026-01-01,2026-01-03,1,live,4\n")


if __name__ == "__main__":
    unittest.main()
