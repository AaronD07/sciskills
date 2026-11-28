"""Check packs, profiles and every packs/<pack>/skills/<name>/SKILL.md.

Standard library only. Errors exit 1; warnings are printed but do not fail.
"""
import argparse
import re
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import packs as P  # noqa: E402

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_NAME = 64
MAX_DESCRIPTION = 1024
MAX_LINES = 500
# Headings a skill must contain (case-insensitive substring of any "##" heading).
REQUIRED_SECTIONS = ("workflow", "guardrails", "completion")
# Backticked repository paths are checked when they start with one of these.
REPO_PREFIXES = ("packs/", "examples/", "benchmarks/", "scripts/", "docs/", "templates/", "tests/")
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
    """Return (number of skills, errors, warnings)."""
    repo_root = Path(repo_root).resolve()
    try:
        packs = P.load_packs(repo_root)
        profiles = P.load_profiles(repo_root)
    except ValueError as exc:
        return 0, [str(exc)], []
    errors, warnings, seen = [], [], {}
    for name, pack in packs.items():
        listed = [entry["name"] for entry in pack["skills"]]
        skills_root = pack["dir"] / "skills"
        on_disk = sorted(p.name for p in skills_root.iterdir() if p.is_dir() and not p.name.startswith(".")) if skills_root.is_dir() else []
        for skill in sorted(set(on_disk) - set(listed)):
            errors.append(f"packs/{name}/skills/{skill}: not listed in packs/{name}/pack.json")
        for skill in listed:
            if skill in seen:
                errors.append(f"packs/{name}/pack.json: skill '{skill}' is also in pack '{seen[skill]}'")
            seen[skill] = name
            if skill not in on_disk:
                errors.append(f"packs/{name}/pack.json: listed skill '{skill}' has no directory")
                continue
            e, w = lint_skill(skills_root / skill, repo_root)
            errors += e
            warnings += w
    for profile, data in profiles.items():
        for pack in data["packs"]:
            if pack not in packs:
                errors.append(f"packs/profiles.json: profile '{profile}' uses unknown pack '{pack}'")
    # The committed router must route to every pack's skills, so none is forgotten.
    router = P.skill_path(packs[P.ROUTER_PACK], P.ROUTER) / "SKILL.md"
    if P.ROUTER not in seen or not router.is_file():
        errors.append(f"packs/{P.ROUTER_PACK}/skills/{P.ROUTER}/SKILL.md: router skill is missing")
    else:
        text = router.read_text(encoding="utf-8")
        try:
            expected = P.with_routes(text, P.render_routes(packs, P.resolve(packs, profiles, everything=True)))
        except ValueError as exc:
            errors.append(str(exc))
        else:
            if expected != text:
                errors.append("router routing table is out of date; run: python3 scripts/install.py sync-router")
    return len(seen), errors, warnings


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
