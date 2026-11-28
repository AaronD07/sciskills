"""Check every skills/<name>/SKILL.md for structure the repository relies on.

Standard library only. Errors exit 1; warnings are printed but do not fail.
"""
import argparse
import re
from pathlib import Path

ROUTER = "sciskills-start-here"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_NAME = 64
MAX_DESCRIPTION = 1024
MAX_LINES = 500
# Headings a skill must contain (case-insensitive substring of any "##" heading).
REQUIRED_SECTIONS = ("workflow", "guardrails", "completion")
# Backticked repository paths are checked when they start with one of these.
REPO_PREFIXES = ("skills/", "examples/", "benchmarks/", "scripts/", "docs/", "templates/", "tests/")
BACKTICK_RE = re.compile(r"`([^`\s]+)`")
LINK_RE = re.compile(r"\]\(([^)\s]+)\)")


def parse_frontmatter(text):
    """Return (fields, body) or raise ValueError. Only single-line `key: value` pairs."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening '---' frontmatter line")
    try:
        end = next(i for i, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration:
        raise ValueError("missing closing '---' frontmatter line") from None
    fields = {}
    for number, line in enumerate(lines[1:end], 2):
        if not line.strip():
            continue
        key, sep, value = line.partition(":")
        if not sep or not key.strip() or line[0].isspace():
            raise ValueError(f"line {number}: expected single-line 'key: value'")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        if value in {">", "|", ">-", "|-"}:
            raise ValueError(f"line {number}: multi-line values are not supported")
        fields[key.strip()] = value
    return fields, "\n".join(lines[end + 1:])


def lint_skill(skill_dir, repo_root):
    """Return (errors, warnings) for one skill directory."""
    errors, warnings = [], []
    path = skill_dir / "SKILL.md"
    if not path.is_file():
        return [f"{skill_dir.name}: missing SKILL.md"], warnings
    rel = path.relative_to(repo_root)
    text = path.read_text(encoding="utf-8")
    try:
        fields, body = parse_frontmatter(text)
    except ValueError as exc:
        return [f"{rel}: {exc}"], warnings

    name = fields.get("name", "")
    description = fields.get("description", "")
    if not name:
        errors.append(f"{rel}: frontmatter needs 'name'")
    elif name != skill_dir.name:
        errors.append(f"{rel}: name '{name}' must match directory '{skill_dir.name}'")
    elif len(name) > MAX_NAME or not NAME_RE.match(name):
        errors.append(f"{rel}: name must be lowercase kebab-case, at most {MAX_NAME} characters")
    if not description:
        errors.append(f"{rel}: frontmatter needs 'description'")
    else:
        if len(description) > MAX_DESCRIPTION:
            errors.append(f"{rel}: description exceeds {MAX_DESCRIPTION} characters")
        if "use when" not in description.lower():
            errors.append(f"{rel}: description must say 'Use when ...' so agents know when to load it")
    unknown = set(fields) - {"name", "description"}
    if unknown:
        warnings.append(f"{rel}: unrecognized frontmatter keys {sorted(unknown)}")

    headings = [line.lstrip("#").strip().lower() for line in body.splitlines() if line.startswith("##")]
    for section in REQUIRED_SECTIONS:
        if not any(section in heading for heading in headings):
            errors.append(f"{rel}: needs a '## ...{section.title()}...' section")
    if len(text.splitlines()) > MAX_LINES:
        warnings.append(f"{rel}: over {MAX_LINES} lines; move detail into reference files")

    for target in BACKTICK_RE.findall(body):
        if target.startswith(REPO_PREFIXES) and not (repo_root / target).exists():
            errors.append(f"{rel}: referenced path `{target}` does not exist")
    for target in LINK_RE.findall(body):
        if "://" in target or target.startswith(("#", "mailto:")):
            continue
        if not (skill_dir / target.split("#")[0]).exists():
            errors.append(f"{rel}: link target '{target}' does not exist")
    return errors, warnings


def lint_repo(repo_root):
    repo_root = Path(repo_root).resolve()
    skills_root = repo_root / "skills"
    if not skills_root.is_dir():
        raise ValueError("no skills/ directory")
    skill_dirs = sorted(p for p in skills_root.iterdir() if p.is_dir() and not p.name.startswith("."))
    errors, warnings = [], []
    for skill_dir in skill_dirs:
        e, w = lint_skill(skill_dir, repo_root)
        errors += e
        warnings += w
    # The router must route to every skill, so new skills cannot be forgotten.
    router = skills_root / ROUTER / "SKILL.md"
    if router.is_file():
        text = router.read_text(encoding="utf-8")
        for skill_dir in skill_dirs:
            if skill_dir.name != ROUTER and f"`{skill_dir.name}`" not in text:
                errors.append(f"skills/{ROUTER}/SKILL.md: does not route to `{skill_dir.name}`")
    else:
        errors.append(f"skills/{ROUTER}/SKILL.md: router skill is missing")
    return len(skill_dirs), errors, warnings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    args = parser.parse_args()
    try:
        count, errors, warnings = lint_repo(args.root)
    except ValueError as exc:
        parser.error(str(exc))
    for message in warnings:
        print(f"warning: {message}")
    for message in errors:
        print(f"error: {message}")
    print(f"{count} skills checked: {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
