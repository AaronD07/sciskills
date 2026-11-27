"""Collect or replay a frozen source-matched scientific integrity cohort."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import sys
import tempfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PAIRED = HERE.parent / "paired_review"
sys.path.insert(0, str(PAIRED))
from grading import equivalent, parse_object  # noqa: E402
from runner import MODELS, authenticate, review_files, run_session  # noqa: E402
from study import digest, materialize, packed, write_atomic  # noqa: E402

FAMILIES = ("coverage", "measurement", "deployment")
CARDS = {
    "general": "audit-a-scientific-claim",
    "coverage": "verify-experimental-coverage",
    "measurement": "verify-measurement-provenance",
    "deployment": "test-the-deployment-claim",
}
ARMS = ("ordinary", "general", "specialist")
VARIANTS = {"compromised", "intact"}
SEED = 143112704
MODULES = {}


def family_module(name):
    if name not in MODULES:
        spec = importlib.util.spec_from_file_location(
            "integrity_" + name, HERE / (name + ".py")
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        MODULES[name] = module
    return MODULES[name]


def load_cases(mode, phase):
    packet_list = family_module(mode).cases(phase)
    cases = {c["id"]: c for c in packet_list}
    expected = 3 if phase == "dev" else 6
    if len(cases) != 2 * expected or len(cases) != len(packet_list):
        raise ValueError("Unexpected or duplicate packet IDs")
    sources = {}
    for c in cases.values():
        if (
            c["mode"] != mode
            or "TASK.md" not in c["files"]
            or {"answer.json", "SKILL.md", "PRIOR_WORK.json", "PRIOR_REPLY.txt"}
            & c["files"].keys()
        ):
            raise ValueError("Invalid packet: " + c["id"])
        if not c["critical"] or not set(c.get("gate_keys", c["critical"])) <= set(
            c["critical"]
        ):
            raise ValueError("Missing scientific severity rules")
        sources.setdefault(c["source"], []).append(c)
    if len(sources) != expected:
        raise ValueError("Source grouping mismatch")
    for twins in sources.values():
        if {c["variant"] for c in twins} != VARIANTS or len(
            {c["files"]["TASK.md"] for c in twins}
        ) != 1:
            raise ValueError("Unmatched tasks within source " + twins[0]["source"])
    return cases


def numeric(value):
    return type(value) in (float, int)


def field_match(value, expected, tol):
    if numeric(value) and numeric(expected):
        try:
            return abs(value - expected) <= tol
        except OverflowError:
            return False
    return equivalent(value, expected)


def semantic(value, expected):
    if isinstance(value, str):
        token = value.strip().casefold()
        if (
            token
            in {"none", "null", "unavailable", "not available", "not applicable", "n/a"}
            and expected is None
        ):
            return None
        if isinstance(expected, str):
            return token
        if isinstance(expected, bool) and token in {"true", "false"}:
            return token == "true"
        if numeric(expected):
            try:
                return float(token)
            except ValueError:
                pass
    return value


def grade(case, files, status):
    answer = parse_object(files.get("answer.json", ""))
    checks = {
        key: key in answer
        and field_match(answer[key], value, case.get("tolerance", {}).get(key, 1e-6))
        for key, value in case["gold"].items()
    }
    module = family_module(case["mode"])
    if hasattr(module, "validate"):
        extra = module.validate(case, files)
        if extra.keys() & checks.keys():
            raise ValueError("Duplicate grade predicate")
        checks.update(extra)
    critical = case["critical"]
    valid = status == "submitted"
    scientific = {}
    failures = []
    for key in critical:
        if key not in case["gold"]:
            scientific[key] = checks[key]
            continue
        expected = case["gold"][key]
        value = semantic(answer.get(key), expected)
        target = semantic(expected, expected)
        tolerance = case.get("tolerance", {}).get(key, 1e-6)
        if type(expected) is float:
            tolerance = max(tolerance, 0.01, 0.02 * abs(expected))
        scientific[key] = key in answer and field_match(value, target, tolerance)
        if (
            key in case.get("gate_keys", critical)
            and valid
            and key in answer
            and not scientific[key]
        ):
            if (
                type(value) is type(target)
                or (numeric(value) and numeric(target))
                or value is None
                or target is None
            ):
                failures.append(key)
    return {
        "critical_pass": valid and all(scientific.values()),
        "critical_checks": scientific,
        "full_pass": valid
        and all(checks.values())
        and case["gold"].keys() == answer.keys(),
        "gate_errors": failures,
        "checks": checks,
    }


def schedule(cases, phase):
    rng = random.Random(SEED)
    jobs = []
    for case in sorted(cases):
        for model in sorted(MODELS):
            arms = list(ARMS) if phase == "holdout" else []
            rng.shuffle(arms)
            jobs.append({"case": case, "model": model, "arms": ["draft", *arms]})
    rng.shuffle(jobs)
    return jobs


def session_id(job, arm):
    return f"{job['case']}_{job['model']}_{arm}"


def inputs(case, arm, draft, cards):
    if arm == "draft":
        return dict(case["files"])
    files = review_files(case["files"], draft)
    if arm in ("general", "specialist"):
        files["SKILL.md"] = cards[arm]
    return files


def execute(case, job, cards, private):
    rows = []
    for arm in job["arms"]:
        label = session_id(job, arm)
        draft = rows[0] if rows else None
        files = inputs(case, arm, draft, cards)
        identity = {
            "id": label,
            "case": case["id"],
            "source": case["source"],
            "variant": case["variant"],
            "mode": case["mode"],
            "model_key": job["model"],
            "arm": arm,
            "input_hash": digest(files),
            "parent": digest(draft) if draft else None,
        }
        saved = private / (label + ".json")
        if saved.exists():
            row = json.loads(saved.read_text())
            if any(row[k] != v for k, v in identity.items()):
                raise ValueError("Checkpoint input mismatch: " + label)
        else:
            scratch = Path(tempfile.mkdtemp(dir=private, prefix=label + "-")) / "log"
            row = {
                **run_session(
                    job["model"],
                    files,
                    "draft" if arm == "draft" else "review",
                    scratch,
                ),
                **identity,
            }
            row["grade"] = grade(case, materialize(files, row), row["status"])
            write_atomic(saved, row)
            print(label, row["status"], flush=True)
        rows.append(row)
    return rows


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dependencies(mode):
    paths = [
        Path(__file__),
        HERE / "analysis.py",
        HERE / "design.md",
        HERE / (mode + ".py"),
        PAIRED / "runner.py",
        PAIRED / "study.py",
        PAIRED / "grading.py",
        HERE.parent / "ledger-replay/study.py",
        HERE.parent / "ledger-replay/python_tool.py",
        HERE.parent / "fieldstudy/runner.py",
    ]
    return {str(p.relative_to(REPO)): checksum(p) for p in paths}


def result_dir(root, mode, phase):
    return root / phase / mode


def replay(root, mode, phase):
    cases = load_cases(mode, phase)
    out = result_dir(root, mode, phase)
    proto = json.loads((out / "protocol.json").read_text())
    jobs = schedule(cases, phase)
    archive = out / "sessions.jsonl"
    if (
        proto["jobs"] != jobs
        or proto["packet_hashes"] != {k: digest(v) for k, v in cases.items()}
        or json.loads((out / "archive.json").read_text())["sha256"] != checksum(archive)
    ):
        raise ValueError("Changed inputs or archive")
    rows = [json.loads(line) for line in archive.read_text().splitlines()]
    table = {r["id"]: r for r in rows}
    if set(table) != {session_id(j, a) for j in jobs for a in j["arms"]} or len(
        table
    ) != len(rows):
        raise ValueError("Invalid session schedule")
    for j in jobs:
        c = cases[j["case"]]
        draft = table[session_id(j, "draft")]
        for a in j["arms"]:
            r = table[session_id(j, a)]
            files = inputs(c, a, draft, proto["skills"])
            if (
                r["input_hash"] != digest(files)
                or r["parent"] != (None if a == "draft" else digest(draft))
                or any(
                    r[k] != v
                    for k, v in {
                        "case": c["id"],
                        "model_key": j["model"],
                        "arm": a,
                        "mode": mode,
                        "source": c["source"],
                        "variant": c["variant"],
                        "model": MODELS[j["model"]],
                    }.items()
                )
                or r["grade"] != grade(c, materialize(files, r), r["status"])
            ):
                raise ValueError("Replay mismatch: " + r["id"])
    return rows


def qualifying_sources(rows):
    return sorted({r["source"] for r in rows if r["grade"]["gate_errors"]})


def collect(args, cases, out):
    if (out / "sessions.jsonl").exists():
        raise FileExistsError("Completed cohort already archived")
    gate = None
    cards = {}
    if args.phase == "holdout":
        dev = replay(args.results, args.mode, "dev")
        sources = qualifying_sources(dev)
        if len(sources) < 2:
            raise ValueError("Development did not qualify this mode")
        if {r["source"] for r in dev} & {c["source"] for c in cases.values()}:
            raise ValueError("Source overlap between development and holdout")
        gate = {
            "sources": sources,
            "development_archive": checksum(
                result_dir(args.results, args.mode, "dev") / "sessions.jsonl"
            ),
        }
        cards = {
            a: (
                REPO
                / "skills"
                / CARDS["general" if a == "general" else args.mode]
                / "SKILL.md"
            ).read_text()
            for a in ("general", "specialist")
        }
    private = result_dir(args.private.resolve(), args.mode, args.phase)
    if private.is_relative_to(REPO):
        raise ValueError("Keep private transcripts outside the checkout")
    private.mkdir(parents=True, exist_ok=True)
    jobs = schedule(cases, args.phase)
    proto = {
        "phase": args.phase,
        "mode": args.mode,
        "gate": gate,
        "skills": cards,
        "jobs": jobs,
        "seed": SEED,
        "models": MODELS,
        "workers": args.workers,
        "clients": authenticate(),
        "packet_hashes": {k: digest(c) for k, c in cases.items()},
        "code": dependencies(args.mode),
    }
    path = out / "protocol.json"
    if path.exists():
        if json.loads(path.read_text()) != proto:
            raise ValueError("Cannot resume a changed experiment")
    elif any(private.iterdir()):
        raise ValueError("New cohort requires fresh private directory")
    else:
        write_atomic(path, proto)
    all_rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for start in range(0, len(jobs), args.workers):
            if start:
                authenticate()
            batch = jobs[start : start + args.workers]
            futures = [
                pool.submit(execute, cases[j["case"]], j, cards, private) for j in batch
            ]
            for future in futures:
                all_rows.extend(future.result())
    archive = out / "sessions.jsonl"
    temp = archive.with_suffix(".tmp")
    temp.write_text(
        "".join(packed(r) + "\n" for r in sorted(all_rows, key=lambda x: x["id"]))
    )
    temp.replace(archive)
    write_atomic(out / "archive.json", {"sha256": checksum(archive)})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=["run", "replay"])
    ap.add_argument("phase", choices=["dev", "holdout"])
    ap.add_argument("mode", choices=FAMILIES)
    ap.add_argument("--results", type=Path, default=HERE / "results")
    ap.add_argument("--private", type=Path)
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()
    if args.action == "replay":
        rows = replay(args.results, args.mode, args.phase)
        print(
            f"Verified {len(rows)} sessions.",
            "Gate sources: " + str(qualifying_sources(rows))
            if args.phase == "dev"
            else "",
        )
        return
    if not args.private or args.workers < 1:
        ap.error("run needs --private and positive worker count")
    out = result_dir(args.results, args.mode, args.phase)
    out.mkdir(parents=True, exist_ok=True)
    fd = os.open(out, os.O_RDONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        collect(args, load_cases(args.mode, args.phase), out)
    finally:
        os.close(fd)


if __name__ == "__main__":
    main()
