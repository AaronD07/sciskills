"""Single local Python tool accessible to both clients through MCP stdio."""
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile


def interpreter():
    configured = Path(sys.executable).resolve()
    framework = configured.parent.parent / "Resources/Python.app/Contents/MacOS/Python"
    return str(framework if framework.is_file() else configured)


def profile(workspace):
    readable = ("/System", "/usr", "/Library/Apple", "/opt/homebrew/Cellar", "/opt/homebrew/opt",
                "/private/etc", "/dev", str(workspace))
    reads = " ".join(f"(subpath {json.dumps(p)})" for p in readable)
    return f"""(version 1)
(allow default)
(deny network*)
(deny file-read-data)
(allow file-read-data (literal "/") {reads})
(deny file-write*)
(allow file-write* (subpath {json.dumps(str(workspace))}) (literal "/dev/null"))
(deny process-fork)
(deny process-exec)
(allow process-exec (literal {json.dumps(interpreter())}))
"""


def limits():
    resource.setrlimit(resource.RLIMIT_CPU, (8, 9))
    resource.setrlimit(resource.RLIMIT_FSIZE, (2 * 1024 * 1024, 2 * 1024 * 1024))


def execute(code, workspace):
    env = {"HOME": str(workspace), "TMPDIR": str(workspace), "PATH": "/usr/bin:/bin",
           "LC_ALL": "C", "PYTHONDONTWRITEBYTECODE": "1"}
    # The workspace is the only writable area. A fresh interpreter serves each call.
    with tempfile.TemporaryFile() as audit, tempfile.TemporaryFile() as output:
        # Only record entry to functions in the staged helper. The log descriptor is
        # separate from model-visible stdout and the submitted source files.
        script = f"""import os, sys
sys.path.insert(0, os.getcwd())
target = os.path.realpath('asof.py')
seen = set()
def record(frame, event, arg):
    if event == 'call' and frame.f_code.co_filename.endswith('asof.py'):
        if os.path.realpath(frame.f_code.co_filename) == target:
            name = frame.f_code.co_name
            if name not in seen:
                seen.add(name)
                os.write({audit.fileno()}, (name + chr(10)).encode())
sys.setprofile(record)
exec(compile(sys.stdin.read(), '<agent>', 'exec'), {{'__name__':'__main__'}})
"""
        cmd = ["/usr/bin/sandbox-exec", "-p", profile(workspace), interpreter(), "-I", "-B", "-c", script]
        try:
            run = subprocess.run(cmd, input=code.encode(), stdout=output, stderr=subprocess.STDOUT,
                                 env=env, cwd=workspace, timeout=12, preexec_fn=limits,
                                 pass_fds=(audit.fileno(),))
            status = run.returncode
        except subprocess.TimeoutExpired:
            status = 124
        output.seek(0)
        audit.seek(0)
        observed = audit.read(1024).decode(errors="replace").splitlines()
        return status, output.read(12000).decode("utf-8", "replace"), observed


def serve(workspace, receipts):
    tool = {"name": "python", "description": "Execute Python in a fresh interpreter. The current directory holds task files and persists between calls. Use Python to inspect files, compute, and write answer.json. Import local helper modules if present. Shell subprocesses and network are unavailable.",
            "inputSchema": {"type": "object", "properties": {"code": {"type": "string"}},
                            "required": ["code"], "additionalProperties": False}}
    for line in sys.stdin:
        msg = json.loads(line)
        if "id" not in msg:
            continue
        method = msg["method"]
        if method == "initialize":
            result = {"protocolVersion": msg["params"]["protocolVersion"], "capabilities": {"tools": {}},
                      "serverInfo": {"name": "sciskills-local-python", "version": "1.0"}}
        elif method == "tools/list":
            result = {"tools": [tool]}
        elif method == "tools/call":
            code = msg["params"]["arguments"]["code"]
            status, output, helper_functions = execute(code, workspace)
            with receipts.open("a") as log:
                log.write(json.dumps({"code": code, "status": status, "output": output, "helper_functions": helper_functions}) + "\n")
            result = {"isError": status != 0, "content": [{"type": "text", "text": f"exit {status}\n{output}"}]}
        elif method in ("ping", "resources/list", "prompts/list"):
            result = {} if method == "ping" else {method.split("/")[0]: []}
        else:
            print(json.dumps({"jsonrpc": "2.0", "id": msg["id"], "error": {
                "code": -32601, "message": "Unknown method"}}), flush=True)
            continue
        print(json.dumps({"jsonrpc": "2.0", "id": msg["id"], "result": result}), flush=True)


if __name__ == "__main__":
    serve(Path(sys.argv[1]).resolve(), Path(sys.argv[2]))
