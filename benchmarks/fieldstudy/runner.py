"""Matched, tool-free field audits using subscribed first-party CLI clients."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import inspect
import json
import math
import os
from pathlib import Path
import random
import selectors
import shutil
import signal
import subprocess
import tempfile
import time

import comparisons
import records

ROOT = Path(__file__).resolve().parent
FAMILIES = {"comparisons": comparisons.make, "records": records.make}
SKILLS = {"comparisons": "compare-experiments-fairly", "records": "trace-claims-to-evidence"}
MODELS = {"codex": "gpt-6.1-terra", "claude": "claude-sonnet-5-5"}
HEADER = ("Audit the supplied scientific records. Use only the text of this message and no tools. "
          "Apply the workflow at the end if one is supplied. Return only the requested flat JSON "
          "object, without Markdown or commentary.")
SEED = 14320261126
TIMEOUT = 240
CONCURRENCY = 4


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def normalized(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def clean_env():
    # An allowlist excludes API keys, cloud credentials, gateway URLs and model overrides.
    return {k: os.environ[k] for k in ("HOME", "USER", "PATH", "TMPDIR", "LANG") if k in os.environ}


def binary(agent):
    return shutil.which(agent) or str(Path.home() / ".local/bin" / agent)


def cli(agent, cwd):
    if agent == "claude":
        return [binary(agent), "-p", "--restricted", "--tools", "", "--strict-mcp-config",
                "--no-session-persistence", "--setting-sources", "", "--disable-slash-commands",
                "--model", MODELS[agent], "--effort", "low", "--output-format", "json"]
    return [binary(agent), "exec", "--ignore-user-config", "--ignore-rules", "--ephemeral",
            "--skip-git-repo-check", "-s", "read-only", "--disable", "apps", "--disable", "shell_tool",
            "--disable", "unified_exec", "--disable", "in_app_browser", "--disable", "skill_search",
            "--enable", "skip_host_skill_discovery", "-c", 'model_reasoning_effort="low"',
            "-m", MODELS[agent], "--json", "-o", str(cwd / "answer"), "-"]


def codex_included_usage(env, cwd):
    # Read only the subscription window. Credit balances and account identifiers stay private.
    with subprocess.Popen([binary("codex"), "app-server"], env=env, cwd=cwd, text=True,
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as proc:
        def send(message):
            proc.stdin.write(json.dumps(message) + "\n")
            proc.stdin.flush()
        try:
            send({"id": 1, "method": "initialize", "params": {
                "clientInfo": {"name": "sciskills-usage", "version": "1"}}})
            deadline = time.monotonic() + 20
            with selectors.DefaultSelector() as events:
                events.register(proc.stdout, selectors.EVENT_READ)
                while time.monotonic() < deadline and events.select(deadline - time.monotonic()):
                    line = proc.stdout.readline()
                    if not line:
                        break
                    reply = json.loads(line)
                    if reply.get("id") == 1:
                        send({"method": "initialized"})
                        send({"id": 2, "method": "account/rateLimits/read", "params": None})
                    if reply.get("id") == 2:
                        info = reply.get("result", {})
                        limits = info.get("rateLimits", {})
                        usage = [window["usedPercent"] for window in
                                 (limits.get("primary"), limits.get("secondary")) if window]
                        if not (info.get("ordinaryUsageAllowed") and usage and max(usage) < 90
                                and not limits.get("rateLimitReachedType")):
                            raise RuntimeError("Insufficient included Codex usage for the study")
                        return True
            raise RuntimeError("Could not confirm included Codex subscription usage")
        finally:
            proc.terminate()


def subscription():
    env = clean_env()
    with tempfile.TemporaryDirectory() as tmp:
        def check(args, input_text=""):
            return subprocess.run(args, input=input_text, text=True, cwd=tmp, env=env,
                                  check=True, capture_output=True, timeout=30)
        auth = check([binary("codex"), "login", "status"])
        if "Logged in using ChatGPT" not in (auth.stdout + auth.stderr):
            raise RuntimeError("Codex requires ChatGPT subscription login")
        codex_included_usage(env, tmp)
        base = [binary("claude"), "--restricted", "--setting-sources", ""]
        auth = json.loads(check([*base, "auth", "status"]).stdout)
        if not (auth.get("loggedIn") and auth.get("authMethod") == "claude.ai" and
                auth.get("apiProvider") == "firstParty" and auth.get("subscriptionType")):
            raise RuntimeError("Claude Code requires a signed-in first-party subscription")
        query = {"type": "control_request", "request_id": "usage", "request": {"subtype": "get_usage"}}
        usage = check([*base, "-p", "--tools", "", "--strict-mcp-config", "--input-format",
                       "stream-json", "--output-format", "stream-json", "--verbose"],
                      json.dumps(query) + "\n")
        replies = [json.loads(line) for line in usage.stdout.splitlines() if line.startswith("{")]
        quota = next(x["response"]["response"] for x in replies if x.get("type") == "control_response"
                     and x["response"].get("request_id") == "usage")
        if quota.get("rate_limits", {}).get("extra_usage", {}).get("is_enabled") is not False:
            raise RuntimeError("Claude Code extra usage must be off for this run")
        return {"auth": {"codex": "ChatGPT", "codex_included_usage_available": True, "claude": auth["subscriptionType"],
                         "claude_api_provider": auth["apiProvider"], "claude_extra_usage": False},
                "versions": {a: check([binary(a), "--version"]).stdout.strip() for a in MODELS}}


def prompt(family, split, condition):
    body, expected = FAMILIES[family](split)
    text = HEADER + "\n\n" + body
    if condition == "skill":
        path = ROOT.parent.parent / "skills" / SKILLS[family] / "SKILL.md"
        text += "\n\nWorkflow:\n" + path.read_text().strip()
    return text, expected


def grade(raw, expected):
    def unique(pairs):
        if len(dict(pairs)) != len(pairs):
            raise ValueError("duplicate JSON key")
        return dict(pairs)
    try:
        obj = json.loads(raw, object_pairs_hook=unique)
        if not isinstance(obj, dict):
            obj = {}
    except (ValueError, TypeError):
        obj = {}
    checks = {}
    for key, gold in expected.items():
        val = obj.get(key)
        if isinstance(gold, (int, float)) and not isinstance(gold, bool):
            checks[key] = (type(val) in (int, float) and math.isfinite(val)
                           and math.isclose(val, gold, rel_tol=0, abs_tol=1e-8))
        else:
            checks[key] = type(val) is type(gold) and val == gold
    return {"full_pass": all(checks.values()) and set(obj) == set(expected),
            "checks": checks, "exact_keys": set(obj) == set(expected)}


def schedule(phase):
    rng = random.Random(SEED)
    splits = ("dev",) if phase == "dev" else ("a", "b", "c")
    reps = (1,) if phase == "dev" else (1, 2, 3)
    pairs = [(agent, fam, sp, rep) for agent in MODELS for fam in FAMILIES for sp in splits for rep in reps]
    rng.shuffle(pairs)
    jobs = []
    for agent, fam, split, rep in pairs:
        arms = ["baseline"] if phase == "dev" else ["baseline", "skill"]
        rng.shuffle(arms)
        for arm in arms:
            jobs.append(dict(agent=agent, family=fam, split=split, repetition=rep, condition=arm))
    return jobs


def frozen_inputs(jobs):
    cases = {}
    for job in jobs:
        key = (job["family"], job["split"], job["condition"])
        if key not in cases:
            text, gold = prompt(*key)
            cases[key] = {"prompt_sha256": digest(text), "gold_sha256": digest(normalized(gold))}
    return {".".join(k): v for k, v in cases.items()}


def freeze(phase):
    jobs = schedule(phase)
    return {"phase": phase, "models": MODELS, **subscription(), "order_seed": SEED,
            "scorer_sha256": digest(inspect.getsource(grade)),
            "timeout_seconds": TIMEOUT, "concurrency": CONCURRENCY, "effort": "low",
            "jobs": jobs, "inputs": frozen_inputs(jobs)}


def execute(job):
    agent = job["agent"]
    text, expected = prompt(job["family"], job["split"], job["condition"])
    row = {**job, "model": MODELS[agent], "prompt_sha256": digest(text),
           "started_utc": datetime.now(timezone.utc).isoformat()}
    start = time.monotonic()
    raw = ""
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        with subprocess.Popen(cli(agent, cwd), cwd=cwd, env=clean_env(), text=True,
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              start_new_session=True) as proc:
            try:
                stdout, _ = proc.communicate(text, timeout=TIMEOUT)
                status = "submitted" if proc.returncode == 0 else "cli_error"
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                stdout, _ = proc.communicate()
                status = "timeout"
        if status == "submitted":
            if agent == "claude":
                output = json.loads(stdout)
                if output.get("is_error") or MODELS[agent] not in output.get("modelUsage", {}):
                    status = "unexpected_model_or_error"
                else:
                    raw = output["result"]
            else:
                events = [json.loads(line) for line in stdout.splitlines() if line.startswith("{")]
                allowed = {"agent_message", "reasoning", "error"}
                if any(e["item"].get("type") not in allowed for e in events if "item" in e):
                    status = "tool_used"
                elif (cwd / "answer").exists():
                    raw = (cwd / "answer").read_text().strip()
                else:
                    status = "missing_reply"
    row.update(elapsed_seconds=round(time.monotonic()-start, 2), status=status,
               reply=raw, reply_sha256=digest(raw), **grade(raw, expected))
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("phase", choices=["dev", "heldout"])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--luna", "--luna-dev", action="store_true", help="Separate secondary Luna cohort")
    args = ap.parse_args()
    if args.luna:
        MODELS.clear()
        MODELS["codex"] = "gpt-6-luna"
    args.out.mkdir(parents=True, exist_ok=True)
    proto = freeze(args.phase)
    protocol_path = args.out / "protocol.json"
    with protocol_path.open("x") as out:
        json.dump(proto, out, ensure_ascii=False, indent=2)
        out.write("\n")
    jobs = proto["jobs"]
    with (args.out / "trials.jsonl").open("x") as out, ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        pending = {pool.submit(execute, job): job for job in jobs}
        for future in as_completed(pending):
            row = future.result()
            key = ".".join(row[k] for k in ("family", "split", "condition"))
            if row["prompt_sha256"] != proto["inputs"][key]["prompt_sha256"]:
                raise RuntimeError("Frozen prompt changed during generation")
            out.write(normalized(row) + "\n")
            out.flush()
            print(*(row[k] for k in ("agent", "family", "split", "condition", "repetition", "status", "full_pass")), flush=True)


if __name__ == "__main__":
    main()
