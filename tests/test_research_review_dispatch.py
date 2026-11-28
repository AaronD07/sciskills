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


class PlacementCapacityTests(unittest.TestCase):
    def setUp(self):
        from unittest.mock import patch

        self.gib = 1024**3
        self.receipt = {
            "task": "test",
            "commit": dispatch.frontier.MANIFEST["commit"],
            "participant_context": "desktop",
            "participant_engine": "d",
            "verifier_context": "colima",
            "verifier_engine": "c",
        }
        self.task = {
            "id": "test",
            "config": {
                "environment": {"cpus": 4, "memory_mb": 8192},
                "verifier": {"environment": {"memory_mb": 4096}},
            },
        }
        self.specs = {
            "desktop": ("d", 16, 8217190400),
            "colima": ("c", 4, 24 * self.gib),
        }
        self.start_patch = patch.object(
            dispatch.frontier, "live_control", return_value=True
        )
        self.start_patch.start()
        self.addCleanup(self.start_patch.stop)
        capacity = patch.object(
            dispatch, "_engine_capacity", side_effect=lambda ctx: self.specs[ctx]
        )
        self.probe = capacity.start()
        self.addCleanup(capacity.stop)

    def choose(self, receipts=None, prior=None, cache=None):
        return dispatch.choose_context(
            receipts or [self.receipt], prior, "test", task=self.task, capacities=cache
        )

    def test_binary_units_apply_to_the_participant_and_pinned_placement(self):
        alternative = {
            **self.receipt,
            "participant_context": "colima",
            "participant_engine": "c",
        }
        self.assertEqual(self.choose([self.receipt, alternative])["context"], "colima")
        with self.assertRaises(RuntimeError):
            self.choose(
                [self.receipt, alternative], {"context": "desktop", "engine": "d"}
            )
        self.specs["desktop"] = ("d", 16, 8 * self.gib - 1)
        with self.assertRaises(ValueError):
            self.choose()
        self.specs["desktop"] = ("d", 16, 8 * self.gib)
        self.assertEqual(self.choose()["context"], "desktop")

    def test_each_verifier_override_is_merged_with_the_participant_settings(self):
        self.specs["desktop"] = ("d", 16, 8 * self.gib)
        self.specs["colima"] = ("c", 3, 4 * self.gib)
        with self.assertRaises(ValueError):  # verifier inherits participant's 4 CPUs
            self.choose()
        self.task["config"]["verifier"]["environment"] = {"cpus": 2}
        self.specs["colima"] = ("c", 2, 8 * self.gib - 1)
        with self.assertRaises(ValueError):  # verifier inherits participant's 8192 MiB
            self.choose()
        self.specs["colima"] = ("c", 2, 8 * self.gib)
        self.assertEqual(self.choose()["engine"], "d")

    def test_capacity_cache_is_bound_to_a_certificate_engine_id_and_pass(self):
        self.specs["desktop"] = ("d", 16, 8 * self.gib)
        cache = {}
        self.choose(cache=cache)
        self.choose(cache=cache)
        self.assertEqual(self.probe.call_count, 2)
        updated = {**self.receipt, "participant_engine": "new"}
        with self.assertRaises(ValueError):
            self.choose(
                [updated], cache=cache
            )  # same context name, different engine ID
        self.assertEqual(self.probe.call_count, 3)
        self.specs["desktop"] = ("new", 16, 8 * self.gib)
        self.assertEqual(self.choose([updated])["engine"], "new")
