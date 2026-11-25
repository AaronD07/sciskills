import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


benchmark = load("benchmark", ROOT / "benchmarks/benchmark.py")
checker = load("checker", ROOT / "scripts/check_repo.py")

# Reference repairs are evaluator self-tests, never participant inputs.
REPAIRS = {
    "kinetics": """import math
def decay(initial, rate_per_second, times_ms):
    if not all(math.isfinite(x) and x >= 0 for x in [initial, rate_per_second, *times_ms]):
        raise ValueError('invalid quantity')
    return [initial * math.exp(-rate_per_second * (t / 1000)) for t in times_ms]
""",
    "assay": """import math
def summarize(values):
    observed = [x for x in values if x is not None]
    if not all(math.isfinite(x) for x in observed):
        raise ValueError('nonfinite measurement')
    return dict(mean=sum(observed)/len(observed) if observed else None,
                observed=len(observed), missing=len(values)-len(observed))
""",
    "prediction": """import math
def evaluate(train, test):
    if not train or not test or not all(math.isfinite(x) for x in [*train, *test]):
        raise ValueError('invalid target')
    prediction = sum(train) / len(train)
    return dict(prediction=prediction, mse=sum((x-prediction)**2 for x in test)/len(test))
""",
}


class BenchmarkTests(unittest.TestCase):
    def test_all_planted_bugs_fail_and_reference_repairs_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            for case in benchmark.CASES:
                with self.subTest(case=case):
                    broken = benchmark.score(case, ROOT / 'benchmarks/tasks' / case / 'analysis.py')
                    self.assertNotIn('error', broken)
                    self.assertLess(broken['passed'], broken['total'])
                    fix = Path(temp) / 'analysis.py'
                    fix.write_text(REPAIRS[case])
                    corrected = benchmark.score(case, fix)
                    self.assertNotIn('error', corrected)
                    self.assertEqual(corrected['passed'], corrected['total'])

    def test_prepare_excludes_answers_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / 'trial'
            benchmark.prepare('assay', dest, 'check-the-numbers')
            self.assertEqual({p.name for p in dest.iterdir()}, {'TASK.md', 'analysis.py', 'SKILL.md'})
            with self.assertRaises(ValueError):
                benchmark.prepare('assay', dest)
            with self.assertRaises(ValueError):
                benchmark.prepare('assay', Path(temp) / 'bad', '../escape')

    def test_crashing_and_hanging_submissions_do_not_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'analysis.py'
            path.write_text('raise RuntimeError("broken import")')
            self.assertEqual(benchmark.score('assay', path)['passed'], 0)
            path.write_text('while True: pass')
            result = benchmark.score('assay', path, timeout=.2)
            self.assertEqual(result['error'], 'timeout')
            self.assertEqual(result['passed'], 0)

    def test_comparison_rejects_nonfinite_and_wrong_shapes(self):
        self.assertFalse(benchmark.same(float('nan'), 1))
        self.assertFalse(benchmark.same([1, 2], [1]))
        self.assertFalse(benchmark.same({'mean': 1, 'extra': 2}, {'mean': 1}))


class CheckerTests(unittest.TestCase):
    def test_evidence_is_syntactic_and_skips_comments_and_symlinks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'README.md').write_text('demo')
            (root / 'experiment.py').write_text('# random.seed(42)\nlabel = "random.seed(42)"\nimport random\nrng = random.Random(42)\n')
            (root / 'outside.py').symlink_to(ROOT / 'examples/pin-the-environment/experiment.py')
            report = checker.inspect(root)
            self.assertEqual(report['evidence']['seed_calls'], ['experiment.py:4'])
            self.assertEqual(report['evidence']['dependency_lock'], [])
            self.assertIn('not run', report['limitations'])
            self.assertNotIn('score', report)


if __name__ == '__main__':
    unittest.main()
