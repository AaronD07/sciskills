"""Freeze and run paired ordinary, general and specialist review on published tasks."""

import argparse
import ast
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import importlib
import json
import math
from pathlib import Path
import random
import sys
import tempfile
import uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
runner = importlib.import_module("benchmarks.paired_review.runner")

SPECIALIST = {
    "contest": "review-an-analysis-program",
    "programming": "review-an-analysis-program",
    "statistics": "review-a-numerical-result",
    "payments": "review-a-protocol-decision",
    "physics": "review-a-numerical-result",
}
ARMS = ("ordinary", "general", "specialist")
TIMEOUT = 480


def adapter(mode):
    return importlib.import_module(f"benchmarks.external_review.{mode}")


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def encode(data):
    return json.dumps(data, sort_keys=True, ensure_ascii=False, allow_nan=False)


def read(path):
    return json.loads(path.read_text())


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as f:
        f.write(encode(obj) + "\n")
    Path(f.name).replace(path)


def intervention(name):
    # The pre-existing exercise is tied to a different repository task.
    return (ROOT / "skills" / name / "SKILL.md").read_text().split("## Exercise")[
        0
    ].rstrip() + "\n"


def freeze(mode, out):
    cases = {phase: adapter(mode).cases(phase) for phase in ("dev", "holdout")}
    skills = {
        "general": intervention("audit-a-scientific-claim"),
        "specialist": intervention(SPECIALIST[mode]),
    }
    protocol = {
        "mode": mode,
        "models": runner.MODELS,
        "timeout": TIMEOUT,
        "effort": "medium",
        "skills": skills,
        "prompts": runner.PROMPTS,
        "runtime": digest((HERE / "runtime.py").read_text()),
        "requirements": digest((HERE / "requirements.txt").read_text()),
        "splits": {},
    }
    for phase, rows in cases.items():
        protocol["splits"][phase] = {
            c["id"]: {
                "family": c["family"],
                "files": {n: digest(v) for n, v in c["files"].items()},
                "reference": digest(encode(c["gold"])),
            }
            for c in rows
        }
    path = out / mode / "protocol.json"
    if path.exists() and read(path) != protocol:
        raise ValueError(f"Frozen protocol differs at {path}")
    if not path.exists():
        save(path, protocol)
    return cases, skills


def grade(c, files):
    if c["kind"] == "program":
        checks = adapter(c["mode"]).inspect_tests(c, files)
        source = files.get("solution.py", "")
        try:
            tree = ast.parse(source)
            implemented = (c["mode"] == "contest" and bool(tree.body)) or any(
                isinstance(node, ast.FunctionDef)
                and any(
                    not isinstance(stmt, (ast.Pass, ast.Expr)) for stmt in node.body
                )
                for node in ast.walk(tree)
            )
        except (SyntaxError, ValueError):
            implemented = False
        return {
            "correct": bool(checks) and all(v == "passed" for v in checks.values()),
            "valid": implemented,
            "tests_passed": sum(v == "passed" for v in checks.values()),
            "tests_total": len(checks),
            "test_status": dict(Counter(checks.values())),
        }
    try:
        answer = json.loads(files["answer.json"])["answer"]
        encode(answer)  # Reject NaN and Infinity before persisting the observation.
    except (ValueError, TypeError, KeyError):
        return {"correct": False, "valid": False}
    if c["kind"] == "pvalue":
        scores = adapter("statistics").score(c, answer)
        valid = (
            isinstance(answer, dict)
            and type(answer.get("p_value")) in (int, float)
            and 0 <= answer["p_value"] <= 1
            and answer.get("decision") in ("reject", "fail_to_reject")
        )
        return {**scores, "valid": valid, "answer": answer}
    gold = c["gold"]["answer"]
    if (
        c["mode"] == "payments"
        and isinstance(answer, str)
        and answer.strip().lower() in {"not applicable", "n/a"}
    ):
        return {"correct": False, "valid": True, "answer": answer}
    if c["kind"] == "number":
        try:
            numeric = float(answer)
            valid = math.isfinite(numeric) and not isinstance(answer, bool)
            correct = valid and abs(numeric - gold) <= c["tol"]
        except (ValueError, TypeError):
            valid = correct = False
    elif c["kind"] == "set":
        values = answer.split(",") if isinstance(answer, str) else answer
        valid = isinstance(values, list) and all(type(v) in (str, int) for v in values)
        correct = valid and {str(v).strip() for v in values} == set(gold)
    else:
        valid = isinstance(answer, str)
        correct = valid and answer.strip() == gold
    return {"correct": correct, "valid": valid, "answer": answer}


def record(out, mode, phase, case, model, arm):
    return out / mode / phase / f"{case['id']}.{model}.{arm}.json"


def run_one(out, scratch, c, phase, model, arm, skills):
    path = record(out, c["mode"], phase, c, model, arm)
    if path.exists():
        prior_status = read(path)["status"]
        failed = path.parent / "infrastructure-attempts" / path.name
        if (
            prior_status not in {"cli_error", "no_python_receipt", "incomplete_turn"}
            or failed.exists()
        ):
            return prior_status
        failed.parent.mkdir(exist_ok=True)
        path.rename(failed)
    original = c["files"]
    files = original
    if arm != "draft":
        prior = read(record(out, c["mode"], phase, c, model, "draft"))
        if prior["status"] != "submitted":
            return "unavailable_draft"
        files = runner.review_files(original, prior)
        treatment = arm.removesuffix("-repeat")
        if treatment in skills:
            files["SKILL.md"] = skills[treatment]
    # Keep interrupted sessions for troubleshooting. Only completed calls enter the outcome.
    log = scratch / f"{path.stem}-{uuid.uuid4().hex}"
    response = runner.run_session(
        model,
        files,
        "draft" if arm == "draft" else "review",
        log,
        client_helper=HERE / "runtime.py",
        timeout=TIMEOUT,
    )
    outcome = {**files, **response["artifacts"]}
    for name in response["deleted"]:
        outcome.pop(name, None)
    score = grade(c, outcome) if response["status"] == "submitted" else None
    save(
        path,
        {
            **response,
            "score": score,
            "case": c["id"],
            "mode": c["mode"],
            "arm": arm,
            "client": model,
            "phase": phase,
        },
    )
    print(phase, path.stem, response["status"], flush=True)
    return response["status"]


def qualifying_errors(out, mode, development):
    """Identify distinct published questions with observable errors before promotion."""
    errors = set()
    for c in development:
        for model in runner.MODELS:
            path = record(out, mode, "dev", c, model, "draft")
            if not path.exists():
                continue
            r = read(path)
            score = r["score"] or {}
            if not score.get("valid") or score["correct"]:
                continue
            if c["kind"] == "pvalue":
                consequential = c["decision_eligible"] and not score["decision_correct"]
                if not c["strict_eligible"] and not consequential:
                    continue
            if c["kind"] == "program":
                if "test_status" not in score:
                    score = grade(c, r["artifacts"])
                if not score["test_status"].get("wrong_output"):
                    continue
            errors.add(c["id"])
            break
    return sorted(errors)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "phase",
        choices=["freeze", "dev", "holdout", "reviews", "dev-repairs", "repeat"],
    )
    p.add_argument("--modes", nargs="+", choices=SPECIALIST, default=list(SPECIALIST))
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--workers", type=int, default=6)
    args = p.parse_args()
    inputs = {m: freeze(m, args.out) for m in args.modes}
    if args.phase == "freeze":
        return
    if args.phase in ("reviews", "holdout", "repeat"):
        for mode, (cases, _) in inputs.items():
            errors = qualifying_errors(args.out, mode, cases["dev"])
            if len(errors) < 2:
                p.error(
                    f"{mode} has {len(errors)} qualifying development questions; two required"
                )
    phase = {"reviews": "holdout", "dev-repairs": "dev", "repeat": "holdout"}.get(
        args.phase, args.phase
    )
    arms = ARMS if args.phase in ("reviews", "dev-repairs") else ["draft"]
    if args.phase == "repeat":
        arms = [a + "-repeat" for a in ARMS]
    jobs = [
        (c, model, arm, skills)
        for cases, skills in inputs.values()
        for c in cases[phase]
        for model in runner.MODELS
        for arm in arms
    ]
    if args.phase in ("dev-repairs", "repeat"):

        def eligible(job):
            c, model, _, _ = job
            draft = read(record(args.out, c["mode"], phase, c, model, "draft"))
            score = draft["score"] or {}
            return (
                draft["status"] == "submitted"
                and score.get("valid")
                and not score["correct"]
                and c.get("strict_eligible", True)
            )

        jobs = [job for job in jobs if eligible(job)]
    random.Random("published-reviews-v1/" + args.phase).shuffle(jobs)
    scratch = args.out / "private"
    scratch.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Verify included usage before each bounded wave. Never switch providers on quota errors.
    if args.workers < 1:
        p.error("--workers must be positive")

    def pending(job):
        path = record(args.out, job[0]["mode"], phase, *job[:3])
        if not path.exists():
            return True
        return (
            read(path)["status"]
            in {"cli_error", "no_python_receipt", "incomplete_turn"}
            and not (path.parent / "infrastructure-attempts" / path.name).exists()
        )

    jobs = [job for job in jobs if pending(job)]
    for start in range(0, len(jobs), args.workers):
        receipt = runner.authenticate()
        save(args.out / "subscription.json", receipt)
        save(args.out / "auth" / f"{uuid.uuid4().hex}.json", receipt)
        with ThreadPoolExecutor(args.workers) as pool:
            futures = [
                pool.submit(run_one, args.out, scratch, c, phase, model, arm, s)
                for c, model, arm, s in jobs[start : start + args.workers]
            ]
            for f in as_completed(futures):
                f.result()


if __name__ == "__main__":
    main()
