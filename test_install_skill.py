from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import install_skill


class InstallSkillSimulations(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_01_explicit_destination(self):
        self.assertTrue((install_skill.install(self.root) / "SKILL.md").is_file())

    def test_02_ai_skills_environment(self):
        with patch.dict(os.environ, {"AI_SKILLS_DIR": str(self.root)}, clear=True):
            self.assertEqual(install_skill.destination_root(None), self.root)

    def test_03_codex_home_environment(self):
        with patch.dict(os.environ, {"CODEX_HOME": str(self.root)}, clear=True):
            self.assertEqual(install_skill.destination_root(None), self.root / "skills")

    def test_04_explicit_destination_wins(self):
        with patch.dict(os.environ, {"AI_SKILLS_DIR": "ignored"}, clear=True):
            self.assertEqual(install_skill.destination_root(str(self.root)), self.root)

    def test_05_missing_destination_fails(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(SystemExit):
            install_skill.destination_root(None)

    def test_06_existing_install_is_not_overwritten(self):
        install_skill.install(self.root)
        with self.assertRaises(SystemExit):
            install_skill.install(self.root)

    def test_07_nested_destination_is_created(self):
        target = install_skill.install(self.root / "nested" / "skills")
        self.assertTrue(target.is_dir())

    def test_08_unicode_and_spaces_destination(self):
        target = install_skill.install(self.root / "AI 스킬 보관함")
        self.assertTrue(target.is_dir())

    def test_09_skill_package_is_copied_completely(self):
        # Full package integrity check against governance skill tree (SOURCE).
        target = install_skill.install(self.root, install_skill.SOURCE.name)
        source_files = {
            p.relative_to(install_skill.SOURCE)
            for p in install_skill.SOURCE.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts
        }
        target_files = {
            p.relative_to(target)
            for p in target.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts
        }
        self.assertEqual(source_files, target_files)
        for document in target.rglob("*.md"):
            for link in re.findall(r"]\((?!https?://|#)([^)]+)\)", document.read_text(encoding="utf-8")):
                self.assertTrue((document.parent / link).resolve().exists(), f"Broken link: {document} -> {link}")

    def test_10_command_line_install(self):
        result = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("install_skill.py")), "--dest", str(self.root)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Installed:", result.stdout)
        self.assertTrue((self.root / "create-best-proposal" / "SKILL.md").is_file())

    def test_11_with_deps_installs_siblings(self):
        names = install_skill.resolve_names("create-best-proposal", False, True)
        self.assertIn("create-best-proposal", names)
        self.assertIn("create-proposal-document", names)
        self.assertIn("create-winning-proposal", names)

    def test_12_default_name_is_flagship(self):
        self.assertEqual(install_skill.DEFAULT_NAME, "create-best-proposal")


if __name__ == "__main__":
    unittest.main()
