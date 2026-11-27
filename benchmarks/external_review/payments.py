"""Frozen public hard DABstep development questions for the payments transfer test."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from functools import lru_cache
from pathlib import Path
from urllib.request import urlopen

MANIFEST = Path(__file__).with_name("payments_data") / "manifest.json"
SPLITS = {
    "dev": (
        ("1273", "average-fee", "number", 0.5e-6),
        ("1464", "static-fee-eligibility", "set", None),
        ("1871", "relative-fee-counterfactual", "number", 1e-10),
    ),
    "holdout": (
        ("1681", "merchant-period-fee-eligibility", "set", None),
        ("1753", "merchant-period-fee-eligibility", "set", None),
    ),
}


def _read_source(root: Path, revision: str, name: str, entry: dict) -> str:
    path = root / Path(name).name

    def matches(data: bytes) -> bool:
        return len(data) == entry["bytes"] and hashlib.sha256(data).hexdigest() == entry["sha256"]

    if path.is_file():
        data = path.read_bytes()
        if matches(data):
            return data.decode("utf-8")
    url = f"https://huggingface.co/datasets/adyen/DABstep/resolve/{revision}/{name}"
    with urlopen(url, timeout=90) as response:
        data = response.read(entry["bytes"] + 1)
    if not matches(data):
        raise ValueError(f"Size or SHA-256 mismatch for pinned DABstep file {name}")
    with tempfile.NamedTemporaryFile(dir=root, delete=False) as temporary:
        temporary.write(data)
    os.replace(temporary.name, path)
    return data.decode("utf-8")


@lru_cache(maxsize=1)
def _dataset() -> tuple[dict, dict]:
    manifest = json.loads(MANIFEST.read_text())
    base = os.environ.get("SCISKILLS_DABSTEP_CACHE", "~/.cache/sciskills/DABstep")
    root = Path(base).expanduser() / manifest["revision"]
    root.mkdir(parents=True, exist_ok=True)
    context = {}
    records = {}
    for name, entry in manifest["files"].items():
        text = _read_source(root, manifest["revision"], name, entry)
        if name.startswith("data/context/"):
            context[Path(name).name] = text
        elif name == "data/tasks/dev.jsonl":
            for line in text.splitlines():
                row = json.loads(line)
                records[row["task_id"]] = row
    return context, records


def cases(phase: str) -> list[dict]:
    """Return question text, original context files and an evaluator-only reference."""
    if phase not in SPLITS:
        raise ValueError(f"Unknown DABstep phase {phase!r}")
    context, records = _dataset()
    selected = []
    for task_id, family, kind, tolerance in SPLITS[phase]:
        row = records[task_id]
        if row["level"] != "hard":
            raise ValueError(f"DABstep question {task_id} is not labeled hard")
        answer = row["answer"]
        if kind == "number":
            answer = float(answer)
        elif kind == "set":
            answer = [value.strip() for value in answer.split(",")]
        prompt = (
            f'{row["question"]}\n\n{row["guidelines"]}\n\n'
            'Write your final response in answer.json as a JSON object with the single key '
            '"answer" containing the requested value.\n'
        )
        case = {
            "id": f"dabstep-{task_id}",
            "family": family,
            "mode": "payments",
            "files": {"TASK.md": prompt, **context},
            "gold": {"answer": answer},
            "kind": kind,
        }
        if tolerance is not None:
            case["tol"] = tolerance
        selected.append(case)
    return selected


if __name__ == "__main__":
    context, records = _dataset()
    print(f"Verified {len(context)} DABstep context files and {len(records)} public labels.")
