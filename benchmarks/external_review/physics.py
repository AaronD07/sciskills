"""Numerical short-answer adaptation of eight original FrontierScience physics problems."""

from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import tempfile
from urllib.request import urlopen

MANIFEST = Path(__file__).with_name("physics_data") / "manifest.json"
REVISION = "647a421c89d15aceaaa1a328e69b950b7632d2cf"
SHA256 = "450e7fceb53c8140283a752f0d62a3abc69a85e252d4dbbd5d9dfbfb762db4e4"
URL = f"https://huggingface.co/datasets/openai/frontierscience/resolve/{REVISION}/olympiad/test.jsonl"
SIZE = 142436


@lru_cache(maxsize=1)
def _questions():
    cache = Path(
        os.environ.get(
            "SCISKILLS_FRONTIERSCIENCE_CACHE", "~/.cache/sciskills/frontierscience"
        )
    ).expanduser()
    root = cache / REVISION
    root.mkdir(parents=True, exist_ok=True)
    path = root / "test.jsonl"
    data = path.read_bytes() if path.is_file() else b""
    if hashlib.sha256(data).hexdigest() != SHA256:
        with urlopen(URL, timeout=90) as response:
            data = response.read(SIZE + 1)
        if len(data) != SIZE or hashlib.sha256(data).hexdigest() != SHA256:
            raise ValueError("Unexpected FrontierScience Olympiad source bytes")
        with tempfile.NamedTemporaryFile(dir=root, delete=False) as staged:
            staged.write(data)
        os.replace(staged.name, path)
    rows = [json.loads(line) for line in data.splitlines()]
    return {r["task_group_id"]: r["problem"] for r in rows if r["subject"] == "physics"}


def cases(phase):
    specs = json.loads(MANIFEST.read_text())
    if phase not in specs:
        raise ValueError(f"Unknown FrontierScience split {phase!r}")
    questions = _questions()
    selected = []
    for spec in specs[phase]:
        key = spec["source_id"]
        problem, marker, _ = questions[key].partition(
            "\n\nThink step by step and solve the problem below."
        )
        if not marker:
            raise ValueError(f"Missing original response-format delimiter for {key}")
        prompt = (
            problem.rstrip()
            + "\n\n"
            + spec["measurement"]
            + '\n\nWrite answer.json as a JSON object with the single key "answer" containing the numeric result.\n'
        )
        selected.append(
            {
                "id": "frontier-" + key[:8],
                "family": spec["family"],
                "mode": "physics",
                "files": {"TASK.md": prompt},
                "gold": {"answer": spec["value"]},
                "kind": "number",
                "tol": spec["absolute_tolerance"],
            }
        )
    return selected
