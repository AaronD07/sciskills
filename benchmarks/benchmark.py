"""Prepare isolated tasks and score submissions. Standard library only."""
import argparse
import contextlib
import importlib.util
import io
import json
import math
import re
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
CASES = ("kinetics", "assay", "prediction")


def checks(case):
    # Independent protocol-derived answers. Never copy this evaluator to a trial.
    if case == "kinetics":
        return [
            ("ordinary_seconds_conversion", "decay", (8, math.log(2), [0, 1000, 2000]), [8, 4, 2]),
            ("unequal_times", "decay", (10, 1, [500, 100, 0]), [10*math.exp(-.5), 10*math.exp(-.1), 10]),
            ("zero_rate", "decay", (3, 0, [0, 1000]), [3, 3]),
            ("empty", "decay", (3, 1, []), []),
            ("negative_time", "decay", (3, 1, [-1]), ValueError),
            ("negative_rate", "decay", (3, -1, [1]), ValueError),
            ("nan_initial", "decay", (float("nan"), 1, [1]), ValueError),
            ("infinite_time", "decay", (3, 1, [float("inf")]), ValueError),
        ]
    if case == "assay":
        return [
            ("zero_is_observed", "summarize", ([0, 2, None, 4],), {"mean": 2, "observed": 3, "missing": 1}),
            ("ordinary", "summarize", ([2, 4, 6],), {"mean": 4, "observed": 3, "missing": 0}),
            ("negative_and_zero", "summarize", ([-2, 0, 2],), {"mean": 0, "observed": 3, "missing": 0}),
            ("all_missing", "summarize", ([None, None],), {"mean": None, "observed": 0, "missing": 2}),
            ("empty", "summarize", ([],), {"mean": None, "observed": 0, "missing": 0}),
            ("nan", "summarize", ([1, float("nan")],), ValueError),
            ("positive_infinity", "summarize", ([float("inf")],), ValueError),
            ("negative_infinity", "summarize", ([float("-inf")],), ValueError),
        ]
    return [
        ("held_out", "evaluate", ([0, 2], [10, 12]), {"prediction": 1, "mse": 101}),
        ("test_shift", "evaluate", ([0, 2], [-2, 0]), {"prediction": 1, "mse": 5}),
        ("constant", "evaluate", ([3, 3], [3]), {"prediction": 3, "mse": 0}),
        ("unequal_lengths", "evaluate", ([2], [1, 3, 5]), {"prediction": 2, "mse": 11/3}),
        ("empty_train", "evaluate", ([], [1]), ValueError),
        ("empty_test", "evaluate", ([1], []), ValueError),
        ("nan_train", "evaluate", ([float("nan")], [1]), ValueError),
        ("infinite_test", "evaluate", ([1], [float("inf")]), ValueError),
    ]


def same(actual, expected):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and actual.keys() == expected.keys() and all(same(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, (list, tuple)) and len(actual) == len(expected) and all(same(a, b) for a, b in zip(actual, expected))
    if expected is None:
        return actual is None
    return isinstance(actual, (int, float)) and not isinstance(actual, bool) and math.isfinite(actual) and math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-12)


def worker(case, submission):
    results = []
    # Quiet normal candidate prints; this is process isolation, not a security sandbox.
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        spec = importlib.util.spec_from_file_location("submission", submission)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for name, function, arguments, expected in checks(case):
            try:
                value = getattr(module, function)(*arguments)
                passed = expected is not ValueError and same(value, expected)
            except Exception as exc:
                passed = expected is ValueError and isinstance(exc, ValueError)
            results.append({"check": name, "passed": passed})
    return {"case": case, "passed": sum(r["passed"] for r in results), "total": len(results), "checks": results}


def score(case, submission, timeout=5):
    try:
        run = subprocess.run([sys.executable, "-I", str(Path(__file__).resolve()), "_worker", "--case", case, "--submission", str(Path(submission).resolve())], capture_output=True, text=True, timeout=timeout)
        if run.returncode != 0:
            return {"case": case, "passed": 0, "total": len(checks(case)), "error": "submission or worker failed"}
        return json.loads(run.stdout)
    except subprocess.TimeoutExpired:
        return {"case": case, "passed": 0, "total": len(checks(case)), "error": "timeout"}
    except (ValueError, OSError):
        return {"case": case, "passed": 0, "total": len(checks(case)), "error": "invalid worker result"}


def prepare(case, dest, skill=None):
    dest = Path(dest)
    if dest.exists():
        raise ValueError("destination exists; choose a fresh directory")
    source = None
    if skill:
        matches = sorted((ROOT.parent / "packs").glob(f"*/skills/{skill}/SKILL.md")) if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", skill) else []
        if len(matches) != 1:
            raise ValueError("unknown skill")
        source = matches[0]
    shutil.copytree(ROOT / "tasks" / case, dest, ignore=shutil.ignore_patterns("__pycache__"))
    if source:
        shutil.copyfile(source, dest / "SKILL.md")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--case", choices=CASES, required=True)
    p.add_argument("--dest", type=Path, required=True)
    p.add_argument("--skill", help="omit for baseline")
    for name in ("score", "_worker"):
        p = sub.add_parser(name)
        p.add_argument("--case", choices=CASES, required=True)
        p.add_argument("--submission", type=Path, required=True)
        if name == "score":
            p.add_argument("--timeout", type=float, default=5)
            p.add_argument("--condition", choices=("baseline", "skill"), required=True)
            p.add_argument("--skill", default=None)
            p.add_argument("--agent", required=True)
            p.add_argument("--model", required=True)
            p.add_argument("--trial", type=int, required=True)
            p.add_argument("--elapsed-seconds", type=float, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        try:
            prepare(args.case, args.dest, args.skill)
        except ValueError as exc:
            parser.error(str(exc))
        print(f"Prepared {args.case} in {args.dest}")
        return 0
    if args.command == "_worker":
        print(json.dumps(worker(args.case, args.submission)))
        return 0
    if args.timeout <= 0 or not math.isfinite(args.timeout) or args.trial < 1 or args.elapsed_seconds < 0 or not math.isfinite(args.elapsed_seconds):
        parser.error("timeout must be positive, trial >= 1 and elapsed seconds finite and nonnegative")
    if (args.condition == "skill") != bool(args.skill):
        parser.error("specify --skill exactly when --condition is skill")
    result = score(args.case, args.submission, args.timeout)
    from datetime import datetime, timezone
    import hashlib
    result.update({"condition": args.condition, "skill": args.skill, "agent": args.agent, "model": args.model, "trial": args.trial, "elapsed_seconds": args.elapsed_seconds, "scored_at": datetime.now(timezone.utc).isoformat(), "python": sys.version.split()[0], "submission_sha256": hashlib.sha256(args.submission.read_bytes()).hexdigest()})
    print(json.dumps(result, sort_keys=True))
    return 0 if result["passed"] == result["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
