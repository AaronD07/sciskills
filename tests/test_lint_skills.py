import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("lint_skills", ROOT / "scripts/lint_skills.py")
lint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lint)

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


def make_repo(temp, skills):
    root = Path(temp)
    (root / "examples/demo").mkdir(parents=True)
    for name, text in skills.items():
        (root / "skills" / name).mkdir(parents=True)
        (root / "skills" / name / "SKILL.md").write_text(text)
    return root


def router_for(*names):
    return GOOD.format(name=lint.ROUTER) + "\n".join(f"- `{n}`" for n in names) + "\n"


class LintTests(unittest.TestCase):
    def test_repository_skills_pass(self):
        count, errors, _ = lint.lint_repo(ROOT)
        self.assertGreater(count, 0)
        self.assertEqual(errors, [])

    def test_valid_minimal_repo_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = make_repo(temp, {"demo-skill": GOOD.format(name="demo-skill"), lint.ROUTER: router_for("demo-skill")})
            self.assertEqual(lint.lint_repo(root), (2, [], []))

    def test_detects_structural_problems(self):
        bad = {
            "wrong-name": GOOD.format(name="other-name"),
            "no-trigger": GOOD.format(name="no-trigger").replace(" Use when the thing might be wrong.", ""),
            "no-sections": "---\nname: no-sections\ndescription: Use when x.\n---\n# Title\n",
            "bad-path": GOOD.format(name="bad-path").replace("examples/demo/", "examples/missing/"),
            "bad-link": GOOD.format(name="bad-link") + "\n[ref](references/nope.md)\n",
            "no-frontmatter": "# Nothing\n",
        }
        with tempfile.TemporaryDirectory() as temp:
            root = make_repo(temp, bad)
            _, errors, _ = lint.lint_repo(root)
        joined = "\n".join(errors)
        self.assertIn("must match directory", joined)
        self.assertIn("Use when", joined)
        self.assertIn("Workflow", joined)
        self.assertIn("examples/missing/", joined)
        self.assertIn("references/nope.md", joined)
        self.assertIn("frontmatter", joined)
        self.assertIn("router skill is missing", joined)

    def test_router_must_list_every_skill(self):
        with tempfile.TemporaryDirectory() as temp:
            root = make_repo(temp, {"a-skill": GOOD.format(name="a-skill"), "b-skill": GOOD.format(name="b-skill"),
                                    lint.ROUTER: router_for("a-skill")})
            _, errors, _ = lint.lint_repo(root)
        self.assertEqual(errors, [f"skills/{lint.ROUTER}/SKILL.md: does not route to `b-skill`"])

    def test_frontmatter_parser_rejects_multiline_values(self):
        with self.assertRaises(ValueError):
            lint.parse_frontmatter("---\nname: x\ndescription: >\n  folded\n---\n")
        fields, _ = lint.parse_frontmatter('---\nname: x\ndescription: "Use when: quoted"\n---\nbody')
        self.assertEqual(fields["description"], "Use when: quoted")


if __name__ == "__main__":
    unittest.main()
