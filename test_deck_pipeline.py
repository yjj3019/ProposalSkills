"""End-to-end golden: mini RFP → slides.json → build_deck → deck_check → quality_gate → meta → audit → unified_gate. fixtures/e2e-mini-rfp covers the entire skill pipeline; skip only rendering if LibreOffice is absent."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
from test_support import Result, run_script  # noqa: E402
DOC = REPO / "skills/create-proposal-document"
BEST = REPO / "skills/create-best-proposal"
FIX = DOC / "fixtures/e2e-mini-rfp"
PY = sys.executable

sys.path.insert(0, str(DOC / "scripts"))
import build_deck  # noqa: E402
import deck_check  # noqa: E402


def run(*args: object, **kw) -> Result:
    """Run skill scripts in-process by default (see test_support); supplying env promotes execution to a child process for encoding-contract checks."""
    return run_script(Path(str(args[0])), *args[1:], **kw)


class DeckPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        cls.pptx = cls.out / "draft.pptx"
        proc = run(DOC / "scripts/build_deck.py", FIX / "slides.json", "-o", cls.pptx, "--strict")
        assert proc.returncode == 0, proc.stdout + proc.stderr
        cls.build_out = proc.stdout

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    # ---- build_deck -----------------------------------------------------------
    def test_build_covers_every_layout_type(self):
        spec = json.loads((FIX / "slides.json").read_text(encoding="utf-8"))
        used = {s["type"] for s in spec["slides"]}
        self.assertEqual(used | {"bullets"}, build_deck.ALL_TYPES, f"미사용 레이아웃: {build_deck.ALL_TYPES - used}")
        self.assertIn("17 slides", self.build_out)

    def test_roles_named_on_body_slides(self):
        from pptx import Presentation
        prs = Presentation(str(self.pptx))
        body = [s for s in prs.slides if deck_check.slide_kind(s) == "body"]
        self.assertGreaterEqual(len(body), 8)
        for s in body:
            names = {sh.name for sh in deck_check.iter_shapes(s.shapes)}
            self.assertTrue({"HEADER", "TITLE", "LEAD", "CAPTION", "REQID", "FOOTER", "PAGENO"} <= names, names)

    def test_matrix_auto_paginates_with_header_repeat(self):
        spec = {"meta": {"title": "t", "bidder": "b"},
                "slides": [{"type": "matrix", "title": "조견표", "lead": "L", "rows_per_slide": 5,
                            "rows": [{"id": f"R{i}", "text": "x", "support": "O", "response_loc": "p", "note": ""}
                                     for i in range(1, 13)]}]}
        p = self.out / "matrix.pptx"
        (self.out / "m.json").write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        proc = run(DOC / "scripts/build_deck.py", self.out / "m.json", "-o", p)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        from pptx import Presentation
        prs = Presentation(str(p))
        self.assertEqual(len(prs.slides), 3)
        titles = [deck_check.shape_text(next(sh for sh in s.shapes if sh.name == "TITLE")) for s in prs.slides]
        self.assertIn("(1/3)", titles[0])
        self.assertIn("(계속 3/3)", titles[2])

    def test_split_matrix_footer_matches_unambiguous_page_rows(self):
        from pptx import Presentation

        rows = [{"id": f"R{i}", "text": f"요구 {i}", "support": "O",
                 "response_loc": "p", "note": ""} for i in range(1, 5)]
        for req_ids, expected in ((["R1", "R2", "R3", "R4"],
                                   ["대응 요구: R1, R2", "대응 요구: R3, R4"]),
                                  (None, ["대응 요구: R1, R2", "대응 요구: R3, R4"]),
                                  (["R1", "SHARED"],
                                   ["대응 요구: R1, SHARED", "대응 요구: R1, SHARED"])):
            with self.subTest(req_ids=req_ids):
                slide = {"type": "matrix", "title": "조견표", "lead": "대응을 설명합니다",
                         "rows_per_slide": 2, "rows": rows}
                if req_ids is not None:
                    slide["req_ids"] = req_ids
                spec = {"meta": {"title": "t", "bidder": "b"}, "slides": [slide]}
                source = self.out / "matrix-footer.json"
                output = self.out / "matrix-footer.pptx"
                source.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
                proc = run(DOC / "scripts/build_deck.py", source, "-o", output)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                prs = Presentation(str(output))
                actual = [deck_check.shape_text(next(sh for sh in s.shapes if sh.name == "REQID"))
                          for s in prs.slides]
                self.assertEqual(actual, expected)
                self.assertEqual(sum(len(sh.table.rows) - 1 for s in prs.slides for sh in s.shapes
                                     if sh.has_table), 4)

    def test_strict_fails_on_missing_lead_and_page_limit(self):
        spec = {"meta": {"title": "t", "page_limit": 1},
                "slides": [{"type": "cover"}, {"type": "bullets", "title": "x", "items": ["a"]}]}
        (self.out / "bad.json").write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        proc = run(DOC / "scripts/build_deck.py", self.out / "bad.json", "-o", self.out / "bad.pptx", "--strict")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("리드문 없음", proc.stdout)
        self.assertIn("페이지 제한", proc.stdout)

    def test_unknown_type_is_usage_error(self):
        (self.out / "u.json").write_text(json.dumps({"slides": [{"type": "hero"}]}), encoding="utf-8")
        proc = run(DOC / "scripts/build_deck.py", self.out / "u.json", "-o", self.out / "u.pptx")
        self.assertEqual(proc.returncode, 2)

    # ---- deck_check -----------------------------------------------------------
    def test_deck_check_passes_golden_and_counts_body_pages(self):
        proc = run(DOC / "scripts/deck_check.py", self.pptx, "--max-pages", "40", "--exclude-cover-toc",
                   "--require-req-ids", "--stage", "draft")
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("본문 14장 / 제한 40장", proc.stdout)

    def test_deck_check_reports_unresolved_body_and_table_fonts(self):
        from pptx import Presentation
        from pptx.util import Inches, Pt

        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        for name, top, text, size in (("TITLE", .3, "제목", 24),
                                      ("LEAD", 1, "근거 있는 제안", 18),
                                      ("BODY", 2, "중요 수치 123", None),
                                      ("HEADER", 3, "머리말", None)):
            shape = slide.shapes.add_textbox(Inches(1), Inches(top), Inches(5), Inches(.5))
            shape.name = name
            run = shape.text_frame.paragraphs[0].add_run()
            run.text = text
            if size is not None:
                run.font.size = Pt(size)
        table = slide.shapes.add_table(1, 1, Inches(1), Inches(4), Inches(3), Inches(.5)).table
        table.cell(0, 0).text = "표의 수치 456"
        saved = self.out / "unresolved-font.pptx"
        prs.save(saved)
        prs = Presentation(str(saved))

        def check():
            return deck_check.lint(prs, max_pages=None, exclude_cover_toc=False,
                                   min_font=14, require_req_ids=False, stage="draft")

        self.assertTrue(any("폰트 크기 2개 run 미검사" in item for item in check()))
        from contextlib import redirect_stdout
        from io import StringIO
        from unittest.mock import patch
        report = self.out / "unresolved-render.json"
        with patch.object(deck_check, "render", return_value=([], {"tool": "simulated"})), redirect_stdout(StringIO()):
            result = deck_check.main([str(saved), "--profile", "detailed-submission", "--emit-render", str(report)])
        evidence = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(result, 1)
        self.assertTrue(evidence["render_succeeded"])
        self.assertFalse(evidence["verified"])
        self.assertFalse(evidence["layout_checked"])
        self.assertFalse(evidence["visual_review_approved"])
        self.assertTrue(any("폰트 크기" in item and "미검사" in item for item in evidence["evidence"]))
        slide = prs.slides[0]
        next(sh for sh in slide.shapes if sh.name == "BODY").text_frame.paragraphs[0].runs[0].font.size = Pt(13)
        next(sh for sh in slide.shapes if sh.has_table).table.cell(0, 0).text_frame.paragraphs[0].runs[0].font.size = Pt(14)
        items = check()
        self.assertFalse(any("폰트 크기" in item and "미검사" in item for item in items))
        self.assertTrue(any("본문 최소 폰트 13pt" in item for item in items))

    @unittest.skipUnless(shutil.which("soffice"), "LibreOffice is required for real rendering")
    def test_unresolved_fonts_prevent_verified_after_real_render(self):
        from pptx import Presentation
        from pptx.util import Inches, Pt

        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        for name, top, text, size in (("TITLE", .3, "제목", 24),
                                      ("LEAD", 1, "근거 있는 제안", 18),
                                      ("BODY", 2, "중요 수치 123", None)):
            shape = slide.shapes.add_textbox(Inches(1), Inches(top), Inches(5), Inches(.5))
            shape.name = name
            text_run = shape.text_frame.paragraphs[0].add_run()
            text_run.text = text
            if size is not None:
                text_run.font.size = Pt(size)
        deck = self.out / "real-font-render.pptx"
        report = self.out / "real-font-render.json"
        prs.save(deck)
        args = (DOC / "scripts/deck_check.py", deck, "--profile", "detailed-submission",
                "--min-font", "14", "--render", "--emit-render", report)
        proc = run(*args)
        evidence = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertTrue(evidence["render_succeeded"])
        self.assertFalse(evidence["verified"])
        self.assertFalse(evidence["layout_checked"])
        self.assertTrue(any("폰트 크기" in item and "미검사" in item for item in evidence["evidence"]))
        next(sh for sh in slide.shapes if sh.name == "BODY").text_frame.paragraphs[0].runs[0].font.size = Pt(14)
        prs.save(deck)
        proc = run(*args)
        evidence = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertTrue(evidence["render_succeeded"])
        self.assertTrue(evidence["verified"])
        self.assertTrue(evidence["layout_checked"])
        self.assertFalse(evidence["visual_review_approved"])

    def test_deck_check_blocks_small_font_and_missing_lead(self):
        spec = {"meta": {"title": "t"},
                "slides": [{"type": "bullets", "title": "x", "lead": "", "items": ["a"]}]}
        (self.out / "nl.json").write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        run(DOC / "scripts/build_deck.py", self.out / "nl.json", "-o", self.out / "nl.pptx")
        proc = run(DOC / "scripts/deck_check.py", self.out / "nl.pptx")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("리드문 없음", proc.stdout)
        proc = run(DOC / "scripts/deck_check.py", self.pptx, "--min-font", "12")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("최소 폰트", proc.stdout)

    def test_deck_check_page_limit_blocks(self):
        proc = run(DOC / "scripts/deck_check.py", self.pptx, "--max-pages", "10")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("> 페이지 제한 10장", proc.stdout)

    def test_deck_check_heuristic_on_external_deck(self):
        from pptx import Presentation
        prs = Presentation()
        s = prs.slides.add_slide(prs.slide_layouts[6])
        s.shapes.add_textbox(0, 0, 100000, 100000).text_frame.text = "제목만 있는 외부 덱"
        p = self.out / "ext.pptx"
        prs.save(str(p))
        proc = run(DOC / "scripts/deck_check.py", p)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("[휴리스틱]", proc.stdout)

    @unittest.skipUnless(shutil.which("soffice") or shutil.which("libreoffice"), "LibreOffice 없음")
    def test_render_emits_verified_block(self):
        rj = self.out / "render.json"
        proc = run(DOC / "scripts/deck_check.py", self.pptx, "--render", "--emit-render", rj, "--max-pages", "40")
        self.assertEqual(proc.returncode, 0, proc.stdout)
        block = json.loads(rj.read_text(encoding="utf-8"))
        self.assertTrue(block["verified"])
        self.assertTrue(block["artifact_hash"].startswith("sha256:"))
        self.assertTrue(any("렌더 OK" in e for e in block["evidence"]))

    def test_emit_render_without_soffice_is_not_verified(self):
        rj = self.out / "render_none.json"
        env = {"PATH": str(self.out)}  # Empty PATH to prevent locating soffice.
        import os
        env.update({k: v for k, v in os.environ.items() if k not in {"PATH"}})
        proc = run(DOC / "scripts/deck_check.py", self.pptx, "--emit-render", rj, env=env)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        block = json.loads(rj.read_text(encoding="utf-8"))
        self.assertFalse(block["verified"])
        self.assertTrue(any("NOT INSPECTED" in e for e in block["evidence"]))

    # ---- quality_gate on the built deck ----------------------------------------
    def test_quality_gate_draft_warns_submission_blocks(self):
        qg = DOC / "scripts/quality_gate.py"
        draft = run(qg, self.pptx, "--stage", "draft")
        self.assertEqual(draft.returncode, 0, draft.stdout)  # [NEEDS INPUT]·○○ are draft warnings.
        self.assertIn("[검토필요]", draft.stdout)
        sub = run(qg, self.pptx, "--stage", "submission")
        self.assertEqual(sub.returncode, 1)
        self.assertIn("needs input", sub.stdout)

    # ---- meta → audit → unified_gate -------------------------------------------
    def test_mid_draft_meta_is_blocked_with_worklist(self):
        audit = self.out / "audit.json"
        proc = run(BEST / "scripts/build_audit_from_meta.py", FIX / "meta.json", "-o", audit)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(audit.read_text(encoding="utf-8"))
        self.assertFalse(data["artifact_required"])  # draft default.
        gate = run(BEST / "scripts/unified_gate.py", audit, "--no-explain")
        self.assertEqual(gate.returncode, 1)
        for needle in ("requirement R6 is not approved", "blocking input I1 is open",
                       "missing attachment: 유사실적증명서(2건)", "unresolved token"):
            self.assertIn(needle, gate.stdout)
        self.assertIn("STATUS: BLOCKED", gate.stdout)

    def test_closed_draft_reaches_draft_ready(self):
        meta = json.loads((FIX / "meta.json").read_text(encoding="utf-8"))
        meta["bid_decision"] = "bid"
        meta["bid_conditions"] = []
        meta["eligibility"][0]["met"] = True
        for r in meta["requirements"]:
            if r["id"] == "R6":
                r.update(state="approved", evidence_refs=["첨부:유사실적증명서 2건"], reviewer="영업")
        meta["attachments"][1]["present"] = True
        meta["inputs"][0]["status"] = "closed"
        meta["unresolved_tokens"] = []
        mp = self.out / "meta_ready.json"
        mp.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        audit = self.out / "audit_ready.json"
        self.assertEqual(run(BEST / "scripts/build_audit_from_meta.py", mp, "-o", audit, "--strict").returncode, 0)
        gate = run(BEST / "scripts/unified_gate.py", audit, "--no-explain")
        self.assertEqual(gate.returncode, 0, gate.stdout)
        self.assertIn("STATUS: DRAFT-READY", gate.stdout)
        self.assertNotIn("SUBMISSION-READY", gate.stdout)
        # Promoting the same audit to submission must block on rendering, package, and clearance requirements.
        meta["mode"] = "submission"
        mp.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        run(BEST / "scripts/build_audit_from_meta.py", mp, "-o", audit)
        gate = run(BEST / "scripts/unified_gate.py", audit, "--no-explain")
        self.assertEqual(gate.returncode, 1)
        self.assertIn("render verification is missing", gate.stdout)


if __name__ == "__main__":
    unittest.main()
