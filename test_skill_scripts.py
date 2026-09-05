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
