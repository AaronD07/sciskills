import unittest

from analyze import summarize
from grading import equivalent, evaluate, run_program


class ReviewStudyTests(unittest.TestCase):
    def test_reference_numbers_accept_roundoff_but_reject_missing_and_boolean(self):
        self.assertTrue(equivalent({"n": 3.0000001}, {"n": 3}))
        for value in (True, float("nan"), "1", None):
            self.assertFalse(equivalent(value, 1))
        case = {"route": "numbers", "gold": {"value": 4}}
        for raw in ('{"value":1,"value":4}', '{"value":4,"extra":2}'):
            self.assertFalse(
                evaluate(case, {"answer.json": raw}, "submitted")["full_pass"]
            )

    def test_large_integer_and_noisy_scientific_program(self):
        self.assertFalse(equivalent(10**309, 1.0))
        files = {
            "solution.py": "def solve(rows):\n    print('x' * 14000)\n    return len(rows)\n"
        }
        self.assertEqual(run_program(files, [{"x": "3"}]), (True, 1))

    def test_compares_repairs_and_damage_from_same_parent(self):
        def row(arm, passed):
            return {
                "grade": {"full_pass": passed},
                "elapsed_seconds": 2,
                "calls": [],
                "arm": arm,
                "status": "submitted",
            }

        def triple(scores):
            return (
                {"source": "single"},
                *(row(k, v) for k, v in zip(("draft", "ordinary", "skill"), scores)),
            )

        result = summarize([triple([False, False, True]), triple([True, True, False])])
        for key in ("only_skill_repairs", "skill_breaks"):
            self.assertEqual(result[key], 1)
        self.assertEqual(result["cluster_interval_pp"], [0, 0])
