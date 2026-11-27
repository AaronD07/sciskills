"""The frontier screen requires a recurrent, witnessed scientific error in both models."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks.research_review import dispatch, frontier, study


class FrontierGate(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.out = Path(tmp.name)
        self.tasks = [{"id": f"task-{i}"} for i in range(12)]
        patcher = patch.object(study, "cases", return_value=self.tasks)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.audit = {}
        for model in study.PRIMARY:
            self.audit[model] = {}
            for index, case in enumerate(self.tasks):
                study.save(
                    study.row_path(self.out, "frontier", "dev", case, model, "draft"),
                    {"status": "submitted", "score": {"correct": index >= 5}},
                )
                self.audit[model][case["id"]] = {
                    "class": "numerical",
                    "pattern": "inconsistent units at input"
                    if index < 2
                    else f"cause-{index}",
                    "evidence": "Independent comparison changes a downstream quantity.",
                }

    def qualifies(self):
        study.save(self.out / "frontier" / "development-audit.json", self.audit)
        return study.gate(self.out, "frontier")

    def test_repeat_required_for_each_model(self):
        self.assertTrue(self.qualifies())
        self.audit["sonnet"]["task-0"]["pattern"] = "different mechanism"
        self.assertFalse(self.qualifies())

    def test_verified_failure_counts_even_when_its_cause_is_unknown(self):
        for model in study.PRIMARY:
            self.audit[model]["task-4"]["pattern"] = None
        self.assertTrue(self.qualifies())
        self.audit["terra"]["task-4"]["evidence"] = None
        self.assertFalse(self.qualifies())

    def test_review_identity_tracks_work_instead_of_its_grade(self):
        row = {
            "track": "frontier",
            "task": "task-0",
            "model": "terra",
            "image": "snapshot",
            "session": {"calls": [], "reply": "done"},
            "score": {"correct": True},
        }
        before = study.draft_identity(row)
        row["score"]["correct"] = False
        self.assertEqual(study.draft_identity(row), before)
        row["image"] = "changed"
        self.assertNotEqual(study.draft_identity(row), before)

    def test_class_or_missing_measurement_cannot_qualify(self):
        for value in self.audit["terra"].values():
            value["pattern"] = "numerical"
        self.assertFalse(self.qualifies())
        study.save(
            study.row_path(
                self.out, "frontier", "dev", self.tasks[0], "sonnet", "draft"
            ),
            {"status": "submitted", "score": {"correct": None}},
        )
        self.assertFalse(self.qualifies())


class ContextPlacement(unittest.TestCase):
    @patch.object(
        frontier,
        "_engine_id",
        side_effect=lambda ctx: {"left": "one", "right": "two"}[ctx],
    )
    def test_verified_engine_affinity(self, _engine):
        base = {
            "task": "science",
            "commit": frontier.MANIFEST["commit"],
            "ready": True,
            "negative": {"correct": False},
            "positive": {"correct": True, "reward": 1},
            "verifier_context": "left",
            "verifier_engine": "one",
            "participant_context": "left",
            "participant_engine": "one",
        }
        second = {**base, "participant_context": "right", "participant_engine": "two"}
        selected = dispatch.choose_context([base, second], None, "science")
        self.assertEqual(
            dispatch.choose_context([second, base], selected, "science"), selected
        )
        with self.assertRaises(RuntimeError):
            dispatch.choose_context(
                [base, second], {**selected, "engine": "changed"}, "science"
            )
        with self.assertRaises(ValueError):
            dispatch.choose_context(
                [{**base, "positive": {"correct": False}}], None, "science"
            )
