"""Source-disjoint, frozen P-Bench Hard tasks and the published strict metric."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

DATA = Path(__file__).with_name("statistics_data")


def _verified_text(path: Path, expected: str) -> str:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f"Unexpected contents of pinned P-Bench file {path}")
    return raw.decode("utf-8")


def cases(phase: str) -> list[dict]:
    if phase not in {"dev", "holdout"}:
        raise ValueError(f"Unknown P-Bench phase {phase!r}")
    records = json.loads((DATA / "manifest.json").read_text())
    audit = json.loads((DATA / "key_audit.json").read_text())
    output = []
    for record in records:
        if record["split"] != phase:
            continue
        directory = DATA / record["id"]
        question = _verified_text(directory / "question.txt", record["question_sha256"])
        dataset = _verified_text(directory / "dataset.csv", record["dataset_sha256"])
        task = (
            question.rstrip() + "\n\nAnalyze dataset.csv for the stated hypothesis. "
            "At a significance level of 0.05, report your numeric p-value and decision. "
            'Write answer.json with one top-level key "answer", containing an object with '
            'keys "p_value" (a number) and "decision" ("reject" or "fail_to_reject").\n'
        )
        output.append(
            {
                "id": record["id"],
                "mode": "statistics",
                "family": record["source_id"],
                "files": {"TASK.md": task, "dataset.csv": dataset},
                "gold": {"answer": record["answer"]},
                "kind": "pvalue",
                "strict_eligible": audit[record["id"]]["strict_eligible"],
                "decision_eligible": audit[record["id"]]["decision_eligible"],
            }
        )
    return output


def _z(p: float) -> float:
    # Match the rounded upper-tail probability used in the public P-Bench scorer.
    from scipy.special import ndtri

    return min(float(ndtri(1 - max(p, 2.2e-16) / 2)), 10.0)


def score(case: dict, answer: object) -> dict[str, bool]:
    """Grade the nested answer value. Report decision errors separately from strict failures."""
    expected = case["gold"]["answer"]
    prediction = answer if isinstance(answer, dict) else {}
    decision_correct = prediction.get("decision") == expected["decision"]
    p_value = prediction.get("p_value")
    pvalue_correct = (
        type(p_value) in (int, float)
        and 0 <= p_value <= 1
        and math.isfinite(p_value)
        and abs(_z(p_value) - _z(expected["p_value"])) < 0.5
    )
    return {
        "correct": decision_correct and pvalue_correct,
        "decision_correct": decision_correct,
        "pvalue_correct": pvalue_correct,
    }
