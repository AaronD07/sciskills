"""Exact stdout judging on high-difficulty AtCoder tasks from LiveCodeBench v6."""

import base64
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import pickletools
import subprocess
import tempfile
import zlib

from benchmarks.external_review.programming import _fetch_rows
from benchmarks.paired_review.grading import sandbox

MANIFEST = Path(__file__).with_name("contest_data") / "manifest.json"
SPLITS = {
    "dev": (
        ("abc398_g", "bipartite-graph-game"),
        ("arc193_b", "wheel-orientation-count"),
        ("arc196_c", "strong-pairings"),
    ),
    "holdout": (
        ("arc192_e", "lattice-path-count"),
        ("arc194_e", "block-swap-reachability"),
        ("arc195_e", "random-tree-distance"),
        ("abc397_g", "shortest-path-optimization"),
    ),
}


@lru_cache(maxsize=1)
def _rows():
    manifest = json.loads(MANIFEST.read_text())
    cache = (
        Path(
            os.environ.get("SCISKILLS_LCB_CACHE", "~/.cache/sciskills/livecodebench")
        ).expanduser()
        / manifest["revision"]
    )
    cache.mkdir(parents=True, exist_ok=True)
    if any(not (cache / f"{key}.json").is_file() for key in manifest["rows"]):
        _fetch_rows(cache, manifest)
    rows = {}
    for key, expected in manifest["rows"].items():
        raw = (cache / f"{key}.json").read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError(f"Unexpected LiveCodeBench contest row {key}")
        record = json.loads(raw)
        if record["platform"] != "atcoder" or record["difficulty"] != "hard":
            raise ValueError(f"Unexpected difficulty/platform for {key}")
        rows[key] = record
    return rows


def cases(phase):
    if phase not in SPLITS:
        raise ValueError(f"Unknown contest split {phase!r}")
    selected = []
    for key, family in SPLITS[phase]:
        problem = _rows()[key]["question_content"].strip()
        prompt = (
            problem
            + "\n\nWrite a self-contained Python 3 program in solution.py. Read standard input "
            "and write the specified result to standard output. Use Python's standard library.\n"
        )
        selected.append(
            {
                "id": "contest-" + key,
                "family": family,
                "mode": "contest",
                "kind": "program",
                "gold": {},
                "files": {"TASK.md": prompt},
            }
        )
    return selected


@lru_cache(maxsize=7)
def _tests(key):
    row = _rows()[key]
    payload = zlib.decompress(
        base64.b64decode(row["private_test_cases"], validate=True)
    )
    strings = []
    for opcode, value, _ in pickletools.genops(payload):
        if opcode.name == "BINUNICODE":
            strings.append(value)
        elif opcode.name not in {"PROTO", "FRAME", "MEMOIZE", "STOP"}:
            raise ValueError(f"Unexpected contest testcase opcode {opcode.name}")
    if len(strings) != 1:
        raise ValueError(f"Malformed private tests for {key}")
    private = json.loads(strings[0])
    if len(private) != 40:
        raise ValueError(f"Unexpected private test count for {key}")
    tests = [
        (f"{group}_{i:02d}", test)
        for group, records in (
            ("public", json.loads(row["public_test_cases"])),
            ("private", private),
        )
        for i, test in enumerate(records, 1)
    ]
    if any(test["testtype"] != "stdin" for _, test in tests):
        raise ValueError(f"Invalid stdin case for {key}")
    return tests


def _run(source, input_text, expected):
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp).resolve()
        (work / "solution.py").write_text(source)
        cmd = [
            "/usr/bin/sandbox-exec",
            "-p",
            sandbox.profile(work),
            sandbox.interpreter(),
            "-I",
            "-B",
            "solution.py",
        ]
        env = {
            "PATH": "/usr/bin:/bin",
            "HOME": str(work),
            "TMPDIR": str(work),
            "LC_ALL": "C",
        }
        with tempfile.TemporaryFile() as output:
            try:
                run = subprocess.run(
                    cmd,
                    input=(input_text.rstrip("\r\n") + "\n").encode(),
                    cwd=work,
                    env=env,
                    stdout=output,
                    stderr=subprocess.DEVNULL,
                    timeout=12,
                    preexec_fn=sandbox.limits,
                )
            except subprocess.TimeoutExpired:
                return "resource_limit"
            if run.returncode in {-9, -24, -25}:
                return "resource_limit"
            if run.returncode:
                return "execution_error"
            output.seek(0)
            actual = output.read()
            # Accept an optional trailing line ending and platform CRLF only.
            return (
                "passed"
                if actual.replace(b"\r\n", b"\n").removesuffix(b"\n")
                == expected.replace("\r\n", "\n").removesuffix("\n").encode()
                else "wrong_output"
            )


def inspect_tests(case, files):
    tests = _tests(case["id"].removeprefix("contest-"))
    source = files.get("solution.py")
    if not isinstance(source, str) or not source.strip():
        return {key: "no_submission" for key, _ in tests}
    return {key: _run(source, test["input"], test["output"]) for key, test in tests}


def grade(case, files):
    return {
        key: status == "passed" for key, status in inspect_tests(case, files).items()
    }
