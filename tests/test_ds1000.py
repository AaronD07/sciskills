"""Offline regression tests for the optional DS-1000 adapter."""

import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from benchmarks.external import ds1000


class ExternalTasksTest(unittest.TestCase):
    def setUp(self):
        self.fresh = tempfile.TemporaryDirectory()
        self.addCleanup(self.fresh.cleanup)
        self.root = Path(self.fresh.name)
        self.task = {
            "metadata": {"problem_id": 166},
            "prompt": "Find the mean.",
            "reference_code": "result = 3",
            "code_context": (
                "def test_execution(solution):\n"
                "    env = {}\n"
                "    exec(solution, env)\n"
                "    assert env['result'] == 3"
            ),
        }

    def test_prepare_excludes_answers_and_preserves_existing_work(self):
        dst = self.root / "workspace"
        ds1000.prepare(self.task, dst)
        prompt = (dst / "TASK.md").read_text()
        self.assertIn("Find the mean.", prompt)
        self.assertNotIn("result = 3", prompt)
        self.assertEqual((dst / "solution.py").read_text(), "")
        (dst / "solution.py").write_text("my work")
        with self.assertRaises(ValueError):
            ds1000.prepare(self.task, dst)
        self.assertEqual((dst / "solution.py").read_text(), "my work")

    def test_distinguishes_correct_incorrect_and_early_exiting_solutions(self):
        for solution, expected in [("result = 3", True), ("result = 5", False), ("raise SystemExit(0)", False)]:
            with self.subTest(solution=solution):
                self.assertEqual(ds1000.score(self.task, solution)["passed"], expected)

    def test_only_reads_verified_offline_cache(self):
        cache = self.root / "sciskills" / f"ds1000-{ds1000.REVISION}.jsonl.gz"
        cache.parent.mkdir()
        data = gzip.compress(json.dumps(self.task).encode())
        cache.write_bytes(data)
        with patch.dict("os.environ", XDG_CACHE_HOME=str(self.root)), patch.object(
            ds1000, "SHA256", hashlib.sha256(data).hexdigest()
        ):
            self.assertEqual(ds1000.load_task(166), self.task)
            cache.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "checksum"):
                ds1000.load_task(166)
