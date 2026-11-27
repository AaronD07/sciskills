"""Regression checks for long scientific review histories and interrupted subscriptions."""

import json
from pathlib import Path
import tempfile
import unittest

from benchmarks.research_review import client


class SessionEvidenceTests(unittest.TestCase):
    def partial(self, events, *, model="terra", error=""):
        with tempfile.TemporaryDirectory() as tmp:
            out, err = (Path(tmp) / n for n in ("stdout", "stderr"))
            out.write_text("".join(json.dumps(e) + "\n" for e in events))
            err.write_text(error)
            return client._result(model, "shell", out, err, -9, deadline=True)

    def test_healthy_partial_codex_and_missing_claude_identity(self):
        call = {
            "type": "item.completed",
            "item": {"type": "mcp_tool_call", "tool": "shell", "server": "ledger"},
        }
        for model_id in (None, client.MODELS["terra"]):
            start = {"type": "turn.started"}
            if model_id:
                start["model"] = model_id
            self.assertEqual(self.partial([start, call]), ("timeout", "", model_id))
        self.assertEqual(self.partial([], model="sonnet"), ("timeout", "", None))
        self.assertEqual(self.partial([])[0], "incomplete_turn")

    def test_deadline_never_hides_observed_protocol_violations(self):
        cases = [
            ({"type": "model/rerouted"}, "model_identity_mismatch"),
            ({"type": "turn.started", "model": "other"}, "model_identity_mismatch"),
            (
                {"type": "item.started", "item": {"type": "command_execution"}},
                "unexpected_tool",
            ),
            (
                {
                    "type": "item.completed",
                    "item": {
                        "type": "mcp_tool_call",
                        "server": "ledger",
                        "tool": "shell",
                        "error": {"message": "transport closed"},
                    },
                },
                "tool_unavailable",
            ),
            (
                {"type": "turn.failed", "error": {"message": "rate_limit_error"}},
                "quota_exhausted",
            ),
            ({"type": "turn.aborted"}, "cli_error"),
        ]
        for event, status in cases:
            with self.subTest(status=status, event=event):
                self.assertEqual(
                    self.partial([{"type": "turn.started"}, event])[0], status
                )
        self.assertEqual(
            self.partial(
                [{"type": "turn.started"}],
                error="stream disconnected before completion",
            )[0],
            "tool_unavailable",
        )

    def test_incomplete_jsonl_cannot_hide_model_or_tool_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, err = (Path(tmp) / n for n in ("stdout", "stderr"))
            out.write_text('{"type":"turn.started"}\n{"type":"item.')
            err.write_text("")
            self.assertEqual(
                client._result("luna", "shell", out, err, -9, deadline=True)[0],
                "invalid_cli_output",
            )
        self.assertEqual(
            self.partial([{"type": "thread.started"}])[0], "incomplete_turn"
        )

    def test_large_history_is_addressable_outside_prompt(self):
        key = "LONG-HISTORY-SENTINEL"
        files = {
            "TASK.md": "solve task",
            "PRIOR_WORK.json": json.dumps([key * 200000]),
            "PRIOR_REPLY.txt": key,
            "SKILL.md": "check accuracy",
        }
        paths = {
            name: "/tmp/sciskills-review.example123/" + name
            for name in ("PRIOR_WORK.json", "PRIOR_REPLY.txt")
        }
        prompt = client._prompt(files, "review", "shell", paths)
        self.assertIn("solve task", prompt)
        self.assertIn("check accuracy", prompt)
        self.assertNotIn(key, prompt)
        self.assertTrue(all(path in prompt for path in paths.values()))
        self.assertLess(len(prompt), 1000)
