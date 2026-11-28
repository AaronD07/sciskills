"""Install SciSkills packs into a research project, or keep the repo's router in sync.

    python3 scripts/install.py list
    python3 scripts/install.py install --into ~/my-project --profile general
    python3 scripts/install.py install --into ~/my-project --packs core,compute-env --link
    python3 scripts/install.py uninstall --into ~/my-project
    python3 scripts/install.py sync-router

Skills are copied (or symlinked with --link) into <project>/.claude/skills by default.
The router is always installed, and always written fresh, with a routing table listing
only the installed skills. A .sciskills.json manifest records what was installed so a
reinstall or uninstall touches nothing else. Standard library only.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import packs as P  # noqa: E402

MANIFEST = ".sciskills.json"
DEFAULT_SKILLS_DIR = ".claude/skills"


def plan(root, selected, packs):
    """Return [(skill name, source dir)] for the router plus every selected skill."""
    items = [(P.ROUTER, P.skill_path(packs[P.ROUTER_PACK], P.ROUTER))]
    for name in selected:
        for entry in packs[name]["skills"]:
            if entry["name"] != P.ROUTER:
                items.append((entry["name"], P.skill_path(packs[name], entry["name"])))
    for skill, source in items:
        if not (source / "SKILL.md").is_file():
            raise ValueError(f"{source.relative_to(root)}: missing SKILL.md")
    return items


def read_manifest(target):
    path = target / MANIFEST
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    # Only ever touch plain directory names recorded by a previous install.
    data["skills"] = [s for s in data.get("skills", []) if isinstance(s, str) and Path(s).name == s and s not in {"", ".", ".."}]
    return data


def remove_installed(target, manifest):
    for skill in manifest["skills"]:
        path = target / skill
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
    (target / MANIFEST).unlink(missing_ok=True)


def install(root, project, selected, skills_dir=DEFAULT_SKILLS_DIR, link=False, dry_run=False):
    root, project = Path(root).resolve(), Path(project).expanduser().resolve()
    if not project.is_dir():
        raise ValueError(f"{project} is not a directory")
    if project == root or root in project.parents:
        raise ValueError("install into a research project, not into the SciSkills repo itself")
    packs = P.load_packs(root)
    items = plan(root, selected, packs)
    target = project / skills_dir
    previous = read_manifest(target) if target.is_dir() else None
    owned = set(previous["skills"]) if previous else set()
    clashes = [s for s, _ in items if (target / s).exists() and s not in owned]
    if clashes:
        raise ValueError(f"{target} already has skills not installed by SciSkills: {', '.join(clashes)}")
    router_text = P.with_routes((items[0][1] / "SKILL.md").read_text(encoding="utf-8"), P.render_routes(packs, selected))
    if dry_run:
        return target, items
    if previous:
        remove_installed(target, previous)
    target.mkdir(parents=True, exist_ok=True)
    for skill, source in items:
        dest = target / skill
        if skill == P.ROUTER:
            # Written, never linked: its routing table depends on this install.
            shutil.copytree(source, dest, ignore=shutil.ignore_patterns("__pycache__"))
            (dest / "SKILL.md").write_text(router_text, encoding="utf-8")
        elif link:
            os.symlink(source, dest, target_is_directory=True)
        else:
            shutil.copytree(source, dest, ignore=shutil.ignore_patterns("__pycache__"))
    manifest = {"source": str(root), "packs": selected, "skills": [s for s, _ in items], "mode": "link" if link else "copy"}
    (target / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return target, items


def uninstall(project, skills_dir=DEFAULT_SKILLS_DIR):
    target = Path(project).expanduser().resolve() / skills_dir
    manifest = read_manifest(target) if target.is_dir() else None
    if not manifest:
        raise ValueError(f"no SciSkills install found in {target}")
    remove_installed(target, manifest)
    return target, manifest["skills"]


def sync_router(root):
    """Rewrite the repo's router to route to every pack. Returns True if it changed."""
    packs = P.load_packs(root)
    path = P.skill_path(packs[P.ROUTER_PACK], P.ROUTER) / "SKILL.md"
    old = path.read_text(encoding="utf-8")
    new = P.with_routes(old, P.render_routes(packs, list(P.resolve(packs, {}, everything=True))))
    if new != old:
        path.write_text(new, encoding="utf-8")
    return new != old


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="show packs and profiles")
    p = sub.add_parser("install", help="install packs into a project")
    p.add_argument("--into", type=Path, required=True, help="research project directory")
    choice = p.add_mutually_exclusive_group(required=True)
    choice.add_argument("--profile")
    choice.add_argument("--packs", help="comma-separated pack names")
    choice.add_argument("--all", action="store_true", help="every pack")
    p.add_argument("--skills-dir", default=DEFAULT_SKILLS_DIR, help=f"relative to the project (default {DEFAULT_SKILLS_DIR})")
    p.add_argument("--link", action="store_true", help="symlink skills so repo edits show up immediately")
    p.add_argument("--dry-run", action="store_true")
    u = sub.add_parser("uninstall", help="remove what a previous install added")
    u.add_argument("--into", type=Path, required=True)
    u.add_argument("--skills-dir", default=DEFAULT_SKILLS_DIR)
    sub.add_parser("sync-router", help="regenerate the repo router's routing table from pack.json files")
    args = parser.parse_args()
    root = P.REPO
    try:
        if args.command == "list":
            packs, profiles = P.load_packs(root), P.load_profiles(root)
            print("Packs:")
            for name, pack in packs.items():
                skills = ", ".join(s["name"] for s in pack["skills"])
                print(f"  {name:<14} {pack['description']}\n  {'':<14} skills: {skills}")
            print("Profiles:")
            for name, profile in profiles.items():
                print(f"  {name:<14} {', '.join(profile['packs'])}: {profile.get('description', '')}")
        elif args.command == "install":
            packs, profiles = P.load_packs(root), P.load_profiles(root)
            names = [n.strip() for n in args.packs.split(",") if n.strip()] if args.packs else None
            selected = P.resolve(packs, profiles, profile=args.profile, names=names, everything=args.all)
            target, items = install(root, args.into, selected, args.skills_dir, args.link, args.dry_run)
            verb = "Would install" if args.dry_run else "Installed"
            print(f"{verb} {len(items)} skills from {', '.join(selected)} into {target}:")
            for skill, _ in items:
                print(f"  {skill}")
        elif args.command == "uninstall":
            target, skills = uninstall(args.into, args.skills_dir)
            print(f"Removed {len(skills)} skills from {target}")
        else:
            print("Router updated." if sync_router(root) else "Router already up to date.")
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
