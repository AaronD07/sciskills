"""Run a paired local Python study of scientific ledger reconstruction."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import os
import random
import signal
import stat
import subprocess
import sys
import tempfile
import time

import cases

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "fieldstudy"))
from runner import binary, clean_env, digest, grade, normalized, subscription
sys.path.pop(0)

MODELS = {"codex": "gpt-6-luna", "claude": "claude-sonnet-5-5"}
SKILL = HERE.parent.parent / "skills/reconstruct-a-vintage"
PROMPT = ("Use the local ledger Python tool to solve TASK.md in its current directory. "
          "Read the task and the supplied data files through Python. If SKILL.md is present, "
          "read it and apply it. The tool preserves files between calls. Write the single "
          "requested object as valid JSON to answer.json in that directory. You can inspect or "
          "import local Python files and use runpy to run a script in-process. "
          "Use only this tool. Finish once you have written your answer.")
TIMEOUT = 240
WORKERS = 4
SEED = 14320261127


def jobs():
    rng = random.Random(SEED)
    pairs = [(agent, s, r) for agent in MODELS for s in ("d","e","f") for r in (1,2,3)]
    rng.shuffle(pairs)
    result = []
    for agent, split, rep in pairs:
        conditions = ["baseline", "skill"]
        rng.shuffle(conditions)
        result.extend(dict(agent=agent, split=split, repetition=rep, condition=c) for c in conditions)
    return result


def cli(agent, config):
    if agent == "claude":
        return [binary(agent), "-p", "--restricted", "--tools", "", "--strict-mcp-config",
                "--setting-sources", "", "--disable-slash-commands", "--no-session-persistence",
                "--model", MODELS[agent], "--effort", "low", "--output-format", "json",
                "--mcp-config", json.dumps({"mcpServers":{"ledger": config}}),
                "--allowedTools", "mcp__ledger__python"]
    cmd = [binary(agent), "exec", "--ignore-user-config", "--ignore-rules", "--ephemeral",
           "--skip-git-repo-check", "-s", "read-only", "--disable", "apps", "--disable", "shell_tool",
           "--disable", "unified_exec", "--disable", "in_app_browser", "--disable", "skill_search",
           "--enable", "skip_host_skill_discovery", "-c", 'model_reasoning_effort="low"',
           "-m", MODELS[agent], "--json"]
    for key in ("command","args"):
        cmd += ["-c",f"mcp_servers.ledger.{key}={json.dumps(config[key])}"]
    return [*cmd, "-c", 'mcp_servers.ledger.tools.python.approval_mode="approve"', "-"]


def materials(split, condition):
    files, gold = cases.make(split)
    files = dict(files)
    if condition == "skill":
        files.update({n:(SKILL / n).read_text() for n in ("SKILL.md","asof.py")})
    return files, gold


def hashes(files):
    return {name:digest(content) for name, content in sorted(files.items())}


def freeze():
    inputs = {}
    for split in ("d","e","f"):
        for condition in ("baseline","skill"):
            files, gold = materials(split, condition)
            inputs[split+"."+condition] = {"files":hashes(files), "gold_sha256":digest(normalized(gold))}
    return {"schedule":jobs(), "models":MODELS, "seed":SEED, "effort":"low", "timeout_seconds":TIMEOUT,
            "concurrency":WORKERS, "inputs":inputs, "wrapper":PROMPT,
            "tool_sha256":digest((HERE/"python_tool.py").read_text()), **subscription()}


def answer_text(work):
    path = work/"answer.json"
    if not path.exists() or path.is_symlink():
        return ""
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > 8192 or info.st_nlink != 1:
        return ""
    return path.read_text(errors="replace")


def invoke(job, files, gold, private):
    start = time.monotonic()
    agent = job["agent"]
    label = "-".join(str(job[k]) for k in ("agent","split","repetition","condition"))
    logdir = private/label
    logdir.mkdir()
    receipts = logdir/"calls.jsonl"
    row = {**job, "model": MODELS[agent], "started_utc":datetime.now(timezone.utc).isoformat(),
           "files":hashes(files)}
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp).resolve()/"workspace"
        client = work.parent/"client"
        work.mkdir()
        client.mkdir()
        for name, content in files.items():
            (work/name).write_text(content)
        config={"command":sys.executable, "args":["-I", str(HERE/"python_tool.py"),str(work),str(receipts)]}
        with subprocess.Popen(cli(agent, config), cwd=client, env=clean_env(), stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                              text=True, start_new_session=True) as proc:
            try:
                stdout,stderr = proc.communicate(PROMPT,timeout=TIMEOUT)
                status = "submitted" if proc.returncode == 0 else "cli_error"
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid,signal.SIGKILL)
                stdout,stderr=proc.communicate()
                status="timeout"
        (logdir/"stdout").write_text(stdout)
        (logdir/"stderr").write_text(stderr)
        if status == "submitted" and agent == "claude":
            try:
                result=json.loads(stdout)
                if result.get("is_error") or MODELS[agent] not in result.get("modelUsage",{}):
                    status="unexpected_model_or_error"
            except ValueError:
                status="invalid_cli_output"
        if status=="submitted" and agent=="codex":
            try:
                events=[json.loads(line) for line in stdout.splitlines() if line.startswith("{")]
            except ValueError:
                status="invalid_cli_output"
                events=[]
            for item in (e["item"] for e in events if "item" in e):
                typ=item.get("type")
                if typ=="mcp_tool_call" and item.get("server")=="ledger" and item.get("tool")=="python":
                    continue
                if typ not in {"agent_message","reasoning","error"}:
                    status="unexpected_tool"
                    break
        calls = []
        if receipts.exists():
            for line in receipts.read_text(errors="replace").splitlines():
                try:
                    calls.append(json.loads(line))
                except ValueError:
                    if status == "submitted":
                        status = "incomplete_receipt"
        raw = answer_text(work)
        if status=="submitted" and not raw:
            status="missing_answer"
        if status=="submitted" and not calls:
            status="no_python_receipt"
    (logdir / "answer.txt").write_text(raw)
    row.update(status=status, elapsed_seconds=round(time.monotonic()-start,2), answer=raw,
               answer_sha256=digest(raw), calls=[{"code_sha256":digest(c["code"]),"exit_status":c["status"],
                                                 "helper_functions":c.get("helper_functions",[])}
                                                  for c in calls],
               **grade(raw if status=="submitted" else "",gold))
    (logdir / "record.json").write_text(normalized(row) + "\n")
    return row


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action",choices=["smoke","run"])
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--private",type=Path,required=True)
    args=ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    args.private.mkdir(parents=True, exist_ok=True)
    private = args.private.resolve()
    if args.action=="smoke":
        print(subscription())
        files={"TASK.md":"Read counts.csv in local Python and write the JSON object with the integer sum under sum.",
               "counts.csv":"number\n17\n34\n8\n"}
        with ThreadPoolExecutor(max_workers=2) as pool:
            fs=[pool.submit(invoke,dict(agent=a,split="smoke",repetition=1,condition="baseline"),
                            files,{"sum":59},private) for a in MODELS]
            rows=[f.result() for f in fs]
        (args.out/"smoke.json").write_text(json.dumps(rows,indent=2)+"\n")
        for r in rows: print(r['agent'],r['status'],len(r['calls']),r['answer'],flush=True)
        return int(not all(r['full_pass'] for r in rows))
    proto=freeze()
    with (args.out/"protocol.json").open("x") as f: json.dump(proto,f,indent=2);f.write("\n")
    with (args.out/"trials.jsonl").open("x") as out, ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures=[]
        for job in proto["schedule"]:
            files,gold=materials(job["split"],job["condition"])
            key=job["split"]+"."+job["condition"]
            if hashes(files)!=proto["inputs"][key]["files"] or digest(normalized(gold))!=proto["inputs"][key]["gold_sha256"]:
                raise RuntimeError("Frozen input changed")
            futures.append(pool.submit(invoke,job,files,gold,private))
        for f in as_completed(futures):
            row=f.result()
            out.write(normalized(row)+"\n");out.flush()
            print(row["agent"],row["split"],row["condition"],row["status"],row["full_pass"],len(row["calls"]),flush=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
