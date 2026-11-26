import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

FIELD = Path(__file__).resolve().parents[1] / "benchmarks" / "fieldstudy"
sys.path.insert(0, str(FIELD))
import analyze
import runner
sys.path.pop(0)


class FieldRunnerTest(unittest.TestCase):
    def test_complete_balanced_schedule(self):
        jobs = runner.schedule("heldout")
        self.assertEqual(jobs, runner.schedule("heldout"))
        self.assertEqual(len(jobs), 72)
        self.assertEqual(len({tuple(row.values()) for row in jobs}), 72)
        for left, right in zip(jobs[::2], jobs[1::2]):
            self.assertEqual({left["condition"], right["condition"]}, {"baseline", "skill"})
            self.assertEqual({k: v for k, v in left.items() if k != "condition"},
                             {k: v for k, v in right.items() if k != "condition"})

    def test_field_and_exact_scores(self):
        gold = {"x": 1, "y": "Z"}
        self.assertTrue(runner.grade('{"x":1.0,"y":"Z"}', gold)["full_pass"])
        wrong = runner.grade('{"x":true,"y":"Z","z":3}', gold)
        self.assertFalse(wrong["full_pass"])
        self.assertFalse(wrong["exact_keys"])
        self.assertEqual(wrong["checks"], {"x": False, "y": True})
        self.assertFalse(any(runner.grade('{"x":0,"x":1,"y":"Z"}', gold)["checks"].values()))
        self.assertFalse(runner.grade('{"x":NaN,"y":"Z"}', gold)["checks"]["x"])

    def test_clean_environment_strips_billing_and_provider_overrides(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "example", "OPENAI_API_KEY": "example",
                                     "ANTHROPIC_BASE_URL": "example", "CODEX_HOME": "example"}):
            self.assertTrue(set(runner.clean_env()).isdisjoint(
                {"ANTHROPIC_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_BASE_URL", "CODEX_HOME"}))

    def test_paired_effect_equal_weights_each_scientific_case(self):
        def scored(scores):
            return {"checks": dict(enumerate(scores)), "full_pass": all(scores), "status": "submitted"}
        measurements = [(scored([False]), scored([True])),
                        (scored([True] * 9), scored([True] * 8 + [False]))]
        result = analyze.summarize(measurements)
        self.assertEqual(result["difference_pp"], 44.444)
        self.assertEqual([result[k] for k in ("better", "tied", "worse")], [1, 0, 1])
