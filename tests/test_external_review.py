"""Regression controls for substantive repairs, invalid artifacts and reference exposure."""

import json
import unittest

from benchmarks.external_review import report, statistics, trial


class ExternalReviewTests(unittest.TestCase):
    def test_payment_abstention_is_a_valid_wrong_answer(self):
        case = {
            "mode": "payments",
            "kind": "number",
            "gold": {"answer": 2.1},
            "tol": 1e-6,
        }
        result = trial.grade(case, {"answer.json": '{"answer":"Not Applicable"}'})
        self.assertTrue(result["valid"])
        self.assertFalse(result["correct"])

    def test_malformed_numeric_submission_cannot_abort_export(self):
        case = statistics.cases("dev")[0]
        for raw in (
            '{"answer":{"decision":"reject","p_value":NaN}}',
            '{"answer":{"decision":[],"p_value":0.01}}',
            "[]",
            "{}",
        ):
            self.assertFalse(trial.grade(case, {"answer.json": raw})["valid"])

    def test_stats_packets_separate_data_and_answer(self):
        dev = statistics.cases("dev")
        held = statistics.cases("holdout")
        self.assertTrue(
            {c["family"] for c in dev}.isdisjoint(c["family"] for c in held)
        )
        for case in dev + held:
            self.assertEqual(set(case["files"]), {"TASK.md", "dataset.csv"})
            self.assertTrue(
                trial.grade(case, {"answer.json": json.dumps(case["gold"])})["correct"]
            )

    def test_one_draft_is_one_repair_opportunity(self):
        rows = [
            {
                "mode": "programming",
                "phase": "holdout",
                "case": "A",
                "client": "m",
                "arm": arm,
                "strict_eligible": True,
                "score": {"valid": True, "correct": correct},
            }
            for arm, correct in zip(
                ("draft", "ordinary", "general", "specialist"),
                (False, False, True, False),
            )
        ]
        count = report.paired(rows)["holdout/programming"]
        self.assertEqual(count["general_only"], 1)
        self.assertEqual(count["general_repairs"], 1)
        self.assertEqual(count["ordinary_opportunities"], 1)

    def test_expected_holdout_schedule_keeps_omissions_and_repeats_errors(self):
        suite = {
            "splits": {"dev": {}, "holdout": {"wrong": {}, "omitted": {}}},
            "models": ["model"],
        }
        protocol = {"suites": {"programming": suite}, "qualified": ["programming"]}
        drafts = [
            {
                "mode": "programming",
                "phase": "holdout",
                "case": case,
                "client": "model",
                "arm": "draft",
                "status": "submitted",
                "strict_eligible": True,
                "initial_score": {"valid": valid, "correct": False},
            }
            for case, valid in [("wrong", True), ("omitted", False)]
        ]
        schedule = report.expected_keys(protocol, drafts)
        self.assertEqual(len(schedule), 11)
        self.assertIn(
            ("programming", "holdout", "omitted", "model", "ordinary"), schedule
        )
        self.assertNotIn(
            ("programming", "holdout", "omitted", "model", "ordinary-repeat"), schedule
        )
        self.assertRaises(ValueError, report.check_schedule, protocol, drafts)
