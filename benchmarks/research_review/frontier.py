"""Run frozen Terminal-Bench-Science tasks using their original images and separate verifiers."""

import argparse
from collections import Counter
from contextlib import contextmanager
from functools import lru_cache
import json
import math
import os
import re
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import tempfile
import time
import tomllib

HERE = Path(__file__).resolve().parent
MANIFEST = json.loads((HERE / "frontier_manifest.json").read_text())
SOURCE = Path(
    os.environ.get(
        "SCISKILLS_TBS_SOURCE",
        str(Path.home() / ".cache/sciskills/terminal-bench-science-v01"),
    )
)
STATE = Path(
    os.environ.get(
        "SCISKILLS_TBS_STATE",
        str(HERE.parents[1] / "benchmark-runs/research-review/frontier-controls"),
    )
)
SOURCE_URL = "https://github.com/harbor-framework/terminal-bench-science.git"


@lru_cache(maxsize=1)
def _docker_arch():
    arch = command("docker", "info", "-f", "{{.Architecture}}").stdout.strip()
    return "arm64" if arch in ("aarch64", "arm64") else "amd64"


def platform(task):
    # These upstream tests execute native seccomp and chroot helpers inside the verifier.
    if task["id"] in ("masked-spherical-remap", "tess-transit-vetting"):
        return "linux/" + _docker_arch()
    return "linux/amd64"


def command(*args, timeout=120, check=True):
    return subprocess.run(
        args,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=check,
    )


def fetch():
    if not (SOURCE / ".git").exists():
        SOURCE.parent.mkdir(parents=True, exist_ok=True)
        command(
            "git",
            "clone",
            "--filter=blob:none",
            "--sparse",
            "--branch",
            MANIFEST["version"],
            "--depth",
            "1",
            SOURCE_URL,
            str(SOURCE),
            timeout=300,
        )
    if (
        command("git", "-C", str(SOURCE), "rev-parse", "HEAD").stdout.strip()
        != MANIFEST["commit"]
    ):
        raise RuntimeError("Configured TBS source has a different commit")
    paths = [entry["path"] for entry in MANIFEST["tasks"]]
    if any(not (SOURCE / path / "task.toml").is_file() for path in paths):
        command("git", "-C", str(SOURCE), "sparse-checkout", "add", *paths, timeout=900)


@lru_cache(maxsize=1)
def _catalog():
    fetch()
    result = []
    for entry in MANIFEST["tasks"]:
        root = SOURCE / entry["path"]
        tree = command(
            "git", "-C", str(SOURCE), "rev-parse", "HEAD:" + entry["path"]
        ).stdout.strip()
        changed = command(
            "git",
            "-C",
            str(SOURCE),
            "status",
            "--porcelain",
            "--untracked-files=all",
            "--",
            entry["path"],
        ).stdout.strip()
        if tree != entry["git_tree"] or changed:
            raise RuntimeError(f"Unverified benchmark source at {root}")
        config = tomllib.loads((root / "task.toml").read_text())
        if config["verifier"]["environment_mode"] != "separate":
            raise RuntimeError(f"Task requires a separate verifier: {root.name}")
        result.append(
            {
                **entry,
                "prompt": (root / "instruction.md").read_text(),
                "agent_timeout_sec": int(config["agent"]["timeout_sec"]),
                "config": config,
            }
        )
    return result


def tasks(phase):
    if phase not in ("dev", "holdout"):
        raise ValueError("Expected dev or holdout")
    return [row for row in _catalog() if row["phase"] == phase]


def image(task, role):
    arch = platform(task).split("/")[-1]
    suffix = "" if arch == "amd64" else "-" + arch
    return f"sciskills-tbs01-{task['id']}:{role}{suffix}"


def build(task, role):
    context = SOURCE / task["path"] / role
    if role not in ("environment", "tests"):
        raise ValueError(role)
    tag = image(task, role)
    if command("docker", "image", "inspect", tag, check=False).returncode:
        run = command(
            "docker",
            "build",
            "--platform",
            platform(task),
            "-t",
            tag,
            str(context),
            timeout=task["config"]["environment"].get("build_timeout_sec", 1800) + 120,
            check=False,
        )
        if run.returncode:
            raise RuntimeError((run.stderr + run.stdout)[-1800:])
    return command("docker", "image", "inspect", "-f", "{{.Id}}", tag).stdout.strip()


def start(task, snapshot=None, *, verifier=False):
    role = "tests" if verifier else "environment"
    cfg = dict(task["config"]["environment"])
    if verifier:
        cfg.update(task["config"]["verifier"].get("environment", {}))
    control = _read_control(task)
    img = (
        snapshot
        or (control.get(role + "_image") if control.get("ready") else None)
        or image(task, role)
    )
    run = command(
        "docker",
        "run",
        "-d",
        "--platform",
        platform(task),
        "--label",
        "sciskills.study=research-review",
        "--label",
        "sciskills.task=" + task["id"],
        "--network",
        "none",
        "--cpus",
        str(cfg.get("cpus", 1)),
        "--memory",
        f"{int(cfg['memory_mb'])}m",
        "--entrypoint",
        "/bin/sh",
        img,
        "-c",
        "exec sleep infinity",
    )
    return run.stdout.strip()


def stop(container):
    command("docker", "rm", "-f", container, check=False)


@contextmanager
def temporary_container(task, snapshot_id=None, *, verifier=False):
    container = start(task, snapshot_id, verifier=verifier)
    try:
        yield container
    finally:
        stop(container)


def snapshot(container):
    return command("docker", "commit", container, timeout=600).stdout.strip()


def _root_exec(container, *cmd, **kwargs):
    return command("docker", "exec", "--user", "0", container, *cmd, **kwargs)


def _transfer(source, target, path):
    """Copy one declared regular file or tree without following submitted links on the host."""
    logical = PurePosixPath(path)
    if not logical.is_absolute() or ".." in logical.parts or len(logical.parts) < 2:
        raise ValueError(f"Invalid upstream artifact path: {path}")
    if _root_exec(source, "test", "-e", str(logical), check=False).returncode:
        return False
    with tempfile.TemporaryFile(buffering=0) as archive:
        result = subprocess.run(
            ["docker", "cp", f"{source}:{logical}", "-"],
            stdout=archive,
            stderr=subprocess.PIPE,
            timeout=300,
        )
        if result.returncode:
            raise RuntimeError("Could not read submitted artifact " + str(logical))
        archive.seek(0)
        with tarfile.open(fileobj=archive, mode="r:") as packed:
            for member in packed:
                name = PurePosixPath(member.name)
                if (
                    name.is_absolute()
                    or ".." in name.parts
                    or not name.parts
                    or name.parts[0] != logical.name
                    or not (member.isfile() or member.isdir())
                    or member.mode & 0o7000
                ):
                    raise ValueError(
                        "Unsupported submitted archive member: " + member.name
                    )
        archive.seek(0)
        _root_exec(target, "mkdir", "-p", str(logical.parent))
        subprocess.run(
            ["docker", "cp", "-", f"{target}:{logical.parent}"],
            stdin=archive,
            capture_output=True,
            timeout=300,
            check=True,
        )
    if _root_exec(target, "test", "-e", str(logical), check=False).returncode:
        raise RuntimeError(
            "Verifier did not receive submitted artifact " + str(logical)
        )
    return True


def _submitted_paths(task):
    for entry in task["config"]["artifacts"]:
        if isinstance(entry, str):
            yield entry
        elif entry.get("source") != "/logs/artifacts" or entry.get("exclude") != ["*"]:
            raise ValueError(f"Unsupported artifact mapping: {entry}")


def _evaluate(task, source):
    with temporary_container(task, verifier=True) as target:
        _root_exec(target, "mkdir", "-p", "/logs/verifier", "/logs/artifacts")
        missing = []
        for path in _submitted_paths(task):
            try:
                if not _transfer(source, target, path):
                    missing.append(path)
            except ValueError as err:
                return {
                    "status": "invalid_submission",
                    "correct": False,
                    "reward": 0,
                    "error": str(err),
                }
        try:
            run = _root_exec(
                target,
                "bash",
                "/tests/test.sh",
                timeout=task["config"]["verifier"]["timeout_sec"],
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {"status": "verifier_timeout", "correct": None, "reward": None}
        reward_file = _root_exec(
            target, "cat", "/logs/verifier/reward.txt", check=False
        )
        outcome = {
            "exit": run.returncode,
            "missing": missing,
            "verifier_tail": (run.stdout + run.stderr)[-2200:],
        }
        if reward_file.returncode:
            # Some upstream scripts begin with a silent shell test for a required
            # file. A crashing verifier, failed dependency or OOM must stay unscored.
            if (
                missing
                and run.returncode == 1
                and not (run.stdout + run.stderr).strip()
            ):
                return {
                    **outcome,
                    "status": "missing_artifact",
                    "correct": False,
                    "reward": 0,
                }
            return {
                **outcome,
                "status": "verifier_no_reward",
                "correct": None,
                "reward": None,
            }
        try:
            reward = float(reward_file.stdout.strip())
        except ValueError:
            reward = math.nan
        if not 0 <= reward <= 1:
            return {
                **outcome,
                "status": "verifier_bad_reward",
                "correct": None,
                "reward": None,
            }
        pytest_counts = _pytest_counts(run.stdout)
        if pytest_counts:
            outcome["pytest_outcomes"] = pytest_counts
        report = _root_exec(target, "cat", "/logs/verifier/ctrf.json", check=False)
        if not report.returncode:
            try:
                records = json.loads(report.stdout)["results"]["tests"]
                outcome["checks"] = dict(Counter(t["status"] for t in records))
            except (ValueError, KeyError, TypeError):
                pass
        return {**outcome, "status": "graded", "correct": reward == 1, "reward": reward}


def _pytest_counts(output):
    """Keep parameterized pytest counts distinct from the grouped CTRF check names."""
    for line in reversed(output.splitlines()):
        if line.startswith("==") and " in " in line and line.endswith("=="):
            matches = re.findall(
                r"(\d+) (passed|failed|errors?|skipped|xfailed|xpassed)\b", line
            )
            if matches:
                return {label: int(count) for count, label in matches}
    return {}


def grade(task, snapshot_id):
    with temporary_container(task, snapshot_id) as source:
        return _evaluate(task, source)


def preflight(task):
    """No upstream references or grader output are added to participant snapshots."""
    record = {
        "platform": platform(task),
        "task": task["id"],
        "phase": task["phase"],
        "commit": MANIFEST["commit"],
        "ready": False,
    }
    stage = "image_build"
    try:
        for role in ("environment", "tests"):
            record[role + "_image"] = build(task, role)
        stage = "negative_control"
        with temporary_container(task) as src:
            record["negative"] = _evaluate(task, src)
            if record["negative"]["correct"] is not False:
                raise RuntimeError(
                    "Baseline did not produce a verified negative control"
                )
            stage = "reference_solution"
            command(
                "docker",
                "cp",
                str(SOURCE / task["path"] / "solution"),
                f"{src}:/solution",
            )
            run = _root_exec(
                src,
                "bash",
                "/solution/solve.sh",
                timeout=task["agent_timeout_sec"],
                check=False,
            )
            if run.returncode:
                raise RuntimeError(
                    "Official reference failed: " + (run.stdout + run.stderr)[-1700:]
                )
            stage = "positive_control"
            record["positive"] = _evaluate(task, src)
            record["ready"] = record["positive"]["correct"] is True
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        record["error"] = str(exc)[-2200:]
    record["status"] = "verified" if record["ready"] else "unqualified_" + stage
    return _write_control(task, record)


def _write_control(task, record):
    record["timestamp"] = int(time.time())
    STATE.mkdir(exist_ok=True, parents=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=STATE, delete=False) as out:
        json.dump(record, out, sort_keys=True, indent=2)
        out.write("\n")
    Path(out.name).replace(STATE / (task["id"] + ".json"))
    return record


def _read_control(task):
    path = STATE / (task["id"] + ".json")
    if not path.exists():
        return {}
    record = json.loads(path.read_text())
    if record.get("commit") != MANIFEST["commit"] or record.get(
        "platform", "linux/amd64"
    ) != platform(task):
        return {}
    return record


def ready(task):
    record = _read_control(task)
    return (
        record.get("ready") is True
        and record.get("negative", {}).get("correct") is False
        and record.get("positive", {}).get("reward") == 1
    )


def control_summary(selected):
    """Publish eligibility and image provenance without verifier messages or answer keys."""
    summary = []
    for task in selected:
        record = _read_control(task)
        row = {
            "task": task["id"],
            "phase": task["phase"],
            "status": record.get("status", "verified" if ready(task) else "pending"),
        }
        for key in ("environment_image", "tests_image", "timestamp"):
            if key in record:
                row[key] = record[key]
        if record:
            row["platform"] = record.get("platform", "linux/amd64")
        for key in ("negative", "positive"):
            if key in record:
                trial = record[key]
                row[key] = {
                    field: trial[field]
                    for field in ("status", "reward", "checks")
                    if field in trial
                }
                pytest_counts = trial.get("pytest_outcomes") or _pytest_counts(
                    trial.get("verifier_tail", "")
                )
                if pytest_counts:
                    row[key]["pytest_outcomes"] = pytest_counts
        summary.append(row)
    return {
        "version": MANIFEST["version"],
        "commit": MANIFEST["commit"],
        "tasks": summary,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("operation", choices=("list", "preflight", "status"))
    p.add_argument("--phase", choices=("dev", "holdout", "all"), default="dev")
    p.add_argument("--task", action="append")
    args = p.parse_args()
    phases = ("dev", "holdout") if args.phase == "all" else (args.phase,)
    selected = [
        row
        for phase in phases
        for row in tasks(phase)
        if not args.task or row["id"] in args.task
    ]
    if args.operation == "status":
        print(json.dumps(control_summary(selected), indent=2))
        raise SystemExit
    for row in selected:
        if args.operation == "list":
            print(row["id"], row["agent_timeout_sec"], ready(row))
        elif not ready(row):
            res = preflight(row)
            print(
                row["id"],
                "ready" if res["ready"] else "failed",
                res.get("error", ""),
                flush=True,
            )
