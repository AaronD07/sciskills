"""File-edit replication on the two input-transfer tasks."""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time

import study

REQUEST = (
    "Use the workspace files to complete this scientific coding task. Read TASK.md "
    "and read SKILL.md if present. Write your Python insertion in solution.py. "
    "The surrounding setup already exists and will supply new inputs. Only the "
    "contents of solution.py will be graded. You may explain your work in the final "
    "message. Stay within this directory, use tools only to read or edit files, "
    "and do not run the code."
)
MODELS = study.MODELS
LIMIT = 180


def material(task, arm):
    files = {"TASK.md": study.ds1000.load_task(task)["prompt"], "solution.py": ""}
    if arm == "skill":
        files["SKILL.md"] = study.SKILL.read_text()
    return files


def fingerprint(files):
    return study.clients.digest(json.dumps(files, ensure_ascii=False, sort_keys=True))


def command(agent, cwd):
    if agent == "claude":
        return [
            study.clients.binary(agent),
            "-p",
            "--restricted",
            "--tools",
            "Read,Edit,Write",
            "--allowedTools",
            "Read",
            "Edit",
            "Write",
            "--permission-mode",
            "dontAsk",
            "--strict-mcp-config",
            "--setting-sources",
            "",
            "--disable-slash-commands",
            "--no-session-persistence",
            "--model",
            MODELS[agent],
            "--effort",
            "low",
            "--output-format",
            "stream-json",
            "--verbose",
        ]
    return [
        study.clients.binary(agent),
        "exec",
        "--ignore-user-config",
        "--ignore-rules",
        "--ephemeral",
        "--skip-git-repo-check",
        "-s",
        "workspace-write",
        "--disable",
        "apps",
        "--disable",
        "in_app_browser",
        "--disable",
        "skill_search",
        "--enable",
        "skip_host_skill_discovery",
        "-c",
        'model_reasoning_effort="low"',
        "-m",
        MODELS[agent],
        "--json",
        "-",
    ]


def audit(agent, raw):
    events = [json.loads(s) for s in raw.splitlines() if s.startswith("{")]
    if agent == "codex":
        items = [e["item"] for e in events if e.get("type") == "item.completed"]
        tools = [
            item["type"]
            for item in items
            if item["type"] not in ("reasoning", "agent_message")
        ]
        commands = [
            item["command"] for item in items if item.get("type") == "command_execution"
        ]
        return (
            bool(events and any(e.get("type") == "turn.completed" for e in events)),
            tools,
            commands,
        )
    final = next((e for e in reversed(events) if e.get("type") == "result"), {})
    tool_uses = [
        part
        for e in events
        if e.get("type") == "assistant"
        for part in e.get("message", {}).get("content", [])
        if part.get("type") == "tool_use"
    ]
    return (
        not final.get("is_error", True)
        and MODELS[agent] in final.get("modelUsage", {}),
        [part["name"] for part in tool_uses],
        [],
    )


def generate(job, files, instruction=REQUEST):
    agent, task, rep, arm = job
    start = time.monotonic()
    stamp = datetime.now(timezone.utc).isoformat()
    source = ""
    tools, commands = [], []
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        for filename, contents in files.items():
            (cwd / filename).write_text(contents)
        with subprocess.Popen(
            command(agent, cwd),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=study.clients.clean_env(),
            text=True,
            start_new_session=True,
        ) as proc:
            try:
                raw, _ = proc.communicate(instruction, timeout=LIMIT)
                ok, tools, commands = audit(agent, raw)
                status = "submitted" if proc.returncode == 0 and ok else "cli_error"
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.communicate()
                status = "timeout"
            except (ValueError, KeyError):
                status = "invalid_client_response"
        path = cwd / "solution.py"
        if path.is_symlink() or not path.is_file():
            status = "missing_or_indirect_submission"
        else:
            source = path.read_text()
        # Keep audit commands reproducible without exposing a machine-specific directory.
        commands = [
            c.replace(str(cwd.resolve()), "<workspace>").replace(
                str(cwd), "<workspace>"
            )
            for c in commands
        ]
    return dict(
        agent=agent,
        task=task,
        repetition=rep,
        condition=arm,
        model=MODELS[agent],
        started_utc=stamp,
        elapsed_seconds=round(time.monotonic() - start, 3),
        status=status,
        workspace_sha256=fingerprint(files),
        source=source,
        source_sha256=study.clients.digest(source),
        tool_counts=dict(Counter(tools)),
        shell_commands=commands,
    )


def run(out, python):
    auth = study.clients.subscription()
    for agent in MODELS:
        row = generate(
            (agent, 0, 0, "smoke"),
            {"TASK.md": "Write x = 42 in solution.py.", "solution.py": ""},
            "Read TASK.md and write exactly x = 42 into solution.py using your file tools.",
        )
        if (
            row["status"] != "submitted"
            or row["source"].strip().replace(" ", "") != "x=42"
        ):
            raise RuntimeError(
                f"{agent} could not complete file-edit preflight: {row['status']}, {row['tool_counts']}"
            )
    for task in study.IDS:
        ref = study.ds1000.load_task(task)["reference_code"]
        if not study.grade(python, task, ref) or study.grade(python, task, ""):
            raise RuntimeError(f"Grader preflight failed on task {task}")
    inputs = {(t, c): material(t, c) for t in study.IDS for c in ("baseline", "skill")}
    protocol = dict(
        frozen_utc=datetime.now(timezone.utc).isoformat(),
        models=MODELS,
        order=list(study.jobs()),
        request=REQUEST,
        materials={f"{t}/{c}": fingerprint(m) for (t, c), m in inputs.items()},
        upstream_sha256=study.ds1000.SHA256,
        seed=study.SEED,
        concurrency=4,
        timeout_seconds=LIMIT,
        **auth,
    )
    out.mkdir(parents=True, exist_ok=True)
    with (out / "protocol.json").open("x") as file:
        json.dump(protocol, file, indent=2)
        file.write("\n")
    with (
        (out / "trials.jsonl").open("x") as file,
        ThreadPoolExecutor(max_workers=4) as pool,
    ):
        calls = [
            (j, pool.submit(generate, j, inputs[j[1], j[3]])) for j in study.jobs()
        ]
        for job, call in calls:
            row = call.result()
            row["passed"] = row["status"] == "submitted" and study.grade(
                python, row["task"], row["source"]
            )
            file.write(json.dumps(row, sort_keys=True) + "\n")
            file.flush()
            print(*job, row["status"], row["passed"], flush=True)


def replay(out, python):
    protocol = json.loads((out / "protocol.json").read_text())
    rows = [json.loads(s) for s in (out / "trials.jsonl").read_text().splitlines()]
    schedule = list(study.jobs())
    if (
        len(rows) != len(schedule)
        or protocol["order"] != list(map(list, schedule))
        or protocol["request"] != REQUEST
    ):
        raise ValueError("Different schedule or instruction")
    for job, r in zip(schedule, rows):
        agent, task, rep, arm = job
        if [r[k] for k in ("agent", "task", "repetition", "condition")] != list(job):
            raise ValueError(f"Wrong trial identity {job}")
        if (
            r["model"] != MODELS[agent]
            or study.clients.digest(r["source"]) != r["source_sha256"]
        ):
            raise ValueError(f"Model or answer differs for {job}")
        if (
            fingerprint(material(task, arm)) != r["workspace_sha256"]
            or r["workspace_sha256"] != protocol["materials"][f"{task}/{arm}"]
        ):
            raise ValueError(f"Different workspace {job}")
        verdict = r["status"] == "submitted" and study.grade(python, task, r["source"])
        if verdict != r["passed"]:
            raise ValueError(f"Grading changed {job}")
    print(f"Replayed {len(rows)} file edits.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "replay"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--external-python", type=Path, required=True)
    args = parser.parse_args()
    (run if args.action == "run" else replay)(args.out, args.external_python.absolute())
