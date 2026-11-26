"""Prepare and grade two scientific data-analysis tasks from DS-1000."""

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.request

REVISION = "cddd24520f374c6cdf3497adf058467394f3cf0b"
DATA_URL = f"https://raw.githubusercontent.com/xlang-ai/DS-1000/{REVISION}/data/ds1000.jsonl.gz"
SHA256 = "ecc827ac1a9d295cd0acf8f765b4c80592d0d749d18871e33030c7dd06d5a10c"
TASK_IDS = (166, 352)
PACKAGES = {"numpy": "1.26.4", "pandas": "1.5.3", "scipy": "1.12.0"}


def load_task(task_id):
    """Keep the complete upstream artifact in the evaluator's cache."""
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    cache = cache / "sciskills" / f"ds1000-{REVISION}.jsonl.gz"
    if cache.exists():
        data = cache.read_bytes()
    else:
        with urllib.request.urlopen(DATA_URL, timeout=30) as response:
            data = response.read()
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise ValueError(f"DS-1000 checksum mismatch. Remove {cache} and retry.")
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=cache.parent, delete=False) as download:
            download.write(data)
        os.replace(download.name, cache)
    for line in gzip.decompress(data).splitlines():
        record = json.loads(line)
        if record["metadata"]["problem_id"] == task_id:
            return record
    raise ValueError(f"Upstream data lacks problem {task_id}")


def prepare(task, workspace):
    workspace.mkdir(parents=True, exist_ok=True)
    if any(workspace.iterdir()):
        raise ValueError("Choose an empty workspace to avoid overwriting a solution.")
    instruction = "Write your Python completion in solution.py. The evaluator supplies the inputs shown below."
    (workspace / "TASK.md").write_text(instruction + "\n\n" + task["prompt"], encoding="utf-8")
    (workspace / "solution.py").write_text("", encoding="utf-8")


def require_environment():
    from importlib.metadata import version

    if sys.version_info[:2] != (3, 10) or any(version(pkg) != pin for pkg, pin in PACKAGES.items()):
        raise RuntimeError("Use Python 3.10 and benchmarks/external/requirements.txt for scoring.")
    # Fail the command if the environment cannot load the libraries used by the evaluator.
    import numpy
    import pandas
    import scipy.stats


def score(task, solution):
    program = task["code_context"] + f"\ntest_execution({solution!r})\n"
    if "test_string(" in task["code_context"]:
        program += f"test_string({solution!r})\n"
    # A successful early exit from a completion must not count as a passed test.
    program += "\nprint('DS1000_TESTS_COMPLETED')\n"
    with tempfile.TemporaryDirectory() as workdir:
        try:
            with tempfile.TemporaryFile() as output:
                run = subprocess.run(
                    [sys.executable, "-I", "-c", program], cwd=workdir, timeout=120,
                    stdout=output, stderr=subprocess.DEVNULL,
                )
                marker = b"DS1000_TESTS_COMPLETED\n"
                output.seek(max(0, output.tell() - len(marker)))
                passed = run.returncode == 0 and output.read() == marker
        except subprocess.TimeoutExpired:
            passed = False
    return {"task_id": task["metadata"]["problem_id"], "passed": passed, "score": int(passed), "total": 1}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    for name in ("prepare", "score"):
        action = actions.add_parser(name)
        action.add_argument("task_id", type=int, choices=TASK_IDS)
        action.add_argument("workspace", type=Path)
    actions.add_parser("self-test", help="Run upstream reference and empty completions.")
    args = parser.parse_args()
    if args.action == "self-test":
        require_environment()
        for task_id in TASK_IDS:
            task = load_task(task_id)
            reference = score(task, task["reference_code"])
            empty = score(task, "")
            print(json.dumps({"task_id": task_id, "reference": reference, "empty": empty}))
            if not reference["passed"] or empty["passed"]:
                return 1
        return 0
    task = load_task(args.task_id)
    if args.action == "prepare":
        prepare(task, args.workspace)
    else:
        require_environment()
        solution = (args.workspace / "solution.py").read_text(encoding="utf-8")
        print(json.dumps(score(task, solution)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
