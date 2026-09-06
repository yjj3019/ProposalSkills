"""회귀 테스트 — 2026-09 외부 정밀 진단(F01~F05)에서 재현된 허위 통과·유실의 재발 방지.

각 테스트는 진단 당시 실제로 '통과'했던 입력을 그대로 재현하고, 이제 차단·사용 오류로
판정되는지 확인한다. 정상 대조군을 함께 둬서 과민 차단도 같이 잡는다.
"""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
from test_support import Result, run_script  # noqa: E402
BEST = REPO / "skills/create-best-proposal"
DOC = REPO / "skills/create-proposal-document"
UG = BEST / "scripts/unified_gate.py"
QG = DOC / "scripts/quality_gate.py"
BAM = BEST / "scripts/build_audit_from_meta.py"
FIXTURES = BEST / "fixtures"

sys.path.insert(0, str(REPO / "skills/create-winning-proposal/scripts"))
sys.path.insert(0, str(BEST / "scripts"))
import ooxml_fixtures as fixtures  # noqa: E402
import proposal_gate as pg  # noqa: E402
import build_audit_from_meta as bam  # noqa: E402


def run(*args: object, **kw) -> Result:
    """스킬 스크립트 실행 — 기본은 같은 프로세스(test_support 참조).

    env를 주면 자식 프로세스로 승격된다(인코딩 계약 검사).
    """
    return run_script(Path(str(args[0])), *args[1:], **kw)


LEDGER_TEXT = "총 사업비 37억원 · 구축비 25억원 · 유지보수비(3년) 12억원"


def make_pptx(path: Path, text: str = "정상 문서 " + LEDGER_TEXT) -> Path:
    """정상 패키지. 열리지 않는 파일을 양성 대조군으로 쓰지 않는다.

    통합 게이트가 원장 수치를 문서와 대조하므로, 양성 대조군은 audit의 원장과 같은
    금액을 담아야 한다 — 원장과 어긋난 문서를 '정상'이라고 부르면 대조 자체가 무의미하다.
    """
    return fixtures.pptx(path, raw={"ppt/slides/slide1.xml":
                                    f"<a:p><a:r><a:t>{text}</a:t></a:r></a:p>"})


def digest_of(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def ready_audit() -> dict:
    return json.loads((FIXTURES / "audit_ready_financial.json").read_text(encoding="utf-8"))


class ArtifactBindingTests(unittest.TestCase):
    """F01 — 검증 기록이 '어느 파일'의 것인지 확인한다."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def _gate(self, data: dict, *extra: str) -> subprocess.CompletedProcess:
        p = self.dir / "audit.json"
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return run(UG, p, "--no-explain", *extra)

    def test_submission_without_document_is_blocked(self):
        proc = self._gate(ready_audit())
        self.assertEqual(proc.returncode, 1)
        self.assertIn("--doc", proc.stdout)

    def test_audit_only_never_claims_submission_ready(self):
        proc = self._gate(ready_audit(), "--audit-only")
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("STATUS: AUDIT-VALID", proc.stdout)
        self.assertNotIn("STATUS: SUBMISSION-READY", proc.stdout)

    def test_matching_document_is_submission_ready(self):
        doc = make_pptx(self.dir / "final.pptx")
        data = ready_audit()
        data["render"]["artifact_hash"] = data["package"]["artifact_hash"] = digest_of(doc)
        proc = self._gate(data, "--doc", str(doc))
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("STATUS: SUBMISSION-READY", proc.stdout)

    def test_changed_document_cannot_reuse_the_verdict(self):
        doc = make_pptx(self.dir / "final.pptx")
        data = ready_audit()
        data["render"]["artifact_hash"] = data["package"]["artifact_hash"] = digest_of(doc)
        changed = make_pptx(self.dir / "changed.pptx", "가격이 바뀐 문서 " + LEDGER_TEXT)
        proc = self._gate(data, "--doc", str(changed))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("전달된 문서와 다르다", proc.stdout)

    def test_render_and_package_must_inspect_the_same_file(self):
        data = ready_audit()
        data["package"]["artifact_hash"] = "sha256:" + "b" * 64
        failures = pg.evaluate(data)
        self.assertIn("render and package artifact_hash differ — "
                      "두 검사가 서로 다른 파일을 대상으로 했다", failures)

    def test_placeholder_hash_is_not_a_digest(self):
        data = ready_audit()
        data["render"]["artifact_hash"] = "sha256:financial-proposal-fixture"
        self.assertTrue(any("must be a sha256 digest" in f for f in pg.evaluate(data)))


class StageAndLabelTests(unittest.TestCase):
    """F02 — 단계·라벨·설명이 하나의 판정에서 나온다."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_submission_audit_rejects_draft_stage(self):
        proc = run(UG, FIXTURES / "audit_ready_financial.json", "--stage", "draft", "--no-explain")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("--stage submission", proc.stdout + proc.stderr)

    def test_simulation_only_cannot_clear_submission(self):
        data = ready_audit()
        data["artifact_mode"] = "simulation-only"
        self.assertTrue(any("simulation-only" in f for f in pg.evaluate(data)))

    def test_draft_explain_does_not_say_submittable(self):
        data = ready_audit()
        data.update(mode="draft", artifact_required=False)
        data["checks"]["submission"] = False
        data["package"]["required"] = False
        data["submission"]["cleared"] = False
        failures = pg.evaluate(data)
        self.assertEqual(failures, [], failures)
        label, code = pg.readiness(data, failures)
        self.assertEqual((label, code), ("DRAFT-READY", 0))
        explain = pg.explain_markdown(data, [], failures)
        self.assertIn("DRAFT-READY", explain)
        self.assertNotIn("제출 가능", explain)

    def test_submission_explain_matches_its_label(self):
        data = ready_audit()
        self.assertEqual(pg.readiness(data, [])[0], "SUBMISSION-READY")
        self.assertIn("SUBMISSION-READY", pg.explain_markdown(data, [], []))


class MetaIntegrityTests(unittest.TestCase):
    """F03 — 변환 단계에서 입력이 조용히 바뀌거나 사라지지 않는다."""

    def _meta(self) -> dict:
        return json.loads((FIXTURES / "meta_sample.json").read_text(encoding="utf-8"))

    def test_string_evidence_is_not_split_into_characters(self):
        meta = self._meta()
        meta.setdefault("render", {})["evidence"] = "TBD"
        with self.assertRaises(ValueError) as ctx:
            bam.build_audit(meta)
        self.assertIn("must be an array of strings", str(ctx.exception))

    def test_non_object_requirement_is_not_dropped(self):
        meta = self._meta()
        meta["requirements"] = list(meta.get("requirements", [])) + ["필수 요구 문자열"]
        with self.assertRaises(ValueError) as ctx:
            bam.build_audit(meta)
        self.assertIn("requirements[", str(ctx.exception))

    def test_requirements_need_unique_ids(self):
        data = ready_audit()
        for item in data["requirements"]:
            item.pop("id", None)
        self.assertTrue(any("lacks a non-empty id" in f for f in pg.validate_schema(data)))
        data = ready_audit()
        data["requirements"][1]["id"] = data["requirements"][0]["id"]
        self.assertTrue(any("duplicate id" in f for f in pg.validate_schema(data)))

    def test_unhashable_enum_is_usage_error_not_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = ready_audit()
            data["mode"] = []
            p = Path(tmp) / "a.json"
            p.write_text(json.dumps(data), encoding="utf-8")
            proc = run(UG, p, "--no-explain")
            self.assertEqual(proc.returncode, 2)
            self.assertNotIn("Traceback", proc.stderr)
            self.assertIn("unsupported mode", proc.stdout + proc.stderr)


class EvidenceSeparationTests(unittest.TestCase):
    """F04 — 검토 상태·준수 상태·근거를 서로 대신하지 않는다."""

    def test_supported_claim_needs_evidence_in_submission(self):
        data = ready_audit()
        data["claims"][0]["evidence_refs"] = []
        self.assertTrue(any("without evidence_refs" in f for f in pg.evaluate(data)))

    def test_approved_but_unsupported_requirement_is_blocked(self):
        data = ready_audit()
        data["requirements"][0].update(support="X", fit="GAP")
        self.assertTrue(any("approved but not met" in f for f in pg.evaluate(data)))

    def test_buyer_granted_exception_is_accepted(self):
        data = ready_audit()
        data["requirements"][0].update(
            support="X", fit="GAP",
            exception={"granted_by": "발주처 계약담당", "evidence": ["질의응답 회신 2026-08-14 3항"]})
        self.assertEqual(pg.evaluate(data), [])

    def test_response_location_is_not_evidence(self):
        import bulk_matrix as bm
        rows = [bm.normalize({"id": "R1", "item": "요구", "mandatory": "필수",
                              "support": "O", "response_loc": "slide:99", "note": ""}, 1)]
        reqs = bm.to_audit_requirements(rows)
        self.assertEqual(reqs[0]["response_refs"], ["slide:99"])
        self.assertEqual(reqs[0]["evidence_refs"], [])


class DocumentScanTests(unittest.TestCase):
    """F05 — 차트 값과 패키지 유효성까지 실제로 읽는다."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def _chart_deck(self, title_xml: str) -> Path:
        return fixtures.pptx(self.dir / "chart.pptx", raw={
            "ppt/slides/slide1.xml": "<a:p><a:r><a:t>정상 본문</a:t></a:r></a:p>",
            "ppt/charts/chart1.xml":
                f"<c:chartSpace>{title_xml}<c:cat><c:strRef><c:strCache>"
                "<c:pt idx=\"0\"><c:v>ABC은행</c:v></c:pt>"
                "<c:pt idx=\"1\"><c:v>기타</c:v></c:pt>"
                "</c:strCache></c:strRef></c:cat></c:chartSpace>"})

    def _names(self) -> Path:
        p = self.dir / "names.txt"
        p.write_text("ABC은행\n", encoding="utf-8")
        return p

    def test_stale_name_in_titled_chart_is_found(self):
        # 제목(a:t)이 있으면 run 경로만 타고 범주값(c:v)을 건너뛰던 미탐지 재현.
        titled = self._chart_deck("<c:title><c:tx><c:rich><a:p><a:r>"
                                  "<a:t>연도별 실적</a:t></a:r></a:p></c:rich></c:tx></c:title>")
        proc = run(QG, titled, "--names", self._names())
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("ABC은행", proc.stdout)

    def test_stale_name_in_untitled_chart_is_found(self):
        proc = run(QG, self._chart_deck(""), "--names", self._names())
        self.assertEqual(proc.returncode, 1, proc.stdout)

    def test_clean_chart_passes(self):
        p = fixtures.pptx(self.dir / "clean.pptx", raw={
            "ppt/slides/slide1.xml": "<a:p><a:r><a:t>정상 본문</a:t></a:r></a:p>",
            "ppt/charts/chart1.xml":
                "<c:chartSpace><c:cat><c:strCache><c:pt><c:v>2025년</c:v></c:pt>"
                "</c:strCache></c:cat></c:chartSpace>"})
        proc = run(QG, p, "--names", self._names())
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_zip_renamed_to_pptx_is_usage_error(self):
        fake = self.dir / "fake.pptx"
        with zipfile.ZipFile(fake, "w") as z:
            z.writestr("readme.txt", "hello")
        proc = run(QG, fake)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("필수 파트 없음", proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
