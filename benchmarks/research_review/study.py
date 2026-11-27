"""Run frozen development and same-draft holdout comparisons on local subscriptions."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import fcntl
import importlib
import json
from pathlib import Path
import random
import sys
import uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from benchmarks.external_review.trial import digest, encode, read, save  # noqa: E402
from benchmarks.paired_review.runner import review_files  # noqa: E402

PRIMARY = ("terra", "sonnet")
TRANSFER = ("luna", "opus")
ARMS = ("ordinary", "general", "specialist")
TRACKS = ("everyday", "frontier", "swe")
DEFAULT_OUT = ROOT / "benchmark-runs/research-review"
SEED = "research-review-2026-v1"
FAMILIES = (
    "numerical",
    "assumption",
    "blocker",
    "scope",
    "verification",
    "implementation",
    "runtime",
)


def module(name):
    return importlib.import_module("benchmarks.research_review." + name)


def cases(track, phase):
    backend = module(track)
    return backend.cases(phase) if track == "everyday" else backend.tasks(phase)


def rank(case):
    return digest(SEED + "/" + case["id"])


def transfer_ids(track, rows):
    marked = [c["id"] for c in rows if c.get("secondary")]
    if marked:
        if len(marked) != 4:
            raise ValueError("Expected four preselected transfer tasks")
        return marked
    selected = []
    for c in sorted(rows, key=rank):
        family = c.get("family", c["id"])
        if family not in {old.get("family", old["id"]) for old in selected}:
            selected.append(c)
        if len(selected) == 4:
            break
    if len(selected) != 4:
        raise ValueError("Need four distinct families for transfer")
    return [c["id"] for c in selected]


def immutable(path, data):
    if path.exists():
        if read(path) != data:
            raise ValueError(f"Frozen configuration changed: {path}")
    else:
        save(path, data)


def freeze(out, track):
    groups = {s: cases(track, s) for s in ("dev", "holdout")}
    expected = {"dev": 16 if track == "everyday" else 12, "holdout": 16}
    ids = [c["id"] for rows in groups.values() for c in rows]
    if len(ids) != len(set(ids)) or any(
        len(groups[s]) != n for s, n in expected.items()
    ):
        raise ValueError(f"Unexpected split for {track}")
    frozen = {
        "study": SEED,
        "track": track,
        "primary": PRIMARY,
        "transfer": TRANSFER,
        "arms": ARMS,
        "effort": "high",
        "transfer_ids": transfer_ids(track, groups["holdout"]),
        "tasks": {
            s: {c["id"]: digest(encode(c)) for c in rows} for s, rows in groups.items()
        },
    }
    immutable(out / track / "design.json", json.loads(encode(frozen)))
    return frozen, groups


def row_path(out, track, phase, case, model, arm):
    return out / track / phase / f"{case['id']}.{model}.{arm}.json"


def gate(out, track):
    if track == "everyday":
        return True
    audit = read(out / track / "development-audit.json")
    subjects = {c["id"]: c for c in cases(track, "dev")}
    for model in PRIMARY:
        patterns = []
        for task_id, c in subjects.items():
            row = read(row_path(out, track, "dev", c, model, "draft"))
            if (
                row["status"] != "submitted"
                or (row["score"] or {}).get("correct") is None
            ):
                return False
            reason = audit[model][task_id]
            if (
                not row["score"]["correct"]
                and reason.get("class") in FAMILIES
                and reason.get("pattern")
                and reason["pattern"] not in FAMILIES
                and reason.get("evidence")
            ):
                patterns.append(reason["pattern"])
        if len(patterns) < 5 or len(set(patterns)) == len(patterns):
            return False
    return True


def skill_text(name):
    body = (ROOT / "skills" / name / "SKILL.md").read_text()
    return body.partition("## Exercise")[0].rstrip() + "\n"


def seal(out, track, groups, skill_map):
    for c in groups["dev"]:
        for model in PRIMARY:
            row = read(row_path(out, track, "dev", c, model, "draft"))
            if (
                row["status"] != "submitted"
                or (row["score"] or {}).get("correct") is None
            ):
                raise ValueError("Development inventory incomplete")
    if not gate(out, track):
        raise ValueError("Frontier development gate not met")
    general = skill_text(skill_map["general"])
    specialist = {
        c["id"]: skill_text(skill_map.get(c.get("family"), skill_map["default"]))
        for c in groups["holdout"]
    }
    immutable(
        out / track / "interventions.json",
        {"general": general, "specialist": specialist},
    )


def draft_identity(row):
    """Hash only the upstream draft and participant-visible material for its review."""
    session = row["session"]
    return digest(
        encode(
            {
                "track": row["track"],
                "task": row["task"],
                "model": row["model"],
                "image": row.get("image"),
                "work": {
                    k: session.get(k)
                    for k in ("calls", "reply", "artifacts", "deleted")
                },
            }
        )
    )


def grade_and_run(out, track, phase, c, model, arm, skills, scratch):
    client = module("client")
    backend = module(track)
    prior = None
    files = dict(c["files"]) if track == "everyday" else {"TASK.md": c["prompt"]}
    if arm != "draft":
        prior = read(row_path(out, track, phase, c, model, "draft"))
        if prior["status"] != "submitted":
            raise ValueError("A valid client session is required before forking")
        if track == "everyday":
            files = review_files(files, prior["session"])
        else:
            files["PRIOR_WORK.json"] = encode(prior["session"]["calls"])
            files["PRIOR_REPLY.txt"] = prior["session"]["reply"]
        if arm == "general":
            files["SKILL.md"] = skills["general"]
        elif arm == "specialist":
            files["SKILL.md"] = skills["specialist"][c["id"]]
    container = None
    image = None
    try:
        if track != "everyday":
            container = backend.start(c, prior["image"] if prior else None)
        session = client.run_session(
            model,
            files,
            "draft" if arm == "draft" else "review",
            scratch,
            container=container,
            timeout=int(c.get("agent_timeout_sec", 480)),
        )
        if session["status"] == "timeout" and session["calls"]:
            session["termination"] = "task_deadline"
            session["status"] = "submitted"
        score = None
        if session["status"] == "submitted":
            if track == "everyday":
                final = {**files, **session["artifacts"]}
                for name in session["deleted"]:
                    final.pop(name, None)
                score = backend.grade(c, final)
            else:
                image = backend.snapshot(container)
        elif container and session["calls"]:
            # Keep partially completed work private for transport and identity audits.
            # Only a validated client session can be scored or reviewed.
            image = backend.snapshot(container)
        if container:
            backend.stop(container)
            container = None
        return {
            "track": track,
            "phase": phase,
            "task": c["id"],
            "model": model,
            "arm": arm,
            "status": session["status"],
            "score": score,
            "session": session,
            "image": image,
            "parent": draft_identity(prior) if prior else None,
            "parent_scheme": "participant-v1" if prior else None,
        }
    finally:
        if container:
            backend.stop(container)


def run_one(args):
    out, track, phase, c, model, arm, skills = args
    path = row_path(out, track, phase, c, model, arm)
    path.parent.mkdir(exist_ok=True, parents=True)
    with path.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if path.exists():
            existing = read(path)
            if existing["status"] == "submitted":
                if (
                    existing.get("image")
                    and (existing["score"] or {}).get("correct") is None
                ):
                    existing["score"] = module(track).grade(c, existing["image"])
                    save(path, existing)
                return
            if existing["status"] not in {
                "cli_error",
                "incomplete_turn",
                "tool_unavailable",
                "quota_exhausted",
                "authentication_error",
            }:
                return
            failed = path.parent / "failed-attempts" / path.name
            if failed.exists():
                return
            failed.parent.mkdir(exist_ok=True)
            path.rename(failed)
        if track != "everyday" and not module(track).ready(c):
            raise RuntimeError(f"Reference controls not ready for {c['id']}")
        scratch = out / "private" / (path.stem + "-" + uuid.uuid4().hex)
        scratch.parent.mkdir(exist_ok=True, parents=True, mode=0o700)
        row = grade_and_run(out, track, phase, c, model, arm, skills, scratch)
        save(path, row)
        if row["status"] == "submitted" and row["image"]:
            row["score"] = module(track).grade(c, row["image"])
            save(path, row)
        print(track, phase, path.stem, row["status"], flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["freeze", "dev", "seal", "holdout", "reviews"])
    p.add_argument("track", choices=TRACKS)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--tasks", nargs="+")
    p.add_argument("--skill-map", type=Path)
    args = p.parse_args()
    design, groups = freeze(args.out, args.track)
    if args.action == "freeze":
        return
    if args.action == "seal":
        if not args.skill_map:
            p.error("seal requires --skill-map")
        seal(args.out, args.track, groups, read(args.skill_map))
        return
    phase = "dev" if args.action == "dev" else "holdout"
    skills = (
        {} if phase == "dev" else read(args.out / args.track / "interventions.json")
    )
    selection = groups[phase]
    if args.tasks:
        if set(args.tasks) - {c["id"] for c in selection}:
            p.error("Unknown task ID for this phase")
        selection = [c for c in selection if c["id"] in args.tasks]
    jobs = []
    for c in selection:
        models = PRIMARY + (
            TRANSFER if phase == "holdout" and c["id"] in design["transfer_ids"] else ()
        )
        arms = ARMS if args.action == "reviews" else ("draft",)
        for m in models:
            for arm in arms:
                path = row_path(args.out, args.track, phase, c, m, arm)
                if (
                    not path.exists()
                    or (read(path)["score"] or {}).get("correct") is None
                ):
                    jobs.append((args.out, args.track, phase, c, m, arm, skills))
    random.Random(SEED + args.action).shuffle(jobs)
    if args.workers < 1:
        p.error("workers must be positive")
    for i in range(0, len(jobs), args.workers):
        receipt = module("client").authenticate()
        save(args.out / "subscriptions" / (uuid.uuid4().hex + ".json"), receipt)
        with ThreadPoolExecutor(args.workers) as pool:
            list(pool.map(run_one, jobs[i : i + args.workers]))


if __name__ == "__main__":
    main()
