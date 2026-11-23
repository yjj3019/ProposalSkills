"""Regression tests for the repository audit: release contents, gate overrides, bundle checks and test-run honesty."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import gate_mutation_probe as probe
import install_skill
import package_plugin
import run_repo_tests

ROOT = Path(__file__).resolve().parent
GATE = ROOT / "skills/create-best-proposal/scripts/unified_gate.py"
READY = ROOT / "skills/create-best-proposal/fixtures/audit_ready_financial.json"
PROPOSAL_GATE = ROOT / "skills/create-winning-proposal/scripts/proposal_gate.py"
LOCAL_FILES = ("skills/create-best-proposal/fixtures/local_rfp.pptx", "skills/create-best-proposal/.env")


class Workspace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.source = self.base / "source"
        for relative in package_plugin.PACKAGE_FILES:
            path = self.source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, path)
        shutil.copytree(ROOT / "skills", self.source / "skills",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    def git(self, *args):
        subprocess.run(["git", "-C", str(self.source), *args], check=True, capture_output=True)

    def add_local_files(self):
        for relative in LOCAL_FILES:
            (self.source / relative).write_bytes(b"synthetic local material")


class ReleaseContentTests(Workspace):
    def test_checkout_with_untracked_files_is_not_packaged(self):
        self.git("init", "-q")
        self.git("add", "-A")
        self.add_local_files()
        output = self.base / "out.zip"
        with self.assertRaisesRegex(ValueError, "not part of the release"):
            package_plugin.build_archive(output, root=self.source)
        self.assertFalse(output.exists())

    def test_clean_checkout_packages_tracked_files(self):
        self.git("init", "-q")
        self.git("add", "-A")
        output = package_plugin.build_archive(self.base / "out.zip", root=self.source)
        with zipfile.ZipFile(output) as archive:
            self.assertIn("skills/create-best-proposal/SKILL.md", archive.namelist())

    def test_ignored_local_file_is_left_out_of_a_checkout_package(self):
        (self.source / ".gitignore").write_text("*.pptx\n", encoding="utf-8")
        self.git("init", "-q")
        self.git("add", "-A")
        (self.source / LOCAL_FILES[0]).write_bytes(b"synthetic local material")
        output = package_plugin.build_archive(self.base / "out.zip", root=self.source)
        with zipfile.ZipFile(output) as archive:
            self.assertNotIn(LOCAL_FILES[0], archive.namelist())

    def test_export_without_git_refuses_unknown_file_types(self):
        self.add_local_files()
        with self.assertRaisesRegex(ValueError, "local_rfp.pptx"):
            package_plugin.build_archive(self.base / "out.zip", root=self.source)

    def test_install_copies_only_released_files(self):
        self.git("init", "-q")
        self.git("add", "-A")
        self.add_local_files()
        with patch.object(install_skill, "SKILLS_ROOT", self.source / "skills"):
            target = install_skill.install(self.base / "installed", "create-best-proposal")
            self.assertEqual(install_skill.verify(target, require_coinstall=False), [])
        self.assertTrue((target / "SKILL.md").is_file())
        self.assertFalse((target / "fixtures/local_rfp.pptx").exists())
        self.assertFalse((target / ".env").exists())
        self.assertFalse(list(target.rglob("test_*.py")))

    def test_untracked_script_is_not_demanded_from_an_install(self):
        self.git("init", "-q")
        self.git("add", "-A")
        (self.source / "skills/create-best-proposal/scripts/local_note.py").write_text("x = 1\n", encoding="utf-8")
        with patch.object(install_skill, "SKILLS_ROOT", self.source / "skills"):
            target = install_skill.install(self.base / "installed", "create-best-proposal")
            self.assertEqual(install_skill.verify(target, require_coinstall=False), [])
        self.assertFalse((target / "scripts/local_note.py").exists())


class GateOverrideTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.stub = self.base / "stub_gate.py"
        self.stub.write_text("def validate_schema(d): return []\ndef evaluate(d): return []\n"
                             "def readiness(d, f): return ('SUBMISSION-READY', 0)\n", encoding="utf-8")

    def run_gate(self, audit, override):
        env = {k: v for k, v in os.environ.items()
               if k not in {"PROPOSAL_GATE_PATH", "QUALITY_GATE_PATH", "CHECK_NUMBERS_PATH"}}
        env.update(PROPOSAL_GATE_PATH=str(override), PYTHONUTF8="1")
        return subprocess.run([sys.executable, str(GATE), str(audit), "--audit-only", "--no-explain"],
                              capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)

    def audit(self, **changes):
        data = json.loads(READY.read_text(encoding="utf-8"))
        data.update(changes)
        path = self.base / "audit.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    def test_replaced_gate_cannot_clear_a_submission_audit(self):
        proc = self.run_gate(self.audit(), self.stub)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("unverified gate override", proc.stdout)
        self.assertNotIn("STATUS: AUDIT-VALID", proc.stdout)

    def test_replaced_gate_cannot_claim_readiness_for_another_mode(self):
        proc = self.run_gate(self.audit(mode="draft"), self.stub)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertNotIn("STATUS: SUBMISSION-READY", proc.stdout)

    def test_byte_identical_copy_is_allowed(self):
        copy = self.base / "proposal_gate.py"
        shutil.copyfile(PROPOSAL_GATE, copy)
        proc = self.run_gate(READY, copy)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("STATUS: AUDIT-VALID", proc.stdout)
        self.assertNotIn("unverified gate override", proc.stdout)


class BundleSuffixTests(unittest.TestCase):
    def test_unlisted_script_and_macro_files_block(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("unified_gate_suffix_test", GATE)
        gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gate)
        for suffix in (".hta", ".wsf", ".psm1", ".cpl", ".pptm", ".docm", ".xlsm", ".XLSM"):
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as tmp:
                (Path(tmp) / f"unlisted{suffix}").write_bytes(b"x")
                self.assertTrue(gate.verify_bundle({"attachments": []}, Path(tmp)))
        with tempfile.TemporaryDirectory() as tmp:  # allowed look-alike: an ordinary document only warns
            (Path(tmp) / "note.pdf").write_bytes(b"x")
            self.assertEqual(gate.verify_bundle({"attachments": []}, Path(tmp)), [])


class TestRunHonestyTests(unittest.TestCase):
    def test_green_exit_with_printed_failure_is_not_a_kill(self):
        self.assertEqual(probe.classify(0, "FAIL: printed by a gate\nRan 3 tests in 0.1s\n\nOK\n")[0], "survived")
        self.assertEqual(probe.classify(0, "FAIL: test_a (m.C.test_a)\nRan 3 tests in 0.1s\n\nOK\n")[0], "error")

    def test_printed_failure_does_not_count_as_a_kill_of_a_crash(self):
        output = "FAIL: printed by a gate\nERROR: test_b (m.C.test_b)\nRan 3 tests in 0.1s\n\nFAILED (errors=1)\n"
        self.assertEqual(probe.classify(1, output), ("crashed", ["test_b"]))

    def test_too_many_skips_fail_the_run(self):
        result = unittest.TestResult()
        result.testsRun = 920
        result.skipped = [(None, "not available")] * 8
        self.assertFalse(run_repo_tests.is_complete(result, 7))
        result.skipped = result.skipped[:7]
        self.assertTrue(run_repo_tests.is_complete(result, 7))

    def test_ci_sets_a_skip_limit_and_the_requirement_floor_matches_its_job(self):
        ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertIn("run_repo_tests.py --max-skipped", ci)
        floor = re.search(r"python-pptx>=([\d.]+)", (ROOT / "requirements.txt").read_text(encoding="utf-8")).group(1)
        self.assertIn(f'"python-pptx=={floor}"', ci)


if __name__ == "__main__":
    unittest.main()
