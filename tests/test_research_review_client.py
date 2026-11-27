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

    def test_codex_feature_notice_is_informational(self):
        warning = {
            "type": "item.completed",
            "item": {
                "type": "error",
                "message": "Under-development features enabled: skip_host_skill_discovery. To suppress this warning, set the config.",
            },
        }
        events = [{"type": "turn.started"}, warning, {"type": "turn.completed"}]
        self.assertEqual(self.partial(events)[0], "submitted")

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


class DockerContextTests(unittest.TestCase):
    def test_clis_scope_explicit_context_to_scientific_tool(self):
        from unittest.mock import patch
        import os
        import tomllib

        for context in (None, "alternate"):
            for model in ("terra", "sonnet"):
                for tool in ("shell", "python"):
                    with (
                        self.subTest(model=model, context=context, tool=tool),
                        patch.dict(os.environ, clear=False),
                        patch.object(os, "execve") as launch,
                    ):
                        os.environ.pop("DOCKER_CONTEXT", None)
                        os.environ["DOCKER_HOST"] = "unforwarded"
                        if context:
                            os.environ["DOCKER_CONTEXT"] = context
                        client._launch(model, tool, "workspace", "receipts", "1")
                        _, cmd, cli_env = launch.call_args.args
                        self.assertNotIn("DOCKER_HOST", cli_env)
                        self.assertNotIn("DOCKER_CONTEXT", cli_env)
                        if model == "terra":
                            values = [
                                x.removeprefix("mcp_servers.ledger.")
                                for x in cmd
                                if x.startswith("mcp_servers.ledger.")
                            ]
                            server = tomllib.loads("\n".join(values))
                        else:
                            server = json.loads(cmd[cmd.index("--mcp-config") + 1])[
                                "mcpServers"
                            ]["ledger"]
                        expected = (
                            {"DOCKER_CONTEXT": "alternate"}
                            if context and tool == "shell"
                            else {}
                        )
                        self.assertEqual(server.get("env", {}), expected)

    def test_explicit_context_rejects_remote_docker_before_container_inspection(self):
        import os
        from unittest.mock import patch
        from benchmarks.research_review import container_tool

        with (
            patch.dict(os.environ, {"DOCKER_CONTEXT": "remote"}),
            patch.object(
                container_tool.subprocess,
                "check_output",
                return_value="tcp://example.invalid:2376",
            ) as inspect,
        ):
            with self.assertRaisesRegex(ValueError, "local Docker socket"):
                container_tool.validate_container("a" * 64)
            self.assertEqual(inspect.call_count, 1)
