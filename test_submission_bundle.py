"""10차 — 제출은 파일 하나가 아니다.

기명 원본·익명 사본·밀봉 가격서·별책 워크시트가 함께 나가고, 파일마다 규칙이 다르다.
대표 파일 하나에만 해시를 묶어 두면 익명본의 노트에 남은 업체명도, 빠진 가격 별책도,
검토 뒤 바뀐 첨부도 잡히지 않는다. 원장 수치와 문서의 대조도 같은 자리에서 돌린다.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
from test_support import Result, run_script  # noqa: E402
BEST = REPO / "skills/create-best-proposal"
WIN = REPO / "skills/create-winning-proposal"
FIXTURES = BEST / "fixtures"
UG = BEST / "scripts/unified_gate.py"

sys.path.insert(0, str(WIN / "scripts"))
sys.path.insert(0, str(REPO))
import proposal_gate as pg  # noqa: E402
import ooxml_fixtures as fixtures  # noqa: E402

DIGEST = "sha256:" + "a" * 64
LEDGER_TEXT = "총 사업비 37억원 · 구축비 25억원 · 유지보수비(3년) 12억원"


def run(*args: object, **kw) -> Result:
    """스킬 스크립트 실행 — 기본은 같은 프로세스(test_support 참조).

    env를 주면 자식 프로세스로 승격된다(인코딩 계약 검사).
    """
    return run_script(Path(str(args[0])), *args[1:], **kw)


def digest_of(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def submission(attachments: list[dict]) -> dict:
    return {"mode": "submission", "attachments": attachments}


class AttachmentLedgerTests(unittest.TestCase):
    """역할을 적으면 그 역할의 규칙이 붙는다. 역할이 없으면 예전처럼 존재 여부만 본다."""

    def test_role_free_ledger_is_unchanged(self):
        self.assertEqual(pg.check_attachments(
            submission([{"name": "서식1", "required": True, "present": True}])), [])
        self.assertTrue(any("missing attachment" in f for f in pg.check_attachments(
            submission([{"name": "서식1", "required": True, "present": False}]))))

    def test_anonymous_copy_needs_an_inspection_record_and_a_reviewer(self):
        item = {"name": "익명본.pptx", "present": True, "role": "proposal-anonymous",
                "sha256": DIGEST, "price_screened": True}
        failures = pg.check_attachments(submission([item]))
        self.assertTrue(any("anonymity_checked is not true" in f for f in failures), failures)
        self.assertTrue(any("without a reviewer" in f for f in failures))
        item.update(anonymity_checked=True, reviewer="QA")
        named = {"name": "기명본.pptx", "present": True, "role": "proposal",
                 "sha256": DIGEST, "price_screened": True}
        self.assertEqual(pg.check_attachments(submission([item, named])), [])

    def test_anonymous_copy_without_a_named_original_is_flagged(self):
        item = {"name": "익명본.pptx", "present": True, "role": "proposal-anonymous",
                "sha256": DIGEST, "price_screened": True, "anonymity_checked": True,
                "reviewer": "QA"}
        self.assertTrue(any("no named original" in f for f in pg.check_attachments(submission([item]))))

    def test_non_price_documents_need_a_price_screening_record(self):
        item = {"name": "기술본.pptx", "present": True, "role": "proposal", "sha256": DIGEST}
        self.assertTrue(any("price_screened" in f for f in pg.check_attachments(submission([item]))))
        # 가격서 자신은 가격을 담아야 하므로 요구하지 않는다
        price = {"name": "가격서.xlsx", "present": True, "role": "price", "sha256": DIGEST}
        self.assertEqual(pg.check_attachments(submission([price])), [])

    def test_submitted_attachment_records_which_bytes_were_checked(self):
        item = {"name": "기술본.pptx", "present": True, "role": "proposal", "price_screened": True}
        self.assertTrue(any("without a sha256" in f for f in pg.check_attachments(submission([item]))))

    def test_structural_errors(self):
        cases = [
            ({"name": "a", "present": True, "role": "cover-letter"}, "unsupported role"),
            ({"name": "a", "present": True, "role": "price", "sha256": "nope"}, "must be a sha256"),
            ({"name": "a", "present": True, "role": "price", "sha256": DIGEST, "copies": 0},
             "copies must be a positive integer"),
            ({"name": "a", "present": True, "role": "price", "sha256": DIGEST, "format": 4},
             "format must be a string"),
        ]
        for item, needle in cases:
            with self.subTest(needle=needle):
                self.assertTrue(any(needle in f for f in pg.check_attachments(submission([item]))),
                                pg.check_attachments(submission([item])))

    def test_duplicate_submission_roles_are_ambiguous(self):
        items = [{"name": f"{n}.pptx", "present": True, "role": "proposal",
                  "sha256": DIGEST, "price_screened": True} for n in ("a", "b")]
        self.assertTrue(any("2 attachments with role proposal" in f
                            for f in pg.check_attachments(submission(items))))

    def test_draft_mode_does_not_demand_submission_records(self):
        item = {"name": "익명본.pptx", "present": True, "role": "proposal-anonymous"}
        data = submission([item])
        data["mode"] = "draft"
        self.assertEqual(pg.check_attachments(data), [])


class BundleVerificationTests(unittest.TestCase):
    """묶음의 파일이 실제로 그 자리에 그 내용으로 있는지 확인한다."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.bundle = self.dir / "제출본"
        self.bundle.mkdir()

    def _audit(self, attachments: list[dict]) -> Path:
        data = json.loads((FIXTURES / "audit_ready_financial.json").read_text(encoding="utf-8"))
        data["attachments"] = attachments
        path = self.dir / "audit.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    def _file(self, name: str, text: str = "본문") -> Path:
        return fixtures.pptx(self.bundle / name,
                             raw={"ppt/slides/slide1.xml": f"<a:p><a:r><a:t>{text}</a:t></a:r></a:p>"})

    def test_matching_bundle_passes(self):
        doc = self._file("기명본.pptx")
        audit = self._audit([{"name": "기명본.pptx", "present": True, "role": "proposal",
                              "sha256": digest_of(doc), "price_screened": True}])
        proc = run(UG, audit, "--audit-only", "--bundle", self.bundle, "--no-explain")
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("첨부 해시가 모두 일치한다", proc.stdout)

    def test_changed_attachment_invalidates_the_verdict(self):
        doc = self._file("기명본.pptx")
        audit = self._audit([{"name": "기명본.pptx", "present": True, "role": "proposal",
                              "sha256": digest_of(doc), "price_screened": True}])
        doc.write_bytes(doc.read_bytes() + b"drift")
        proc = run(UG, audit, "--audit-only", "--bundle", self.bundle, "--no-explain")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("해시가 audit과 다르다", proc.stdout)

    def test_missing_attachment_file_is_reported(self):
        doc = self._file("기명본.pptx")
        digest = digest_of(doc)
        audit = self._audit([{"name": "가격서.xlsx", "file": "가격서.xlsx", "present": True,
                              "role": "price", "sha256": digest}])
        proc = run(UG, audit, "--audit-only", "--bundle", self.bundle, "--no-explain")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("첨부 파일 없음", proc.stdout)

    def test_missing_bundle_directory_is_a_usage_error(self):
        audit = self._audit([])
        proc = run(UG, audit, "--audit-only", "--bundle", self.dir / "없음", "--no-explain")
        self.assertEqual(proc.returncode, 2)


class NumbersInTheUnifiedGateTests(unittest.TestCase):
    """원장 수치 대조를 사람 손에 맡기지 않는다 — 문서를 받은 경로에서 기본으로 돈다."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def _bound(self, text: str) -> tuple[Path, Path]:
        doc = fixtures.pptx(self.dir / "final.pptx",
                            raw={"ppt/slides/slide1.xml": f"<a:p><a:r><a:t>{text}</a:t></a:r></a:p>"})
        data = json.loads((FIXTURES / "audit_ready_financial.json").read_text(encoding="utf-8"))
        data["render"]["artifact_hash"] = data["package"]["artifact_hash"] = digest_of(doc)
        audit = self.dir / "audit.json"
        audit.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return audit, doc

    def test_document_matching_the_ledger_is_submission_ready(self):
        audit, doc = self._bound("정상 문서 " + LEDGER_TEXT)
        proc = run(UG, audit, "--doc", doc, "--no-explain")
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("=== check_numbers ===", proc.stdout)
        self.assertIn("STATUS: SUBMISSION-READY", proc.stdout)

    def test_stale_amount_in_the_document_blocks(self):
        """원장은 37억인데 장표에 옛 금액이 남은 경우 — 해시는 맞아도 통과하지 못한다."""
        audit, doc = self._bound("총 사업비 40억원 · 구축비 25억원 · 유지보수비(3년) 12억원")
        proc = run(UG, audit, "--doc", doc, "--no-explain")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("원장 수치가 문서 본문과 일치하지 않는다", proc.stdout)

    def test_skip_numbers_is_not_a_pass_in_submission(self):
        audit, doc = self._bound("정상 문서 " + LEDGER_TEXT)
        proc = run(UG, audit, "--doc", doc, "--skip-numbers", "--no-explain")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("NOT INSPECTED", proc.stdout)
        self.assertIn("제출 판정에 쓸 수 없다", proc.stdout)


if __name__ == "__main__":
    unittest.main()
