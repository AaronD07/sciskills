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
        archive = {"schema_version": 1, "tracks": {"frontier": design}, "rows": rows}
        self.assertNotIn("all four submissions failed", report.render(archive))
        rows[0]["correct"] = False
        self.assertIn("all four submissions failed", report.render(archive))
