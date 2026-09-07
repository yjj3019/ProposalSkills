"""Multi-host skill schema: flagship entry vs explicit-only siblings."""

from __future__ import annotations

import unittest
from pathlib import Path

import install_skill

REPO = Path(__file__).resolve().parent
SKILLS = REPO / "skills"


class SkillSchemaTests(unittest.TestCase):
    def test_all_skills_pass_schema(self):
        names = install_skill.available_skills()
        self.assertGreaterEqual(len(names), 3)
        for name in names:
            with self.subTest(skill=name):
                problems = install_skill.skill_schema_problems(SKILLS / name)
                self.assertEqual(problems, [], problems)

    def test_dir_name_matches_frontmatter(self):
        for name in install_skill.available_skills():
            fm = install_skill.parse_frontmatter(
                (SKILLS / name / "SKILL.md").read_text(encoding="utf-8"))
            self.assertEqual(fm.get("name"), name)
            self.assertTrue(fm.get("description"))

    def test_openai_yaml_parses_interface(self):
        for name in install_skill.available_skills():
            meta = install_skill.load_openai_yaml(SKILLS / name)
            self.assertIsNotNone(meta, name)
            self.assertIn("interface", meta)
            iface = meta["interface"]
            self.assertTrue(iface.get("display_name") or iface.get("short_description"))

    def test_siblings_are_explicit_only(self):
        for name in sorted(install_skill.SIBLINGS):
            with self.subTest(skill=name):
                fm = install_skill.parse_frontmatter(
                    (SKILLS / name / "SKILL.md").read_text(encoding="utf-8"))
                self.assertTrue(fm.get("disable-model-invocation"), name)
                meta = install_skill.load_openai_yaml(SKILLS / name)
                self.assertFalse(install_skill.allow_implicit_invocation(meta), name)

    def test_flagship_allows_implicit_and_model_invocation(self):
        name = install_skill.FLAGSHIP
        fm = install_skill.parse_frontmatter(
            (SKILLS / name / "SKILL.md").read_text(encoding="utf-8"))
        self.assertFalse(bool(fm.get("disable-model-invocation")))
        meta = install_skill.load_openai_yaml(SKILLS / name)
        self.assertTrue(install_skill.allow_implicit_invocation(meta))
        # Prefer omitting policy entirely on the flagship.
        self.assertNotIn("policy", meta or {})

    def test_flagship_packaged_deps_exist(self):
        for dep in install_skill.DEPS[install_skill.FLAGSHIP]:
            self.assertTrue((SKILLS / dep / "SKILL.md").is_file(), dep)

    def test_plugin_manifest_points_at_skills(self):
        manifest = REPO / ".codex-plugin" / "plugin.json"
        self.assertTrue(manifest.is_file())
        text = manifest.read_text(encoding="utf-8")
        self.assertIn('"skills"', text)
        self.assertIn("./skills/", text)

    def test_docs_name_flagship_entry_and_explicit_siblings(self):
        for doc in ("AGENTS.md", "README.md"):
            body = (REPO / doc).read_text(encoding="utf-8")
            self.assertIn("create-best-proposal", body)
            self.assertRegex(body, r"진입점|flagship|Entry", doc)
            self.assertRegex(body, r"명시|explicit", doc)

    def test_sibling_default_prompt_is_not_main_entry(self):
        for name in sorted(install_skill.SIBLINGS):
            meta = install_skill.load_openai_yaml(SKILLS / name)
            prompt = (meta or {}).get("interface", {}).get("default_prompt", "")
            self.assertIn("create-best-proposal", prompt, name)
            self.assertRegex(prompt.lower(), r"only|unavailable|prefer|명시|레이어")


class VerifySchemaIntegrationTests(unittest.TestCase):
    def test_verify_accepts_intact_source_copies(self):
        import tempfile
        import shutil

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in install_skill.available_skills():
                shutil.copytree(
                    SKILLS / name, root / name,
                    ignore=install_skill.COPY_IGNORE)
            for name in install_skill.available_skills():
                with self.subTest(skill=name):
                    self.assertEqual(install_skill.verify(root / name), [])

    def test_coinstall_helper_flags_missing_siblings(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            target = install_skill.install(Path(tmp), "create-best-proposal")
            problems = install_skill.coinstall_problems(target)
            self.assertTrue(any("create-proposal-document" in p for p in problems))
            self.assertTrue(any("create-winning-proposal" in p for p in problems))


if __name__ == "__main__":
    unittest.main()
