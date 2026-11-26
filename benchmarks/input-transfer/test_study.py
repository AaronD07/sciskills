"""Offline checks for the paired transfer protocol."""

from collections import Counter
import unittest
from unittest.mock import patch

import study
import files


class InputTransferTests(unittest.TestCase):
    def test_every_pair_has_both_conditions(self):
        schedule = list(study.jobs())
        counts = Counter((agent, task, rep) for agent, task, rep, _ in schedule)
        self.assertEqual(len(schedule), 24)
        self.assertEqual(len(set(schedule)), 24)
        self.assertEqual(len(counts), 12)
        self.assertEqual(set(counts.values()), {2})
        self.assertEqual(schedule, list(study.jobs()))

    def test_primary_task_is_identical_in_both_conditions(self):
        supplied = {
            "prompt": "Write a calculation.",
            "reference_code": "hidden-reference",
        }
        with patch.object(study.ds1000, "load_task", return_value=supplied):
            baseline = study.text_for(108, "baseline")
            skill = study.text_for(108, "skill")
        self.assertEqual(
            skill, baseline + "\n\nWorkflow:\n" + study.SKILL.read_text().strip()
        )
        self.assertNotIn("hidden-reference", skill)

    def test_file_workspace_controls(self):
        supplied = {
            "prompt": "Write a calculation.",
            "reference_code": "hidden-reference",
        }
        with patch.object(study.ds1000, "load_task", return_value=supplied):
            baseline = files.material(411, "baseline")
            skill = files.material(411, "skill")
        self.assertEqual(
            baseline, {"TASK.md": "Write a calculation.", "solution.py": ""}
        )
        self.assertEqual(skill, {**baseline, "SKILL.md": study.SKILL.read_text()})
        self.assertNotEqual(files.fingerprint(skill), files.fingerprint(baseline))

    def test_file_cli_audit(self):
        codex = '{"type":"item.completed","item":{"type":"command_execution","command":"cat TASK.md"}}\n{"type":"turn.completed"}'
        ok, tools, commands = files.audit("codex", codex)
        self.assertTrue(ok)
        self.assertEqual(tools, ["command_execution"])
        self.assertEqual(commands, ["cat TASK.md"])
        ok, _, _ = files.audit(
            "claude", '{"type":"result","is_error":false,"modelUsage":{"wrong":{}}}'
        )
        self.assertFalse(ok)

    def test_only_outer_fence_is_removed(self):
        self.assertEqual(
            study.source_from("```python\nresult = 3\n```"), "result = 3\n"
        )
        self.assertEqual(
            study.source_from("prior prose\nresult = 3"), "prior prose\nresult = 3\n"
        )


if __name__ == "__main__":
    unittest.main()
