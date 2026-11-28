"""The post-study material-property audit releases only coarse outcomes for fixed submissions."""

import json
from pathlib import Path
import unittest
from unittest.mock import patch

from benchmarks.research_review import material_properties as audit


class MaterialPropertiesTests(unittest.TestCase):
    def test_numeric_directions_and_tolerance_decisions(self):
        rows = [
            ["s", "relative", [70, 70, 99]],
            ["s", "absolute", [0.001, 0.001, 0.007]],
        ]
        truth = {"s": {"relative": 100, "absolute": 0.0}}
        rules = {
            "relative": {"mode": "rel", "tol": 0.05},
            "absolute": {"mode": "abs", "tol": 0.01},
        }
        result = audit.compare_changes(rows, truth, lambda sample, prop: rules[prop])
        self.assertEqual(
            result,
            [
                {
                    "within_tolerance": [False, False, True],
                    "ordinary_vs_draft": "unchanged",
                    "skill_vs_ordinary": "closer",
                },
                {
                    "within_tolerance": [True, True, True],
                    "ordinary_vs_draft": "unchanged",
                    "skill_vs_ordinary": "farther",
                },
            ],
        )
        self.assertNotIn("100", json.dumps(result))

    def test_exact_and_near_ties_get_same_result_for_distinct_inputs(self):
        rows = [["s", "p", [8, 8, 12]]]

        def rule(*_):
            return {"mode": "abs", "tol": 1}

        for reference in (10, 10.00025):
            self.assertEqual(
                audit.compare_changes(rows, {"s": {"p": reference}}, rule)[0][
                    "skill_vs_ordinary"
                ],
                "unresolved",
            )

    def test_invalid_measurement_rules_fail_closed(self):
        for rule in (
            {"mode": "unknown", "tol": 1},
            {"mode": "rel", "tol": 1},
            {"mode": "abs", "tol": 0},
            {"mode": "abs", "tol": float("inf")},
        ):
            with self.assertRaises(ValueError):
                audit.compare_changes(
                    [["s", "x", [0, 1, 2]]], {"s": {"x": 0}}, lambda *_: rule
                )

    def test_partial_cohort_never_contacts_the_verifier(self):
        models = {"models": ["terra", "sonnet"]}
        incomplete = {arm: {"outcome": "missing"} for arm in audit.repair_trial.ARMS}
        with (
            patch.object(
                audit.repair_trial,
                "validate_protocol",
                return_value=(models, "skill", {audit.TASK: {"id": audit.TASK}}),
            ),
            patch.object(audit.repair_trial, "assignment", return_value=incomplete),
            patch.object(audit.frontier, "temporary_container") as create,
        ):
            with self.assertRaisesRegex(ValueError, "Finish all six"):
                audit.audit(Path("."))
            create.assert_not_called()
