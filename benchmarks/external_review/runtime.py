"""Subscription client and isolated, scientific-Python MCP tool for public tasks."""

import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "ledger-replay"))
import python_tool
import study

DEPENDENCIES = Path("/private/tmp/sciskills-external-python-314-v1")
MODELS = {"sonnet": "claude-sonnet-5-5", "luna": "gpt-6-luna", "terra": "gpt-6.1-terra"}


def limits():
    resource.setrlimit(resource.RLIMIT_CPU, (35, 40))
    resource.setrlimit(resource.RLIMIT_FSIZE, (12 << 20, 12 << 20))


def execute(code, workspace):
    workspace = Path(workspace).resolve()
    profile = python_tool.profile(workspace)
    profile += f"(allow file-read-data (subpath {json.dumps(str(DEPENDENCIES))}))"
    script = (
        f"import sys,os;sys.path[:0]=[os.getcwd(),{str(DEPENDENCIES)!r}];"
        "exec(compile(sys.stdin.read(),'<agent>','exec'),{'__name__':'__main__'})"
    )
    command = ["/usr/bin/sandbox-exec", "-p", profile, python_tool.interpreter(), "-I", "-B", "-c", script]
    env = {"PATH": "/usr/bin:/bin", "HOME": str(workspace), "TMPDIR": str(workspace),
           "LC_ALL": "C", "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}
    with tempfile.TemporaryFile() as output:
        try:
            run = subprocess.run(command, input=code.encode(), stdout=output, stderr=subprocess.STDOUT,
                                 cwd=workspace, env=env, timeout=50, preexec_fn=limits)
            status = run.returncode
        except subprocess.TimeoutExpired:
            status = 124
        output.seek(0)
        return status, output.read(32000).decode(errors="replace"), []


def main(args):
    if args[0] == "tool":
        python_tool.execute = execute
        python_tool.serve(Path(args[1]).resolve(), Path(args[2]))
        return
    _, model, work, receipts = args
    agent = "claude" if model == "sonnet" else "codex"
    study.MODELS[agent] = MODELS[model]
    config = {"command": sys.executable, "args": ["-I", str(HERE / "runtime.py"), "tool", work, receipts]}
    cmd = study.cli(agent, config)
    if agent == "claude":
        cmd[cmd.index("--effort") + 1] = "medium"
    else:
        cmd[cmd.index('model_reasoning_effort="low"')] = 'model_reasoning_effort="medium"'
        cmd[-1:-1] = ["-c", 'web_search="disabled"']
    os.execve(cmd[0], cmd, study.clean_env())


if __name__ == "__main__":
    main(sys.argv[1:])
