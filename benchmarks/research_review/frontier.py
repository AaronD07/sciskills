"""Run frozen Terminal-Bench-Science tasks using their original images and separate verifiers."""

import argparse
import hashlib
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
from urllib.parse import urlsplit
from uuid import uuid4

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
PROVISION_TIMEOUT_SEC = 900
SOURCE_URL = "https://github.com/harbor-framework/terminal-bench-science.git"
SIDECARS = {
    "inverse-lithography": "fabricator",
    "noisy-blackbox-optimization": "public-evaluator",
}


def _docker_arch():
    arch = command(*_docker(), "info", "-f", "{{.Architecture}}").stdout.strip()
    return "arm64" if arch in ("aarch64", "arm64") else "amd64"


def platform(task):
    # Remap/TESS use native jails. The timed Lean verifier supports both architectures.
    if task["id"] in (
        "masked-spherical-remap",
        "tess-transit-vetting",
        "finite-free-stam",
    ):
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
    _require_local(_participant_context())
    root = SOURCE / task["path"]
    dockerfile = []
    if role in ("environment", "tests"):
        context = root / role
    elif role == SIDECARS.get(task["id"]):
        if role == "fabricator":
            context = root / "environment"
            dockerfile = ["-f", str(context / "fabricator/Dockerfile")]
        else:
            context = root / "environment/public_evaluator"
    else:
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
            *dockerfile,
            str(context),
            timeout=task["config"]["environment"].get("build_timeout_sec", 1800) + 120,
            check=False,
        )
        if run.returncode:
            raise RuntimeError((run.stderr + run.stdout)[-1800:])
    return command("docker", "image", "inspect", "-f", "{{.Id}}", tag).stdout.strip()


def _auxiliary_container(context, *options):
    """Keep an identity for cleanup if Docker never returns the cold container ID."""
    name = "sciskills-" + uuid4().hex
    try:
        return command(
            *_docker(context),
            "run",
            "--name",
            name,
            *options,
            timeout=PROVISION_TIMEOUT_SEC,
        )
    except BaseException:
        stop(name, context=context)
        raise


def _start_sidecar(task, main, service, image_id, *, context):
    # The upstream service reaches only the isolated main container's loopback.
    # Mount, PID and filesystem namespaces stay separate.
    options = []
    service_command = []
    if service == "public-evaluator":
        options = [
            "--pids-limit",
            "128",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=128m",
            "--cap-drop",
            "ALL",
            "--cap-add",
            "KILL",
            "--cap-add",
            "SETGID",
            "--cap-add",
            "SETUID",
            "--security-opt",
            "no-new-privileges:true",
        ]
        service_command = ["python", "/srv/server.py"]
    _auxiliary_container(
        context,
        "-d",
        "--init",
        "--network",
        "container:" + main,
        "--platform",
        platform(task),
        "--cpus",
        "1" if service == "fabricator" else "4",
        "--memory",
        "4096m",
        "--label",
        "sciskills.sidecar-for=" + main,
        *options,
        image_id,
        *service_command,
    )
    check = (
        "import urllib.request; "
        f"urllib.request.urlopen('http://{service}:8080/health', timeout=2).read()"
    )
    for _ in range(40):
        if not _root_exec(
            main, "python3", "-c", check, context=context, check=False
        ).returncode:
            return
        time.sleep(1)
    raise RuntimeError(f"Upstream sidecar {service} did not become healthy")


def _require_local(context):
    def check(endpoint):
        parsed = urlsplit(endpoint)
        if parsed.scheme != "unix" or parsed.netloc or not parsed.path.startswith("/"):
            raise RuntimeError(
                "Research trials require a local Unix-socket Docker endpoint"
            )

    if ambient := os.environ.get("DOCKER_HOST"):
        check(ambient)
    endpoint = command(
        "docker",
        "context",
        "inspect",
        context,
        "--format",
        "{{.Endpoints.docker.Host}}",
    ).stdout.strip()
    check(endpoint)


def _docker(context=None):
    context = context or _participant_context()
    _require_local(context)
    return ["docker", "--context", context]


def _participant_context():
    return os.environ.get("DOCKER_CONTEXT") or _default_context()


def _default_context():
    return command("docker", "context", "show").stdout.strip()


def _engine_id(context):
    ident = command(*_docker(context), "info", "-f", "{{.ID}}").stdout.strip()
    if not ident:
        raise RuntimeError(f"Docker context {context} has no engine ID")
    return ident


def _sync_image(context, image_id, tag):
    """Copy the unchanged local image to an optional second local verifier engine."""
    source = _docker()
    docker = _docker(context)
    if not command(*docker, "image", "inspect", image_id, check=False).returncode:
        return
    with tempfile.TemporaryDirectory() as folder:
        archive = str(Path(folder) / "image.tar")
        if (
            command(*source, "image", "inspect", "-f", "{{.Id}}", tag).stdout.strip()
            != image_id
        ):
            raise RuntimeError(
                "The source image tag changed before the verifier transfer"
            )
        command(*source, "image", "save", "-o", archive, tag, timeout=1200)
        command(*docker, "image", "load", "-i", archive, timeout=1200)
    target_id = command(
        *docker, "image", "inspect", "-f", "{{.Id}}", tag
    ).stdout.strip()
    if target_id != image_id:
        raise RuntimeError(
            f"Image on verifier context differs from {image_id}: {target_id}"
        )


def start(
    task,
    snapshot=None,
    *,
    verifier=False,
    artifacts_only=False,
    context=None,
    image_id=None,
    sidecar_image=None,
):
    role = "tests" if verifier else "environment"
    cfg = dict(task["config"]["environment"])
    if verifier:
        cfg.update(task["config"]["verifier"].get("environment", {}))
    control = _read_control(task)
    service = None if verifier or artifacts_only else SIDECARS.get(task["id"])
    if snapshot and service:
        raise ValueError(
            "This development task has live instrument state and cannot be forked for a review"
        )
    hosts = ["--add-host", service + ":127.0.0.1"] if service else []
    img = (
        snapshot
        or image_id
        or (control.get(role + "_image") if control.get("ready") else None)
        or image(task, role)
    )
    context = context or _participant_context()
    docker = _docker(context)
    name = f"sciskills-{uuid4().hex}"
    main = name
    try:
        # A large image may need several minutes to unpack before the study starts.
        run = command(
            *docker,
            "run",
            "-d",
            "--name",
            name,
            "--platform",
            platform(task),
            "--label",
            "sciskills.study=research-review",
            "--label",
            "sciskills.task=" + task["id"],
            "--network",
            "none",
            *hosts,
            "--cpus",
            str(cfg.get("cpus", 1)),
            "--memory",
            f"{int(cfg['memory_mb'])}m",
            "--entrypoint",
            "/bin/sh",
            img,
            "-c",
            "exec sleep infinity",
            timeout=PROVISION_TIMEOUT_SEC,
        )
        main = run.stdout.strip()
        if service:
            service_image = (
                sidecar_image or control.get("sidecar_image") or image(task, service)
            )
            _start_sidecar(task, main, service, service_image, context=context)
    except BaseException:
        stop(main, context=context)
        raise
    return main


def stop(container, *, context=None):
    docker = _docker(context)
    services = command(
        *docker, "ps", "-aq", "--filter", "label=sciskills.sidecar-for=" + container
    ).stdout.split()
    # Remove dependants first; Docker can otherwise reject removal of their namespace owner.
    for ident in [*services, container]:
        for attempt in range(3):
            result = command(*docker, "rm", "-f", ident, check=False)
            if not result.returncode or "No such container" in result.stderr:
                break
            if attempt == 2:
                raise RuntimeError(
                    f"Could not remove container {ident}: {result.stderr.strip()}"
                )
            time.sleep(1)


@contextmanager
def temporary_container(
    task,
    snapshot_id=None,
    *,
    verifier=False,
    artifacts_only=False,
    context=None,
    image_id=None,
    sidecar_image=None,
):
    context = context or _participant_context()
    container = start(
        task,
        snapshot_id,
        verifier=verifier,
        artifacts_only=artifacts_only,
        context=context,
        image_id=image_id,
        sidecar_image=sidecar_image,
    )
    try:
        yield container
    finally:
        stop(container, context=context)


def snapshot(container):
    return command(*_docker(), "commit", container, timeout=600).stdout.strip()


def _root_exec(container, *cmd, context=None, **kwargs):
    return command(*_docker(context), "exec", "--user", "0", container, *cmd, **kwargs)


def _transfer(source, target, path, *, context=None):
    """Copy one declared regular file or tree without following submitted links on the host."""
    source_engine = _docker()
    target_engine = _docker(context)
    logical = PurePosixPath(path)
    if not logical.is_absolute() or ".." in logical.parts or len(logical.parts) < 2:
        raise ValueError(f"Invalid upstream artifact path: {path}")
    if _root_exec(source, "test", "-e", str(logical), check=False).returncode:
        return False
    with tempfile.TemporaryFile(buffering=0) as archive:
        result = subprocess.run(
            [*source_engine, "cp", f"{source}:{logical}", "-"],
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
        _root_exec(target, "mkdir", "-p", str(logical.parent), context=context)
        subprocess.run(
            [*target_engine, "cp", "-", f"{target}:{logical.parent}"],
            stdin=archive,
            capture_output=True,
            timeout=300,
            check=True,
        )
    if _root_exec(
        target, "test", "-e", str(logical), check=False, context=context
    ).returncode:
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


def _evaluate(task, source, *, context=None, image_id=None):
    with temporary_container(
        task, verifier=True, context=context, image_id=image_id
    ) as target:

        def execute(*args, **kwargs):
            return _root_exec(target, *args, context=context, **kwargs)

        execute("mkdir", "-p", "/logs/verifier", "/logs/artifacts")
        missing = []
        for path in _submitted_paths(task):
            try:
                if not _transfer(source, target, path, context=context):
                    missing.append(path)
            except ValueError as err:
                return {
                    "status": "unsupported_artifact",
                    "correct": None,
                    "reward": None,
                    "error": str(err),
                }
        try:
            run = execute(
                "bash",
                "/tests/test.sh",
                timeout=task["config"]["verifier"]["timeout_sec"],
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {"status": "verifier_timeout", "correct": None, "reward": None}
        reward_file = execute("cat", "/logs/verifier/reward.txt", check=False)
        outcome = {
            "exit": run.returncode,
            "missing": missing,
            "verifier_tail": (run.stdout + run.stderr)[-2200:],
        }
        failures = _pytest_failures(run.stdout + "\n" + run.stderr)
        if failures:
            outcome["private_pytest_failures"] = failures
        events = execute("cat", "/sys/fs/cgroup/memory.events", check=False).stdout
        oom = re.search(r"^oom_kill ([1-9]\d*)$", events, re.MULTILINE)
        killed = re.search(r"line \d+:\s+\d+ Killed\s+", run.stderr)
        if oom or killed or run.returncode == 137:
            return {
                **outcome,
                "status": "verifier_killed",
                "correct": None,
                "reward": None,
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
        report = execute("cat", "/logs/verifier/ctrf.json", check=False)
        if not report.returncode:
            try:
                records = json.loads(report.stdout)["results"]["tests"]
                outcome["checks"] = dict(Counter(t["status"] for t in records))
            except (ValueError, KeyError, TypeError):
                pass
        if task["id"] == "noisy-blackbox-optimization":
            metrics = _blackbox_metrics(execute)
            if metrics:
                outcome["private_scientific_metrics"] = metrics
        return {**outcome, "status": "graded", "correct": reward == 1, "reward": reward}


def _pytest_failures(output):
    """Keep early failure assertions externally to the participant and published results."""
    failures = []
    in_failures = False
    case = None
    for line in output.splitlines():
        if line.startswith("==="):
            if re.fullmatch(r"=+ FAILURES =+", line.rstrip()):
                in_failures = True
            elif in_failures:
                break
        elif in_failures:
            header = re.fullmatch(r"_+ (.+?) _+", line.rstrip())
            if header:
                if len(failures) == 4:
                    break
                case = {
                    "test": header[1].encode()[:160].decode(errors="ignore"),
                    "assertions": [],
                }
            elif line.startswith("---"):
                # Pytest can echo arbitrary submitted stdout/stderr after the assertion.
                case = None
            elif case is not None and re.match(r"^E[ \t]+\S", line):
                assertions = case["assertions"]
                if not assertions:
                    failures.append(case)
                if len(assertions) < 6:
                    assertions.append(
                        line[1:].lstrip().encode()[:384].decode(errors="ignore")
                    )
    return failures


# This optional verifier report includes hidden per-problem records. Select only the
# documented aggregate scalar fields *inside* the isolated verifier.
_BLACKBOX_FIELDS = (
    "score_diff",
    "pass_score_diff",
    "agent_score",
    "baseline_score",
    "num_problems",
    "invalid_submission",
)
_BLACKBOX_READER = """
import json, math, sys
from pathlib import Path
p = Path("/logs/verifier/report.json")
if p.is_file() and not p.is_symlink() and p.stat().st_size <= 4 * 1024 * 1024:
    data = json.loads(p.read_bytes())
    selected = {k: data[k] for k in sys.argv[1:] if type(data.get(k)) in (bool, int, float)
                and math.isfinite(data[k])}
    print(json.dumps(selected, allow_nan=False))
"""


def _blackbox_metrics(execute):
    try:
        run = execute(
            "python3",
            "-I",
            "-c",
            _BLACKBOX_READER,
            *_BLACKBOX_FIELDS,
            check=False,
            timeout=15,
        )
        if run.returncode or not run.stdout.strip():
            return {}
        values = json.loads(run.stdout)
        if not isinstance(values, dict):
            return {}
        return {
            k: v
            for k, v in values.items()
            if k in _BLACKBOX_FIELDS
            and type(v) in (bool, int, float)
            and math.isfinite(v)
        }
    except (OSError, subprocess.SubprocessError, ValueError, OverflowError):
        # An absent or malformed optional diagnostic cannot change the upstream grade.
        return {}


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
    receipt = _read_control(task)
    if not ready(task):
        raise RuntimeError(
            "Draft grading requires matching participant and verifier control receipts"
        )
    with temporary_container(task, snapshot_id, artifacts_only=True) as source:
        return _evaluate(
            task,
            source,
            context=receipt["verifier_context"],
            image_id=receipt["tests_image"],
        )


def preflight(task):
    """No upstream references or grader output are added to participant snapshots."""
    record = {
        "platform": platform(task),
        "task": task["id"],
        "phase": task["phase"],
        "commit": MANIFEST["commit"],
        "ready": False,
    }
    participant = _participant_context()
    context = os.environ.get("SCISKILLS_TBS_VERIFIER_CONTEXT") or participant
    record.update(participant_context=participant, verifier_context=context)
    stage = "image_build"
    try:
        record.update(
            participant_engine=_engine_id(participant),
            verifier_engine=_engine_id(context),
        )
        for role in ("environment", "tests"):
            record[role + "_image"] = build(task, role)
        if context != participant:
            _sync_image(context, record["tests_image"], image(task, "tests"))
        if service := SIDECARS.get(task["id"]):
            record["sidecar_image"] = build(task, service)
        stage = "negative_control"
        with temporary_container(
            task,
            image_id=record["environment_image"],
            sidecar_image=record.get("sidecar_image"),
        ) as src:
            record["negative"] = _evaluate(
                task, src, context=context, image_id=record["tests_image"]
            )
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
            record["positive"] = _evaluate(
                task, src, context=context, image_id=record["tests_image"]
            )
            record["ready"] = record["positive"]["correct"] is True
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        record["error"] = str(exc)[-2200:]
    record["status"] = "verified" if record["ready"] else "unqualified_" + stage
    return _write_control(task, record)


def _scoped_receipt(task, participant):
    key = hashlib.sha256(participant.encode()).hexdigest()[:16]
    return STATE / "contexts" / key / (task["id"] + ".json")


def _save_receipt(path, record):
    path.parent.mkdir(exist_ok=True, parents=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as out:
        json.dump(record, out, sort_keys=True, indent=2)
        out.write("\n")
    Path(out.name).replace(path)


def _write_control(task, record):
    record["timestamp"] = int(time.time())
    participant = record["participant_context"]
    _save_receipt(_scoped_receipt(task, participant), record)
    main = STATE / (task["id"] + ".json")
    if not main.exists() or json.loads(main.read_text()).get("participant_context") in (
        None,
        participant,
    ):
        _save_receipt(main, record)
    return record


def _read_control(task):
    participant = _participant_context()
    for path in (_scoped_receipt(task, participant), STATE / (task["id"] + ".json")):
        if not path.exists():
            continue
        record = json.loads(path.read_text())
        if (
            record.get("participant_context") == participant
            and record.get("commit") == MANIFEST["commit"]
            and record.get("platform", "linux/amd64") == platform(task)
        ):
            return record
    return {}


def ready(task):
    return live_control(task, _read_control(task))


def live_control(task, record):
    if not (
        record.get("ready") is True
        and record.get("negative", {}).get("correct") is False
        and record.get("positive", {}).get("reward") == 1
        and (task["id"] not in SIDECARS or bool(record.get("sidecar_image")))
    ):
        return False
    try:
        engines = {
            context: _engine_id(context)
            for context in {record["participant_context"], record["verifier_context"]}
        }
        return (
            record.get("participant_engine") == engines[record["participant_context"]]
            and record.get("verifier_engine") == engines[record["verifier_context"]]
        )
    except (KeyError, RuntimeError, subprocess.SubprocessError):
        return False


def available_memory_mib(task):
    """Read the participant engine's system-wide reclaimable memory before admission."""
    context = _participant_context()
    receipt = _read_control(task)
    img = receipt.get("environment_image") or image(task, "environment")
    probe = _auxiliary_container(
        context,
        "--rm",
        "--network",
        "none",
        "--platform",
        platform(task),
        "--cap-drop",
        "ALL",
        "--read-only",
        "--entrypoint",
        "/bin/cat",
        img,
        "/proc/meminfo",
    )
    match = re.search(r"^MemAvailable:\s+(\d+) kB$", probe.stdout, re.MULTILINE)
    if not match:
        raise RuntimeError("Participant engine did not report MemAvailable")
    return int(match.group(1)) // 1024


def control_summary(selected):
    """Publish eligibility and image provenance without verifier messages or answer keys."""
    summary = []
    for task in selected:
        record = _read_control(task)
        row = {
            "task": task["id"],
            "phase": task["phase"],
            "status": record.get("status")
            or ("verified" if record.get("ready") else "pending"),
        }
        for key in (
            "environment_image",
            "tests_image",
            "sidecar_image",
            "participant_context",
            "participant_engine",
            "verifier_context",
            "verifier_engine",
            "timestamp",
        ):
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
