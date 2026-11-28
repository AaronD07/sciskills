"""Regressions for the frozen scientific repair comparison."""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from benchmarks.research_review import container_tool, repair_trial, study


class RepairTrialTests(unittest.TestCase):
    def test_two_models_on_one_task_count_once_and_regressions_reduce_net(self):
        protocol = study.read(repair_trial.PROTOCOL)
        archive = {
            "protocol_sha256": study.digest(repair_trial.PROTOCOL.read_text()),
            "skill_sha256": protocol["skill_sha256"],
            "observations": [],
        }
        for task in protocol["tasks"]:
            for model in protocol["models"]:
                archive["observations"].append(
                    {
                        "task": task,
                        "model": model,
                        "arms": {
                            a: {
                                "outcome": "graded",
                                "correct": False,
                                "reward": 0,
                                "draft_sha256": study.digest(task + model),
                            }
                            for a in repair_trial.ARMS
                        },
                    }
                )
        rows = archive["observations"]

        def passes(i, *arms):
            for arm in arms:
                rows[i]["arms"][arm].update(correct=True, reward=1)

        passes(0, "repair")
        passes(1, "repair")
        self.assertEqual(repair_trial.summarize(archive, protocol)["target"], "missed")
        passes(2, "repair")
        passes(3, "draft", "ordinary")
        result = repair_trial.summarize(archive, protocol)
        self.assertEqual(
            (result["target"], result["net"], result["distinct"]), ("met", 2, 2)
        )
        self.assertEqual(result["ordinary_only"], result["broken_drafts"])
        rows[0]["arms"]["ordinary"]["draft_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "fingerprints"):
            repair_trial.summarize(archive, protocol)
        rows[0]["arms"]["ordinary"]["draft_sha256"] = rows[0]["arms"]["draft"][
            "draft_sha256"
        ]
        rows[-1]["arms"]["draft"] = {
            "outcome": "ungraded",
            "reason": "verifier_timeout",
        }
        rows[0]["arms"]["ordinary"]["pytest_outcomes"] = {"passed": 4, "failed": 5}
        self.assertEqual(repair_trial.summarize(archive, protocol)["target"], "pending")
        rendered = repair_trial.render(archive)
        self.assertIn("4 passed", rendered)
        self.assertIn("verifier timeout", rendered)
        with self.assertRaises(ValueError):
            repair_trial.summarize(
                {**archive, "observations": [*rows[:-1], rows[0]]}, protocol
            )

    def test_unresolved_attempt_never_resamples_after_supervisor_loss(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = (root, "frontier", "holdout", {"id": "case"}, "terra", "draft", {})
            with (
                patch.object(study, "module"),
                patch.object(
                    study,
                    "grade_and_run",
                    side_effect=RuntimeError("supervisor exited"),
                ) as launch,
            ):
                with self.assertRaisesRegex(RuntimeError, "supervisor exited"):
                    study.run_one(args)
                with self.assertRaisesRegex(
                    RuntimeError, "Unresolved original attempt"
                ):
                    study.run_one(args)
                self.assertEqual(launch.call_count, 1)

    def test_known_prelaunch_error_retries_without_resampling_a_model(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = (
                root,
                "frontier",
                "holdout",
                {"id": "case", "prompt": "example"},
                "terra",
                "draft",
                {},
            )
            with (
                patch.object(study, "module"),
                patch.object(
                    study,
                    "participant_engine",
                    side_effect=RuntimeError("preflight failed"),
                ) as check,
            ):
                for _ in range(2):
                    with self.assertRaisesRegex(RuntimeError, "preflight failed"):
                        study.run_one(args)
                self.assertEqual(check.call_count, 2)

    def test_recovering_a_legacy_session_never_issues_prelaunch_proof(self):
        with TemporaryDirectory() as tmp:
            scratch = Path(tmp) / "example.terra.draft-123"
            scratch.mkdir()
            (scratch / "stdout").write_text("original session")
            with (
                patch.object(study, "module"),
                patch.object(
                    study, "participant_engine", side_effect=RuntimeError("lost engine")
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "lost engine"):
                    study.grade_and_run(
                        Path(tmp),
                        "frontier",
                        "holdout",
                        {"id": "example", "prompt": "task"},
                        "terra",
                        "draft",
                        {},
                        scratch,
                    )
            self.assertFalse(
                scratch.with_suffix(scratch.suffix + ".unstarted").exists()
            )

    def test_full_assignment_rejects_invalid_receipts(self):
        protocol = {"skill_sha256": "frozen"}
        task = "example"

        def path(root, arm):
            return study.row_path(
                root, "frontier", "holdout", {"id": task}, "terra", arm
            )

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            study.save(
                root / "frontier" / "execution-contexts" / "example.json",
                {"context": "participant", "engine": "engine"},
            )
            study.save(
                root / "frontier-controls" / "example.json",
                {
                    "task": task,
                    "phase": "holdout",
                    "participant_context": "participant",
                    "participant_engine": "engine",
                    "verifier_context": "verifier",
                    "verifier_engine": "second",
                    "ready": True,
                    "positive": {"correct": True, "reward": 1},
                    "negative": {"correct": False},
                },
            )
            draft = {
                "track": "frontier",
                "phase": "holdout",
                "task": task,
                "model": "terra",
                "arm": "draft",
                "status": "submitted",
                "participant_context": "participant",
                "participant_engine": "engine",
                "image": "sha256:" + "a" * 64,
                "score": {"status": "graded", "correct": False, "reward": 0},
                "session": {
                    "model": "gpt-6.1-terra",
                    "reply": "draft",
                    "calls": [],
                    "subscription": {
                        "auth": {
                            "claude_api_provider": "firstParty",
                            "claude_extra_usage": False,
                            "codex": "ChatGPT",
                            "codex_included_usage_available": True,
                        }
                    },
                },
            }
            study.save(path(root, "draft"), draft)
            history = {
                "PRIOR_WORK.json": study.digest(study.encode([])),
                "PRIOR_REPLY.txt": study.digest("draft"),
            }
            review = {
                **draft,
                "parent_scheme": "participant-v1",
                "parent": study.draft_identity(draft),
                "session": {**draft["session"], "review_context_sha256": history},
                "score": {"status": "graded", "correct": True, "reward": 1},
            }
            for arm in ("ordinary", "repair"):
                study.save(
                    path(root, arm),
                    {**review, "arm": arm, "review_skill_sha256": "frozen"},
                )

            def result():
                return repair_trial.assignment(root, task, "terra", protocol)

            self.assertEqual(
                [result()[arm]["correct"] for arm in repair_trial.ARMS],
                [False, True, True],
            )
            original = study.read(path(root, "repair"))
            for changes, expected in [
                ({"participant_engine": "different"}, "unverified_engine"),
                ({"review_skill_sha256": "different"}, "unverified_skill"),
                ({"parent": "other draft"}, "lineage_error"),
                (
                    {"session": {**review["session"], "review_context_sha256": {}}},
                    "unverified_review_history",
                ),
                (
                    {"session": {**review["session"], "subscription": {}}},
                    "unverified_subscription",
                ),
                (
                    {"session": {**review["session"], "reported_model": "different"}},
                    "unverified_model",
                ),
                (
                    {
                        "session": {
                            **review["session"],
                            "client_deadline_reached": True,
                            "cutoff_image": "other",
                        }
                    },
                    "unverified_deadline",
                ),
                ({"score": {"correct": True, "reward": 0.98}}, "unverified_reward"),
                ({"image": None}, "unverified_snapshot"),
            ]:
                with self.subTest(outcome=expected):
                    study.save(path(root, "repair"), {**original, **changes})
                    self.assertEqual(result()["repair"]["outcome"], expected)

    def test_one_unavailable_task_does_not_starve_others(self):
        protocol = {"tasks": {"unavailable": 1, "ready": 2}, "models": ["terra"]}
        calls = []
        with (
            TemporaryDirectory() as tmp,
            (
                patch.object(
                    repair_trial,
                    "validate_protocol",
                    return_value=(protocol, "text", {"ready": {"id": "ready"}}),
                )
            ),
            patch.object(
                repair_trial.dispatch,
                "reserve_context",
                side_effect=[ValueError("no controls"), {"context": "ctx"}],
            ),
            patch.object(study, "run_one", side_effect=lambda job: calls.append(job)),
            patch.object(
                repair_trial,
                "assignment",
                return_value={a: {"correct": False} for a in repair_trial.ARMS},
            ),
            redirect_stdout(io.StringIO()),
        ):
            blocked = repair_trial.run(Path(tmp), list(protocol["tasks"]), ["terra"])
        self.assertEqual(len(blocked), 1)
        self.assertEqual({job[5] for job in calls}, set(repair_trial.ARMS))

    def test_tool_respects_remaining_session_budget(self):
        msg = {
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "shell",
                "arguments": {"command": "true", "timeout_seconds": 120},
            },
        }
        with (
            TemporaryDirectory() as tmp,
            patch.object(
                container_tool, "validate_container", return_value="/workspace"
            ),
            patch.object(container_tool.sys, "stdin", [json.dumps(msg)] * 2),
            patch.object(container_tool.time, "monotonic", side_effect=[99.1, 102.0]),
            patch.object(container_tool, "shell", return_value=(0, "ok")) as shell,
            redirect_stdout(io.StringIO()),
        ):
            out = Path(tmp) / "calls"
            container_tool.serve("container", out, 120, 102.0)
            self.assertEqual(
                [json.loads(line)["status"] for line in out.read_text().splitlines()],
                [0, 124],
            )
            shell.assert_called_once_with("container", "true", 2)

    def test_cutoff_commit_is_taken_while_container_is_paused(self):
        calls = []

        def run(args, **kwargs):
            calls.append(args[1])

        def commit(args, **kwargs):
            calls.append(args[1])
            return "sha256:" + "1" * 64

        with (
            patch.object(container_tool.subprocess, "run", side_effect=run),
            patch.object(container_tool.subprocess, "check_output", side_effect=commit),
        ):
            self.assertEqual(
                container_tool.freeze_snapshot(
                    "cid", lambda: calls.append("stop_client")
                ),
                "sha256:" + "1" * 64,
            )
        self.assertEqual(calls, ["pause", "stop_client", "commit", "unpause"])
