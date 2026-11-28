"""A saved boolean alone cannot complete a sealed frontier assignment."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from benchmarks.research_review import dispatch, report, study


class DispatchQualificationTests(unittest.TestCase):
    def test_completion_uses_qualified_draft_engine_and_matching_review_lineage(self):
        placement = {"context": "selected", "engine": "first"}
        identity = {"participant_context": "selected", "participant_engine": "first"}
        design = {
            "study": "test",
            "effort": "high",
            "primary": ["terra"],
            "transfer": ["luna"],
            "transfer_ids": [],
            "tasks": {"dev": {}, "holdout": {"task": "digest"}},
        }
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "frontier"
            study.save(out / "design.json", design)
            study.save(
                root / "frontier-controls" / "task.json",
                {
                    "task": "task",
                    **identity,
                    "ready": True,
                    "negative": {"correct": False},
                    "positive": {"correct": True, "reward": 1},
                },
            )
            draft = {
                "track": "frontier",
                "phase": "holdout",
                "model": "terra",
                "task": "task",
                "arm": "draft",
                "status": "submitted",
                "image": "draft-snapshot",
                "score": {"correct": False, "reward": 0},
                "session": {"calls": [], "reply": "example"},
                **identity,
            }

            def write(arm, **changes):
                record = {**draft, "arm": arm}
                if arm != "draft":
                    record.update(
                        parent=study.draft_identity(draft),
                        parent_scheme="participant-v1",
                    )
                study.save(
                    out / "holdout" / f"task.terra.{arm}.json", {**record, **changes}
                )

            def missing(phase="reviews", machine=placement):
                archive = report.archive_runs(root, ("frontier",))
                return list(
                    dispatch.incomplete_assignments(
                        archive, design, [("task", machine)], phase
                    )
                )

            for arm in ("draft", *study.ARMS):
                write(arm)
            self.assertEqual(
                missing(), []
            )  # A valid wrong answer still completes its assignment.
            self.assertEqual(
                missing("holdout", {"context": "selected", "engine": "replaced"}),
                [("task", "terra", "draft")],
            )
            design["transfer_ids"] = ["task"]
            self.assertEqual(missing("holdout"), [("task", "luna", "draft")])
            design["transfer_ids"] = []
            write("general", parent="another draft")
            write("specialist", participant_engine="unqualified")
            self.assertEqual(
                missing(),
                [("task", "terra", "general"), ("task", "terra", "specialist")],
            )
            write("general")
            write("specialist")
            write("draft", participant_context=None)
            self.assertEqual(missing(), [("task", "terra", "draft")])
