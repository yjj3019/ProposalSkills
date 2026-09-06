"""스킬 안에 있는 테스트 파일을 루트 실행에 합류시킨다.

`unittest discover -s .`는 패키지가 아닌 하위 디렉터리(`__init__.py`가 없는
`skills/*/scripts/`)를 재귀하지 않는다. 그래서 그 파일들은 CI에서 별도 스텝으로만
돌았고, 로컬 전체 실행은 통과하는데 CI는 실패하는 상태가 생겼다(10차에서 실제로 그랬다).

여기서 load_tests로 끌어와 루트 실행과 CI의 검사 범위를 같게 만든다. 어느 쪽에서 돌려도
같은 결과가 나와야 "전체 통과"라는 말이 의미를 갖는다.
"""
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
    # 스킬 스크립트는 형제 모듈을 같은 폴더에서 import한다(sys.path 규약).
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
    """이 파일이 실제로 무언가를 끌어오고 있는지 확인한다(빈 채로 통과하지 않게)."""

    def test_skill_script_tests_are_found(self):
        found = script_test_files()
        self.assertGreaterEqual(len(found), 2, [str(p) for p in found])

    def test_every_tracked_test_file_runs_somewhere(self):
        """추적 중인 test_*.py는 루트 discover 대상이거나 여기서 끌어오는 것이어야 한다."""
        import subprocess
        out = subprocess.run(["git", "ls-files", "*test_*.py"], cwd=str(REPO),
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
        if out.returncode != 0:
            self.skipTest("git 추적 목록을 얻을 수 없다")
        collected = {p.relative_to(REPO).as_posix() for p in script_test_files()}
        orphans = []
        for line in out.stdout.splitlines():
            path = REPO / line
            if path.parent == REPO or line in collected:
                continue  # 루트는 discover가, scripts/는 이 파일이 담당
            orphans.append(line)
        self.assertEqual(orphans, [],
                         "어느 실행 경로에도 포함되지 않는 테스트 파일:\n" + "\n".join(orphans))


if __name__ == "__main__":
    unittest.main()


class SpeedContractTests(unittest.TestCase):
    """검사 내용과 무관한 비용을 다시 들이지 않는다.

    스킬 스크립트 호출은 기본이 같은 프로세스다. 자식 프로세스는 그 자체가 검사 대상일
    때만 쓴다(인코딩·종료 코드·설치본 실행). 이 계약이 깨지면 로컬 전체 실행이 다시
    수십 분이 되고, 그러면 CI만 보고 밀게 된다.
    """

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
        """인코딩 계약처럼 실제 프로세스가 필요한 경로는 남아 있어야 한다."""
        import test_support
        before = test_support.SPAWNS
        test_support.run_script(REPO / "skills/create-winning-proposal/scripts/proposal_gate.py",
                                "--help", isolated=True)
        self.assertEqual(test_support.SPAWNS, before + 1)

    def test_in_process_and_subprocess_agree(self):
        """같은 입력에 두 경로가 같은 판정을 내야 in-process 전환이 안전하다."""
        import test_support
        gate = REPO / "skills/create-best-proposal/scripts/unified_gate.py"
        audit = REPO / "skills/create-best-proposal/fixtures/audit_ready_financial.json"
        for extra in (("--audit-only", "--no-explain"), ("--no-explain",)):
            with self.subTest(extra=extra):
                a = test_support.run_script(gate, audit, *extra)
                b = test_support.run_script(gate, audit, *extra, isolated=True)
                self.assertEqual((a.returncode, a.stdout), (b.returncode, b.stdout))
