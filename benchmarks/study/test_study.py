"""Regression checks for session recovery, input integrity and submission errors."""
from argparse import Namespace
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import run
import score


class StudyTests(unittest.TestCase):
    def test_interrupted_directory_preserves_spent_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / "interrupted"
            dest.mkdir()
            log = dest / "stdout"
            log.write_text("partial output")
            row = run.generate(("codex", "claims", 1, "baseline"), "task", dest)
            self.assertEqual(row["status"], "interrupted")
            self.assertEqual(log.read_text(), "partial output")

    def test_unreadable_cli_reply_records_failure(self):
        def invalid(_job, _prompt, dest):
            dest.mkdir()
            raise ValueError("malformed output")

        with tempfile.TemporaryDirectory() as directory, patch.object(run, "_generate", invalid):
            dest = Path(directory) / "malformed"
            row = run.generate(("claude", "subjects", 1, "skill"), "task", dest)
            self.assertEqual(row["status"], "infrastructure_error")
            self.assertEqual(json.loads((dest / "generation.json").read_text()), row)

    def test_changed_prompt_rejected_on_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            args = Namespace(out=Path(directory), workers=1)
            with patch.object(run, "jobs", return_value=[]), patch("subprocess.check_output", return_value="1.0"):
                with patch.object(run, "prompt", return_value="original task"):
                    run.generate_all(args)
                with patch.object(run, "prompt", return_value="changed task"):
                    with self.assertRaisesRegex(ValueError, "different protocols"):
                        run.generate_all(args)

    @unittest.skipUnless(sys.platform == "darwin", "macOS scoring sandbox")
    def test_grader_accounts_for_invalid_python(self):
        job = ("codex", "claims", 1, "baseline")
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            dest = work / run.name(job)
            dest.mkdir()
            source = b"this is (invalid python"
            (dest / "submission.py").write_bytes(source)
            record = dict(status="submitted", elapsed_seconds=2.0, model=run.MODELS["codex"],
                          submission_sha256=run.digest(source))
            (dest / "generation.json").write_text(json.dumps(record))
            row = score.grade(job, work, Path("/unused"), Path("/unused"))
            self.assertEqual((row["passed"], row["total"]), (0, 8))
            self.assertIn("grading_error", row)


if __name__ == "__main__":
    unittest.main()
