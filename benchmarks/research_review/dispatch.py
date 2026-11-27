"""Run a sealed frontier holdout across locally verified participant engines."""

import argparse
import fcntl
from concurrent.futures import ThreadPoolExecutor
import os
import subprocess
import sys

from . import frontier, study


def choose_context(controls, prior, task_id):
    """Keep all drafts and forks on a single previously qualified machine."""
    eligible = {
        r["participant_context"]: r["participant_engine"]
        for r in controls
        if r.get("task") == task_id
        and r.get("commit") == frontier.MANIFEST["commit"]
        and frontier.live_control({"id": task_id}, r)
    }
    if prior:
        if eligible.get(prior["context"]) != prior["engine"]:
            raise RuntimeError(
                f"Saved task placement no longer has valid controls: {task_id}"
            )
        return prior
    if not eligible:
        raise ValueError(f"Missing positive/negative controls for {task_id}")
    # When both engines qualify, an outcome-independent hash divides their work.
    contexts = sorted(eligible)
    chosen = contexts[int(study.digest(task_id), 16) % len(contexts)]
    return {"context": chosen, "engine": eligible[chosen]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("phase", choices=["holdout", "reviews"])
    p.add_argument("--tasks", nargs="+")
    p.add_argument("--parallel-tasks", type=int, default=2)
    p.add_argument("--workers-per-task", type=int, default=2)
    args = p.parse_args()
    if min(args.parallel_tasks, args.workers_per_task) < 1:
        p.error("Worker counts must be positive")
    out = study.DEFAULT_OUT / "frontier"
    if not (out / "interventions.json").is_file():
        p.error("Qualify and seal the frontier track before dispatching its holdout")
    design = study.read(out / "design.json")
    case_ids = list(design["tasks"]["holdout"])
    if args.tasks:
        if set(args.tasks) - set(case_ids):
            p.error("Unknown frontier holdout task")
        case_ids = list(dict.fromkeys(args.tasks))
    jobs = []
    for task in sorted(case_ids):
        path = out / "execution-contexts" / (task + ".json")
        controls = [
            study.read(f) for f in frontier.STATE.glob(f"contexts/*/{task}.json")
        ]
        path.parent.mkdir(exist_ok=True)
        with path.with_suffix(".lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if args.phase == "reviews" and not path.exists():
                p.error(f"No original participant placement saved for {task}")
            placement = choose_context(
                controls, study.read(path) if path.is_file() else None, task
            )
            study.immutable(path, placement)
        jobs.append((task, placement))

    def run(job):
        task, placement = job
        cmd = [
            sys.executable,
            "-u",
            "-m",
            "benchmarks.research_review.study",
            args.phase,
            "frontier",
            "--tasks",
            task,
            "--workers",
            str(args.workers_per_task),
        ]
        code = subprocess.run(
            cmd,
            cwd=study.ROOT,
            env={**os.environ, "DOCKER_CONTEXT": placement["context"]},
        ).returncode
        if code:
            return code
        models = design["primary"] + (
            design["transfer"] if task in design["transfer_ids"] else []
        )
        arms = ("draft",) if args.phase == "holdout" else study.ARMS
        for model in models:
            for arm in arms:
                path = out / "holdout" / f"{task}.{model}.{arm}.json"
                row = study.read(path) if path.is_file() else {}
                if (
                    row.get("status") != "submitted"
                    or type((row.get("score") or {}).get("correct")) is not bool
                ):
                    print(f"Incomplete result {task}/{model}/{arm}", flush=True)
                    return 1
        return 0

    with ThreadPoolExecutor(args.parallel_tasks) as pool:
        codes = list(pool.map(run, jobs))
    if any(codes):
        raise SystemExit(
            "One or more tasks require attention. Saved attempts can be resumed."
        )


if __name__ == "__main__":
    main()
