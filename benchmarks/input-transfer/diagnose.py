"""Separate value checks from DS-1000's source-form check on join submissions."""

import argparse
import json
from pathlib import Path
from unittest.mock import patch

import study


def replay_values(out, python):
    rows = [json.loads(s) for s in (out / "trials.jsonl").read_text().splitlines()]
    task = study.ds1000.load_task(108)
    prefix, separator, suffix = task["code_context"].partition(
        "def test_string(solution: str):"
    )
    if (
        not separator
        or 'assert "for" not in tokens and "while" not in tokens' not in suffix
    ):
        raise ValueError("Unexpected DS-1000 source-form test")
    # The original value-check functions and both input cases remain intact.
    values_only = {**task, "code_context": prefix}
    with patch.object(study.ds1000, "load_task", return_value=values_only):
        for row in rows:
            if row["task"] != 108 or row["passed"] or row["status"] != "submitted":
                continue
            ok = study.grade(python, 108, row["source"])
            print(
                row["agent"],
                row["condition"],
                row["repetition"],
                "value checks passed:",
                ok,
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--external-python", type=Path, required=True)
    args = parser.parse_args()
    replay_values(args.out, args.external_python.absolute())
