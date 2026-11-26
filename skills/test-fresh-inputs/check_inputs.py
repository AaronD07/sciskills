"""Check a Python insertion for direct replacement of declared caller inputs."""

import argparse
import ast
import keyword
from pathlib import Path
import sys
import tokenize


CONSTRUCTORS = {
    "numpy.array",
    "numpy.asarray",
    "numpy.arange",
    "numpy.full",
    "numpy.linspace",
    "numpy.ones",
    "numpy.zeros",
    "pandas.DataFrame",
    "pandas.Series",
}


def literal(node):
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        return isinstance(node.operand, ast.Constant) and type(node.operand.value) in (
            int,
            float,
            complex,
        )
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return all(literal(item) for item in node.elts)
    if isinstance(node, ast.Dict):
        return all(key is not None and literal(key) for key in node.keys) and all(
            literal(val) for val in node.values
        )
    return False


def fixed_value(node, aliases):
    if literal(node):
        return True
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name):
        name = aliases.get(func.id)
    elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        name = f"{aliases.get(func.value.id)}.{func.attr}"
    else:
        return False
    return (
        name in CONSTRUCTORS
        and all(literal(arg) for arg in node.args)
        and all(kw.arg is not None and literal(kw.value) for kw in node.keywords)
    )


def bound_names(statement):
    """Potential rebindings invalidate constructor recognition conservatively."""
    nodes = [statement]
    while nodes:
        node = nodes.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            yield node.name
            continue
        if isinstance(
            node,
            (ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp),
        ):
            continue
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            yield node.id
        elif isinstance(node, ast.alias):
            yield node.asname or node.name.partition(".")[0]
        elif isinstance(node, ast.ExceptHandler) and node.name:
            yield node.name
        nodes.extend(ast.iter_child_nodes(node))


def assigned_values(target, value):
    if isinstance(target, ast.Name):
        yield target.id, value
    elif isinstance(target, (ast.Tuple, ast.List)) and isinstance(
        value, (ast.Tuple, ast.List)
    ):
        if len(target.elts) == len(value.elts):
            for child, item in zip(target.elts, value.elts):
                yield from assigned_values(child, item)


def find_overwrites(source, inputs):
    findings = []
    aliases = {}
    for statement in ast.parse(source).body:
        if (
            isinstance(statement, (ast.Assign, ast.AnnAssign))
            and statement.value is not None
        ):
            targets = (
                statement.targets
                if isinstance(statement, ast.Assign)
                else [statement.target]
            )
            for target in targets:
                for name, value in assigned_values(target, statement.value):
                    if name in inputs and fixed_value(value, aliases):
                        findings.append((statement.lineno, name))
        for name in bound_names(statement):
            aliases.pop(name, None)
        if isinstance(statement, ast.Import):
            for item in statement.names:
                if item.name in ("numpy", "pandas"):
                    aliases[item.asname or item.name] = item.name
        elif isinstance(statement, ast.ImportFrom) and statement.level == 0:
            for item in statement.names:
                full = f"{statement.module}.{item.name}"
                if full in CONSTRUCTORS:
                    aliases[item.asname or item.name] = full
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument(
        "--inputs",
        nargs="+",
        required=True,
        metavar="NAME",
        help="Names the caller supplies when the insertion starts",
    )
    args = parser.parse_args()
    if any(not name.isidentifier() or keyword.iskeyword(name) for name in args.inputs):
        parser.error("Each input must be a Python variable name")
    try:
        with tokenize.open(args.source) as handle:
            findings = find_overwrites(handle.read(), set(args.inputs))
    except (OSError, UnicodeError, SyntaxError) as exc:
        print(f"Could not inspect {args.source}: {exc}", file=sys.stderr)
        return 2
    for line, name in findings:
        print(
            f"{args.source}:{line}: {name} replaces a caller input with fixed data. "
            "Keep the supplied value here and move example initialization into a test."
        )
    if not findings:
        print("No direct fixed-data replacements detected for the declared inputs.")
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
