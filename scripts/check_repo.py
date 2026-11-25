"""Report repository evidence without assigning a correctness score."""
import argparse
import ast
import json
from pathlib import Path

SKIP = {".git", ".venv", "venv", "node_modules", "__pycache__", "benchmark-runs"}
LOCKS = {"uv.lock", "poetry.lock", "Pipfile.lock", "conda-lock.yml", "conda-lock.yaml", "requirements-lock.txt", "package-lock.json", "pnpm-lock.yaml", "yarn.lock"}


def inspect(root):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError("repository must be a directory")
    # Do not follow symlinks outside the supplied project.
    files = []
    def visit(directory):
        for p in sorted(directory.iterdir()):
            if p.is_symlink() or p.name in SKIP:
                continue
            if p.is_dir():
                visit(p)
            elif p.is_file():
                files.append(p)
    visit(root)
    evidence = {"readme": [], "tests": [], "dependency_lock": [], "runtime_metadata": [], "seed_calls": []}
    for p in files:
        rel = str(p.relative_to(root))
        if p.stem.lower() == "readme":
            evidence["readme"].append(rel)
        if p.suffix == ".py" and (p.name.startswith("test_") or p.name.endswith("_test.py")):
            evidence["tests"].append(rel)
        if p.name in LOCKS:
            evidence["dependency_lock"].append(rel)
        if p.name in {".python-version", "runtime.txt", "pyproject.toml", "environment.yml", "environment.yaml"}:
            evidence["runtime_metadata"].append(rel)
        if p.suffix != ".py":
            continue
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeError):
            continue
        # Explicit API spellings only. Aliases and runtime dataflow are not inferred.
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = ast.unparse(node.func)
                if name in {"random.seed", "random.Random", "np.random.seed", "numpy.random.seed", "np.random.default_rng", "numpy.random.default_rng", "torch.manual_seed"} and (node.args or any(k.arg == "seed" for k in node.keywords)):
                    evidence["seed_calls"].append(f"{rel}:{node.lineno}")
    return {"root": str(root), "evidence": evidence, "limitations": "Presence only: tests were not run; lockfiles and runtime constraints were not validated; seed values and RNG coverage were not verified. Missing evidence may be inapplicable. This is not a correctness or security grade."}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    args = p.parse_args()
    try:
        print(json.dumps(inspect(args.root), indent=2))
    except ValueError as exc:
        p.error(str(exc))


if __name__ == "__main__":
    main()
