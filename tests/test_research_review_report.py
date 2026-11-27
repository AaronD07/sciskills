"""Privacy, incomplete denominators and same-draft pairing in the public results."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from benchmarks.research_review import everyday, report, study


class ResearchReportTests(unittest.TestCase):
    def test_export_and_render_with_unscored_transfer_and_mismatched_parent(self):
        case = next(
            c for c in everyday.cases("holdout") if c["key"]["value"] is not None
        )
        task = case["id"]
        secret = "private-user@example.invalid"
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = root / "everyday"
            design = {
                "effort": "high",
                "study": "test",
                "tasks": {"dev": {}, "holdout": {task: "hash"}},
                "transfer_ids": [task],
                "primary": ["terra"],
                "transfer": ["opus"],
            }
            study.save(d / "design.json", design)
            study.save(
                d / "interventions.json", {"general": "g", "specialist": {task: "s"}}
            )

            def record(model, arm, correct=None, parent=None, status="submitted"):
                score = (
                    None
                    if correct is None
                    else {
                        "correct": correct,
                        "valid": True,
                        "details": {"value": correct},
                        "notes": secret,
                    }
                )
                return {
                    "track": "everyday",
                    "phase": "holdout",
                    "task": task,
                    "model": model,
                    "arm": arm,
                    "score": score,
                    "status": status,
                    "parent": parent,
                    "path": secret,
                    "session": {
                        "receipt": secret,
                        "reply": secret,
                        "calls": [secret],
                        "deleted": [],
                        "artifacts": {
                            "answer.json": json.dumps(
                                {
                                    "value": case["key"]["value"] if correct else -23,
                                    "state": "complete",
                                    "need": secret,
                                }
                            )
                        },
                    },
                }

            draft = record("terra", "draft", False)
            draft["session"]["termination"] = "task_deadline"
            fingerprint = study.digest(study.encode(draft))
            records = [
                draft,
                record("terra", "ordinary", False, fingerprint),
                record("terra", "general", True, fingerprint),
                record("terra", "specialist", True, "stale"),
                record("opus", "draft", status="quota_exhausted"),
            ]
            for row in records:
                study.save(
                    d / "holdout" / f"{task}.{row['model']}.{row['arm']}.json", row
                )
            output = report.archive_runs(root)
            self.assertNotIn(secret, json.dumps(output))
            self.assertEqual(output, report.archive_runs(root))
            results = report.render(output)
            self.assertTrue(
                next(
                    r
                    for r in output["rows"]
                    if r["model"] == "terra" and r["arm"] == "draft"
                )["task_deadline"]
            )
            self.assertIn(
                "| primary | terra | draft | 0/1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |", results
            )
            self.assertIn("unique repair", results)
            self.assertIn("reported -23", results)
            self.assertIn("ordinary → general | 1 | 0 → 1 | 1 | 0", results)
            self.assertIn("ordinary → specialist | 0 | 0 → 0 | 0 | 0", results)
            self.assertIn(
                "| transfer | opus | draft | 0/0 | 0 | 0 | 0 | 0 | 1 | 0 |", results
            )
            self.assertIn("| transfer | opus | general | 0/0 | 0 | 1 |", results)

    def test_paired_counts_include_invalid_but_exclude_ungraded(self):
        rows = {
            "repaired": {
                "ordinary": {"outcome": "invalid", "correct": False},
                "general": {"correct": True},
            },
            "regressed": {"ordinary": {"correct": True}, "general": {"correct": False}},
            "interrupted": {
                "ordinary": {"correct": False},
                "general": {"outcome": "incomplete"},
            },
        }
        self.assertEqual(
            report.paired(rows, "ordinary", "general"),
            {
                "n": 2,
                "before": 1,
                "after": 1,
                "repairs": ["repaired"],
                "regressions": ["regressed"],
            },
        )

    def test_review_borrows_unchanged_answer_and_honors_deletions(self):
        key = {"value": 42, "unit": "m", "evidence": {}}
        draft = {
            "session": {
                "artifacts": {"answer.json": '{"value":41,"state":"complete"}'},
                "deleted": [],
            }
        }
        review = {"session": {"artifacts": {}, "deleted": []}}
        self.assertEqual(
            report.measurements({"key": key}, review, draft)["observed"], 41
        )
        review["session"]["deleted"] = ["answer.json"]
        self.assertIsNone(report.measurements({"key": key}, review, draft)["observed"])


class ControlArchiveTests(unittest.TestCase):
    def test_control_summary_omits_logs_and_separates_unattempted(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            design = {
                "study": "test",
                "effort": "high",
                "tasks": {"dev": {"a": "h", "b": "h", "c": "h"}, "holdout": {"d": "h"}},
                "transfer_ids": [],
                "primary": [],
                "transfer": [],
            }
            study.save(root / "frontier" / "design.json", design)
            study.save(
                root / "frontier-controls" / "a.json",
                {
                    "ready": True,
                    "negative": {"correct": False},
                    "positive": {"correct": True},
                },
            )
            study.save(
                root / "frontier-controls" / "c.json",
                {"ready": False, "error": "account@private.invalid"},
            )
            output = report.archive_runs(root)
            self.assertNotIn("account@private.invalid", json.dumps(output))
            self.assertEqual(
                output["tracks"]["frontier"]["controls"]["a"]["positive_correct"], True
            )
            self.assertIn(
                "control counts are 1 ready, 1 failed and 1 without a receipt.",
                report.render(output),
            )


class FourArmSummaryTests(unittest.TestCase):
    def test_three_review_failures_do_not_imply_failed_draft(self):
        design = {
            "sealed": True,
            "tasks": {"dev": {}, "holdout": {"task": "digest"}},
            "primary": ["terra"],
            "transfer": [],
            "transfer_ids": [],
        }
        rows = [
            {
                "track": "frontier",
                "phase": "holdout",
                "model": "terra",
                "task": "task",
                "arm": arm,
                "outcome": "graded",
                "correct": arm == "draft",
                "reward": float(arm == "draft"),
            }
            for arm in report.ARMS
        ]
        participant = {"context": "context-one", "engine": "engine-one"}
        design["controls"] = {
            "task": {
                "ready": True,
                "contexts": [
                    {
                        "participant": participant,
                        "verifier": {},
                        "ready": True,
                        "negative_correct": False,
                        "positive_correct": True,
                    }
                ],
                "used_contexts": [participant],
            }
        }
        for row in rows:
            row["participant"] = participant
        archive = {"schema_version": 1, "tracks": {"frontier": design}, "rows": rows}
        self.assertNotIn("all four submissions failed", report.render(archive))
        rows[0]["correct"] = False
        self.assertIn("all four submissions failed", report.render(archive))


class MultiEngineReportTests(unittest.TestCase):
    def test_scoped_success_qualifies_its_engine_only(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            design = {
                "study": "test",
                "effort": "high",
                "tasks": {"dev": {"dev-case": "h"}, "holdout": {"case": "h"}},
                "transfer_ids": [],
                "primary": ["terra", "sonnet"],
                "transfer": [],
            }
            study.save(root / "frontier" / "design.json", design)
            desktop = {
                "participant_context": "private-desktop-label",
                "participant_engine": "private-engine-a",
                "verifier_context": "private-grader-label",
                "verifier_engine": "private-engine-v",
            }
            alternate = {
                **desktop,
                "participant_context": "private-colima-label",
                "participant_engine": "private-engine-b",
            }
            for task in ("dev-case", "case"):
                failed = {
                    **desktop,
                    "task": task,
                    "ready": False,
                    "negative": {"correct": False},
                    "error": "/Users/private-developer",
                }
                qualified = {
                    **alternate,
                    "task": task,
                    "ready": True,
                    "negative": {"correct": False},
                    "positive": {"correct": True, "reward": 1},
                }
                study.save(root / "frontier-controls" / (task + ".json"), failed)
                study.save(
                    root
                    / "frontier-controls"
                    / "contexts"
                    / "opaque-local-path"
                    / (task + ".json"),
                    qualified,
                )
            for model, participant in [
                ("terra", alternate),
                ("sonnet", {**alternate, "participant_engine": "private-recreated-id"}),
            ]:
                row = {
                    "track": "frontier",
                    "phase": "holdout",
                    "model": model,
                    "task": "case",
                    "arm": "draft",
                    "score": {"correct": True, "reward": 1},
                    "status": "submitted",
                    "session": {},
                    **participant,
                }
                study.save(
                    root / "frontier" / "holdout" / f"case.{model}.draft.json", row
                )
            result = report.archive_runs(root)
            controls = result["tracks"]["frontier"]["controls"]
            self.assertTrue(controls["dev-case"]["ready"])
            self.assertTrue(controls["case"]["any_context_ready"])
            self.assertFalse(controls["case"]["ready"])
            self.assertEqual(len(controls["case"]["contexts"]), 2)
            rows = {r["model"]: r for r in result["rows"]}
            self.assertTrue(rows["terra"]["correct"])
            self.assertEqual(rows["sonnet"]["outcome"], "infrastructure")
            self.assertNotIn("correct", rows["sonnet"])
            rendered = report.render(result)
            for private_text in ("private-", "/Users/", "opaque-local-path"):
                self.assertNotIn(private_text, json.dumps(result) + rendered)
            self.assertIn("missing | yes", rendered)
            # A later scoped failure on the same participant supersedes its old main receipt.
            passage = (
                root
                / "frontier-controls"
                / "contexts"
                / "opaque-local-path"
                / "case.json"
            )
            study.save(root / "frontier-controls" / "case.json", study.read(passage))
            study.save(passage, {**study.read(passage), "ready": False})
            refreshed = report.archive_runs(root)
            self.assertFalse(
                refreshed["tracks"]["frontier"]["controls"]["case"]["any_context_ready"]
            )

    def test_legacy_or_partial_context_can_only_support_development(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            design = {
                "study": "test",
                "effort": "high",
                "primary": ["terra"],
                "transfer": [],
                "transfer_ids": [],
                "tasks": {"dev": {"old": "h"}, "holdout": {"case": "h"}},
            }
            study.save(root / "frontier" / "design.json", design)
            matching = {"participant_context": "ctx", "participant_engine": "engine"}
            for task in ("old", "case"):
                study.save(
                    root / "frontier-controls" / (task + ".json"),
                    {
                        **matching,
                        "ready": True,
                        "negative": {"correct": False},
                        "positive": {"correct": True, "reward": 1},
                    },
                )
            for identity in (
                {},
                {"participant_context": "ctx"},
                {"participant_engine": "engine"},
            ):
                with self.subTest(identity=identity):
                    for task, phase in (("old", "dev"), ("case", "holdout")):
                        row = {
                            **identity,
                            "track": "frontier",
                            "task": task,
                            "phase": phase,
                            "arm": "draft",
                            "model": "terra",
                            "status": "submitted",
                            "score": {"correct": True, "reward": 1},
                            "session": {},
                        }
                        study.save(
                            root / "frontier" / phase / f"{task}.terra.draft.json", row
                        )
                    result = report.archive_runs(root)
                    dev, held = result["rows"]
                    self.assertTrue(dev["correct"])
                    self.assertFalse(held["participant_control_verified"])
                    self.assertNotIn("correct", held)
                    self.assertEqual(held["outcome"], "infrastructure")
                    self.assertFalse(
                        result["tracks"]["frontier"]["controls"]["case"]["ready"]
                    )
                    held.update(
                        correct=True,
                        outcome="graded",
                        participant_control_verified=True,
                    )
                    self.assertIn(
                        "| primary | terra | draft | 0/0 | 0 | 0 | 0 | 0 | 1 |",
                        report.render(result),
                    )
