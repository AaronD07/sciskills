"""Prepare isolated tasks and score submissions. Standard library only."""
import argparse
import contextlib
from copy import deepcopy
import io
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
from types import ModuleType

ROOT = Path(__file__).resolve().parent
CASES = ("kinetics", "assay", "prediction", "contract", "subjects", "comparison", "claims")


def checks(case):
    # Independent protocol-derived answers. Never copy this evaluator to a trial.
    if case == "contract":
        def cohort(name, rows, status, mean=None, n=0):
            return (name, "estimate", ({"cohort": "field", "endpoint": "yield"}, rows),
                    {"cohort": "field", "status": status, "mean": mean, "n": n})

        explicit_demo = ({"cohort": "demo", "endpoint": "x"}, {"demo": [{"x": 5}]})
        return [
            cohort("demo_only", {"demo": [{"yield": 50}]}, "missing cohort"),
            cohort("missing_all", {}, "missing cohort"),
            cohort("field_with_demo", {"field": [{"yield": 0}, {"yield": 6}], "demo": [{"yield": 50}]}, "ok", 3, 2),
            cohort("absent_column", {"field": [{"yield": 3}, {"other": 6}]}, "missing endpoint"),
            cohort("empty_field", {"field": []}, "no observations"),
            cohort("all_missing", {"field": [{"yield": None}]}, "no observations"),
            cohort("partial_observations", {"field": [{"yield": None}, {"yield": -2}]}, "ok", -2, 1),
            ("explicit_demo", "estimate", explicit_demo, {"cohort": "demo", "status": "ok", "mean": 5, "n": 1}),
        ]
    if case == "subjects":
        def paired(name, rows, change, stderr, n, excluded):
            return (name, "paired_change", (rows,),
                    {"mean_change": change, "standard_error": stderr, "n": n, "excluded": excluded})

        a = [("A", "before", 2), ("A", "after", 5)]
        b = [("B", "after", 2), ("B", "before", 3)]
        return [
            paired("shuffled_ids", [a[0], *b, a[1]], 1, 2, 2, 0),
            paired("unequal_repeats", a + b + [("A", "before", 6)], 0, 1, 2, 0),
            paired("unpaired", a + [("C", "before", 2)], 3, None, 1, 1),
            paired("one_pair", a, 3, None, 1, 0),
            paired("empty", [], None, None, 0, 0),
            paired("no_pairs", [("A", "before", 2), ("B", "after", 3)], None, None, 0, 2),
            paired("replicated_visit", a + b + [a[1], a[1]], 1, 2, 2, 0),
            paired("constant_changes", a + [("B", "before", 4), ("B", "after", 7)], 3, 0, 2, 0),
        ]
    if case == "comparison":
        def comparison(name, schedule, rows, primary, paired_delta, completed):
            return (name, "compare", (schedule, rows),
                    {"delta_all": primary, "delta_complete": paired_delta,
                     "planned_pairs": len(schedule), "complete_pairs": completed})

        a, b, c = ("x", 1), ("x", 2), ("y", 1)
        rows = [(*a, "skill", "ok", 1), (*b, "baseline", "ok", 0.25),
                (*a, "baseline", "ok", 0.5), (*b, "skill", "ok", 0)]
        return [
            comparison("shuffled", [a, b], rows, 0.125, 0.125, 2),
            comparison("timeouts", [a, b], rows[:3] + [(*b, "skill", "timeout", None)], 0.125, 0.5, 1),
            comparison("missing", [a, b], rows[:3], 0.125, 0.5, 1),
            comparison("different_cases", [a, c], [rows[0], (*c, "baseline", "ok", 0.5)], 0.25, None, 0),
            comparison("crash", [a], [(*a, "baseline", "crash", None), rows[0]], 1, None, 0),
            comparison("empty", [], [], None, None, 0),
            ("duplicate_run", "compare", ([a], [rows[0], rows[0]]), ValueError),
            ("unscheduled_run", "compare", ([b], [rows[0]]), ValueError),
        ]
    if case == "claims":
        current = {"id": "fig2", "version": "final", "group": "Coast", "positive": 3, "observed": 8}
        stale = dict(current, id="fig1", version="draft", observed=10)
        base = {"id": "s1", "group": "Coast", "kind": "rate", "percent": 38,
                "figure": "fig2", "text": "Improvement was reported by 38% on the coast."}
        kept = {key: base[key] for key in ("id", "figure", "percent", "text")}
        kept["status"] = "keep"
        revised = dict(kept, status="revise", text="Coast: 3 of 8 respondents (38%) reported improvement.")
        unsupported = dict(kept, status="unsupported", figure=None, percent=None,
                           text="The current survey does not establish this result.")
        def audit(name, draft, figures, expected):
            return (name, "audit_claims", (draft, figures, "final"), expected)

        wrong = dict(base, id="s2", percent=30)
        cause = dict(base, kind="cause", text="The program caused the improvement.")
        return [
            audit("keep_original_prose", [base], [stale, current], [kept]),
            audit("correct_denominator", [wrong], [current], [dict(revised, id="s2")]),
            audit("stale_figure", [dict(base, figure="fig1")], [current, stale], [revised]),
            audit("causal_overstatement", [cause], [current], [revised]),
            audit("no_current_source", [base], [stale], [unsupported]),
            audit("wrong_group", [base], [dict(current, group="Inland")], [unsupported]),
            audit("zero_observed", [base], [dict(current, positive=0, observed=0)], [unsupported]),
            audit("ordered_edits", [wrong, base], [dict(current, group="Inland"), current],
                  [dict(revised, id="s2"), kept]),
        ]
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
    if isinstance(expected, str):
        return isinstance(actual, str) and actual == expected
    if expected is None:
        return actual is None
    return isinstance(actual, (int, float)) and not isinstance(actual, bool) and math.isfinite(actual) and math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-12)


def worker(case, submission):
    results = []
    # Quiet normal candidate prints; this is process isolation, not a security sandbox.
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        # Score the source bytes on disk even after a same-size, same-timestamp edit.
        path = Path(submission)
        module = ModuleType("submission")
        module.__file__ = str(path)
        sys.modules[module.__name__] = module
        exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
        for name, function, arguments, expected in checks(case):
            try:
                value = getattr(module, function)(*deepcopy(arguments))
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
        source = ROOT.parent / "skills" / skill / "SKILL.md"
        if Path(skill).name != skill or not source.is_file():
            raise ValueError("unknown skill")
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
