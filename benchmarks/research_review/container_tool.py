"""Expose one already-isolated scientific workspace through a single shell MCP tool."""

from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading

OUTPUT_LIMIT = 32_000


def validate_container(container):
    if not re.fullmatch(r"[0-9a-f]{64}", container):
        raise ValueError("Expected a full immutable Docker container ID")
    context = os.environ.get("DOCKER_CONTEXT")
    if context:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", context):
            raise ValueError("Invalid Docker context name")
        endpoint = subprocess.check_output(
            [
                "docker",
                "context",
                "inspect",
                context,
                "--format",
                "{{.Endpoints.docker.Host}}",
            ],
            timeout=15,
            text=True,
        ).strip()
        if not endpoint.startswith("unix:///"):
            raise ValueError("Research containers require a local Docker socket")
    info = json.loads(
        subprocess.check_output(["docker", "inspect", container], timeout=15)
    )[0]
    host = info["HostConfig"]
    if (
        not info["State"]["Running"]
        or host["NetworkMode"] != "none"
        or host["Privileged"]
        or host.get("Devices")
        or host.get("CapAdd")
        or host.get("PidMode") == "host"
        or host.get("IpcMode") == "host"
        or any(mount["Type"] != "tmpfs" for mount in info["Mounts"])
    ):
        raise ValueError(
            "Scientific tool requires a running offline container without host access"
        )
    return info["Config"]["WorkingDir"] or "/"


@contextmanager
def review_history(container, files):
    """Give one isolated reviewer its original history without consuming its prompt budget."""
    names = ("PRIOR_WORK.json", "PRIOR_REPLY.txt")
    if not all(isinstance(files.get(name), str) for name in names):
        raise ValueError("Scientific review requires both original history files")
    folder = subprocess.check_output(
        [
            "docker",
            "exec",
            container,
            "mktemp",
            "-d",
            "/tmp/sciskills-review.XXXXXXXXXX",
        ],
        timeout=30,
        text=True,
    ).strip()
    if not re.fullmatch(r"/tmp/sciskills-review\.[a-zA-Z0-9]{10}", folder):
        raise ValueError("Unexpected review context directory")
    paths = {name: folder + "/" + name for name in names}
    try:
        for name, path in paths.items():
            subprocess.run(
                [
                    "docker",
                    "exec",
                    "-i",
                    container,
                    "sh",
                    "-c",
                    'cat > "$1"',
                    "sh",
                    path,
                ],
                input=files[name].encode(),
                capture_output=True,
                timeout=120,
                check=True,
            )
        yield paths
    finally:
        # Remove only the two files we staged before the submitted work is snapshotted.
        subprocess.run(
            ["docker", "exec", container, "rm", "-f", *paths.values()],
            capture_output=True,
            timeout=30,
            check=True,
        )
        subprocess.run(
            ["docker", "exec", container, "rmdir", folder],
            capture_output=True,
            timeout=30,
            check=False,
        )


def shell(container, script, seconds):
    # The in-container deadline also applies if a host-side tool client disconnects.
    cmd = [
        "docker",
        "exec",
        container,
        "timeout",
        "-k",
        "3",
        str(seconds),
        "/bin/bash",
        "-c",
        script,
    ]
    with subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL
    ) as proc:
        captured = bytearray()
        total = 0

        def drain():
            nonlocal total
            while chunk := proc.stdout.read(65536):
                total += len(chunk)
                captured.extend(chunk[: max(0, OUTPUT_LIMIT - len(captured))])

        reader = threading.Thread(target=drain, daemon=True)
        reader.start()
        try:
            proc.wait(timeout=seconds + 10)
            status = proc.returncode
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            status = 124
        reader.join()
    output = captured.decode(errors="replace")
    if total > len(captured):
        output += f"\n[Tool output truncated after {len(captured)} of {total} bytes]"
    return status, output


def serve(container, receipts, max_seconds):
    cwd = validate_container(container)
    tool = {
        "name": "shell",
        "description": (
            f"Run Bash in the isolated scientific task container. Each call starts in "
            f"{cwd}. Files persist. Run scripts, inspect data and write the requested "
            "deliverables here. Each call returns its exit code and combined output."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "timeout_seconds": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": max_seconds,
                },
            },
            "required": ["command"],
            "additionalProperties": False,
        },
    }
    for line in sys.stdin:
        msg = json.loads(line)
        if "id" not in msg:
            continue
        method = msg["method"]
        if method == "initialize":
            result = {
                "protocolVersion": msg["params"]["protocolVersion"],
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "research-workspace", "version": "1"},
            }
        elif method == "tools/list":
            result = {"tools": [tool]}
        elif method == "tools/call" and msg.get("params", {}).get("name") == "shell":
            args = msg["params"]["arguments"]
            script = args.get("command")
            requested = args.get("timeout_seconds", max_seconds)
            if (
                isinstance(script, str)
                and type(requested) is int
                and 1 <= requested <= max_seconds
            ):
                status, output = shell(container, script, requested)
                with receipts.open("a", encoding="utf-8") as log:
                    log.write(
                        json.dumps({"code": script, "status": status, "output": output})
                        + "\n"
                    )
            else:
                status, output = 2, "Expected command string and valid timeout_seconds"
            result = {
                "isError": bool(status),
                "content": [{"type": "text", "text": f"exit {status}\n{output}"}],
            }
        elif method in ("ping", "resources/list", "prompts/list"):
            result = {} if method == "ping" else {method.split("/")[0]: []}
        else:
            print(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": msg["id"],
                        "error": {"code": -32601, "message": "Unknown method"},
                    }
                ),
                flush=True,
            )
            continue
        print(
            json.dumps({"jsonrpc": "2.0", "id": msg["id"], "result": result}),
            flush=True,
        )


if __name__ == "__main__":
    serve(sys.argv[1], Path(sys.argv[2]), int(sys.argv[3]))
