"""Exercise the actual calculator sandbox on supported macOS machines."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

TOOL = Path(__file__).resolve().parents[1] / "benchmarks/ledger-replay/python_tool.py"
spec = importlib.util.spec_from_file_location("ledger_python_tool", TOOL)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


@unittest.skipUnless(sys.platform == "darwin", "requires macOS sandbox-exec")
class PythonToolTests(unittest.TestCase):
    def test_staged_reads_writes_and_observed_helper_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory).resolve()
            (work / "asof.py").write_text("def select(): return 7\n")
            run = "import asof, pathlib; pathlib.Path('answer.json').write_text(str(asof.select()))"
            code, _, observed = tool.execute(run, work)
            self.assertEqual(code, 0)
            self.assertEqual((work / "answer.json").read_text(), "7")
            self.assertIn("select", observed)

    def test_network_and_files_outside_workspace(self):
        with tempfile.TemporaryDirectory() as root:
            parent = Path(root).resolve()
            work = parent / "participant"
            work.mkdir()
            hidden = parent / "private.tsv"
            hidden.write_text("hidden")
            for code in (f"print(open({str(hidden)!r}).read())",
                         f"open({str(hidden)!r},'w').write('changed')",
                         "import socket; socket.socket().connect(('127.0.0.1',9))"):
                with self.subTest(code=code):
                    status, log, _ = tool.execute(code, work)
                    self.assertNotEqual(status, 0)
                    self.assertIn("Operation not permitted", log)
            self.assertEqual(hidden.read_text(), "hidden")
