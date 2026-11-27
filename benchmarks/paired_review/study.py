"""Freeze, run, and independently replay the matched scientific review study."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import fcntl
from pathlib import Path
import random

from grading import evaluate

HERE = Path(__file__).resolve().parent
MODELS = ("luna", "terra", "sonnet")
ROUTES = {
    "numbers": "review-a-numerical-result",
    "program": "review-an-analysis-program",
    "protocol": "review-a-protocol-decision",
}
SEED = 1432711


def packed(value):
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )


def digest(value):
    return hashlib.sha256(packed(value).encode()).hexdigest()


def cases_for(phase):
    import science

    cases = science.cases("dev" if phase == "dev" else "science")
    if phase == "holdout":
        import finance

        cases = [*cases, *finance.cases()]
    return {case["id"]: case for case in cases}


def materialize(initial, row):
    result = {**initial, **row["artifacts"]}
    for name in row["deleted"]:
        result.pop(name, None)
    return result


def dependencies():
    return {
        str(path.relative_to(HERE.parent.parent)): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in (
            HERE / "runner.py",
            HERE / "grading.py",
            HERE / "study.py",
            HERE / "analyze.py",
            HERE / "design.md",
            HERE.parent / "ledger-replay/python_tool.py",
            HERE.parent / "ledger-replay/study.py",
            HERE.parent / "fieldstudy/runner.py",
        )
    }


def frozen_inputs(phase, cases):
    skills = (
        {
            route: (HERE.parents[1] / "skills" / name / "SKILL.md").read_text()
            for route, name in ROUTES.items()
        }
        if phase == "holdout"
        else {}
    )
    return {
        "cases": {k: digest(v) for k, v in cases.items()},
        "skills": skills,
        "dependencies": dependencies(),
    }


def schedule(phase, cases):
    rng = random.Random(SEED + int(phase == "holdout"))
    jobs = []
    for case in sorted(cases):
        for model in MODELS:
            for rep in range(1, 3 if phase == "dev" else 2):
                arms = ["ordinary", "skill"] if phase == "holdout" else []
                rng.shuffle(arms)
                jobs.append({"case": case, "model": model, "rep": rep, "reviews": arms})
    rng.shuffle(jobs)
    return jobs


def check_counts(phase, cases):
    from collections import Counter

    science = [c for c in cases.values() if not c["id"].startswith("fin")]
    n = 4 if phase == "dev" else 8
    if Counter(c["route"] for c in science) != {k: n for k in ROUTES}:
        raise ValueError("Unexpected science task counts")
    if len(cases) != (12 if phase == "dev" else 32):
        raise ValueError("Unexpected task count")
    for c in cases.values():
        if "TASK.md" not in c["files"] or "SKILL.md" in c["files"]:
            raise ValueError(c["id"])
        if c["route"] == "program" and len(c["tests"]) < 3:
            raise ValueError("Insufficient behavioral checks: " + c["id"])


def write_atomic(path, obj):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(packed(obj) + "\n")
    tmp.replace(path)


def labeled(job, arm):
    return f"{job['case']}_{job['model']}_{job['rep']}_{arm}"


def record_session(case, job, arm, files, scratch, previous=None):
    from runner import run_session

    label = labeled(job, arm)
    saved = scratch / (label + ".json")
    identity = {
        "id": label,
        "case": case["id"],
        "model_key": job["model"],
        "rep": job["rep"],
        "arm": arm,
        "parent": previous,
        "input_hash": digest(files),
    }
    if saved.exists():
        row = json.loads(saved.read_text())
        if any(row[k] != v for k, v in identity.items()):
            raise ValueError("Conflicting saved session: " + label)
        return row
    attempt = scratch / label
    index = 1
    while attempt.exists():
        index += 1
        attempt = scratch / f"{label}-attempt-{index}"
    result = run_session(
        job["model"], files, "draft" if arm == "draft" else "review", attempt
    )
    row = {**result, **identity}
    row["grade"] = evaluate(case, materialize(files, row), row["status"])
    write_atomic(saved, row)
    print(f"{label}: {row['status']}", flush=True)
    return row


def run_job(case, job, skills, scratch):
    from runner import review_files

    draft = record_session(case, job, "draft", case["files"], scratch)
    rows = [draft]
    if job["reviews"]:
        base = review_files(case["files"], draft)
        for arm in job["reviews"]:
            files = dict(base)
            if arm == "skill":
                files["SKILL.md"] = skills[case["route"]]
            rows.append(record_session(case, job, arm, files, scratch, digest(draft)))
    return rows


def run(args, cases):
    from runner import authenticate

    args.out.mkdir(parents=True, exist_ok=True)
    args.private.mkdir(parents=True, exist_ok=True)
    if args.private.resolve().is_relative_to(HERE.parents[1]):
        raise ValueError("Private logs must live outside the repository")
    if (args.out / "sessions.jsonl").exists():
        raise FileExistsError(
            "Completed archive already exists. Use replay or choose a new output directory."
        )
    frozen = frozen_inputs(args.phase, cases)
    jobs = schedule(args.phase, cases)
    protofile = args.out / "protocol.json"
    auth = authenticate()
    if protofile.exists():
        proto = json.loads(protofile.read_text())
        if (
            proto["inputs"] != frozen
            or proto["jobs"] != jobs
            or proto["workers"] != args.workers
            or proto["clients"] != auth
            or proto["phase"] != args.phase
        ):
            raise ValueError("Frozen study inputs or client configuration changed")
    else:
        if any(args.private.iterdir()):
            raise ValueError("New study needs an empty private directory")
        write_atomic(
            protofile,
            {
                "phase": args.phase,
                "inputs": frozen,
                "jobs": jobs,
                "clients": auth,
                "seed": SEED + int(args.phase == "holdout"),
                "workers": args.workers,
            },
        )
    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for offset in range(0, len(jobs), args.workers):
            if offset:
                authenticate()
            batch = jobs[offset : offset + args.workers]
            futures = [
                pool.submit(
                    run_job, cases[j["case"]], j, frozen["skills"], args.private
                )
                for j in batch
            ]
            for future in as_completed(futures):
                rows.extend(future.result())
    target = args.out / "sessions.jsonl"
    tmp = target.with_suffix(".tmp")
    tmp.write_text(
        "".join(packed(r) + "\n" for r in sorted(rows, key=lambda r: r["id"]))
    )
    tmp.replace(target)
    write_atomic(
        args.out / "archive.json",
        {"sha256": hashlib.sha256(target.read_bytes()).hexdigest()},
    )


def replay(args, cases):
    from runner import review_files

    protocol = json.loads((args.out / "protocol.json").read_text())
    actual_inputs = {k: digest(v) for k, v in cases.items()}
    if protocol["phase"] != args.phase or protocol["inputs"]["cases"] != actual_inputs:
        raise ValueError("Frozen input mismatch")
    archive = args.out / "sessions.jsonl"
    checksum = args.out / "archive.json"
    if (
        checksum.exists()
        and json.loads(checksum.read_text())["sha256"]
        != hashlib.sha256(archive.read_bytes()).hexdigest()
    ):
        raise ValueError("Archive checksum mismatch")
    rows = [json.loads(line) for line in archive.read_text().splitlines()]
    by_id = {r["id"]: r for r in rows}
    jobs = schedule(args.phase, cases)
    expected = {labeled(j, arm) for j in jobs for arm in ["draft", *j["reviews"]]}
    if protocol["jobs"] != jobs or expected != set(by_id) or len(rows) != len(expected):
        raise ValueError("Incomplete or duplicated schedule")
    for job in jobs:
        case = cases[job["case"]]
        draft = by_id[labeled(job, "draft")]
        for arm in ["draft", *job["reviews"]]:
            row = by_id[labeled(job, arm)]
            files = (
                dict(case["files"])
                if arm == "draft"
                else review_files(case["files"], draft)
            )
            if arm == "skill":
                files["SKILL.md"] = protocol["inputs"]["skills"][case["route"]]
            parent = None if arm == "draft" else digest(draft)
            checks = evaluate(case, materialize(files, row), row["status"])
            if (
                digest(files) != row["input_hash"]
                or checks != row["grade"]
                or parent != row["parent"]
                or any(
                    row[k] != v
                    for k, v in {
                        "model_key": job["model"],
                        "case": job["case"],
                        "rep": job["rep"],
                        "arm": arm,
                    }.items()
                )
            ):
                raise ValueError("Replay mismatch in " + row["id"])
    print(f"Verified {len(rows)} scheduled sessions")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["run", "replay"])
    parser.add_argument("phase", choices=["dev", "holdout"])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--private", type=Path)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if args.action == "run" and (args.private is None or args.workers < 1):
        parser.error("run requires --private and a positive worker count")
    cases = cases_for(args.phase)
    check_counts(args.phase, cases)
    if args.action == "replay":
        replay(args, cases)
    else:
        args.out.mkdir(parents=True, exist_ok=True)
        # Lock the directory itself to avoid publishing a lock file.
        import os

        directory = os.open(args.out, os.O_RDONLY)
        try:
            fcntl.flock(directory, fcntl.LOCK_EX | fcntl.LOCK_NB)
            run(args, cases)
        finally:
            os.close(directory)


if __name__ == "__main__":
    main()
