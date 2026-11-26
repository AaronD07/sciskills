"""Inspect reproducibility evidence without executing repository code."""
import argparse
import ast
import json
import os
from pathlib import Path
import re
import shlex

try:
    import tomllib
except ImportError:  # Python 3.10; the rest of the scan still works.
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

SKIP = {".git", ".venv", "venv", "node_modules", "__pycache__", "benchmark-runs"}
PY_LOCKS = {"uv.lock", "poetry.lock", "Pipfile.lock", "requirements-lock.txt", "pylock.toml"}
NODE_LOCKS = {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "npm-shrinkwrap.json"}
LOCKS = PY_LOCKS | NODE_LOCKS | {"conda-lock.yml", "conda-lock.yaml"}
RUNTIME = {"pyproject.toml", "runtime.txt", ".python-version", "environment.yml", "environment.yaml"}
ENTROPY = {"random.seed", "random.Random", "numpy.random.seed", "numpy.random.default_rng"}
LEGACY_RNG = ENTROPY | {"np.random.seed", "np.random.default_rng", "torch.manual_seed"}
LIMITS = ("Static inspection only. Tests were not run. Lock contents, dynamic paths, "
          "runtime seed values and scientific correctness require separate checks.")


def finding(rule, where, observation, action, limit):
    return dict(rule=rule, location=where, observation=observation, action=action, limitation=limit)


def scan_python(source, path, evidence, findings):
    tree = ast.parse(source)
    # Resolve explicit imports. A syntactic match can still be shadowed at runtime.
    imports = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                first = item.name.split(".")[0]
                imports[item.asname or first] = item.name if item.asname else first
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            for item in node.names:
                imports[item.asname or item.name] = f"{node.module}.{item.name}"

    for call in (n for n in ast.walk(tree) if isinstance(n, ast.Call)):
        spelling = ast.unparse(call.func)
        first, dot, rest = spelling.partition(".")
        name = imports.get(first, "") + dot + rest
        where = f"{path}:{call.lineno}"
        if name not in ENTROPY | {"torch.manual_seed"} and spelling not in LEGACY_RNG:
            continue
        seed_keyword = "a" if name == "random.seed" else ("x" if name == "random.Random" else "seed")
        seed = call.args[0] if call.args else next(
            (item.value for item in call.keywords if item.arg == seed_keyword), None)
        if seed is not None:
            evidence["seed_calls"].append(where)
        empty = not call.args and not call.keywords
        if name in ENTROPY and (empty or isinstance(seed, ast.Constant) and seed.value is None):
            findings.append(finding("entropy-seeded-rng", where,
                f"{spelling} requests a generator state without a reproducible seed.",
                "If the analysis should replay exactly, pass and record the experiment seed.",
                "This checks explicit calls. Fresh randomness can be intentional."))


def dependencies(path, source):
    """Return names of applicable locks only for recognized dependency declarations."""
    if path.name == "requirements.txt":
        for number, line in enumerate(source.splitlines(), 1):
            if re.match(r"^\s*[A-Za-z0-9][\w.-]*", line):
                return PY_LOCKS, number
    elif path.name == "package.json":
        data = json.loads(source)
        if not isinstance(data, dict):
            raise ValueError("expected a package object")
        if any(data.get(key) for key in ("dependencies", "devDependencies", "optionalDependencies")):
            return NODE_LOCKS, None
    elif path.name == "pyproject.toml":
        if tomllib is None:
            raise ValueError("TOML parsing requires Python 3.11+ or tomli")
        data = tomllib.loads(source)
        project = data.get("project", {})
        poetry = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
        if project.get("dependencies") or any(project.get("optional-dependencies", {}).values()) or set(poetry) - {"python"}:
            return PY_LOCKS, None
    return set(), None


def shell_lines(source):
    """Recognize fenced shell examples and standalone inline-code commands."""
    fence = None
    for number, line in enumerate(source.splitlines(), 1):
        line = line.strip()
        if line.startswith(("```", "~~~")):
            if fence is None:
                fence = line[3:].strip().lower()
            else:
                fence = None
            yield number, None
            continue
        if fence in {"", "bash", "shell", "sh", "console", "zsh"} or line.startswith("$ "):
            yield number, line.removeprefix("$ ").strip()
        elif fence is None:
            for snippet in re.findall(r"`([^`]+)`", line):
                yield number, snippet


def scan_doc(path, source, files, skipped, findings):
    has_test = False
    cwd = path.parent
    explicit_cd = False
    for line, command in shell_lines(source):
        if command is None:
            cwd = path.parent
            explicit_cd = False
            continue
        try:
            words = shlex.split(command, comments=True)
        except ValueError:
            continue
        if not words:
            continue
        if words[0] == "cd":
            explicit_cd = True
            if len(words) == 2 and cwd and re.fullmatch(r"[\w./-]+", words[1]):
                cwd = Path(os.path.normpath(cwd / words[1]))
            else:
                cwd = None
            continue
        python = bool(re.fullmatch(r"python(?:3(?:\.\d+)?)?", words[0]))
        if words[0] in {"pytest", "py.test"} or (python and words[1:3] in (["-m", "pytest"], ["-m", "unittest"])):
            has_test = True
        if len(words) < 2 or not python or cwd is None:
            continue
        script = words[1]
        if not re.fullmatch(r"[\w./-]+\.py", script) or Path(script).is_absolute():
            continue
        target = Path(os.path.normpath(cwd / script))
        if not explicit_cd and Path(script) in files:
            target = Path(script)
        if target.is_absolute() or ".." in target.parts or any(p in skipped for p in (target, *target.parents)):
            continue
        if target not in files:
            findings.append(finding("missing-script", f"{path}:{line}",
                f"The documented command refers to {target}, which the scan could not find.",
                "Correct the command, state its working directory, or document how to generate the script.",
                "Paths are checked against the document directory, repository root and literal cd commands."))
        elif target.name.startswith("test_") or target.name.endswith("_test.py"):
            has_test = True
    return has_test


def inspect(root):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError("repository must be a directory")
    evidence = {k: [] for k in ("readme", "tests", "dependency_lock", "runtime_metadata", "seed_calls")}
    findings, coverage = [], []
    files, skipped = set(), set()

    def walk_error(exc):
        path = Path(exc.filename).relative_to(root)
        skipped.add(path)
        coverage.append({"path": str(path), "reason": type(exc).__name__})

    for directory, dirs, names in os.walk(root, onerror=walk_error):
        base = Path(directory)
        for name in dirs[:]:
            if name in SKIP or (base / name).is_symlink():
                dirs.remove(name)
                skipped.add((base / name).relative_to(root))
        for name in names:
            candidate = base / name
            rel = candidate.relative_to(root)
            if candidate.is_symlink() or not candidate.is_file():
                skipped.add(rel)
            else:
                files.add(rel)

    has_test_command = False
    for path in sorted(files):
        where = str(path)
        readme = path.stem.lower() == "readme"
        if readme:
            evidence["readme"].append(where)
        if path.name in LOCKS:
            evidence["dependency_lock"].append(where)
        if path.name in RUNTIME:
            evidence["runtime_metadata"].append(where)
        if path.suffix == ".py" and (path.name.startswith("test_") or path.name.endswith("_test.py")):
            evidence["tests"].append(where)
        doc = readme or (path.parts[0] == "docs" and path.suffix.lower() == ".md")
        manifest = path.name in {"pyproject.toml", "requirements.txt", "package.json"}
        if not (doc or manifest or path.suffix == ".py"):
            continue
        try:
            source = (root / path).read_text(encoding="utf-8")
            if doc:
                has_test_command |= scan_doc(path, source, files, skipped, findings)
            elif manifest:
                locks, line = dependencies(path, source)
                if locks and not any(path.parent / lock in files for lock in locks):
                    findings.append(finding("missing-lock", f"{where}:{line}" if line else where,
                        "A dependency manifest has no recognized matching lockfile beside it.",
                        "Record the resolved environment or document the shared lockfile used for this project.",
                        "A parent workspace lock, external environment, or fully pinned manifest may already cover these dependencies."))
            else:
                scan_python(source, path, evidence, findings)
        except (OSError, UnicodeError, SyntaxError, ValueError, AttributeError, TypeError) as exc:
            reason = type(exc).__name__
            if isinstance(exc, SyntaxError) and exc.lineno:
                reason += f" on line {exc.lineno}"
            if manifest and isinstance(exc, ValueError) and tomllib is None and path.name == "pyproject.toml":
                reason = str(exc)
            coverage.append({"path": where, "reason": reason})

    if evidence["tests"] and not has_test_command:
        findings.append(finding("undocumented-test-command", evidence["tests"][0],
            "The scan found Python tests and no recognized invocation in the scanned documentation.",
            "Document the command a new contributor can run from a fresh checkout.",
            "The scan covers README files and Markdown under docs. A custom test runner may exist."))
    return {"root": str(root), "evidence": evidence, "limitations": LIMITS,
            "findings": findings, "incomplete_coverage": coverage}


def format_text(report):
    lines = [f"Repository: {report['root']}", f"Findings: {len(report['findings'])}"]
    for item in report["findings"]:
        lines.extend([f"\n{item['location']} [{item['rule']}]", item["observation"], item["action"], item["limitation"]])
    for item in report["incomplete_coverage"]:
        lines.append(f"Incomplete coverage: {item['path']} ({item['reason']})")
    return "\n".join([*lines, "", report["limitations"]])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--format", choices=("json", "text"), default="json")
    args = parser.parse_args()
    try:
        report = inspect(args.root)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2) if args.format == "json" else format_text(report))


if __name__ == "__main__":
    main()
