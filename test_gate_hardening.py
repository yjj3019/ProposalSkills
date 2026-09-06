"""회귀 테스트 — 2026-09 게이트 신뢰성 감사에서 발견된 허위 통과(P0)·fail-open(P1) 재발 방지.

각 테스트는 감사 당시 실제로 '통과'했던 입력을 재현하고, 이제 차단·오류로 판정되는지 확인한다.
python-pptx/python-docx/openpyxl 없이 zipfile로 OOXML을 직접 조립한다(CI 의존성 최소화).
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
from test_support import run_script  # noqa: E402
sys.path.insert(0, str(REPO / "skills/create-proposal-document/scripts"))
sys.path.insert(0, str(REPO / "skills/create-winning-proposal/scripts"))
sys.path.insert(0, str(REPO / "skills/create-best-proposal/scripts"))
sys.path.insert(0, str(REPO))

import quality_gate as qg  # noqa: E402
import build_audit_from_meta as bam  # noqa: E402
import bulk_matrix as bm  # noqa: E402
import install_skill  # noqa: E402
import ooxml_fixtures as fixtures  # noqa: E402

QG = REPO / "skills/create-proposal-document/scripts/quality_gate.py"
UG = REPO / "skills/create-best-proposal/scripts/unified_gate.py"
FIXTURES = REPO / "skills/create-best-proposal/fixtures"

def pptx(path: Path, parts: dict[str, str]) -> None:
    """parts: {zip 내부 경로: 문단 텍스트}. 텍스트는 run 분할 상태로 기록한다."""
    fixtures.pptx(path, parts)


def docx(path: Path, body_xml: str, extra: dict[str, str] | None = None) -> None:
    fixtures.docx(path, body_xml, extra)


def blockers(path: Path, names=(), lang="ko", stage="submission") -> list[str]:
    return qg.blocking(qg.run(path, list(names), set(), lang, stage))


class QualityGateScanScopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_split_runs_and_nbsp_are_detected(self):
        p = self.dir / "d.pptx"
        fixtures.pptx(p, raw={
            # 실제 슬라이드는 루트가 하나다 — 문단만 나열한 조각은 XML 문서가 아니며
            # 실제 로더도 열지 못한다(픽스처가 실제 파일과 달라지면 안 된다).
            "ppt/slides/slide1.xml":
                "<p:sld>"
                "<a:p><a:r><a:t>업계 최</a:t></a:r><a:r><a:t>고 수준</a:t></a:r></a:p>"
                "<a:p><a:r><a:t>[NEEDS INPUT: PM]</a:t></a:r></a:p>"
                "<a:p><a:r><a:t>10</a:t></a:r><a:r><a:t>0% 무중</a:t></a:r>"
                "<a:r><a:t>단</a:t></a:r></a:p>"
                "</p:sld>"})
        found = " ".join(blockers(p))
        for needle in ("'최고'", "'100%'", "'무중단'", "needs input"):
            self.assertIn(needle, found)

    def test_notes_layouts_masters_charts_are_scanned(self):
        p = self.dir / "d.pptx"
        pptx(p, {
            "ppt/slides/slide1.xml": "정상 본문",
            "ppt/notesSlides/notesSlide1.xml": "ABC은행 발표 노트 TBD",
            "ppt/slideLayouts/slideLayout3.xml": "레이아웃 바닥글 최고",
            "ppt/slideMasters/slideMaster1.xml": "마스터 무중단",
            "ppt/charts/chart1.xml": "차트 제목 100%",
        })
        found = blockers(p, names=["ABC은행"])
        joined = " ".join(found)
        self.assertIn("노트 1", joined)
        self.assertIn("레이아웃 3", joined)
        self.assertIn("마스터 1", joined)
        self.assertIn("차트 1", joined)
        self.assertTrue(any("[금지 명칭]" in f for f in found))

    def test_hidden_or_orphan_slide_parts_are_scanned(self):
        p = self.dir / "d.pptx"
        fixtures.pptx(
            p,
            presentation='<p:presentation><p:sldIdLst><p:sldId id="256" r:id="rId2"/>'
                         '</p:sldIdLst></p:presentation>',
            raw={"ppt/_rels/presentation.xml.rels":
                 '<Relationships><Relationship Id="rId2" Target="slides/slide2.xml"/></Relationships>',
                 "ppt/slides/slide2.xml": "<a:p><a:r><a:t>표지</a:t></a:r></a:p>",
                 "ppt/slides/slide1.xml": "<a:p><a:r><a:t>고아 슬라이드 ABC은행</a:t></a:r></a:p>"})
        found = blockers(p, names=["ABC은행"])
        self.assertTrue(any("[금지 명칭]" in f and "슬라이드 2" in f for f in found), found)

    def test_docx_headers_footers_footnotes_comments_are_scanned(self):
        p = self.dir / "d.docx"
        docx(p, "<w:p><w:r><w:t>정상 본문</w:t></w:r></w:p>", {
            "word/header1.xml": "ABC은행 제안서",
            "word/footer2.xml": "무중단 보장",
            "word/footnotes.xml": "각주 TBD",
            "word/comments.xml": "검토 의견: 최고",
        })
        found = blockers(p, names=["ABC은행"])
        joined = " ".join(found)
        for label in ("머리말 1", "바닥글 2", "각주", "주석"):
            self.assertIn(label, joined)

    def test_docx_nested_textbox_does_not_truncate_paragraph(self):
        p = self.dir / "d.docx"
        body = ("<w:p><w:r><w:t>앞부분 </w:t></w:r>"
                "<w:r><w:pict><w:txbxContent><w:p><w:r><w:t>상자</w:t></w:r></w:p></w:txbxContent></w:pict></w:r>"
                "<w:r><w:t> 뒷부분: 최고 무중단 ABC은행 TBD</w:t></w:r></w:p>")
        docx(p, body)
        found = blockers(p, names=["ABC은행"])
        self.assertEqual(len(found), 4, found)
        self.assertTrue(all("문단 1" in f for f in found))

    def test_xlsx_cells_are_scanned(self):
        p = self.dir / "q.xlsx"
        fixtures.xlsx(p, {
            "xl/workbook.xml": '<workbook><sheets><sheet name="보안질의" sheetId="1"/></sheets></workbook>',
            "xl/sharedStrings.xml":
                "<sst><si><t>무중단 100%</t></si><si><r><t>ABC</t></r><r><t>은행</t></r></si></sst>",
            "xl/worksheets/sheet1.xml":
                '<worksheet><sheetData><row><c t="s"><v>0</v></c><c t="s"><v>1</v></c>'
                '<c t="inlineStr"><is><t>[NEEDS INPUT: 보안팀]</t></is></c></row></sheetData></worksheet>'})
        found = blockers(p, names=["ABC은행"])
        joined = " ".join(found)
        self.assertIn("시트 보안질의", joined)
        for needle in ("'무중단'", "'100%'", "[금지 명칭]", "needs input"):
            self.assertIn(needle, joined)


class QualityGateMatchingTests(unittest.TestCase):
    def test_banned_name_is_case_and_space_insensitive(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "d.pptx"
            pptx(p, {"ppt/slides/slide1.xml": "Prepared for ABC Bank / ABC 은행 귀중"})
            self.assertTrue(blockers(p, names=["abc bank"]))
            self.assertTrue(blockers(p, names=["ABC은행"]))

    def test_names_file_with_bom(self):
        with tempfile.TemporaryDirectory() as tmp:
            names = Path(tmp) / "n.txt"
            names.write_bytes("﻿ABC은행\n".encode("utf-8"))
            self.assertEqual(qg.read_names(names), ["ABC은행"])

    def test_title_and_technical_terms_are_not_overclaims(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "d.pptx"
            pptx(p, {"ppt/slides/slide1.xml":
                     "최고정보책임자(CIO) 승인, 최고경영자 보고. best practice 기반, unique identifier 부여"})
            self.assertEqual(blockers(p, lang="both"), [])
            pptx(p, {"ppt/slides/slide1.xml": "업계 최고의 best solution"})
            self.assertEqual(len(blockers(p, lang="both")), 2)

    def test_corrupt_or_unsupported_file_is_usage_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.pptx"
            bad.write_bytes(b"not a zip")
            proc = subprocess.run([sys.executable, str(QG), str(bad)], capture_output=True, text=True,
                                  encoding="utf-8", errors="replace")
            self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
            txt = Path(tmp) / "x.txt"
            txt.write_text("x")
            proc = subprocess.run([sys.executable, str(QG), str(txt)], capture_output=True, text=True,
                                  encoding="utf-8", errors="replace")
            self.assertEqual(proc.returncode, 2)

    def test_cp949_console_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "d.pptx"
            pptx(p, {"ppt/slides/slide1.xml": "정상 문서 — 대시 포함"})
            env = {**os.environ, "PYTHONIOENCODING": "cp949"}
            env.pop("PYTHONUTF8", None)
            proc = subprocess.run([sys.executable, str(QG), str(p)], capture_output=True, env=env)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            pptx(p, {"ppt/slides/slide1.xml": "최고 — 대시"})
            proc = subprocess.run([sys.executable, str(QG), str(p)], capture_output=True, env=env)
            self.assertEqual(proc.returncode, 1)


class UnifiedGateModeTests(unittest.TestCase):
    def _run(self, audit: Path, *extra: str):
        return run_script(UG, audit, *extra)

    def test_draft_audit_never_shows_submission_ready(self):
        data = json.loads((FIXTURES / "audit_ready_financial.json").read_text(encoding="utf-8"))
        data["mode"] = "draft"
        data["submission"] = {"cleared": False, "rehearsal_evidence": [], "receipt_plan": "",
                              "deadline": data["submission"]["deadline"]}
        with tempfile.TemporaryDirectory() as tmp:
            audit = Path(tmp) / "audit.json"
            audit.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            proc = self._run(audit, "--stage", "submission", "--no-explain")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertNotIn("SUBMISSION-READY", proc.stdout)
            self.assertIn("STATUS: DRAFT-READY", proc.stdout)
            self.assertIn("NOTE: audit.mode='draft'", proc.stdout)

    def _audit_bound_to(self, doc: Path, tmp: str) -> Path:
        """audit의 render/package 해시를 실제 파일 해시로 맞춘 사본을 만든다."""
        data = json.loads((FIXTURES / "audit_ready_financial.json").read_text(encoding="utf-8"))
        digest = "sha256:" + hashlib.sha256(doc.read_bytes()).hexdigest()
        data["render"]["artifact_hash"] = digest
        data["package"]["artifact_hash"] = digest
        audit = Path(tmp) / "bound.json"
        audit.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return audit

    def test_submission_ready_requires_the_matching_document(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / "final.pptx"
            pptx(doc, {"ppt/slides/slide1.xml": "정상 문서 총 사업비 37억원 · 구축비 25억원 · 유지보수비(3년) 12억원"})  # 원장과 같은 금액
            audit = self._audit_bound_to(doc, tmp)
            ok = self._run(audit, "--doc", str(doc), "--no-explain")
            self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
            self.assertIn("STATUS: SUBMISSION-READY", ok.stdout)

            # 1) 문서 없이 제출 판정을 받으려 하면 차단된다.
            none = self._run(audit, "--no-explain")
            self.assertEqual(none.returncode, 1)
            self.assertIn("--doc", none.stdout)
            # 2) --audit-only는 통과하되 SUBMISSION-READY로 표시하지 않는다.
            only = self._run(audit, "--audit-only", "--no-explain")
            self.assertEqual(only.returncode, 0, only.stdout)
            self.assertIn("STATUS: AUDIT-VALID", only.stdout)
            self.assertNotIn("STATUS: SUBMISSION-READY", only.stdout)
            # 3) 검토 이후 내용이 바뀐 파일은 과거 판정을 재사용하지 못한다.
            changed = Path(tmp) / "changed.pptx"
            pptx(changed, {"ppt/slides/slide1.xml": "가격이 바뀐 문서"})
            drift = self._run(audit, "--doc", str(changed), "--no-explain")
            self.assertEqual(drift.returncode, 1)
            self.assertIn("전달된 문서와 다르다", drift.stdout)

    def test_submission_audit_rejects_draft_stage(self):
        proc = self._run(FIXTURES / "audit_ready_financial.json", "--stage", "draft", "--no-explain")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("--stage submission", proc.stdout + proc.stderr)

    def test_bogus_gate_path_is_invalid_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "fake.py"
            fake.write_text("x = 1\n")
            env = {**os.environ, "PROPOSAL_GATE_PATH": str(fake)}
            proc = subprocess.run([sys.executable, str(UG), str(FIXTURES / "audit_ready_financial.json")],
                                  capture_output=True, text=True, encoding="utf-8", env=env)
            self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
            self.assertIn("INVALID", proc.stdout + proc.stderr)

    def test_document_gate_runs_under_cp949_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "d.pptx"
            pptx(p, {"ppt/slides/slide1.xml": "정상 — 문서 총 사업비 37억원 · 구축비 25억원 · 유지보수비(3년) 12억원"})
            env = {**os.environ, "PYTHONIOENCODING": "cp949"}
            audit = self._audit_bound_to(p, tmp)
            proc = subprocess.run([sys.executable, str(UG), str(audit),
                                   "--doc", str(p), "--no-explain"],
                                  capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


class BuildAuditTests(unittest.TestCase):
    def _meta(self) -> dict:
        return json.loads((FIXTURES / "meta_sample.json").read_text(encoding="utf-8"))

    def test_non_list_requirements_is_error_not_empty(self):
        meta = self._meta()
        meta["requirements"] = "R1 R2 all approved"
        with self.assertRaises(ValueError):
            bam.build_audit(meta)

    def test_string_booleans_are_errors(self):
        meta = self._meta()
        meta["submission"] = {"cleared": "no"}
        with self.assertRaises(ValueError):
            bam.build_audit(meta)
        meta = self._meta()
        meta["checks"] = {"consistency": "true", "arithmetic": True, "submission": True}
        with self.assertRaises(ValueError):
            bam.build_audit(meta)

    def test_slide_number_is_not_fabricated_into_evidence(self):
        meta = self._meta()
        meta["requirements"] = [{"id": "R1", "text": "표준 이미지", "mandatory": True, "state": "approved", "slide": 7}]
        meta["win_themes"] = []
        audit = bam.build_audit(meta)
        self.assertEqual(audit["requirements"][0]["evidence_refs"], [])
        self.assertTrue(any("approved without evidence_refs" in w for w in audit["_builder_warnings"]))
        with self.assertRaises(ValueError):
            bam.build_audit(meta, strict=True)


class BulkMatrixTests(unittest.TestCase):
    def test_blank_mandatory_is_mandatory_and_codes_normalized(self):
        row = bm.normalize({"id": "R1", "support": "o", "mandatory": ""}, 1)
        self.assertTrue(row["mandatory"])
        self.assertEqual(row["support"], "O")
        self.assertEqual(bm.normalize({"id": "R2", "support": "Y"}, 2)["support"], "O")
        self.assertEqual(bm.normalize({"id": "R3", "지원여부": "△"}, 3)["support"], "부분")

    def test_unknown_support_code_is_rejected(self):
        with self.assertRaises(ValueError):
            bm.normalize({"id": "R1", "support": "maybe"}, 1)

    def test_csv_multiline_cell_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "r.csv"
            p.write_text('id,text,support\nR1,"multi\nline item",O\n', encoding="utf-8")
            rows = bm.load_rows(p)
            self.assertEqual(rows[0]["text"], "multi\nline item")


class InstallSkillTests(unittest.TestCase):
    def test_name_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                install_skill.install(Path(tmp), "../../skills/create-winning-proposal")

    def test_partial_install_is_replaced_and_force_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "create-winning-proposal").mkdir()  # SKILL.md 없는 불완전 디렉터리
            target = install_skill.install(root, "create-winning-proposal")
            self.assertTrue((target / "SKILL.md").is_file())
            with self.assertRaises(SystemExit):
                install_skill.install(root, "create-winning-proposal")
            marker = target / "SKILL.md"
            marker.write_text("stale", encoding="utf-8")
            install_skill.install(root, "create-winning-proposal", force=True)
            self.assertNotEqual(marker.read_text(encoding="utf-8"), "stale")
            self.assertFalse(list(target.rglob("__pycache__")))


if __name__ == "__main__":
    unittest.main()
