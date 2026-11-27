"""Run the pinned, unrestricted SWE-bench-Science fallback with the published verifier.

From the repository root, list the frozen cases or check one environment with
`python -m benchmarks.research_review.swe preflight --task swe-107`. Setup
downloads hash-checked public instructions and digest-pinned Linux/amd64 images.
Dev and holdout repositories are disjoint. Task containers have no network.
The unmodified release hook extracts the binary patch; the official verifier
resets its own checkout, applies that patch and writes the binary reward. The
upstream release excludes gold patches, so readiness records only a demonstrated
negative control. Authoring and release contract:
https://github.com/OpenMOSS/SWE-bench-Science/blob/main/docs/architecture.md
"""

import argparse
from contextlib import contextmanager
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import tomllib
from urllib.request import urlopen

from . import frontier

HERE = Path(__file__).resolve().parent
MANIFEST = json.loads((HERE / "swe_manifest.json").read_text())
CACHE = Path.home() / ".cache/sciskills" / ("swe-science-" + MANIFEST["commit"][:7])
STATE = HERE.parents[1] / "benchmark-runs/research-review/swe-controls"
DOCKER_PLATFORM = "linux/amd64"
PATCH = "/logs/artifacts/model.patch"
snapshot = frontier.snapshot
stop = frontier.stop
command = frontier.command


def _source(entry, name):
    path = CACHE / entry["path"] / name
    if not path.is_file():
        url = f"https://huggingface.co/datasets/{MANIFEST['dataset']}/resolve/{MANIFEST['commit']}/{entry['path']}/{name}"
        with urlopen(url, timeout=60) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != entry["files"][name]:
            raise ValueError(f"Downloaded file failed hash check: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
            tmp.write(data)
        Path(tmp.name).replace(path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != entry["files"][name]:
        raise ValueError(f"Cached file failed hash check: {path}")
    return path


@lru_cache(maxsize=2)
def tasks(phase):
    if phase not in ("dev", "holdout"):
        raise ValueError("Expected dev or holdout")
    rows = []
    for entry in MANIFEST["tasks"]:
        if entry["phase"] != phase:
            continue
        config = tomllib.loads(_source(entry, "task.toml").read_text())
        if (
            config["environment"]["docker_image"] != entry["environment"]
            or config["verifier"]["environment"]["docker_image"] != entry["verifier"]
            or config["verifier"]["environment_mode"] != "separate"
            or config["artifacts"] != [PATCH]
        ):
            raise ValueError(f"Unexpected upstream execution contract: {entry['id']}")
        rows.append(
            {
                **entry,
                "config": config,
                "agent_timeout_sec": int(config["agent"]["timeout_sec"]),
                "prompt": _source(entry, "instruction.md").read_text(),
            }
        )
    return rows


def _pinned_image(task, role):
    image = task[role]
    if command("docker", "image", "inspect", image, check=False).returncode:
        command(
            "docker",
            "pull",
            "--platform",
            DOCKER_PLATFORM,
            image,
            timeout=1800,
        )
    return image


def start(task, snapshot=None, *, verifier=False):
    role = "verifier" if verifier else "environment"
    config = (
        task["config"]["verifier"]["environment"]
        if verifier
        else task["config"]["environment"]
    )
    image = snapshot or _pinned_image(task, role)
    return command(
        "docker",
        "run",
        "-d",
        "--platform",
        DOCKER_PLATFORM,
        "--network",
        "none",
        "--label",
        "sciskills.study=research-review",
        "--label",
        "sciskills.task=" + task["id"],
        "--cpus",
        str(config["cpus"]),
        "--memory",
        f"{config['memory_mb']}m",
        "--workdir",
        config["workdir"],
        "--entrypoint",
        "/bin/sh",
        image,
        "-c",
        "exec sleep infinity",
    ).stdout.strip()


@contextmanager
def _container(task, snapshot_id=None, *, verifier=False):
    ident = start(task, snapshot_id, verifier=verifier)
    try:
        yield ident
    finally:
        stop(ident)


def _evaluate(task, source):
    # Capture the patch with the published hook. Only this file enters a clean verifier.
    hook = _source(task, "pre_artifacts.sh")
    with hook.open("rb") as script:
        proc = subprocess.run(
            ["docker", "exec", "-i", source, "sh", "-s"],
            stdin=script,
            capture_output=True,
            timeout=300,
        )
    if proc.returncode:
        return {"status": "patch_capture_error", "correct": None, "reward": None}
    with _container(task, verifier=True) as target:
        try:
            if not frontier._transfer(source, target, PATCH):
                return {"status": "missing_patch", "correct": None, "reward": None}
        except ValueError:
            return {"status": "invalid_submission", "correct": False, "reward": 0}
        size = int(
            frontier._root_exec(target, "stat", "-c", "%s", PATCH).stdout.strip()
        )
        try:
            run = frontier._root_exec(
                target,
                "/bin/sh",
                "/tests/test.sh",
                timeout=task["config"]["verifier"]["timeout_sec"],
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {
                "status": "verifier_timeout",
                "correct": None,
                "reward": None,
                "patch_bytes": size,
            }
        raw = frontier._root_exec(
            target, "cat", "/logs/verifier/reward.txt", check=False
        )
        outcome = {"patch_bytes": size, "exit": run.returncode}
        if raw.returncode or raw.stdout.strip() not in {"0", "0.0", "1", "1.0"}:
            return {
                **outcome,
                "status": "verifier_no_binary_reward",
                "correct": None,
                "reward": None,
                "verifier_tail": (run.stdout + run.stderr)[-1600:],
            }
        reward = float(raw.stdout.strip())
        return {**outcome, "status": "graded", "correct": reward == 1, "reward": reward}


def grade(task, snapshot_id):
    with _container(task, snapshot_id) as source:
        return _evaluate(task, source)


def preflight(task):
    """Exercise upstream grading without a model. The public release omits gold patches."""
    record = {
        "task": task["id"],
        "commit": MANIFEST["commit"],
        "ready": False,
        "positive_reference": "not released upstream",
    }
    try:
        with _container(task) as source:
            record["negative"] = _evaluate(task, source)
        record["ready"] = (
            record["negative"]["correct"] is False
            and record["negative"].get("patch_bytes") == 0
        )
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        record["error"] = str(exc)[-1600:]
    STATE.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=STATE, delete=False) as tmp:
        json.dump(record, tmp, indent=2)
        tmp.write("\n")
    Path(tmp.name).replace(STATE / (task["id"] + ".json"))
    return record


def ready(task):
    path = STATE / (task["id"] + ".json")
    if not path.is_file():
        return False
    record = json.loads(path.read_text())
    return record["commit"] == MANIFEST["commit"] and record["ready"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["list", "preflight"])
    parser.add_argument("--phase", choices=["dev", "holdout"], default="dev")
    parser.add_argument("--task", action="append")
    args = parser.parse_args()
    for case in tasks(args.phase):
        if args.task and case["id"] not in args.task:
            continue
        if args.operation == "list":
            print(case["id"], case["domain"], ready(case))
        elif not ready(case):
            print(json.dumps(preflight(case)), flush=True)
