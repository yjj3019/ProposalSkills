"""Include skill-local tests in root discovery. unittest discover -s . does not recurse into non-package skills/*/scripts/ directories without __init__.py, so local suites previously passed while separate CI steps failed (round 10). load_tests aligns root and CI coverage so full-pass claims mean the same thing."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent
SKILLS = REPO / "skills"


def script_test_files() -> list[Path]:
    return sorted(SKILLS.glob("*/scripts/test_*.py"))


def _load(path: Path) -> unittest.TestSuite:
    # Skill scripts import sibling modules from the same directory (sys.path convention).
    sys.path.insert(0, str(path.parent))
    name = f"skillscripts_{path.parent.parent.name.replace('-', '_')}_{path.stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return unittest.defaultTestLoader.loadTestsFromModule(module)


def load_tests(loader, tests, pattern):  # noqa: ARG001 (unittest protocol)
    suite = unittest.TestSuite([tests])
    for path in script_test_files():
        suite.addTest(_load(path))
    return suite


class CoverageContractTests(unittest.TestCase):
    """Verify this file actually imports tests rather than passing empty."""

    def test_skill_script_tests_are_found(self):
        found = script_test_files()
        self.assertGreaterEqual(len(found), 2, [str(p) for p in found])

    def test_every_tracked_test_file_runs_somewhere(self):
        """Tracked test_*.py files must be covered by root discovery or loaded here."""
        import subprocess
        out = subprocess.run(["git", "ls-files", "*test_*.py"], cwd=str(REPO),
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
        if out.returncode != 0:
            if not (REPO / ".git").exists():
                self.skipTest("설치 사본에는 Git 추적 목록이 없다")
            self.fail(f"git ls-files failed: {out.stderr.strip()}")
        collected = {p.relative_to(REPO).as_posix() for p in script_test_files()}
        orphans = []
        for line in out.stdout.splitlines():
            path = REPO / line
            if path.parent == REPO or line in collected:
                continue  # Root discover handles root tests; this file handles scripts/.
            orphans.append(line)
        self.assertEqual(orphans, [],
                         "어느 실행 경로에도 포함되지 않는 테스트 파일:\n" + "\n".join(orphans))


if __name__ == "__main__":
    unittest.main()


class SpeedContractTests(unittest.TestCase):
    """Avoid costs unrelated to test content. Run skill scripts in-process by default; use child processes only when testing encoding, exit codes, or installed execution. Breaking this contract restores tens-of-minutes local suites and encourages CI-only validation."""

    def test_scripts_are_called_in_process_by_default(self):
        import test_support
        before = test_support.SPAWNS
        result = test_support.run_script(
            REPO / "skills/create-best-proposal/scripts/unified_gate.py",
            REPO / "skills/create-best-proposal/fixtures/audit_ready_financial.json",
            "--audit-only", "--no-explain")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(test_support.SPAWNS, before, "기본 호출이 자식 프로세스를 띄웠다")

    def test_isolated_and_env_still_spawn(self):
        """Preserve paths requiring real processes, such as encoding-contract checks."""
        import test_support
        before = test_support.SPAWNS
        test_support.run_script(REPO / "skills/create-winning-proposal/scripts/proposal_gate.py",
                                "--help", isolated=True)
        self.assertEqual(test_support.SPAWNS, before + 1)

    def test_in_process_and_subprocess_agree(self):
        """The two execution paths must produce identical decisions on identical input for safe in-process execution."""
        import test_support
        gate = REPO / "skills/create-best-proposal/scripts/unified_gate.py"
        audit = REPO / "skills/create-best-proposal/fixtures/audit_ready_financial.json"
        for extra in (("--audit-only", "--no-explain"), ("--no-explain",)):
            with self.subTest(extra=extra):
                a = test_support.run_script(gate, audit, *extra)
                b = test_support.run_script(gate, audit, *extra, isolated=True)
                self.assertEqual((a.returncode, a.stdout), (b.returncode, b.stdout))
