import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from benchmarks.research_review.spin_replay import replay


class SpinReplayTests(unittest.TestCase):
    def test_recombination_can_reuse_the_original_draft(self):
        problem = {
            "instance_index": 0,
            "N": 5,
            "edges": [
                [0, 1, -1],
                [0, 2, 2],
                [1, 2, 4],
                [1, 4, -5],
                [2, 3, 2],
                [3, 4, -1],
            ],
        }
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            instance = root / "instance.json"
            instance.write_text(json.dumps(problem))
            for name, spins in {
                "draft.txt": "-1 1 -1 -1 1",
                "a.txt": "-1 1 -1 -1 -1",
                "b.txt": "-1 -1 -1 1 -1",
                "c.txt": "-1 1 -1 1 -1",
            }.items():
                (root / name).write_text(spins)
            result = replay(
                instance, root / "draft.txt", [root / f"{s}.txt" for s in "cba"]
            )
        self.assertEqual(result["draft"], 3)
        self.assertEqual(result["best_input"], -5)
        self.assertEqual(result["final"], -13)
        self.assertIn("draft.txt", [step["candidate"] for step in result["steps"]])
