"""Run a single subscribed draft or review in a new tool-isolated workspace."""

import json
import os
from pathlib import Path, PurePosixPath
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time

HERE = Path(__file__).resolve().parent
LEDGER = HERE.parent / "ledger-replay"
MODELS = {"luna": "gpt-6-luna", "terra": "gpt-6.1-terra", "sonnet": "claude-sonnet-5-5"}
TIMEOUT = 240
MAX_ARTIFACT_BYTES = 8 * 1024 * 1024
MAX_FILES = 512
MAX_LOG_BYTES = 32 * 1024 * 1024
COMMON = (
    "Use only the local ledger Python tool. Read TASK.md and the supplied files in the "
    "tool's current directory. The filesystem persists between calls. Write the artifact "
    "requested by TASK.md there. If SKILL.md is provided, read and apply it."
)
PROMPTS = {
    "draft": "Complete the task. " + COMMON,
    "review": (
        "Review your earlier work against the original request and source materials. "
        "Keep or revise the submission as warranted. Complete any missing submission. "
        "PRIOR_WORK.json contains the earlier Python calls and PRIOR_REPLY.txt the final message. If any original input files "
        "were changed, copies are under original_packet/. " + COMMON
    ),
}
_auth_lock = threading.Lock()
_auth = None


def _environment():
    return {
        k: os.environ[k]
        for k in ("HOME", "USER", "PATH", "TMPDIR", "LANG")
        if k in os.environ
    }


def _helper():
    # Each isolated helper gets its own ledger model mapping and legacy module names.
    sys.path.insert(0, str(LEDGER))
    import study

    if sys.argv[1] == "authenticate":
        print(json.dumps(study.subscription()))
        return
    model, work, receipts = sys.argv[2:]
    agent = "claude" if model == "sonnet" else "codex"
    study.MODELS[agent] = MODELS[model]
    config = {
        "command": sys.executable,
        "args": ["-I", str(LEDGER / "python_tool.py"), work, receipts],
    }
    cmd = study.cli(agent, config)
    os.execve(cmd[0], cmd, study.clean_env())


def authenticate():
    """Check both subscription identities, included Codex usage, and Claude extra usage."""
    global _auth
    with _auth_lock:
        with tempfile.TemporaryDirectory() as tmp:
            verified = subprocess.run(
                [sys.executable, "-I", str(HERE / "runner.py"), "authenticate"],
                cwd=tmp,
                env=_environment(),
                capture_output=True,
                text=True,
                check=True,
                timeout=150,
            )
        _auth = json.loads(verified.stdout)
        return _auth


def _safe_name(name):
    path = PurePosixPath(name)
    if path.is_absolute() or not path.parts or ".." in path.parts or str(path) != name:
        raise ValueError("Invalid relative artifact name")
    return name


def _collect(work, files):
    """Snapshot regular UTF-8 artifacts without following links or reading special files."""
    changed = {}
    seen = set()
    total = 0
    count = 0
    for directory, dirs, names in os.walk(work, followlinks=False):
        folder = Path(directory)
        if any((folder / d).is_symlink() for d in dirs):
            raise ValueError("Unreplayable workspace directory link")
        for filename in sorted(names):
            path = folder / filename
            name = path.relative_to(work).as_posix()
            seen.add(name)
            count += 1
            info = path.lstat()
            if (
                count > MAX_FILES
                or not stat.S_ISREG(info.st_mode)
                or info.st_nlink != 1
            ):
                raise ValueError("Unreplayable workspace entry")
            original = files.get(name)
            original_bytes = original.encode() if original is not None else None
            if info.st_size > MAX_ARTIFACT_BYTES and (
                original_bytes is None or len(original_bytes) != info.st_size
            ):
                raise ValueError("Artifact exceeds snapshot bound")
            data = path.read_bytes()
            if data != original_bytes:
                total += len(data)
                if total > MAX_ARTIFACT_BYTES:
                    raise ValueError("Artifacts exceed snapshot bound")
                changed[name] = data.decode()
    return changed, sorted(set(files) - seen)


def review_files(original, draft):
    """Rebuild the first draft exactly for either review and expose its prior computations."""
    files = dict(original)
    for name in draft["deleted"]:
        files.pop(_safe_name(name), None)
    for name, contents in draft["artifacts"].items():
        files[_safe_name(name)] = contents
    for name, contents in original.items():
        if files.get(name) != contents:
            files["original_packet/" + name] = contents
    # These names belong to the runner, not to the model. A participant cannot place
    # a skill in the control arm or replace the original task with new instructions.
    files.pop("SKILL.md", None)
    files["TASK.md"] = original["TASK.md"]
    files["PRIOR_WORK.json"] = json.dumps(draft["calls"], ensure_ascii=False, indent=2)
    files["PRIOR_REPLY.txt"] = draft.get("reply", "")
    return files


def final_reply(model, path):
    if model == "sonnet":
        return json.loads(path.read_bytes()).get("result", "")
    messages = []
    with path.open() as stream:
        for line in stream:
            event = json.loads(line)
            item = event.get("item", {})
            if (
                event.get("type") == "item.completed"
                and item.get("type") == "agent_message"
            ):
                messages.append(item.get("text", ""))
    return "\n".join(messages)


def _client_status(model, path):
    if path.stat().st_size > MAX_LOG_BYTES:
        return "oversize_transcript"
    try:
        if model == "sonnet":
            response = json.loads(path.read_bytes())
            if response.get("is_error") or MODELS[model] not in response.get(
                "modelUsage", {}
            ):
                return "unexpected_model_or_error"
        else:
            completed = False
            with path.open() as stream:
                for line in stream:
                    event = json.loads(line)
                    kind = event.get("type")
                    if kind == "turn.completed":
                        completed = True
                    item = event.get("item", {})
                    item_type = item.get("type")
                    if item_type == "mcp_tool_call" and (
                        item.get("server"),
                        item.get("tool"),
                    ) == ("ledger", "python"):
                        continue
                    if item_type not in (None, "agent_message", "reasoning", "error"):
                        return "unexpected_tool"
            if not completed:
                return "incomplete_turn"
    except (ValueError, TypeError, AttributeError):
        return "invalid_cli_output"
    return "submitted"


def _calls(path):
    if not path.exists():
        return []
    if path.stat().st_size > MAX_LOG_BYTES:
        raise ValueError("Oversize call receipts")
    calls = []
    with path.open() as stream:
        for line in stream:
            receipt = json.loads(line)
            calls.append({"code": receipt["code"], "status": receipt["status"]})
    return calls


def run_session(model, files, stage, scratch, *, client_helper=None, timeout=TIMEOUT):
    """Run one fresh model; raw provider transcripts remain in the caller's private directory."""
    if model not in MODELS or stage not in PROMPTS or "TASK.md" not in files:
        raise ValueError("Unknown model, stage, or missing task")
    if _auth is None:
        authenticate()
    scratch = Path(scratch).resolve()
    scratch.mkdir(parents=True, exist_ok=False, mode=0o700)
    stdout = scratch / "stdout"
    receipts = scratch / "calls.jsonl"
    start = time.monotonic()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        work, client = root / "workspace", root / "client"
        work.mkdir()
        client.mkdir()
        for name, content in files.items():
            path = work / _safe_name(name)
            path.parent.mkdir(exist_ok=True, parents=True)
            path.write_bytes(content.encode())
        cmd = [
            sys.executable,
            "-I",
            str(client_helper or HERE / "runner.py"),
            "client",
            model,
            str(work),
            str(receipts),
        ]
        with stdout.open("wb") as out, (scratch / "stderr").open("wb") as err:
            with subprocess.Popen(
                cmd,
                cwd=client,
                env=_environment(),
                stdin=subprocess.PIPE,
                stdout=out,
                stderr=err,
                start_new_session=True,
            ) as proc:
                try:
                    proc.communicate(PROMPTS[stage].encode(), timeout=timeout)
                    status = "submitted" if proc.returncode == 0 else "cli_error"
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.communicate()
                    status = "timeout"
        if status == "submitted":
            status = _client_status(model, stdout)
        reply = final_reply(model, stdout) if status == "submitted" else ""
        try:
            calls = _calls(receipts)
            if not calls and status == "submitted":
                status = "no_python_receipt"
        except (KeyError, ValueError, TypeError):
            calls = []
            status = "invalid_receipt"
        try:
            artifacts, deleted = _collect(work, files)
        except (OSError, ValueError):
            artifacts, deleted = {}, []
            status = "unreplayable_workspace"
    return {
        "status": status,
        "elapsed_seconds": round(time.monotonic() - start, 2),
        "model": MODELS[model],
        "reply": reply,
        "calls": calls,
        "artifacts": artifacts,
        "deleted": deleted,
    }


if __name__ == "__main__":
    _helper()
