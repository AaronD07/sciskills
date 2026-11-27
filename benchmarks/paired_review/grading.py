"""Grade submissions without sending expected values or tests to a participant."""

import importlib.util
import json
from pathlib import Path
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "review_python", HERE.parent / "ledger-replay/python_tool.py"
)
sandbox = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sandbox)


def equivalent(value, expected):
    if type(expected) in (float, int):
        if type(value) not in (float, int):
            return False
        try:
            return abs(value - expected) <= 1e-6
        except OverflowError:
            return False
    if isinstance(expected, list):
        return (
            isinstance(value, list)
            and len(value) == len(expected)
            and all(equivalent(a, b) for a, b in zip(value, expected))
        )
    if isinstance(expected, dict):
        return (
            isinstance(value, dict)
            and value.keys() == expected.keys()
            and all(equivalent(value[key], expected[key]) for key in expected)
        )
    return type(value) is type(expected) and value == expected


def parse_object(raw):
    def unique(pairs):
        if len(dict(pairs)) != len(pairs):
            raise ValueError("Duplicate key")
        return dict(pairs)

    try:
        obj = json.loads(raw, object_pairs_hook=unique)
        return obj if isinstance(obj, dict) else {}
    except (ValueError, TypeError, RecursionError):
        return {}


def run_program(files, rows):
    # A submitted module sees one test input at a time. Expectations stay in the parent.
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp).resolve()
        for name, value in files.items():
            dest = work / name
            if dest.resolve().is_relative_to(work) and dest != work:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(value)
        script = (
            "import json, os, contextlib\n"
            "with open(os.devnull, 'w') as null, contextlib.redirect_stdout(null), "
            "contextlib.redirect_stderr(null):\n"
            "    from solution import solve\n"
            f"    result = solve(json.loads({json.dumps(rows)!r}))\n"
            "print(json.dumps(result, allow_nan=False))"
        )
        status, output, _ = sandbox.execute(script, work)
        if status == 0:
            try:
                return True, json.loads(output)
            except ValueError:
                pass
    return False, None


def evaluate(case, files, status):
    if case["route"] == "program":
        checks = {}
        for index, test in enumerate(case["tests"]):
            ok, actual = (
                run_program(files, test["rows"])
                if "solution.py" in files and status == "submitted"
                else (False, None)
            )
            checks[f"input_{index + 1}"] = ok and equivalent(actual, test["expected"])
    else:
        answer = parse_object(files.get("answer.json", ""))
        checks = {
            key: key in answer and equivalent(answer[key], val)
            for key, val in case["gold"].items()
        }
        checks["output_keys"] = answer.keys() == case["gold"].keys()
    return {
        "checks": checks,
        "full_pass": status == "submitted" and bool(checks) and all(checks.values()),
    }
