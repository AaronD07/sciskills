import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_repo as checker


class CheckerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_all_four_rules_have_evidence_and_actions(self):
        self.write("requirements.txt", "# dependencies\nnumpy>=1\n")
        self.write("package-lock.json", "{}")
        self.write("test_experiment.py", "")
        self.write("README.md", "Run `python missing.py`.")
        self.write("experiment.py", "from numpy.random import default_rng as rng\nsamples = rng(None)\n")
        report = checker.inspect(self.root)
        locations = {f["rule"]: f["location"] for f in report["findings"]}
        self.assertEqual(locations, {"missing-lock": "requirements.txt:2",
                                    "entropy-seeded-rng": "experiment.py:2",
                                    "undocumented-test-command": "test_experiment.py",
                                    "missing-script": "README.md:1"})
        for item in report["findings"]:
            self.assertTrue(all(item[key] for key in ("observation", "action", "limitation")))

    def test_clean_stdlib_and_replayable_seed(self):
        self.write("test_demo.py", "import random\nrandom.Random(42)\n")
        self.write("README.md", "Use `python3 -m unittest discover`.")
        self.assertEqual(checker.inspect(self.root)["findings"], [])

    def test_manifest_scopes_and_node_lock(self):
        self.write("a/package.json", '{"dependencies":{"x":"^1"}}')
        self.write("a/package-lock.json", "{}")
        self.write("b/requirements.txt", "numpy")
        self.write("c/uv.lock", "")
        report = checker.inspect(self.root)
        self.assertEqual([i["location"] for i in report["findings"]], ["b/requirements.txt:1"])
        self.write("b/uv.lock", "")
        self.assertEqual(checker.inspect(self.root)["findings"], [])

    @unittest.skipIf(checker.tomllib is None, "requires a TOML parser")
    def test_pyproject(self):
        self.write("pyproject.toml", '[project]\nname="example"\n')
        self.assertEqual(checker.inspect(self.root)["findings"], [])
        self.write("pyproject.toml", '[project]\ndependencies=["demo>=1"]\n')
        self.assertEqual(checker.inspect(self.root)["findings"][0]["rule"], "missing-lock")

    def test_implicit_and_explicit_directory_and_non_shell_snippets(self):
        self.write("examples/demo.py", "")
        self.write("examples/README.md", """Run this from the root or the example directory.
```sh
python3 examples/demo.py
python3 demo.py
cd fixtures
python3 demo.py
```

```python
python nonexistent.py
```
""")
        findings = checker.inspect(self.root)["findings"]
        self.assertEqual([i["location"] for i in findings], ["examples/README.md:6"])

    def test_damaged_inputs_and_links(self):
        self.write("broken.py", "def (")
        self.write("package.json", "{")
        bad = self.write("README.md", "")
        bad.write_bytes(b"\xff")
        (self.root / "duplicate.py").symlink_to(self.root / "broken.py")
        (self.root / "cycle").symlink_to(self.root, target_is_directory=True)
        report = checker.inspect(self.root)
        self.assertEqual({r["path"] for r in report["incomplete_coverage"]},
                         {"broken.py", "package.json", "README.md"})
        self.assertFalse(report["findings"])

    def test_static_rng_scope(self):
        self.write("demo.py", "from random import Random\nRandom()\nRandom(3)\n"
                   "import random as rn\nrn.seed(a=None)\nrn.seed(42)\nprint('Random()')\n")
        report = checker.inspect(self.root)
        self.assertEqual([f["location"] for f in report["findings"]], ["demo.py:2", "demo.py:5"])

    def test_cli(self):
        self.write("README.md", "Run `python evaluate.py`.")
        command = [sys.executable, str(ROOT / "scripts/check_repo.py"), str(self.root)]
        report = json.loads(subprocess.check_output(command))
        self.assertTrue({"evidence", "root", "limitations", "findings", "incomplete_coverage"} <= report.keys())
        text = subprocess.check_output(command + ["--format", "text"], text=True)
        self.assertIn("README.md:1 [missing-script]", text)


if __name__ == "__main__":
    unittest.main()
