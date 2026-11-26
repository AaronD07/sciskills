"""A small paired study of code insertions on two published DS-1000 tasks."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import os

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
for directory in ("fieldstudy", "study", "external"):
    sys.path.insert(0, str(BENCH / directory))
import runner as clients
import ds1000
from score import sandbox_grade

IDS = (108, 411)
MODELS = {"codex": "gpt-6.1-terra", "claude": "claude-sonnet-5-5"}
SKILL = BENCH.parent / "skills/test-fresh-inputs/SKILL.md"
SEED = 143411108
LIMIT = 180
HEADER = (
    "Complete the Python insertion marked BEGIN SOLUTION. The surrounding setup "
    "has already run with the supplied input variables. Return only the Python "
    "code to insert at the marker. Work from this message without tools. "
    "If a workflow is provided, apply it to your completion."
)


def text_for(task, condition):
    message = HEADER + "\n\n" + ds1000.load_task(task)["prompt"]
    if condition == "skill":
        message += "\n\nWorkflow:\n" + SKILL.read_text().strip()
    return message


def jobs():
    rng = random.Random(SEED)
    pairs = [(a, t, n) for a in MODELS for t in IDS for n in (1, 2, 3)]
    rng.shuffle(pairs)
    for a, t, n in pairs:
        arms = ["baseline", "skill"]
        rng.shuffle(arms)
        for arm in arms:
            yield a, t, n, arm


def source_from(raw):
    match = re.fullmatch(r"```(?:python|py)?\s*\n(.*?)\n```", raw.strip(), re.S)
    return (match.group(1) if match else raw.strip()) + "\n"


def ask(job, prompt):
    agent, task, rep, arm = job
    output = ""
    start = time.monotonic()
    stamp = datetime.now(timezone.utc).isoformat()
    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp)
        cmd = clients.cli(agent, work)
        if MODELS[agent] not in cmd:
            raise RuntimeError("Unexpected CLI model selection")
        with subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=work,
            env=clients.clean_env(),
            start_new_session=True,
            text=True,
        ) as process:
            try:
                stdout, _ = process.communicate(prompt, timeout=LIMIT)
                status = "cli_error" if process.returncode else "submitted"
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
                status = "timeout"
        if status == "submitted":
            try:
                if agent == "claude":
                    reply = json.loads(stdout)
                    if (
                        reply.get("is_error")
                        or MODELS[agent] not in reply["modelUsage"]
                    ):
                        status = "client_error_or_model_mismatch"
                    else:
                        output = reply["result"]
                else:
                    events = [
                        json.loads(s) for s in stdout.splitlines() if s.startswith("{")
                    ]
                    if any(
                        e["item"].get("type")
                        not in {"agent_message", "reasoning", "error"}
                        for e in events
                        if "item" in e
                    ):
                        status = "tool_use"
                    else:
                        output = (work / "answer").read_text()
            except (KeyError, OSError, ValueError):
                status = "invalid_client_response"
    code = source_from(output) if status == "submitted" else ""
    return dict(
        agent=agent,
        task=task,
        repetition=rep,
        condition=arm,
        model=MODELS[agent],
        started_utc=stamp,
        elapsed_seconds=round(time.monotonic() - start, 3),
        status=status,
        prompt_sha256=clients.digest(prompt),
        source=code,
        source_sha256=clients.digest(code),
    )


def grade(python, task, source):
    """Run the pristine upstream tests through the existing sandboxed scorer."""
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp).resolve()
        shutil.copyfile(ds1000.__file__, root / "ds1000.py")
        record = ds1000.load_task(task)
        (root / "task.json").write_text(json.dumps(record))
        (root / "solution.py").write_text(source)
        script = root / "grade.py"
        script.write_text(
            "import sys, json\nfrom pathlib import Path\n"
            "sys.path.insert(0, str(Path(__file__).parent))\n"
            "from ds1000 import score, require_environment\nrequire_environment()\n"
            "print(json.dumps(score(json.loads(Path('task.json').read_text()), "
            "Path('solution.py').read_text())))\n"
        )
        verdict = sandbox_grade(
            [str(python), "-I", str(script)], root, [python.parent.parent.resolve()]
        )
        return verdict["passed"]


def replay(out, python):
    protocol = json.loads((out / "protocol.json").read_text())
    rows = [
        json.loads(line) for line in (out / "trials.jsonl").read_text().splitlines()
    ]
    if [list(j) for j in jobs()] != protocol["order"] or len(rows) != len(
        protocol["order"]
    ):
        raise ValueError("Incomplete or changed study schedule")
    for job, row in zip(jobs(), rows):
        agent, task, rep, arm = job
        assert (row["agent"], row["task"], row["repetition"], row["condition"]) == job
        assert row["model"] == MODELS[agent]
        assert (
            clients.digest(text_for(task, arm))
            == row["prompt_sha256"]
            == protocol["prompts"][f"{task}/{arm}"]
        )
        assert clients.digest(row["source"]) == row["source_sha256"]
        observed = row["status"] == "submitted" and grade(python, task, row["source"])
        if observed != row["passed"]:
            raise ValueError(f"Replay mismatch for {job}")
    print(f"Reproduced {len(rows)} outcomes.")


def run(out, python):
    if clients.MODELS != MODELS:
        raise RuntimeError("Mismatched CLI model IDs")
    auth = clients.subscription()
    for task in IDS:
        record = ds1000.load_task(task)
        if not grade(python, task, record["reference_code"]) or grade(python, task, ""):
            raise RuntimeError(f"Evaluator preflight failed for {task}")
    for agent in MODELS:
        check = ask(
            (agent, 0, 0, "smoke"),
            "Return exactly result = 2 + 3 as one line of Python. Do not use tools.",
        )
        if check["status"] != "submitted" or not check["source"].strip():
            raise RuntimeError(f"{agent} client preflight: {check['status']}")
    prompts = {(t, c): text_for(t, c) for t in IDS for c in ("baseline", "skill")}
    protocol = dict(
        frozen_utc=datetime.now(timezone.utc).isoformat(),
        order=list(jobs()),
        seed=SEED,
        timeout_seconds=LIMIT,
        concurrency=4,
        models=MODELS,
        upstream_sha256=ds1000.SHA256,
        evaluator_revision=ds1000.REVISION,
        prompts={f"{t}/{c}": clients.digest(v) for (t, c), v in prompts.items()},
        **auth,
    )
    out.mkdir(parents=True, exist_ok=True)
    with (out / "protocol.json").open("x") as f:
        json.dump(protocol, f, indent=2)
        f.write("\n")
    with (
        (out / "trials.jsonl").open("x") as f,
        ThreadPoolExecutor(max_workers=4) as pool,
    ):
        calls = [(j, pool.submit(ask, j, prompts[j[1], j[3]])) for j in jobs()]
        for job, handle in calls:
            row = handle.result()
            row["passed"] = row["status"] == "submitted" and grade(
                python, row["task"], row["source"]
            )
            f.write(json.dumps(row, sort_keys=True) + "\n")
            f.flush()
            print(*job, row["status"], row["passed"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "replay"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--external-python", type=Path, required=True)
    args = parser.parse_args()
    (run if args.action == "run" else replay)(args.out, args.external_python.absolute())
