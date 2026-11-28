"""Run a high-effort research draft or review through one subscription CLI."""

from contextlib import nullcontext
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time

HERE = Path(__file__).resolve().parent
LEDGER = HERE.parent / "ledger-replay"
sys.path.insert(0, str(HERE.parents[1]))
from benchmarks.paired_review import runner  # noqa: E402
from benchmarks.research_review import container_tool  # noqa: E402

MODELS = {
    "terra": "gpt-6.1-terra",
    "luna": "gpt-6-luna",
    "sonnet": "claude-sonnet-5-5",
    "opus": "claude-opus-5-5",
}
EFFORT = "high"

_auth_lock = threading.Lock()
_receipt = None
_checked_at = 0.0


def authenticate():
    """Check subscription identity and included usage; share receipts during a launch wave."""
    global _receipt, _checked_at
    with _auth_lock:
        if _receipt is None or time.monotonic() - _checked_at > 30:
            _receipt = runner.authenticate()
            _checked_at = time.monotonic()
        return _receipt


def _launch(model, tool, workspace, receipts, seconds, deadline=None):
    # This helper process isolates the legacy study module's imports and model overrides.
    sys.path.insert(0, str(LEDGER))
    import study

    agent = "claude" if model in ("sonnet", "opus") else "codex"
    study.MODELS[agent] = MODELS[model]
    mcp_args = (
        ["-I", str(HERE / "container_tool.py"), workspace, receipts, seconds]
        if tool == "shell"
        else ["-I", str(LEDGER / "python_tool.py"), workspace, receipts]
    )
    if tool == "shell" and deadline is not None:
        mcp_args.append(deadline)
    config = {"command": sys.executable, "args": mcp_args}
    context = os.environ.get("DOCKER_CONTEXT") if tool == "shell" else None
    if context:
        config["env"] = {"DOCKER_CONTEXT": context}
    cmd = study.cli(agent, config)
    env = study.clean_env()
    if agent == "claude":
        cmd[cmd.index("--effort") + 1] = EFFORT
        cmd[cmd.index("--allowedTools") + 1] = f"mcp__ledger__{tool}"
        env["MCP_TOOL_TIMEOUT"] = str((int(seconds) + 20) * 1000)
    else:
        if context:
            cmd[-1:-1] = [
                "-c",
                "mcp_servers.ledger.env.DOCKER_CONTEXT=" + json.dumps(context),
            ]
        if tool == "shell":
            # The client directory is disposable. The authorized research workspace
            # lives inside Docker; a read-only system instruction conflicts with its writes.
            cmd[cmd.index("read-only")] = "workspace-write"
        cmd[cmd.index('model_reasoning_effort="low"')] = (
            f'model_reasoning_effort="{EFFORT}"'
        )
        cmd[cmd.index('mcp_servers.ledger.tools.python.approval_mode="approve"')] = (
            f'mcp_servers.ledger.tools.{tool}.approval_mode="approve"'
        )
        cmd[-1:-1] = [
            "-c",
            'web_search="disabled"',
            "-c",
            f"mcp_servers.ledger.tool_timeout_sec={int(seconds) + 20}",
        ]
    os.execve(cmd[0], cmd, env)


def _prompt(files, stage, tool, history=None):
    if tool == "python":
        return runner.PROMPTS[stage]
    if set(files) - {"TASK.md", "PRIOR_WORK.json", "PRIOR_REPLY.txt", "SKILL.md"}:
        raise ValueError("Mount original science data in the task container")
    request = (
        "Use only the supplied shell tool in the isolated scientific task container. "
        "Files are writable there. Complete the original task below and leave its requested results there."
    )
    if stage == "review":
        if not history:
            raise ValueError("Scientific review requires staged history")
        request += (
            " Review your earlier work against the original request and source materials. "
            "Keep or revise it as warranted and complete missing work. "
            f"Your earlier tool calls and outputs are in {history['PRIOR_WORK.json']}. "
            f"Your earlier final reply is in {history['PRIOR_REPLY.txt']}. "
            "Consult these files as needed using the shell."
        )
    return (
        request
        + "\n\n"
        + "\n\n".join(
            f"--- {name} ---\n{files[name]}"
            for name in ("TASK.md", "SKILL.md")
            if name in files
        )
    )


def _failure(text):
    lower = text.lower()
    if any(
        term in lower
        for term in (
            "usage limit",
            "rate_limit_error",
            "rate limit reached",
            "exceeded your quota",
            "out of extra usage",
            "hit your limit",
            "429 too many requests",
        )
    ):
        return "quota_exhausted"
    if any(
        term in lower
        for term in ("not logged in", "login required", "authentication_error")
    ):
        return "authentication_error"
    if any(
        term in lower
        for term in (
            "model_not_found",
            "does not exist or you do not have access",
            "model is not supported",
            "not a valid model",
        )
    ):
        return "model_unavailable"
    return "cli_error"


def _transport_failure(message):
    text = str(message).casefold()
    return any(
        term in text
        for term in (
            "transport closed",
            "transport is closed",
            "stream disconnected before completion",
            "transport error",
        )
    )


def _result(model, tool, stdout, stderr, returncode, *, deadline=False):
    if stdout.stat().st_size > runner.MAX_LOG_BYTES:
        return "oversize_transcript", "", None
    raw = stdout.read_text(errors="replace")
    if returncode and not deadline:
        return (
            _failure(raw[-12000:] + stderr.read_text(errors="replace")[-4000:]),
            "",
            None,
        )
    try:
        if deadline:
            tail = stderr.read_text(errors="replace")[-4000:]
            failure = _failure(tail)
            if failure != "cli_error":
                return failure, "", None
            if _transport_failure(tail):
                return "tool_unavailable", "", None
        if model in ("sonnet", "opus"):
            # Claude Code normally emits its sole JSON response at natural completion.
            if deadline and not raw.strip():
                return "timeout", "", None
            response = json.loads(raw)
            if response.get("is_error") or response.get("subtype") != "success":
                return _failure(str(response.get("result", ""))), "", None
            reported = list(response.get("modelUsage", {}))
            if reported != [MODELS[model]]:
                return "model_identity_mismatch", "", reported
            return "submitted", response.get("result", ""), reported[0]
        completed = False
        started = False
        reply = ""
        observed = None
        for line in raw.splitlines():
            event = json.loads(line)
            if event.get("type") in {"turn.started", "item.started", "item.completed"}:
                started = True
            if event.get("type") in {"model.rerouted", "model/rerouted"}:
                return "model_identity_mismatch", "", None
            if event.get("type") in {
                "turn.failed",
                "turn.aborted",
                "turn.interrupted",
                "error",
            }:
                return (
                    _failure(str(event.get("error", event.get("message", "")))),
                    "",
                    None,
                )
            if event.get("model"):
                observed = event["model"]
                if observed != MODELS[model]:
                    return "model_identity_mismatch", "", observed
            if event.get("type") == "turn.completed":
                completed = True
            item = event.get("item", {})
            kind = item.get("type")
            if kind == "error":
                message = str(item.get("message", ""))
                # Codex emits this informational feature notice as an error item even
                # on successful runs. Other errors still invalidate the submission.
                if (
                    message.startswith(
                        "Under-development features enabled: skip_host_skill_discovery."
                    )
                    and "To suppress this warning" in message
                ):
                    continue
                return _failure(message), "", observed
            if kind == "mcp_tool_call" and (item.get("server"), item.get("tool")) == (
                "ledger",
                tool,
            ):
                if _transport_failure(item.get("error", "")):
                    return "tool_unavailable", "", observed
                continue
            if kind not in (None, "reasoning", "agent_message"):
                return "unexpected_tool", "", observed
            if kind == "agent_message" and event.get("type") == "item.completed":
                reply = item.get("text", "")
        status = "incomplete_turn"
        if completed:
            status = "submitted"
        elif deadline and started:
            status = "timeout"
        return status, reply, observed
    except (ValueError, TypeError, AttributeError):
        return "invalid_cli_output", "", None


def run_session(model, files, stage, scratch, *, timeout=480, container=None):
    """Run in a fresh client directory. The caller owns the isolated container and its snapshot."""
    if (
        model not in MODELS
        or stage not in runner.PROMPTS
        or "TASK.md" not in files
        or timeout < 1
    ):
        raise ValueError("Unknown client, stage, task, or budget")
    if container:
        container_tool.validate_container(container)
    auth = authenticate()
    tool = "shell" if container else "python"
    scratch = Path(scratch).resolve()
    scratch.mkdir(parents=True, exist_ok=False, mode=0o700)
    stdout, stderr, receipts = [
        scratch / p for p in ("stdout", "stderr", "calls.jsonl")
    ]
    (scratch / "subscription.json").write_text(json.dumps(auth))
    start = time.monotonic()
    reply, observed, calls, artifacts, deleted = "", None, [], {}, []
    context = (
        container_tool.review_history(container, files)
        if container and stage == "review"
        else nullcontext({})
    )
    deadline_hit = False
    cutoff_image = None
    with tempfile.TemporaryDirectory() as tmp, context as history:
        prompt = _prompt(files, stage, tool, history)
        root = Path(tmp).resolve()
        work, cli_dir = root / "task", root / "client"
        cli_dir.mkdir()
        if not container:
            work.mkdir()
            for name, content in files.items():
                path = work / runner._safe_name(name)
                path.parent.mkdir(exist_ok=True, parents=True)
                path.write_bytes(content.encode())
        cmd = [
            sys.executable,
            "-I",
            str(HERE / "client.py"),
            model,
            tool,
            container or str(work),
            str(receipts),
            str(int(timeout)),
        ]
        helper_env = runner._environment()
        if container and os.environ.get("DOCKER_CONTEXT"):
            helper_env["DOCKER_CONTEXT"] = os.environ["DOCKER_CONTEXT"]
        with stdout.open("wb") as out, stderr.open("wb") as err:
            deadline = time.monotonic() + timeout
            cmd.append(str(deadline))
            # A crash after this marker is ambiguous until the original attempt is recovered.
            (scratch / "launch-intent").touch(exist_ok=False)
            with subprocess.Popen(
                cmd,
                cwd=cli_dir,
                env=helper_env,
                stdin=subprocess.PIPE,
                stdout=out,
                stderr=err,
                start_new_session=True,
            ) as proc:
                try:
                    (scratch / "process.json").write_text(
                        json.dumps(
                            {
                                "pid": proc.pid,
                                "container": container,
                                "model": MODELS[model],
                                "deadline_monotonic": deadline,
                                "context": helper_env.get("DOCKER_CONTEXT"),
                            }
                        )
                    )
                    proc.communicate(
                        prompt.encode(), timeout=max(0, deadline - time.monotonic())
                    )
                    status, reply, observed = _result(
                        model, tool, stdout, stderr, proc.returncode
                    )
                except subprocess.TimeoutExpired:
                    # Stopping the CLI alone leaves detached Docker execs running.
                    # Capture the actual cutoff image before parsing its transcript.
                    try:
                        os.killpg(proc.pid, signal.SIGSTOP)
                    except ProcessLookupError:
                        pass

                    group_stopped = False

                    def stop_client():
                        nonlocal group_stopped
                        if not group_stopped:
                            try:
                                os.killpg(proc.pid, signal.SIGKILL)
                            except ProcessLookupError:
                                pass
                            group_stopped = True
                            proc.communicate()

                    try:
                        if container:
                            cutoff_image = container_tool.freeze_snapshot(
                                container, stop_client
                            )
                    finally:
                        stop_client()
                    deadline_hit = True
                    status, reply, observed = _result(
                        model, tool, stdout, stderr, proc.returncode, deadline=True
                    )
        try:
            if receipts.exists():
                if receipts.stat().st_size > runner.MAX_LOG_BYTES:
                    raise ValueError("Oversize receipts")
                for line in receipts.read_text().splitlines():
                    record = json.loads(line)
                    calls.append({k: record[k] for k in ("code", "status", "output")})
            if (
                status == "submitted"
                and not calls
                and any(
                    phrase in reply.lower()
                    for phrase in (
                        "transport closed",
                        "tool is unavailable",
                        "failed to start",
                    )
                )
            ):
                status = "tool_unavailable"
        except (ValueError, KeyError, TypeError):
            status = "invalid_receipt"
        if not container:
            try:
                artifacts, deleted = runner._collect(work, files)
            except (ValueError, OSError):
                status = "unreplayable_workspace"
    return {
        "status": status,
        "elapsed_seconds": round(time.monotonic() - start, 2),
        "model": MODELS[model],
        "reported_model": observed,
        "model_identity_evidence": (
            "mismatch"
            if status == "model_identity_mismatch"
            else "provider_reported"
            if observed == MODELS[model]
            else "requested_only"
        ),
        "client_deadline_reached": deadline_hit,
        "cutoff_image": cutoff_image,
        "review_context_sha256": {
            name: hashlib.sha256(files[name].encode()).hexdigest() for name in history
        },
        "effort": EFFORT,
        "subscription": auth,
        "reply": reply,
        "calls": calls,
        "artifacts": artifacts,
        "deleted": deleted,
    }


if __name__ == "__main__":
    _launch(*sys.argv[1:])
