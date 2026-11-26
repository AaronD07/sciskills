import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


CHECK = Path(__file__).resolve().parents[1] / "skills/test-fresh-inputs/check_inputs.py"
spec = importlib.util.spec_from_file_location("check_inputs", CHECK)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class TestCheckInputs(unittest.TestCase):
    def test_literals_unpacking_and_imported_constructors(self):
        source = """import numpy as n
from pandas import DataFrame as frame
bounds: tuple[int, int] = (-1, 2)
a, b = n.ones((3, 3)), 0
df = frame({'site': ['sample']})
unused = [1, 2, 3]
"""
        self.assertEqual(
            checker.find_overwrites(source, {"bounds", "a", "b", "df"}),
            [(3, "bounds"), (4, "a"), (4, "b"), (5, "df")],
        )

    def test_derived_values_conditional_defaults_and_local_variables(self):
        source = """from numpy import asarray
a = asarray(a)
size = a.shape[0]
if a is None:
    a = [0]
def smoke():
    a = [1, 2, 3]
a[:1] = [4]
a, size = size, a
"""
        self.assertEqual(checker.find_overwrites(source, {"a", "size"}), [])

    def test_unknown_or_shadowed_constructors_and_dynamic_arguments(self):
        source = """import numpy as np
a = np.zeros(a.shape)
a = external.array([1])
np = alternate
a = np.array([1])
"""
        self.assertEqual(checker.find_overwrites(source, {"a"}), [])

    def test_local_alias_shadowing_leaves_module_binding_intact(self):
        source = """import numpy as np
def helper():
    np = 1
class Case:
    np = 2
a = np.zeros((2, 2))
"""
        self.assertEqual(checker.find_overwrites(source, {"a"}), [(6, "a")])

    def test_cli_does_not_execute_and_distinguishes_scan_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "solution.py"

            def run(names):
                return subprocess.run(
                    [sys.executable, str(CHECK), str(source), "--inputs", *names],
                    capture_output=True,
                    text=True,
                )

            source.write_text("raise RuntimeError('cannot run this file')\nx = -1\n")
            self.assertEqual(run(["y"]).returncode, 0)
            hit = run(["x"])
            self.assertEqual(hit.returncode, 1)
            self.assertIn("solution.py:2: x", hit.stdout)
            self.assertEqual(run(["not-valid"]).returncode, 2)
            source.write_text("x = (")
            self.assertEqual(run(["x"]).returncode, 2)
            source.unlink()
            self.assertEqual(run(["x"]).returncode, 2)


if __name__ == "__main__":
    unittest.main()
