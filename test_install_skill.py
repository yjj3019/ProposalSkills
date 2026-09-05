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


class AutoInstallTests(unittest.TestCase):
    """--auto: 호스트 감지 → 각 스킬 디렉터리에 설치 (경로를 되묻지 않는다)."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def _run(self, *args: str, home: Path | None = None) -> subprocess.CompletedProcess:
        env = {k: v for k, v in os.environ.items() if k not in {"AI_SKILLS_DIR", "CODEX_HOME"}}
        env["HOME"] = env["USERPROFILE"] = str(home or self.home)
        return subprocess.run(
            [sys.executable, str(Path(__file__).with_name("install_skill.py")), *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)

    def test_detects_each_host_skill_directory(self):
        for marker, expected in ((".claude", ".claude/skills"), (".codex", ".agents/skills"),
                                 (".grok", ".grok/skills"), (".agents", ".agents/skills")):
            with self.subTest(marker=marker):
                home = Path(tempfile.mkdtemp(dir=self.home))
                (home / marker).mkdir()
                with patch.dict(os.environ, {}, clear=True):
                    targets = install_skill.detect_targets(home)
                self.assertEqual([p for _, p in targets], [home / expected])

    def test_detects_nothing_on_a_bare_home(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(install_skill.detect_targets(self.home), [])

    def test_auto_installs_all_three_skills_into_every_host(self):
        (self.home / ".claude").mkdir()
        (self.home / ".grok").mkdir()
        proc = self._run("--auto")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        for host in (".claude/skills", ".grok/skills"):
            for name in install_skill.available_skills():
                self.assertTrue((self.home / host / name / "SKILL.md").is_file(),
                                f"{host}/{name} 미설치: {proc.stdout}")

    def test_auto_falls_back_to_the_shared_agents_directory(self):
        proc = self._run("--auto")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("감지된 AI CLI 없음", proc.stdout)
        self.assertTrue((self.home / ".agents/skills/create-best-proposal/SKILL.md").is_file())

    def test_auto_is_idempotent(self):
        (self.home / ".claude").mkdir()
        self._run("--auto")
        again = self._run("--auto")
        self.assertEqual(again.returncode, 0, again.stdout)
        self.assertIn("Skip (exists)", again.stdout)

    def test_list_targets_installs_nothing(self):
        (self.home / ".claude").mkdir()
        proc = self._run("--list-targets")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn(".claude", proc.stdout)
        self.assertFalse((self.home / ".claude/skills").exists())

    def test_verify_reports_a_gutted_install(self):
        target = install_skill.install(self.home, "create-best-proposal")
        self.assertEqual(install_skill.verify(target), [])
        (target / "scripts" / "unified_gate.py").unlink()
        self.assertTrue(any("unified_gate.py" in p for p in install_skill.verify(target)))

    def test_agent_instructions_name_the_auto_command(self):
        repo = Path(__file__).resolve().parent
        for doc in ("AGENTS.md", "CLAUDE.md"):
            self.assertIn("install_skill.py --auto", (repo / doc).read_text(encoding="utf-8"), doc)

    def test_cp949_console_does_not_crash(self):
        """한글·em dash 출력이 기본 코드페이지에서 UnicodeEncodeError로 죽지 않는다."""
        env = {k: v for k, v in os.environ.items() if k not in {"AI_SKILLS_DIR", "CODEX_HOME"}}
        env.update(HOME=str(self.home), USERPROFILE=str(self.home), PYTHONIOENCODING="cp949")
        env.pop("PYTHONUTF8", None)
        for args in (["--list-targets"], ["--auto"]):
            with self.subTest(args=args):
                proc = subprocess.run(
                    [sys.executable, str(Path(__file__).with_name("install_skill.py")), *args],
                    capture_output=True, env=env)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertNotIn(b"UnicodeEncodeError", proc.stderr)
