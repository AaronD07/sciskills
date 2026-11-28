import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lint = load("lint_skills")
P = load("packs")

GOOD = """---
name: {name}
description: Check a thing. Use when the thing might be wrong.
---

# {name}

## Workflow

1. Look at `examples/demo/`.

## Guardrails and completion

Report what was checked.
"""

ROUTER_BODY = GOOD.format(name=P.ROUTER) + f"\n{P.ROUTES_START}\n{P.ROUTES_END}\n"


def make_repo(temp, packs, profiles=None, sync=True):
    """packs: {pack: {skill: SKILL.md text}}; the router is added to core automatically."""
    root = Path(temp)
    (root / "examples/demo").mkdir(parents=True)
    packs = {"core": {}, **packs}
    packs["core"] = {P.ROUTER: ROUTER_BODY, **packs["core"]}
    for pack, skills in packs.items():
        entries = [{"name": s, "route": None if s == P.ROUTER else f"Doing {s}"} for s in skills]
        (root / "packs" / pack).mkdir(parents=True)
        (root / "packs" / pack / "pack.json").write_text(json.dumps({"name": pack, "description": "d", "skills": entries}))
        for skill, text in skills.items():
            (root / "packs" / pack / "skills" / skill).mkdir(parents=True)
            (root / "packs" / pack / "skills" / skill / "SKILL.md").write_text(text)
    (root / "packs/profiles.json").write_text(json.dumps(profiles or {"basic": {"packs": ["core"]}}))
    if sync:
        loaded = P.load_packs(root)
        router = root / "packs/core/skills" / P.ROUTER / "SKILL.md"
        router.write_text(P.with_routes(router.read_text(), P.render_routes(loaded, list(loaded))))
    return root


class LintTests(unittest.TestCase):
    def test_repository_passes(self):
        count, errors, _ = lint.lint_repo(ROOT)
        self.assertGreater(count, 1)
        self.assertEqual(errors, [])

    def test_valid_minimal_repo_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = make_repo(temp, {"extra": {"demo-skill": GOOD.format(name="demo-skill")}})
            self.assertEqual(lint.lint_repo(root), (2, [], []))

    def test_detects_skill_problems(self):
        bad = {
            "wrong-name": GOOD.format(name="other-name"),
            "no-trigger": GOOD.format(name="no-trigger").replace(" Use when the thing might be wrong.", ""),
            "no-sections": "---\nname: no-sections\ndescription: Use when x.\n---\n# Title\n",
            "bad-path": GOOD.format(name="bad-path").replace("examples/demo/", "examples/missing/"),
            "bad-link": GOOD.format(name="bad-link") + "\n[ref](references/nope.md)\n",
            "no-frontmatter": "# Nothing\n",
        }
        with tempfile.TemporaryDirectory() as temp:
            _, errors, _ = lint.lint_repo(make_repo(temp, {"extra": bad}))
        joined = "\n".join(errors)
        for needle in ("must match directory", "Use when", "Workflow", "examples/missing/", "references/nope.md", "frontmatter"):
            self.assertIn(needle, joined)

    def test_detects_pack_problems(self):
        with tempfile.TemporaryDirectory() as temp:
            root = make_repo(temp, {"extra": {"a-skill": GOOD.format(name="a-skill")}},
                             profiles={"p": {"packs": ["core", "ghost"]}})
            (root / "packs/extra/skills/stray").mkdir()
            manifest = json.loads((root / "packs/extra/pack.json").read_text())
            manifest["skills"].append({"name": "listed-only", "route": "x"})
            (root / "packs/extra/pack.json").write_text(json.dumps(manifest))
            _, errors, _ = lint.lint_repo(root)
        joined = "\n".join(errors)
        self.assertIn("stray: not listed", joined)
        self.assertIn("'listed-only' has no directory", joined)
        self.assertIn("unknown pack 'ghost'", joined)

    def test_router_must_be_in_sync(self):
        with tempfile.TemporaryDirectory() as temp:
            root = make_repo(temp, {"extra": {"a-skill": GOOD.format(name="a-skill")}}, sync=False)
            _, errors, _ = lint.lint_repo(root)
        self.assertEqual(errors, ["router routing table is out of date; run: python3 scripts/install.py sync-router"])

    def test_frontmatter_parser_rejects_multiline_values(self):
        with self.assertRaises(ValueError):
            lint.parse_frontmatter("---\nname: x\ndescription: >\n  folded\n---\n")
        fields, _ = lint.parse_frontmatter('---\nname: x\ndescription: "Use when: quoted"\n---\nbody')
        self.assertEqual(fields["description"], "Use when: quoted")


if __name__ == "__main__":
    unittest.main()
