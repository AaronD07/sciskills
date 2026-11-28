import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("install", ROOT / "scripts/install.py")
install = importlib.util.module_from_spec(spec)
spec.loader.exec_module(install)
P = install.P


def router_rows(skill_md):
    return [line for line in skill_md.read_text().splitlines() if line.startswith("| ") and "`" in line]


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name)
        self.target = self.project / install.DEFAULT_SKILLS_DIR

    def tearDown(self):
        self.temp.cleanup()

    def test_router_lists_only_installed_skills(self):
        install.install(ROOT, self.project, ["compute-env"])
        installed = sorted(p.name for p in self.target.iterdir() if p.is_dir())
        self.assertEqual(installed, ["memory-budget", "pin-the-environment", P.ROUTER])
        rows = router_rows(self.target / P.ROUTER / "SKILL.md")
        self.assertEqual(len(rows), 2)
        self.assertTrue(all("memory-budget" in r or "pin-the-environment" in r for r in rows))

    def test_reinstall_replaces_and_uninstall_leaves_other_skills(self):
        (self.target / "my-own-skill").mkdir(parents=True)
        install.install(ROOT, self.project, ["core", "compute-env"])
        install.install(ROOT, self.project, ["core"], link=True)
        self.assertFalse((self.target / "memory-budget").exists())
        self.assertTrue((self.target / "check-the-numbers").is_symlink())
        self.assertFalse((self.target / P.ROUTER).is_symlink())
        self.assertEqual(json.loads((self.target / install.MANIFEST).read_text())["mode"], "link")
        install.uninstall(self.project)
        self.assertEqual([p.name for p in self.target.iterdir()], ["my-own-skill"])

    def test_refuses_to_overwrite_foreign_skill(self):
        (self.target / "check-the-numbers").mkdir(parents=True)
        with self.assertRaises(ValueError):
            install.install(ROOT, self.project, ["core"])
        self.assertFalse((self.target / install.MANIFEST).exists())

    def test_dry_run_writes_nothing(self):
        install.install(ROOT, self.project, ["core"], dry_run=True)
        self.assertFalse(self.target.exists())

    def test_refuses_to_install_into_repo(self):
        with self.assertRaises(ValueError):
            install.install(ROOT, ROOT, ["core"], dry_run=True)

    def test_resolve_options(self):
        packs, profiles = P.load_packs(ROOT), P.load_profiles(ROOT)
        self.assertEqual(P.resolve(packs, profiles, names=["compute-env", "core"])[0], "core")
        for bad in ({}, {"profile": "nope"}, {"names": ["ghost"]}, {"profile": "general", "everything": True}):
            with self.assertRaises(ValueError):
                P.resolve(packs, profiles, **bad)


if __name__ == "__main__":
    unittest.main()
