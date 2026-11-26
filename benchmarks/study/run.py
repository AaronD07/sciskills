"""Run the paired SciSkills pilot. Keep session logs outside the checkout."""
import argparse
import concurrent.futures
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import random
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

STUDY = Path(__file__).resolve().parent
BENCH = STUDY.parent
TASKS = {
    "contract": "preserve-the-research-question",
    "subjects": "identify-the-independent-unit",
    "comparison": "compare-experiments-fairly",
    "claims": "trace-claims-to-evidence",
    "166": "identify-the-independent-unit",
    "352": "known-answers-first",
}
MODELS = {"codex": "gpt-6.2-sol", "claude": "claude-sonnet-5-5"}
SEED = 20261126
BUDGET = 180
HEADER = """You are completing a scientific coding task. Work entirely from the supplied text. Use no tools or external files. Follow the supplied skill when present. Return only the complete Python source for the participant file. You may explain assumptions in code comments. Do not include Markdown fences or prose outside the Python source."""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def jobs():
    rng = random.Random(SEED)
    pairs = [(a, t, r) for a in MODELS for t in TASKS for r in range(1, 4)]
    rng.shuffle(pairs)
    for agent, task, rep in pairs:
        conditions = ["baseline", "skill"]
        rng.shuffle(conditions)
        for condition in conditions:
            yield agent, task, rep, condition


def name(job):
    return "-".join(map(str, job))


def prompt(task, condition):
    if task.isdecimal():
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run([sys.executable, str(BENCH / "external/ds1000.py"),
                            "prepare", task, directory], check=True)
            body = (Path(directory) / "TASK.md").read_text()
    else:
        files = BENCH / "tasks" / task
        body = (files / "TASK.md").read_text() + "\nCurrent analysis.py:\n" + (files / "analysis.py").read_text()
    if condition == "skill":
        body += "\nSKILL.md:\n" + (BENCH.parent / "skills" / TASKS[task] / "SKILL.md").read_text()
    return HEADER + "\n\nTASK.md:\n" + body


def cli(agent):
    configured = os.environ.get(agent.upper() + "_BIN")
    binary = configured or shutil.which(agent) or str(Path.home() / ".local/bin" / agent)
    return binary


def _generate(job, input_text, destination):
    agent, task, rep, condition = job
    destination.mkdir()
    started = time.monotonic()
    result = dict(agent=agent, task=task, repetition=rep, condition=condition, model=MODELS[agent],
                  skill=TASKS[task] if condition == "skill" else None, prompt_sha256=digest(input_text.encode()),
                  started_utc=datetime.now(timezone.utc).isoformat())
    (destination / "prompt.txt").write_text(input_text)
    with tempfile.TemporaryDirectory() as cwd:
        if agent == "codex":
            cmd = [cli(agent), "exec", "--ignore-user-config", "--ignore-rules", "--ephemeral",
                   "--skip-git-repo-check", "-s", "read-only", "-m", MODELS[agent], "-c",
                   'model_reasoning_effort="low"', "--json", "-o", str(destination / "answer.txt"), "-"]
        else:
            cmd = [cli(agent), "-p", "--tools", "", "--strict-mcp-config", "--disable-slash-commands",
                   "--setting-sources", "", "--no-session-persistence", "--model", MODELS[agent],
                   "--output-format", "json"]
        with (destination / "stdout").open("w") as out, (destination / "stderr").open("w") as err:
            with subprocess.Popen(cmd, cwd=cwd, stdin=subprocess.PIPE, stdout=out, stderr=err,
                                  start_new_session=True, text=True) as process:
                try:
                    process.communicate(input_text, timeout=BUDGET)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                    result["status"] = "timeout"
                if process.returncode:
                    result.setdefault("status", "infrastructure_error")
    result["elapsed_seconds"] = round(time.monotonic() - started, 2)
    if "status" not in result:
        raw = (destination / "stdout").read_text()
        if agent == "claude":
            reply = json.loads(raw)
            if reply.get("is_error") or MODELS[agent] not in reply.get("modelUsage", {}):
                result["status"] = "infrastructure_error"
            else:
                source = reply["result"]
        else:
            events = [json.loads(line) for line in raw.splitlines() if line.startswith("{")]
            forbidden = {"command_execution", "mcp_tool_call", "web_search", "file_change"}
            if any(e.get("item", {}).get("type") in forbidden for e in events):
                result["status"] = "tool_used"
            else:
                source = (destination / "answer.txt").read_text()
        if "status" not in result:
            fence = re.fullmatch(r"`{3}(?:python|py)?\s*\n(.*?)\n`{3}", source.strip(), re.S)
            source = (fence.group(1) if fence else source.strip()) + "\n"
            (destination / "submission.py").write_text(source)
            result.update(status="submitted", submission_sha256=digest(source.encode()))
    (destination / "generation.json").write_text(json.dumps(result) + "\n")
    return result


def generation_failure(job, input_text, destination, status):
    agent, task, rep, condition = job
    result = dict(agent=agent, task=task, repetition=rep, condition=condition,
                  model=MODELS[agent], skill=TASKS[task] if condition == "skill" else None,
                  status=status, elapsed_seconds=None, started_utc=None,
                  prompt_sha256=digest(input_text.encode()))
    (destination / "generation.json").write_text(json.dumps(result) + "\n")
    return result


def generate(job, input_text, destination):
    if destination.exists():
        # A killed session may already have consumed its attempt. Keep the event.
        return generation_failure(job, input_text, destination, "interrupted")
    try:
        return _generate(job, input_text, destination)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        if not destination.is_dir():
            raise
        (destination / "failure-type.txt").write_text(type(exc).__name__ + "\n")
        return generation_failure(job, input_text, destination, "infrastructure_error")


def generate_all(args):
    args.out.mkdir(parents=True, exist_ok=True)
    versions = {a: subprocess.check_output([cli(a), "--version"], text=True).strip() for a in MODELS}
    schedule = list(jobs())
    metadata = dict(models=MODELS, cli_versions=versions, timeout=BUDGET, seed=SEED,
                    order=list(map(name, schedule)), max_workers=args.workers)
    inputs = {(t, c): prompt(t, c) for t in TASKS for c in ("baseline", "skill")}
    metadata["prompt_sha256"] = {f"{t}/{c}": digest(text.encode()) for (t, c), text in inputs.items()}
    protocol = args.out / "protocol.json"
    if protocol.exists() and json.loads(protocol.read_text()) != metadata:
        raise ValueError("Refusing to mix different protocols or CLI versions")
    protocol.write_text(json.dumps(metadata, indent=2) + "\n")
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        running = []
        for job in schedule:
            dest = args.out / name(job)
            if (dest / "generation.json").exists():
                continue
            running.append(pool.submit(generate, job, inputs[job[1], job[3]], dest))
        for future in concurrent.futures.as_completed(running):
            row = future.result()
            print(row["agent"], row["task"], row["condition"], row["repetition"], row["status"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=lambda p: Path(p).resolve())
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    args.out.mkdir(exist_ok=True, parents=True)
    with (args.out / ".runner.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        generate_all(args)
