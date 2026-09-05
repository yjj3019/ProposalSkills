"""공개 저장소 위생 — 커밋되면 안 되는 것이 들어왔는지 기계가 검사한다.

이 저장소는 공개돼 있다. 제안서 작업은 성격상 고객사명·담당자·견적·내부 경로를 다루므로,
작업 산출물이 그대로 커밋되면 그 정보가 영구히 공개된다. 사람이 매번 눈으로 거르는 대신
여기서 막는다.

검사 대상은 **객관적으로 판별 가능한 것**뿐이다. "이 이름이 고객사인가"는 기계가 알 수 없으므로,
그 판단은 AGENTS.md의 작성 규칙과 사람의 검토에 맡긴다.
"""
from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent

# 검사에서 제외: 이 파일 자신(패턴을 문자열로 들고 있다)과 이진 파일.
SELF = Path(__file__).name
BINARY_SUFFIXES = {".pptx", ".docx", ".xlsx", ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".zip"}

PATTERNS: list[tuple[str, str, str]] = [
    # (이름, 정규식, 왜 문제인가)
    ("windows-user-path", r"[A-Za-z]:\\+(?:Users|AI-Codding)\\+",
     "로컬 절대 경로 — 작업자의 디렉터리 구조가 드러난다"),
    ("unix-home-path", r"/(?:home|Users)/(?!runner\b|claude\b)[A-Za-z][A-Za-z0-9._-]{2,}/",
     "로컬 홈 경로 — 계정명이 드러난다"),
    ("email", r"[A-Za-z0-9._%+-]+@(?!example\.(?:com|org)\b|noreply\b)[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
     "이메일 주소 — 개인 연락처는 공개 저장소에 두지 않는다"),
    ("private-workspace-url", r"notion\.so/[A-Za-z0-9]",
     "사내 워크스페이스 링크 — 외부에서 접근할 수 없고 조직이 드러난다"),
    ("api-key-shape", r"(?i)(?:api[_-]?key|secret|token|password)\s*[:=]\s*[\"'][A-Za-z0-9/_+-]{16,}[\"']",
     "자격증명 형태의 문자열"),
]


def tracked_files() -> list[Path]:
    out = subprocess.run(["git", "ls-files"], cwd=str(REPO), capture_output=True,
                         text=True, encoding="utf-8", errors="replace")
    if out.returncode != 0:  # git 없는 환경(설치 트리 등)에서는 검사 생략
        return []
    files = []
    for line in out.stdout.splitlines():
        path = REPO / line
        if not path.is_file() or path.name == SELF or path.suffix.lower() in BINARY_SUFFIXES:
            continue
        files.append(path)
    return files


class RepoHygieneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = tracked_files()

    def test_git_is_available_and_files_are_tracked(self):
        if not self.files:
            self.skipTest("git 추적 파일 목록을 얻을 수 없다(설치 트리 등)")
        self.assertGreater(len(self.files), 20)

    def test_no_local_paths_credentials_or_contacts(self):
        if not self.files:
            self.skipTest("git 추적 파일 목록을 얻을 수 없다")
        hits: list[str] = []
        for path in self.files:
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            rel = path.relative_to(REPO)
            for name, pattern, why in PATTERNS:
                for m in re.finditer(pattern, text):
                    line = text.count("\n", 0, m.start()) + 1
                    hits.append(f"{rel}:{line} [{name}] {m.group(0)[:60]} — {why}")
        self.assertEqual(hits, [], "공개 저장소에 두면 안 되는 내용:\n" + "\n".join(hits))

    def test_no_real_looking_customer_fixtures(self):
        """픽스처의 발주처는 가상 표기(○○·가상)여야 한다 — 실제 고객명 유입 방지."""
        if not self.files:
            self.skipTest("git 추적 파일 목록을 얻을 수 없다")
        import json
        problems: list[str] = []
        for path in self.files:
            if "fixtures" not in path.parts or path.suffix != ".json":
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except ValueError:
                continue
            buyer = data.get("buyer") or (data.get("meta") or {}).get("buyer")
            if isinstance(buyer, str) and buyer and not re.search(r"○|가상|샘플|sample|example", buyer, re.I):
                problems.append(f"{path.relative_to(REPO)}: buyer={buyer!r}")
        self.assertEqual(problems, [],
                         "픽스처 발주처는 가상 표기여야 한다:\n" + "\n".join(problems))

    def test_the_rule_is_documented_for_contributors_and_agents(self):
        text = (REPO / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("공개 저장소", text)
        for needle in ("고객사", "커밋"):
            self.assertIn(needle, text, needle)


if __name__ == "__main__":
    unittest.main()
