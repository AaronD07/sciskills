"""Private verifier diagnostics remain bounded and absent from the published score."""

import io
import json
from contextlib import nullcontext, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from benchmarks.research_review import frontier, report


class FrontierDiagnosticsTests(unittest.TestCase):
    def test_preserves_first_metric_before_long_pass_list_and_skips_captured_output(
        self,
    ):
        raw = """===== FAILURES =====
_____ test_metric _____
>   assert not failures
E   AssertionError:
E     observed 0.158, threshold 0.150
----- Captured stdout call -----
E   private stdout must not be selected
===== PASSES =====
"""
        raw += "PASSED unrelated_scenario\n" * 1000
        self.assertNotIn("0.158", raw[-2200:])
        self.assertEqual(
            frontier._pytest_failures(raw),
            [
                {
                    "test": "test_metric",
                    "assertions": [
                        "AssertionError:",
                        "observed 0.158, threshold 0.150",
                    ],
                }
            ],
        )
        self.assertEqual(
            frontier._pytest_failures("E   extraneous\n===== PASSES ====="), []
        )

    def test_many_large_failures_are_bounded_by_count_and_bytes(self):
        case = "____ test_" + "x" * 900 + " ____\n" + ("E   " + "é" * 800 + "\n") * 12
        failures = frontier._pytest_failures("===== FAILURES =====\n" + case * 10)
        self.assertEqual(len(failures), 4)
        for f in failures:
            self.assertLessEqual(len(f["test"].encode()), 160)
            self.assertEqual(len(f["assertions"]), 6)
            self.assertTrue(all(len(line.encode()) <= 384 for line in f["assertions"]))

    def test_blackbox_reader_returns_only_finite_aggregate_scalars(self):
        raw = json.dumps(
            {
                "score_diff": 0.775715,
                "pass_score_diff": 0.8,
                "num_problems": 24,
                "invalid_submission": False,
                "agent_score": "private string",
                "per_problem_results": [{"hidden": "private instance"}],
            }
        )
        stream = io.StringIO()
        with (
            patch("sys.argv", ["reader", *frontier._BLACKBOX_FIELDS]),
            patch.object(Path, "is_file", return_value=True),
            patch.object(Path, "is_symlink", return_value=False),
            patch.object(Path, "stat", return_value=SimpleNamespace(st_size=len(raw))),
            patch.object(Path, "read_bytes", return_value=raw.encode()),
            redirect_stdout(stream),
        ):
            exec(frontier._BLACKBOX_READER, {})

        def execute(*args, **kwargs):
            return SimpleNamespace(stdout=stream.getvalue(), returncode=0)

        self.assertEqual(
            frontier._blackbox_metrics(execute),
            {
                "score_diff": 0.775715,
                "pass_score_diff": 0.8,
                "num_problems": 24,
                "invalid_submission": False,
            },
        )
        self.assertNotIn("private", stream.getvalue())
        self.assertEqual(
            frontier._blackbox_metrics(
                lambda *a, **kw: SimpleNamespace(stdout="broken", returncode=1)
            ),
            {},
        )

    def test_grader_saves_diagnostics_without_changing_official_reward(self):
        case = {
            "id": "noisy-blackbox-optimization",
            "config": {"artifacts": [], "verifier": {"timeout_sec": 5}},
        }

        def execute(target, *args, **kwargs):
            if args[0] == "bash":
                output = "===== FAILURES =====\n___ test_metric ___\nE   AssertionError: margin 0.77\n"
            elif args == ("cat", "/logs/verifier/reward.txt"):
                output = "0.5"
            elif args[0] == "python3":
                output = (
                    '{"score_diff":0.77,"pass_score_diff":0.8,"unrelated":"hidden"}'
                )
            else:
                output = ""
            return SimpleNamespace(stdout=output, stderr="", returncode=0)

        with (
            patch.object(
                frontier, "temporary_container", return_value=nullcontext("verifier")
            ),
            patch.object(frontier, "_root_exec", side_effect=execute),
        ):
            result = frontier._evaluate(case, "participant")
        self.assertEqual(result["status"], "graded")
        self.assertEqual(result["reward"], 0.5)
        self.assertFalse(result["correct"])
        self.assertEqual(
            result["private_scientific_metrics"],
            {"score_diff": 0.77, "pass_score_diff": 0.8},
        )
        self.assertEqual(
            result["private_pytest_failures"][0]["assertions"],
            ["AssertionError: margin 0.77"],
        )

    def test_public_export_omits_private_fields(self):
        score = {
            "status": "graded",
            "correct": False,
            "reward": 0,
            "private_scientific_metrics": {"score_diff": 0.775715},
            "private_pytest_failures": [
                {"test": "private_test_name", "assertions": ["private expected values"]}
            ],
        }
        public = report.public_row(
            {"arm": "draft", "status": "submitted", "score": score}, None, None
        )
        self.assertFalse(public["correct"])
        self.assertNotIn("private", json.dumps(public))
        self.assertNotIn("0.775715", json.dumps(public))
