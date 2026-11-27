"""Offline checks for matching review workspaces and bounded, isolated artifacts."""

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest


def load_runner():
    spec = importlib.util.spec_from_file_location(
        "paired_session_runner", Path(__file__).with_name("runner.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = load_runner()


class RunnerTests(unittest.TestCase):
    def test_fork_reconstructs_nested_changes_and_exposes_original_records(self):
        original = {"TASK.md": "task", "data.csv": "value\n3", "extra.csv": "field"}
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            (work / "TASK.md").write_text("task")
            (work / "data.csv").write_text("revised")
            (work / "subdir").mkdir()
            (work / "subdir/note.md").write_text("work")
            (work / "answer.json").write_text('{"sum":3}')
            artifacts, deleted = runner._collect(work, original)
        draft = {
            "calls": [{"code": "print(3)", "status": 0}],
            "artifacts": artifacts,
            "deleted": deleted,
        }
        a, b = (runner.review_files(original, draft) for _ in range(2))
        self.assertEqual(a, b)
        draft["reply"] = "A previous implementation"
        self.assertEqual(
            runner.review_files(original, draft)["PRIOR_REPLY.txt"], draft["reply"]
        )
        self.assertEqual(a["subdir/note.md"], "work")
        self.assertEqual(a["answer.json"], '{"sum":3}')
        self.assertNotIn("extra.csv", a)
        self.assertEqual(a["original_packet/extra.csv"], "field")
        self.assertEqual(a["data.csv"], "revised")
        self.assertEqual(a["original_packet/data.csv"], original["data.csv"])
        self.assertEqual(json.loads(a["PRIOR_WORK.json"]), draft["calls"])
        a["SKILL.md"] = "review"
        self.assertNotIn("SKILL.md", b)

    def test_draft_cannot_inject_control_skill_or_replace_task(self):
        draft = {
            "calls": [],
            "deleted": [],
            "artifacts": {"TASK.md": "changed", "SKILL.md": "leak"},
        }
        reviewed = runner.review_files({"TASK.md": "original"}, draft)
        self.assertEqual(reviewed["TASK.md"], "original")
        self.assertNotIn("SKILL.md", reviewed)

    def test_rejects_path_traversal_links_fifos_and_binary_outputs(self):
        for name in ("", "/tmp/creds", "a/../b", "../b", "./a"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                runner._safe_name(name)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            target = path / "target"
            target.write_text("data")
            for fn in (
                lambda p: p.symlink_to(target),
                lambda p: os.mkfifo(p),
                lambda p: p.write_bytes(bytes([255])),
            ):
                candidate = path / "bad"
                fn(candidate)
                with self.assertRaises(ValueError):
                    runner._collect(path, {})
                candidate.unlink()

    def test_codex_requires_finished_turn_and_only_permitted_tool(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "log"
            path.write_text('{"type":"thread.started"}\n')
            self.assertEqual(runner._client_status("luna", path), "incomplete_turn")
            path.write_text(
                '{"type":"item.completed","item":{"type":"command_execution"}}\n'
                '{"type":"turn.completed"}\n'
            )
            self.assertEqual(runner._client_status("terra", path), "unexpected_tool")
            path.write_text(
                '{"type":"item.completed","item":{"type":"mcp_tool_call","server":"ledger","tool":"python"}}\n'
                '{"type":"turn.completed"}\n'
            )
            self.assertEqual(runner._client_status("terra", path), "submitted")

    def test_provider_keys_are_excluded(self):
        os.environ["SCISKILLS_TEST_SECRET"] = "test"
        try:
            self.assertNotIn("SCISKILLS_TEST_SECRET", runner._environment())
        finally:
            del os.environ["SCISKILLS_TEST_SECRET"]


if __name__ == "__main__":
    unittest.main()
