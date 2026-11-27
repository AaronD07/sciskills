"""Original LiveCodeBench v6 Hard functional problems, graded outside the model session."""

from __future__ import annotations

import base64
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import pickletools
import tempfile
from urllib.request import urlopen
import zlib

from benchmarks.paired_review.grading import sandbox

MANIFEST = Path(__file__).with_name("programming_data") / "manifest.json"
SPLITS = {
    "dev": (
        ("3777", "constrained-subsequence"),
        ("3701", "caption-reconstruction"),
        ("3784", "prefix-removal"),
    ),
    "holdout": (
        ("3783", "permutation-unranking"),
        ("3801", "digit-counting"),
        ("3733", "grid-path"),
        ("3770", "string-overlap"),
        ("3781", "boundary-geometry"),
    ),
}


def _fetch_rows(cache, manifest):
    revision, name = manifest["revision"], manifest["filename"]
    source = f"https://huggingface.co/datasets/livecodebench/code_generation_lite/resolve/{revision}/{name}"
    with tempfile.TemporaryFile() as shard, urlopen(source, timeout=90) as response:
        digest = hashlib.sha256()
        size = 0
        while chunk := response.read(1 << 20):
            size += len(chunk)
            if size > manifest["bytes"]:
                raise ValueError("Unexpected LiveCodeBench shard size")
            digest.update(chunk)
            shard.write(chunk)
        if size != manifest["bytes"] or digest.hexdigest() != manifest["sha256"]:
            raise ValueError("LiveCodeBench shard failed integrity validation")
        shard.seek(0)
        for line in shard:
            key = json.loads(line)["question_id"]
            if key in manifest["rows"]:
                with tempfile.NamedTemporaryFile(dir=cache, delete=False) as staged:
                    staged.write(line)
                os.replace(staged.name, cache / f"{key}.json")


@lru_cache(maxsize=1)
def _dataset():
    manifest = json.loads(MANIFEST.read_text())
    cache = Path(
        os.environ.get("SCISKILLS_LCB_CACHE", "~/.cache/sciskills/livecodebench")
    ).expanduser()
    cache = cache / manifest["revision"]
    cache.mkdir(parents=True, exist_ok=True)
    if any(not (cache / f"{key}.json").is_file() for key in manifest["rows"]):
        _fetch_rows(cache, manifest)
    result = {}
    for key, expected in manifest["rows"].items():
        line = (cache / f"{key}.json").read_bytes()
        if hashlib.sha256(line).hexdigest() != expected:
            raise ValueError(f"LiveCodeBench record {key} failed integrity validation")
        result[key] = json.loads(line)
    return result


def cases(phase):
    if phase not in SPLITS:
        raise ValueError(f"Unknown LiveCodeBench split {phase!r}")
    selected = []
    for key, family in SPLITS[phase]:
        row = _dataset()[key]
        if row["difficulty"] != "hard" or row["platform"] != "leetcode":
            raise ValueError(f"Unexpected LiveCodeBench metadata for {key}")
        prompt = (
            row["question_content"].strip()
            + "\n\nImplement the method below in solution.py using Python's standard library. "
            "Include all necessary imports. Your code will be called with the stated arguments."
            + "\n\n```python\n"
            + row["starter_code"].strip()
            + "\n```\n"
        )
        selected.append(
            {
                "id": f"lcb-{key}",
                "family": family,
                "mode": "programming",
                "files": {"TASK.md": prompt},
                "gold": {},
                "kind": "program",
            }
        )
    return selected


@lru_cache(maxsize=8)
def _tests(key):
    row = _dataset()[key]
    # The source wraps a JSON string in pickle. Inspect data opcodes without
    # interpreting pickle instructions or importing objects from the dataset.
    packed = zlib.decompress(base64.b64decode(row["private_test_cases"], validate=True))
    strings = []
    for opcode, value, _ in pickletools.genops(packed):
        if opcode.name == "BINUNICODE":
            strings.append(value)
        elif opcode.name not in {"PROTO", "FRAME", "MEMOIZE", "STOP"}:
            raise ValueError(f"Unexpected testcase opcode {opcode.name}")
    if len(strings) != 1:
        raise ValueError("Expected one testcase payload")
    tests = json.loads(strings[0])
    if len(tests) != 40 or any(t["testtype"] != "functional" for t in tests):
        raise ValueError(f"Unexpected private test collection {key}")
    labeled = [
        (f"{group}_{index:02d}", test)
        for group, rows in (
            ("public", json.loads(row["public_test_cases"])),
            ("private", tests),
        )
        for index, test in enumerate(rows, start=1)
    ]
    return json.loads(row["metadata"])["func_name"], labeled


def _hash_value(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def inspect_tests(case, files):
    """Record output mismatches separately from execution and resource failures."""
    key = case["id"].removeprefix("lcb-")
    method, tests = _tests(key)
    source = files.get("solution.py")
    checks = {}
    for label, test in tests:
        checks[label] = "no_submission"
        if not isinstance(source, str) or not source.strip():
            continue
        args = [json.loads(arg) for arg in test["input"].splitlines()]
        expected_hash = _hash_value(json.loads(test["output"]))
        # Outcomes stay in the parent. A digest accommodates long strings/lists
        # without truncating outputs in the shared sandbox's stdout capture.
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp).resolve()
            for name, content in files.items():
                member = Path(name)
                if (member.suffix == ".py" and not member.is_absolute() and ".." not in member.parts
                        and member.parts[0] != "original_packet"):
                    destination = work / member
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_text(content)
            (work / "input.json").write_text(json.dumps(args))
            invocation = (
                "import contextlib, hashlib, json, os, sys\n"
                "sys.setprofile(None)\n"
                "with open(os.devnull, 'w') as out, contextlib.redirect_stdout(out):\n"
                "    with open('input.json') as f: args = json.load(f)\n"
                "    from solution import Solution\n"
                f"    value = getattr(Solution(), {method!r})(*args)\n"
                "    raw = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)\n"
                "print(hashlib.sha256(raw.encode()).hexdigest())"
            )
            status, output, _ = sandbox.execute(invocation, work)
            if status == 0:
                checks[label] = "passed" if output.strip() == expected_hash else "wrong_output"
            elif status in {-9, -24, 124}:
                checks[label] = "resource_limit"
            else:
                checks[label] = "execution_error"
    return checks


def grade(case, files):
    return {key: value == "passed" for key, value in inspect_tests(case, files).items()}
