"""Tests for the editorial-design tooling and the defects found while building the AI model comparison deck."""
from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).parent
DOC = ROOT / "skills/create-proposal-document/scripts"
EXAMPLE = ROOT / "skills/create-proposal-document/assets/examples/ai-model-comparison/make_deck.py"
sys.path.insert(0, str(DOC))
import contact_sheet  # noqa: E402,F401
import mapping_check  # noqa: E402
import package_inspect  # noqa: E402
import render_delta  # noqa: E402,F401
import review_ledger  # noqa: E402,F401
import tidy_audit  # noqa: E402


def make_deck(path: Path, *, sizes=(11,), misalign=False, rules=0, hidden=False, chart=False) -> None:
    from pptx import Presentation
    from pptx.chart.data import CategoryChartData
    from pptx.enum.chart import XL_CHART_TYPE
    from pptx.util import Inches, Pt
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    for i, size in enumerate(sizes):
        box = slide.shapes.add_textbox(Inches(1.0 + (0.05 if misalign and i % 2 else 0)), Inches(0.5 + i * 0.5), Inches(4), Inches(0.4))
        run = box.text_frame.paragraphs[0].add_run()
        run.text = f"line {i}"
        run.font.size = Pt(size)
    for i in range(rules):
        slide.shapes.add_shape(1, Inches(1), Inches(6 + i * 0.01), Inches(4), Inches(0.01))
    if hidden:
        slide._element.set("show", "0")
    if chart:
        data = CategoryChartData()
        data.categories = ["a", "b"]
        data.add_series("s", [1, 2])
        slide.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(1), Inches(3), Inches(4), Inches(3), data)
    prs.save(str(path))


def make_body_deck(path: Path, kind: str) -> None:
    """Three slides: cover, one content slide of the given kind, closing."""
    from pptx import Presentation
    from pptx.chart.data import CategoryChartData
    from pptx.enum.chart import XL_CHART_TYPE
    from pptx.util import Inches, Pt
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    for index in range(3):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        if index != 1:
            continue
        rows = 1 if kind == "sparse" else 5
        for i in range(rows):
            box = slide.shapes.add_textbox(Inches(1), Inches(2.0 + i * 1.0), Inches(8), Inches(0.9 if kind != "sparse" else 0.4))
            box.text_frame.paragraphs[0].add_run().text = f"row {i}"
            box.text_frame.paragraphs[0].runs[0].font.size = Pt(11)
        if kind == "chart":
            data = CategoryChartData()
            data.categories = ["a", "b"]
            data.add_series("s", [1, 2])
            slide.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(9.2), Inches(2.0), Inches(3.4), Inches(4.5), data)
    prs.save(str(path))


class TidyAuditTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def report(self, **kw):
        deck = self.dir / "d.pptx"
        make_deck(deck, **kw)
        return tidy_audit.measure(deck)

    def test_an_orderly_deck_is_clean(self):
        report = self.report(sizes=(11, 11, 13))
        self.assertEqual(report["font_sizes"], [11.0, 13.0])
        self.assertEqual(report["near_miss"], 0)
        self.assertEqual(tidy_audit.warnings(report, 9, 10, 24, 700, min_fill=0.0, max_text_only=1.0), [])

    def test_too_many_sizes_are_reported(self):
        report = self.report(sizes=(8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 20))
        self.assertTrue(any("font sizes" in w for w in tidy_audit.warnings(report, 9, 10, 24, 700)))

    def test_almost_aligned_boxes_are_counted_but_exact_and_clearly_different_are_not(self):
        self.assertGreater(self.report(sizes=(11, 11, 11, 11), misalign=True)["near_miss"], 0)
        self.assertEqual(self.report(sizes=(11, 11, 11, 11))["near_miss"], 0)

    def test_rule_clutter_and_density_are_reported_per_slide(self):
        report = self.report(rules=30)
        self.assertEqual(report["slides"][0]["rules"], 30)
        self.assertTrue(any("thin rules" in w for w in tidy_audit.warnings(report, 9, 10, 24, 700)))
        self.assertTrue(any("characters" in w for w in tidy_audit.warnings(report, 9, 10, 24, 3)))

    def test_a_half_empty_slide_is_reported_as_sparse(self):
        deck = self.dir / "s.pptx"
        make_body_deck(deck, "sparse")
        report = tidy_audit.measure(deck)
        self.assertLess(report["slides"][1]["fill"], 0.2)
        self.assertTrue(any("fills" in w for w in tidy_audit.warnings(report, 9, 10, 24, 700)))

    def test_a_full_text_only_slide_is_reported_but_a_chart_makes_it_visual(self):
        text_deck, chart_deck = self.dir / "t.pptx", self.dir / "c.pptx"
        make_body_deck(text_deck, "text")
        make_body_deck(chart_deck, "chart")
        text = tidy_audit.measure(text_deck)
        self.assertGreaterEqual(text["slides"][1]["fill"], 0.8)
        self.assertFalse(text["slides"][1]["visual"])
        self.assertTrue(any("text or table only" in w for w in tidy_audit.warnings(text, 9, 10, 24, 700)))
        chart = tidy_audit.measure(chart_deck)
        self.assertTrue(chart["slides"][1]["visual"])
        self.assertEqual(tidy_audit.warnings(chart, 9, 10, 24, 700), [])

    def test_cover_and_closing_are_not_judged_for_fill(self):
        deck = self.dir / "t.pptx"
        make_body_deck(deck, "chart")
        report = tidy_audit.measure(deck)
        self.assertEqual([s["slide"] for s in tidy_audit.content_slides(report)], [2])

    def test_cli_exit_codes(self):
        deck = self.dir / "d.pptx"
        make_deck(deck, sizes=tuple(range(8, 20)))
        run = lambda *a: subprocess.run([sys.executable, str(DOC / "tidy_audit.py"), *a], capture_output=True, text=True,
                                        encoding="utf-8", errors="replace")
        self.assertEqual(run(str(deck)).returncode, 0)
        self.assertEqual(run(str(deck), "--strict").returncode, 1)
        self.assertEqual(json.loads(run(str(deck), "--json").stdout)["font_sizes"][0], 8.0)
        drm = self.dir / "drm.pptx"
        drm.write_bytes(b"<## DRM ##>")
        result = run(str(drm))
        self.assertEqual(result.returncode, 2)
        self.assertIn("NOT INSPECTED", result.stderr)
        self.assertEqual(run(str(self.dir / "missing.pptx")).returncode, 2)


class ContactSheetTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        from PIL import Image
        for name, color in (("page-10.png", "red"), ("page-2.png", "green"), ("page-1.png", "blue"), ("page-3.png", "white"), ("page-4.png", "gray")):
            Image.new("RGB", (160, 90), color).save(self.dir / name)

    def run_cli(self, *args):
        import contact_sheet
        return contact_sheet.main([str(a) for a in args])

    def test_pages_are_taken_in_natural_order(self):
        import contact_sheet
        self.assertEqual([p.name for p in contact_sheet.page_images(self.dir)],
                         ["page-1.png", "page-2.png", "page-3.png", "page-4.png", "page-10.png"])

    def test_one_sheet_holds_all_pages_and_splits_when_asked(self):
        out = self.dir / "out" / "sheet.png"
        with redirect_stdout(io.StringIO()):
            self.assertEqual(self.run_cli(self.dir, "-o", out, "--cols", 3, "--thumb", 200), 0)
        from PIL import Image
        with Image.open(out) as sheet:
            self.assertGreater(sheet.width, 3 * 200)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(self.run_cli(self.dir, "-o", self.dir / "split.png", "--per-sheet", 2), 0)
        self.assertEqual(sorted(p.name for p in self.dir.glob("split_*.png")), ["split_1.png", "split_2.png", "split_3.png"])

    def test_a_missing_folder_an_empty_folder_and_an_unreadable_image_exit_2(self):
        empty = self.dir / "empty"
        empty.mkdir()
        with redirect_stderr(io.StringIO()):
            self.assertEqual(self.run_cli(self.dir / "nope"), 2)
            self.assertEqual(self.run_cli(empty), 2)
            (self.dir / "page-5.png").write_bytes(b"<## DRM ##>")
            err = io.StringIO()
            with redirect_stderr(err):
                self.assertEqual(self.run_cli(self.dir, "-o", self.dir / "x.png"), 2)
            self.assertIn("NOT INSPECTED", err.getvalue())
        self.assertFalse((self.dir / "x.png").exists())


class PackageInspectDefectTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def test_a_hidden_slide_is_found_where_powerpoint_stores_it(self):
        deck = self.dir / "h.pptx"
        make_deck(deck, hidden=True)
        self.assertTrue(any(f.startswith("[숨김]") for f in package_inspect.run(deck)))
        make_deck(deck, hidden=False)
        self.assertFalse(any(f.startswith("[숨김]") for f in package_inspect.run(deck)))

    def test_chart_workbooks_are_information_not_an_attachment_blocker(self):
        deck = self.dir / "c.pptx"
        make_deck(deck, chart=True)
        findings = package_inspect.run(deck)
        self.assertTrue(any(f.startswith("[차트데이터]") for f in findings))
        self.assertFalse(any(f.startswith("[임베드]") for f in findings))
        self.assertFalse(any("차트데이터" in f for f in package_inspect.blocking(findings)))

    def test_a_real_attachment_still_blocks(self):
        deck = self.dir / "a.pptx"
        make_deck(deck)
        with zipfile.ZipFile(deck, "a") as z:
            z.writestr("ppt/embeddings/oleObject1.bin", b"x")
        self.assertTrue(any(f.startswith("[임베드]") for f in package_inspect.blocking(package_inspect.run(deck))))

    def test_tracked_changes_in_a_docx_block(self):
        doc = self.dir / "t.docx"
        with zipfile.ZipFile(doc, "w") as z:
            z.writestr("word/document.xml", "<w:body><w:ins w:author='k'><w:r><w:t>x</w:t></w:r></w:ins></w:body>")
        self.assertTrue(any(f.startswith("[추적변경]") for f in package_inspect.blocking(package_inspect.run(doc))))


class MappingCheckDefectTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def test_ids_split_across_runs_are_joined(self):
        deck = self.dir / "d.pptx"
        with zipfile.ZipFile(deck, "w") as z:
            z.writestr("ppt/slides/slide1.xml", "<p><a:p><a:r><a:t>REQ-</a:t></a:r><a:r><a:t>001</a:t></a:r></a:p>"
                       "<a:p><a:r><a:t>REQ-0002</a:t></a:r></a:p></p>")
        self.assertEqual(mapping_check.ids_in_doc(deck), {"REQ-001", "REQ-002"})

    def test_adjacent_paragraphs_do_not_glue_ids_together(self):
        deck = self.dir / "d.pptx"
        with zipfile.ZipFile(deck, "w") as z:
            z.writestr("ppt/slides/slide1.xml", "<a:p><a:r><a:t>REQ-1</a:t></a:r></a:p><a:p><a:r><a:t>2 pages</a:t></a:r></a:p>")
        self.assertEqual(mapping_check.ids_in_doc(deck), {"REQ-001"})

    def test_long_ids_are_kept_not_dropped_or_truncated(self):
        self.assertEqual(mapping_check.normalize_id("REQ-12345"), "REQ-12345")
        doc = self.dir / "d.md"
        doc.write_text("see REQ-12345 and REQ-7", encoding="utf-8")
        self.assertEqual(mapping_check.ids_in_doc(doc), {"REQ-12345", "REQ-007"})

    def test_docx_headers_and_footnotes_are_read(self):
        doc = self.dir / "d.docx"
        with zipfile.ZipFile(doc, "w") as z:
            z.writestr("word/document.xml", "<w:p><w:r><w:t>REQ-001</w:t></w:r></w:p>")
            z.writestr("word/header1.xml", "<w:p><w:r><w:t>REQ-009</w:t></w:r></w:p>")
            z.writestr("word/footnotes.xml", "<w:p><w:r><w:t>REQ-010</w:t></w:r></w:p>")
        self.assertEqual(mapping_check.ids_in_doc(doc), {"REQ-001", "REQ-009", "REQ-010"})


class BuildDeckMetadataTests(unittest.TestCase):
    def test_template_author_and_comment_are_cleared(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            spec = tmp / "s.json"
            spec.write_text(json.dumps({"meta": {"title": "T", "subtitle": "s", "doc_name": "d", "buyer": "b", "bidder": "c",
                                                 "date": "2099-01-01", "require_req_ids": False},
                                        "slides": [{"type": "cover"}]}), encoding="utf-8")
            out = tmp / "o.pptx"
            run = subprocess.run([sys.executable, str(DOC / "build_deck.py"), str(spec), "-o", str(out)],
                                 capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            from pptx import Presentation
            props = Presentation(str(out)).core_properties
            self.assertEqual((props.author, props.last_modified_by, props.comments, props.title), ("", "", "", "T"))
            with zipfile.ZipFile(out) as z:
                core = z.read("docProps/core.xml").decode("utf-8")
            self.assertNotIn("python-pptx", core)
            self.assertNotIn("Steve Canny", core)


class AtAGlanceSlideTypeTests(unittest.TestCase):
    META = {"title": "T", "subtitle": "s", "doc_name": "d", "buyer": "b", "bidder": "c", "date": "2099-01-01", "require_req_ids": False}

    def build(self, slide: dict):
        sys.path.insert(0, str(DOC))
        import build_deck
        builder = build_deck.DeckBuilder({"meta": self.META, "slides": [slide]}, None, False)
        builder.build()
        return builder

    def names(self, builder) -> set[str]:
        return {shape.name for shape in builder.prs.slides[0].shapes}

    def scoreboard(self, **kw):
        rows = [{"item": f"항목{i}", "a": "가", "b": "나", "win": w} for i, w in enumerate("ab=a")]
        return {"type": "scoreboard", "title": "t", "lead": "l", "a_name": "A", "b_name": "B", "rule": "낮은 가격", "rows": rows, **kw}

    def test_scoreboard_marks_one_winner_per_row_and_prints_the_tally(self):
        builder = self.build(self.scoreboard())
        self.assertEqual(builder.violations, [])
        self.assertTrue({"BODY_SCOREITEM1", "BODY_SCORETRACK4", "BODY_SCOREVERDICT3", "BODY_SCORERULE"} <= self.names(builder))
        rule = next(sh for sh in builder.prs.slides[0].shapes if sh.name == "BODY_SCORERULE")
        self.assertIn("A 2 · B 1 · 동일 1", rule.text_frame.text)

    def test_scoreboard_without_a_rule_or_with_a_bad_win_is_flagged(self):
        no_rule = self.build(self.scoreboard(rule=""))
        self.assertTrue(any("rule" in w for w in no_rule.warnings))
        bad = self.build(self.scoreboard(rows=[{"item": "x", "a": "1", "b": "2", "win": "z"}]))
        self.assertTrue(any("win" in v for v in bad.violations))
        long = self.build(self.scoreboard(rows=[{"item": str(i), "a": "1", "b": "2", "win": "a"} for i in range(11)]))
        self.assertTrue(any("10" in v for v in long.violations))

    def test_triage_needs_two_or_three_columns_with_items(self):
        col = lambda n: {"head": f"h{n}", "models": f"m{n}", "items": [{"situation": "s", "evidence": "e"}]}
        ok = self.build({"type": "triage", "title": "t", "lead": "l", "columns": [col(1), col(2), col(3)]})
        self.assertEqual(ok.violations, [])
        self.assertTrue({"BODY_TRIAGEITEM3_1", "BODY_TRIAGEWHY1_1"} <= self.names(ok))
        self.assertTrue(self.build({"type": "triage", "title": "t", "lead": "l", "columns": [col(1)]}).violations)
        empty = {"head": "h", "models": "m", "items": []}
        self.assertTrue(self.build({"type": "triage", "title": "t", "lead": "l", "columns": [col(1), empty]}).violations)

    def test_weights_must_add_up_to_100_and_stay_within_five_segments(self):
        seg = lambda *p: [{"label": f"L{i}", "pct": v, "note": "n"} for i, v in enumerate(p)]
        ok = self.build({"type": "weights", "title": "t", "lead": "l", "segments": seg(50, 20, 30)})
        self.assertEqual(ok.violations, [])
        self.assertEqual(len([n for n in self.names(ok) if n.startswith("BODY_WEIGHT") and "NOTE" not in n]), 3)
        self.assertTrue(any("합계" in v for v in self.build({"type": "weights", "title": "t", "lead": "l", "segments": seg(50, 20, 20)}).violations))
        self.assertTrue(any("5" in v for v in self.build({"type": "weights", "title": "t", "lead": "l", "segments": seg(20, 20, 20, 20, 10, 10)}).violations))

    def test_a_deck_with_all_three_passes_the_layout_lint(self):
        col = lambda n: {"head": f"h{n}", "models": f"m{n}", "items": [{"situation": "s", "evidence": "e"}]}
        spec = {"meta": self.META, "slides": [{"type": "cover"}, self.scoreboard(),
                {"type": "triage", "title": "t", "lead": "l", "columns": [col(1), col(2)]},
                {"type": "weights", "title": "t", "lead": "l", "segments": [{"label": "a", "pct": 60, "note": "n"}, {"label": "b", "pct": 40, "note": "n"}]}]}
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "s.json").write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            build = subprocess.run([sys.executable, str(DOC / "build_deck.py"), str(tmp / "s.json"), "-o", str(tmp / "o.pptx"), "--strict"],
                                   capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            check = subprocess.run([sys.executable, str(DOC / "deck_check.py"), str(tmp / "o.pptx"), "--stage", "draft"],
                                   capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)


class EditorialThemeTests(unittest.TestCase):
    FIX = ROOT / "skills/create-proposal-document/fixtures/e2e-mini-rfp/slides.json"

    def build(self, theme):
        sys.path.insert(0, str(DOC))
        import build_deck
        spec = json.loads(self.FIX.read_text(encoding="utf-8"))
        if theme:
            spec["meta"]["theme"] = theme
        builder = build_deck.DeckBuilder(spec, None, False)
        builder.build()
        return builder

    def test_unknown_theme_is_rejected(self):
        with self.assertRaises(ValueError):
            self.build("neon")

    def test_editorial_frame_has_no_title_rule_a_paper_background_and_a_serif_title(self):
        builder = self.build("editorial")
        self.assertEqual(builder.violations, [])
        slide = builder.prs.slides[2]
        names = {sh.name: sh for sh in slide.shapes}
        self.assertNotIn("TITLE_RULE", names)
        self.assertEqual(str(slide.background.fill.fore_color.rgb), "FAF8F4")
        run = names["TITLE"].text_frame.paragraphs[0].runs[0]
        self.assertEqual(run.font.name, "Noto Serif KR SemiBold")

    def test_the_standard_frame_is_unchanged_but_every_run_now_carries_the_east_asian_typeface(self):
        builder = self.build(None)
        slide = builder.prs.slides[2]
        names = {sh.name: sh for sh in slide.shapes}
        self.assertIn("TITLE_RULE", names)
        self.assertEqual(str(slide.background.fill.fore_color.rgb), "FFFFFF")
        r_pr = names["TITLE"].text_frame.paragraphs[0].runs[0]._r.find("{http://schemas.openxmlformats.org/drawingml/2006/main}rPr")
        for tag in ("latin", "ea", "cs"):
            self.assertIsNotNone(r_pr.find("{http://schemas.openxmlformats.org/drawingml/2006/main}" + tag), tag)

    def test_editorial_tables_use_hairlines_and_cards_a_top_rule(self):
        builder = self.build("editorial")
        table = next(sh for sh in builder.prs.slides[2].shapes if sh.has_table)
        xml = table._element.xml
        self.assertIn("a:lnB", xml)
        names = {sh.name for slide in builder.prs.slides for sh in slide.shapes}
        self.assertTrue({"BODY_CARDTITLE1", "BODY_CARDHDR1"} <= names)

    def test_an_editorial_deck_passes_the_layout_lint(self):
        spec = json.loads(self.FIX.read_text(encoding="utf-8"))
        spec["meta"]["theme"] = "editorial"
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "s.json").write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            build = subprocess.run([sys.executable, str(DOC / "build_deck.py"), str(tmp / "s.json"), "-o", str(tmp / "o.pptx"), "--strict"],
                                   capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            check = subprocess.run([sys.executable, str(DOC / "deck_check.py"), str(tmp / "o.pptx"), "--stage", "draft"],
                                   capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)


class ReviewLedgerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name).resolve()
        self.deck = self.dir / "deck.pptx"
        make_body_deck(self.deck, "chart")
        self.png = self.dir / "png"
        self.png.mkdir()
        from PIL import Image
        for i in (1, 2, 3):
            Image.new("RGB", (160, 90), "white").save(self.png / f"page-{i}.png")
        self.ledger = self.dir / "ledger.json"

    def run_cli(self, *args):
        import review_ledger
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = review_ledger.main([str(a) for a in args])
        return code, out.getvalue() + err.getvalue()

    def fill(self, overrides=None):
        overrides = overrides or {}
        for n in (1, 2, 3):
            kw = dict(viewed="full", plain="pass", busy="pass", glance="pass", unfinished="pass")
            kw.update(overrides.get(n, {}))
            args = ["set", self.ledger, "--slide", n]
            for key, value in kw.items():
                args += [f"--{key}", value]
            self.assertEqual(self.run_cli(*args)[0], 0)
        self.assertEqual(self.run_cli("set", self.ledger, "--slide", 1, "--revisions", 1)[0], 0)

    def init(self):
        code, _ = self.run_cli("init", self.deck, "-o", self.ledger, "--png-dir", self.png, "--engine", "LibreOffice")
        self.assertEqual(code, 0)

    def test_a_fresh_ledger_is_incomplete_and_a_filled_one_is_complete(self):
        self.init()
        code, out = self.run_cli("check", self.ledger)
        self.assertEqual(code, 1)
        self.assertIn("not viewed", out)
        self.fill()
        code, out = self.run_cli("check", self.ledger)
        self.assertEqual(code, 0, out)
        self.assertIn("COMPLETE", out)

    def test_a_changed_deck_makes_the_ledger_stale(self):
        self.init()
        self.fill()
        self.deck.write_bytes(self.deck.read_bytes() + b"x")
        code, out = self.run_cli("check", self.ledger)
        self.assertEqual(code, 1)
        self.assertIn("stale", out)

    def test_a_chart_slide_on_a_contact_sheet_only_is_refused(self):
        self.init()
        self.fill({2: {"viewed": "sheet"}})
        code, out = self.run_cli("check", self.ledger)
        self.assertEqual(code, 1)
        self.assertIn("full size", out)

    def test_open_major_findings_missing_images_old_images_and_failed_rungs_are_refused(self):
        self.init()
        self.fill()
        self.assertEqual(self.run_cli("set", self.ledger, "--slide", 2, "--finding", "Major|open|axis unit missing|")[0], 0)
        self.assertIn("open Major", self.run_cli("check", self.ledger)[1])
        self.assertEqual(self.run_cli("set", self.ledger, "--slide", 2, "--glance", "fail")[0], 0)
        self.assertIn("rung 'glance'", self.run_cli("check", self.ledger)[1])
        (self.png / "page-2.png").unlink()
        self.assertIn("image is missing", self.run_cli("check", self.ledger)[1])

    def test_an_image_older_than_the_deck_is_refused(self):
        import os
        self.init()
        self.fill()
        old = self.deck.stat().st_mtime - 3600
        os.utime(self.png / "page-3.png", (old, old))
        self.assertIn("older than the deck", self.run_cli("check", self.ledger)[1])

    def test_waivers_need_a_reason_no_revision_is_refused_and_scores_are_not_allowed(self):
        self.init()
        self.fill({2: {"glance": "waived"}})
        self.assertIn("waived without a reason", self.run_cli("check", self.ledger)[1])
        self.assertEqual(self.run_cli("set", self.ledger, "--slide", 2, "--waived-reason", "agenda is a list by nature")[0], 0)
        self.assertEqual(self.run_cli("check", self.ledger)[0], 0)
        data = json.loads(self.ledger.read_text(encoding="utf-8"))
        data["revisions"] = 0
        data["score"] = 9
        self.ledger.write_text(json.dumps(data), encoding="utf-8")
        out = self.run_cli("check", self.ledger)[1]
        self.assertIn("no revision recorded", out)
        self.assertIn("score fields", out)

    def test_usage_errors_exit_2(self):
        self.assertEqual(self.run_cli("init", self.dir / "missing.pptx", "-o", self.ledger)[0], 2)
        self.assertEqual(self.run_cli("check", self.dir / "missing.json")[0], 2)


class SlideDeltaTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name).resolve()

    def edited_copy(self, source: Path, slide_index: int, suffix: str) -> Path:
        from pptx import Presentation
        prs = Presentation(str(source))
        box = next(sh for sh in prs.slides[slide_index].shapes if sh.has_text_frame and sh.text_frame.text.strip())
        box.text_frame.paragraphs[0].runs[0].text += suffix
        target = self.dir / f"edited{slide_index}.pptx"
        prs.save(str(target))
        return target

    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = review_ledger.main([str(a) for a in args])
        return code, out.getvalue() + err.getvalue()

    def test_delta_marks_changed_unchanged_and_net_removed_slides(self):
        import render_delta
        self.assertEqual(render_delta.delta(["a", "b", "c"], ["a", "x", "c"]), ([2], [1, 3], 0))
        self.assertEqual(render_delta.delta(["a", "b", "c"], ["a", "c"]), ([], [1, 2], 1))
        self.assertEqual(render_delta.delta([], ["a"]), ([1], [], 0))
        self.assertEqual(render_delta.delta(["a", "a"], ["a", "a", "a"]), ([3], [1, 2], 0))

    def test_only_the_edited_slide_changes_its_hash(self):
        deck = self.dir / "d.pptx"
        make_body_deck(deck, "text")
        before = review_ledger.slide_hashes(deck)
        after = review_ledger.slide_hashes(self.edited_copy(deck, 1, " edited"))
        self.assertEqual([a == b for a, b in zip(before, after)], [True, False, True])

    def test_deleting_a_slide_does_not_change_the_hashes_of_the_others(self):
        from pptx import Presentation
        deck = self.dir / "d.pptx"
        make_body_deck(deck, "text")
        before = review_ledger.slide_hashes(deck)
        prs = Presentation(str(deck))
        first = prs.slides._sldIdLst[0]
        prs.part.drop_rel(first.rId)
        prs.slides._sldIdLst.remove(first)
        shorter = self.dir / "shorter.pptx"
        prs.save(str(shorter))
        self.assertEqual(review_ledger.slide_hashes(shorter), before[1:])

    def test_sync_keeps_unchanged_verdicts_and_resets_only_the_changed_slide(self):
        import os
        from PIL import Image
        deck = self.dir / "d.pptx"
        make_body_deck(deck, "chart")
        png = self.dir / "png"
        png.mkdir()
        for i in (1, 2, 3):
            Image.new("RGB", (160, 90), "white").save(png / f"page-{i}.png")
        ledger = self.dir / "ledger.json"
        self.assertEqual(self.cli("init", deck, "-o", ledger, "--png-dir", png, "--engine", "LibreOffice")[0], 0)
        for n in (1, 2, 3):
            for key in ("--plain", "--busy", "--glance", "--unfinished"):
                self.cli("set", ledger, "--slide", n, key, "pass")
            self.cli("set", ledger, "--slide", n, "--viewed", "full")
        self.cli("set", ledger, "--slide", 1, "--revisions", 1)
        self.assertEqual(self.cli("check", ledger)[0], 0)
        deck.write_bytes(self.edited_copy(deck, 1, " edited").read_bytes())
        for path in png.iterdir():
            os.utime(path, None)                      # a fresh render touches every page image
        self.assertIn("stale", self.cli("check", ledger)[1])
        code, out = self.cli("sync", ledger, "--png-dir", png)
        self.assertEqual(code, 0)
        self.assertIn("kept 2", out)
        self.assertIn("[2]", out)
        status, report = self.cli("check", ledger)
        self.assertEqual(status, 1)
        self.assertIn("slide 2: not viewed", report)
        self.assertNotIn("slide 1:", report)
        self.assertNotIn("slide 3:", report)
        for key in ("--plain", "--busy", "--glance", "--unfinished"):
            self.cli("set", ledger, "--slide", 2, key, "pass")
        self.cli("set", ledger, "--slide", 2, "--viewed", "full")
        self.assertEqual(self.cli("check", ledger)[0], 0)
        data = json.loads(ledger.read_text(encoding="utf-8"))
        data["slides"][2]["hash"] = "tampered"
        ledger.write_text(json.dumps(data), encoding="utf-8")
        self.assertIn("slide 3: changed since it was judged", self.cli("check", ledger)[1])

    def test_a_theme_colour_or_slide_size_change_changes_every_slide_hash(self):
        import re
        from pptx import Presentation
        from pptx.enum.dml import MSO_THEME_COLOR
        from pptx.opc.constants import RELATIONSHIP_TYPE as RT
        from pptx.util import Inches
        prs = Presentation()
        for _ in range(3):
            slide = prs.slides.add_slide(prs.slide_layouts[6])
            shape = slide.shapes.add_shape(1, Inches(1), Inches(1), Inches(2), Inches(1))
            shape.fill.solid()
            shape.fill.fore_color.theme_color = MSO_THEME_COLOR.ACCENT_1
        base = self.dir / "base.pptx"
        prs.save(str(base))
        before = review_ledger.slide_hashes(base)
        themed = Presentation(str(base))
        part = themed.slide_master.part.part_related_by(RT.THEME)
        changed = re.sub(rb'(<a:accent1>\s*<a:srgbClr val=")[0-9A-Fa-f]{6}', rb'\g<1>112233', part.blob, count=1)
        self.assertNotEqual(changed, part.blob)
        part._blob = changed
        themed_path = self.dir / "themed.pptx"
        themed.save(str(themed_path))
        self.assertTrue(all(a != b for a, b in zip(before, review_ledger.slide_hashes(themed_path))))
        resized = Presentation(str(base))
        resized.slide_width = resized.slide_width + Inches(1)
        resized_path = self.dir / "resized.pptx"
        resized.save(str(resized_path))
        self.assertTrue(all(a != b for a, b in zip(before, review_ledger.slide_hashes(resized_path))))

    def mocked_render(self, deck, out, *, pages=None, environment=None, extra=()):
        """Run render_delta.main with the engines replaced: pages are generated, never rendered."""
        from unittest import mock
        from PIL import Image
        import render_delta
        from pptx import Presentation
        count = len(Presentation(str(deck)).slides)

        def fake_pngs(pdf, pages_dir, dpi):
            pages_dir.mkdir(parents=True, exist_ok=True)
            for old in pages_dir.iterdir():
                if old.is_file() and render_delta.OWN_PAGE.match(old.name):
                    old.unlink()
            made = []
            for n in range(1, count + 1):
                shade = (pages or {}).get(n, 255)
                path = pages_dir / f"page-{n:02d}.png"
                Image.new("RGB", (160, 90), (shade, shade, shade)).save(path)
                made.append(path)
            return made

        env = environment or {"soffice": "LibreOffice test", "converter": "fake"}
        buffer = io.StringIO()
        with mock.patch.object(render_delta, "find_soffice", return_value="soffice"), \
                mock.patch.object(render_delta, "environment", return_value=env), \
                mock.patch.object(render_delta, "to_pdf", return_value=self.dir / "x.pdf"), \
                mock.patch.object(render_delta, "to_pngs", side_effect=fake_pngs), redirect_stdout(buffer), redirect_stderr(buffer):
            code = render_delta.main([str(deck), "-o", str(out), *extra])
        return code, buffer.getvalue()

    def many_slides_deck(self, name="many.pptx", count=13):
        from pptx import Presentation
        deck = self.dir / name
        prs = Presentation()
        for i in range(count):
            slide = prs.slides.add_slide(prs.slide_layouts[6])
            slide.shapes.add_textbox(0, 0, 100, 100).text_frame.text = f"slide {i}"
        prs.save(str(deck))
        return deck

    def test_more_than_twelve_changed_slides_report_every_sheet_and_only_its_own_sheets_are_replaced(self):
        deck = self.many_slides_deck()
        out = self.dir / "render"
        code, text = self.mocked_render(deck, out)
        self.assertEqual(code, 0, text)
        first = json.loads((out / "delta.json").read_text(encoding="utf-8"))
        self.assertEqual([Path(p).name for p in first["changed_sheets"]], ["changed_sheet_1.png", "changed_sheet_2.png"])
        self.assertEqual([Path(p).name for p in first["sheets"]], ["sheet_1.png", "sheet_2.png"])
        for path in first["changed_sheets"] + first["sheets"]:
            self.assertTrue(Path(path).is_file(), path)
        self.assertIn("changed_sheet_1.png", text)
        self.assertIn("changed_sheet_2.png", text)
        # things the user keeps in the folder must survive, even with a matching name
        for name in ("changed_sheet_9.png", "sheet_mine.png", "notes.png"):
            (out / name).write_bytes(b"mine")
        (out / "pages" / "keep.txt").write_text("mine", encoding="utf-8")
        (out / "pages" / "cover.png").write_bytes(b"mine")
        (out / "pages" / "page-99.png").write_bytes(b"mine")       # matches the tool's own naming but was never recorded
        from pptx import Presentation
        prs = Presentation(str(deck))
        prs.slides[4].shapes[0].text_frame.paragraphs[0].runs[0].text += " edited"
        prs.save(str(deck))
        code, text = self.mocked_render(deck, out)
        self.assertEqual(code, 0, text)
        second = json.loads((out / "delta.json").read_text(encoding="utf-8"))
        self.assertEqual(second["changed"], [5])
        self.assertEqual([Path(p).name for p in second["changed_sheets"]], ["changed_sheet.png"])
        self.assertFalse((out / "changed_sheet_1.png").exists())      # its own earlier sheet is replaced
        self.assertFalse((out / "changed_sheet_2.png").exists())
        self.assertTrue((out / "sheet_1.png").is_file())               # the full sheet is not rewritten, so it stays
        for name in ("changed_sheet_9.png", "sheet_mine.png", "notes.png"):
            self.assertEqual((out / name).read_bytes(), b"mine", name)
        self.assertEqual((out / "pages" / "keep.txt").read_text(encoding="utf-8"), "mine")
        self.assertEqual((out / "pages" / "cover.png").read_bytes(), b"mine")
        self.assertEqual((out / "pages" / "page-99.png").read_bytes(), b"mine")
        self.assertFalse((out / "_pdf").exists())                       # the PDF lives in a temporary folder, not in the user's folder

    def test_a_file_the_tool_is_about_to_write_but_did_not_record_is_never_overwritten(self):
        deck = self.many_slides_deck("five.pptx", 3)
        out = self.dir / "render"
        self.assertEqual(self.mocked_render(deck, out)[0], 0)
        bigger = self.many_slides_deck("bigger.pptx", 5)
        (out / "pages" / "page-04.png").write_bytes(b"mine")           # the next run would write page-04.png
        code, text = self.mocked_render(bigger, out)
        self.assertEqual(code, 2)
        self.assertIn("page-04.png", text)
        self.assertEqual((out / "pages" / "page-04.png").read_bytes(), b"mine")
        self.assertTrue((out / "pages" / "page-01.png").is_file())      # nothing else was touched
        (out / "pages" / "page-04.png").unlink()
        state_file = out / "render_state.json"
        state = json.loads(state_file.read_text(encoding="utf-8"))
        state["created"] = []                                          # forget its own sheets: they now look like a user's files
        state_file.write_text(json.dumps(state), encoding="utf-8")
        before = (out / "sheet.png").read_bytes()
        code, text = self.mocked_render(bigger, out)
        self.assertEqual(code, 2)
        self.assertIn("not created by render_delta", text)
        self.assertEqual((out / "sheet.png").read_bytes(), before)

    def test_a_folder_that_is_not_this_tools_is_refused_before_anything_is_written(self):
        deck = self.many_slides_deck("few.pptx", 3)
        foreign = self.dir / "photos"
        foreign.mkdir()
        (foreign / "holiday.png").write_bytes(b"mine")
        code, text = self.mocked_render(deck, foreign)
        self.assertEqual(code, 2)
        self.assertIn("not created by render_delta", text)
        self.assertEqual([p.name for p in foreign.iterdir()], ["holiday.png"])
        empty = self.dir / "empty"
        empty.mkdir()
        self.assertEqual(self.mocked_render(deck, empty)[0], 0)
        self.assertEqual(self.mocked_render(deck, self.dir / "brand-new")[0], 0)

    def test_the_real_converter_writes_into_a_staging_folder_and_install_replaces_only_recorded_pages(self):
        try:
            import pymupdf
        except ImportError:
            self.skipTest("PyMuPDF is needed to make a PDF here")
        import render_delta
        pdf = self.dir / "one.pdf"
        doc = pymupdf.open()
        doc.new_page()
        doc.save(str(pdf))
        doc.close()
        staged = render_delta.to_pngs(pdf, self.dir / "staging", 40)
        self.assertEqual([p.name for p in staged], ["page-01.png"])
        pages = self.dir / "pages"
        pages.mkdir()
        (pages / "page-01.png").write_bytes(b"recorded")
        (pages / "page-07.png").write_bytes(b"recorded")
        (pages / "page-99.png").write_bytes(b"mine")
        (pages / "cover.png").write_bytes(b"mine")
        installed = render_delta.install_pages(staged, pages, ["page-01.png", "page-07.png"])
        self.assertEqual([p.name for p in installed], ["page-01.png"])
        self.assertNotEqual((pages / "page-01.png").read_bytes(), b"recorded")
        self.assertFalse((pages / "page-07.png").exists())             # recorded and no longer produced: removed
        self.assertEqual((pages / "page-99.png").read_bytes(), b"mine")
        self.assertEqual((pages / "cover.png").read_bytes(), b"mine")
        with self.assertRaises(FileExistsError):
            render_delta.install_pages(staged, pages, [])               # page-01.png is now not recorded: refused
        self.assertEqual((pages / "page-99.png").read_bytes(), b"mine")

    def test_a_changed_render_environment_or_a_changed_picture_makes_the_slide_count_as_changed(self):
        deck = self.many_slides_deck("few.pptx", 3)
        out = self.dir / "render"
        self.assertEqual(self.mocked_render(deck, out)[0], 0)
        code, text = self.mocked_render(deck, out)
        self.assertEqual(json.loads((out / "delta.json").read_text(encoding="utf-8"))["changed"], [])
        code, text = self.mocked_render(deck, out, pages={2: 200})          # same content, a different picture (font or engine)
        result = json.loads((out / "delta.json").read_text(encoding="utf-8"))
        self.assertEqual((result["changed"], result["render_changed"]), ([2], [2]))
        self.assertIn("rendered differently", text)
        code, text = self.mocked_render(deck, out, environment={"soffice": "LibreOffice newer", "converter": "fake"})
        result = json.loads((out / "delta.json").read_text(encoding="utf-8"))
        self.assertEqual(result["changed"], [1, 2, 3])
        self.assertTrue(result["environment_changed"])
        self.assertIn("render environment changed", text)

    def judged_ledger(self, deck_kind="chart"):
        from PIL import Image
        deck = self.dir / "led.pptx"
        make_body_deck(deck, deck_kind)
        png = self.dir / "png"
        png.mkdir()
        for i in (1, 2, 3):
            Image.new("RGB", (160, 90), "white").save(png / f"page-{i}.png")
        ledger = self.dir / "ledger.json"
        self.assertEqual(self.cli("init", deck, "-o", ledger, "--png-dir", png, "--engine", "LibreOffice")[0], 0)
        for n in (1, 2, 3):
            for key in ("--plain", "--busy", "--glance", "--unfinished"):
                self.cli("set", ledger, "--slide", n, key, "pass")
            self.cli("set", ledger, "--slide", n, "--viewed", "full" if n == 2 else "sheet")
        self.cli("set", ledger, "--slide", 1, "--revisions", 1)
        self.assertEqual(self.cli("check", ledger)[0], 0)
        return deck, png, ledger

    def slide_state(self, ledger, number):
        return json.loads(ledger.read_text(encoding="utf-8"))["slides"][number - 1]

    def test_sync_does_not_carry_a_verdict_that_has_no_recorded_image_hash(self):
        deck, png, ledger = self.judged_ledger()
        data = json.loads(ledger.read_text(encoding="utf-8"))
        for slide in data["slides"]:
            slide.pop("image_sha256", None)                 # a ledger written before hashes were recorded
        ledger.write_text(json.dumps(data), encoding="utf-8")
        code, out = self.cli("sync", ledger, "--png-dir", png)
        self.assertEqual(code, 0)
        self.assertIn("kept 0", out)
        for n in (1, 2, 3):
            self.assertEqual(self.slide_state(ledger, n)["viewed"], "none")

    def test_a_different_image_path_or_a_changed_image_clears_the_viewing_and_the_rungs(self):
        from PIL import Image
        deck, png, ledger = self.judged_ledger()
        Image.new("RGB", (160, 90), "red").save(png / "other.png")
        self.cli("set", ledger, "--slide", 2, "--image", "png/other.png")
        state = self.slide_state(ledger, 2)
        self.assertEqual((state["viewed"], state["rungs"]["plain"], state["image_sha256"]), ("none", None, ""))
        self.assertIn("slide 2: not viewed", self.cli("check", ledger)[1])
        # viewing it again records the new picture but the verdict still has to be given again
        self.cli("set", ledger, "--slide", 2, "--viewed", "full")
        state = self.slide_state(ledger, 2)
        self.assertEqual((state["viewed"], state["rungs"]["plain"]), ("full", None))
        self.assertTrue(state["image_sha256"])
        self.assertIn("rung 'plain'", self.cli("check", ledger)[1])
        for key in ("--plain", "--busy", "--glance", "--unfinished"):
            self.cli("set", ledger, "--slide", 2, key, "pass")
        self.assertEqual(self.cli("check", ledger)[0], 0)
        # the same path, new content: set --image alone must not keep the verdict
        Image.new("RGB", (160, 90), "blue").save(png / "other.png")
        self.cli("set", ledger, "--slide", 2, "--image", "png/other.png")
        self.assertEqual(self.slide_state(ledger, 2)["viewed"], "none")
        # looking again after the image changed also clears the rungs
        self.cli("set", ledger, "--slide", 2, "--viewed", "full")
        for key in ("--plain", "--busy", "--glance", "--unfinished"):
            self.cli("set", ledger, "--slide", 2, key, "pass")
        Image.new("RGB", (160, 90), "green").save(png / "other.png")
        self.cli("set", ledger, "--slide", 2, "--viewed", "full")
        self.assertIsNone(self.slide_state(ledger, 2)["rungs"]["busy"])

    def test_a_cover_seen_on_a_sheet_is_held_to_the_same_image_proof(self):
        from PIL import Image
        deck, png, ledger = self.judged_ledger()
        Image.new("RGB", (160, 90), "black").save(png / "page-1.png")
        status, report = self.cli("check", ledger)
        self.assertEqual(status, 1)
        self.assertIn("slide 1: the image changed after it was viewed", report)
        self.assertIn("1", self.cli("sync", ledger, "--png-dir", png)[1])
        self.assertEqual(self.slide_state(ledger, 1)["viewed"], "none")

    def test_an_open_major_finding_of_a_slide_that_no_longer_exists_is_not_lost(self):
        deck, png, ledger = self.judged_ledger()
        self.cli("set", ledger, "--slide", 2, "--finding", "Major|open|chart axis has no unit|")
        edited = self.edited_copy(deck, 1, " rewritten")
        deck.write_bytes(edited.read_bytes())
        import os
        for path in png.iterdir():
            os.utime(path, None)
        self.assertEqual(self.cli("sync", ledger, "--png-dir", png)[0], 0)
        data = json.loads(ledger.read_text(encoding="utf-8"))
        self.assertEqual([f["text"] for f in data["orphaned_findings"]], ["chart axis has no unit"])
        for key in ("--plain", "--busy", "--glance", "--unfinished"):
            self.cli("set", ledger, "--slide", 2, key, "pass")
        self.cli("set", ledger, "--slide", 2, "--viewed", "full")
        status, report = self.cli("check", ledger)
        self.assertEqual(status, 1)
        self.assertIn("open Major finding from old slide 2", report)
        data = json.loads(ledger.read_text(encoding="utf-8"))
        data["orphaned_findings"][0]["status"] = "fixed"
        ledger.write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(self.cli("check", ledger)[0], 0)

    def test_the_ledger_ties_a_verdict_to_the_image_that_was_viewed(self):
        from PIL import Image
        deck = self.dir / "led.pptx"
        make_body_deck(deck, "chart")
        png = self.dir / "png"
        png.mkdir()
        for i in (1, 2, 3):
            Image.new("RGB", (160, 90), "white").save(png / f"page-{i}.png")
        ledger = self.dir / "ledger.json"
        self.assertEqual(self.cli("init", deck, "-o", ledger, "--png-dir", png, "--engine", "LibreOffice")[0], 0)
        for n in (1, 2, 3):
            for key in ("--plain", "--busy", "--glance", "--unfinished"):
                self.cli("set", ledger, "--slide", n, key, "pass")
            self.cli("set", ledger, "--slide", n, "--viewed", "full")
        self.cli("set", ledger, "--slide", 1, "--revisions", 1)
        self.assertEqual(self.cli("check", ledger)[0], 0)
        Image.new("RGB", (160, 90), "black").save(png / "page-2.png")    # same deck, but slide 2 renders differently now
        status, report = self.cli("check", ledger)
        self.assertEqual(status, 1)
        self.assertIn("slide 2: the image changed after it was viewed", report)
        code, out = self.cli("sync", ledger, "--png-dir", png)
        self.assertEqual(code, 0)
        self.assertIn("[2] render differently", out)
        self.assertIn("slide 2: not viewed", self.cli("check", ledger)[1])
        # recording a rung later does not re-record the image hash, only viewing does
        before = json.loads(ledger.read_text(encoding="utf-8"))["slides"][1].get("image_sha256")
        self.cli("set", ledger, "--slide", 2, "--plain", "pass")
        self.assertEqual(json.loads(ledger.read_text(encoding="utf-8"))["slides"][1].get("image_sha256"), before)

    def test_render_delta_reports_only_the_edited_slide(self):
        import importlib.util
        import shutil
        import render_delta
        if not render_delta.find_soffice() or not (shutil.which("pdftoppm") or importlib.util.find_spec("pymupdf")):
            self.skipTest("LibreOffice and a PDF-to-PNG converter are needed")
        deck = self.dir / "d.pptx"
        make_body_deck(deck, "chart")
        out = self.dir / "render"
        with redirect_stdout(io.StringIO()):
            self.assertEqual(render_delta.main([str(deck), "-o", str(out)]), 0)
        first = json.loads((out / "delta.json").read_text(encoding="utf-8"))
        self.assertEqual(first["changed"], [1, 2, 3])
        with redirect_stdout(io.StringIO()):
            self.assertEqual(render_delta.main([str(self.edited_copy(deck, 1, " edited")), "-o", str(out)]), 0)
        second = json.loads((out / "delta.json").read_text(encoding="utf-8"))
        self.assertEqual((second["changed"], second["unchanged"]), ([2], [1, 3]))
        self.assertEqual([Path(p).name for p in second["changed_sheets"]], ["changed_sheet.png"])
        self.assertTrue((out / "changed_sheet.png").is_file())
        self.assertEqual(len(list((out / "pages").glob("page-*.png"))), 3)

    def test_render_delta_without_a_deck_or_an_engine_exits_2(self):
        from unittest import mock
        import render_delta
        deck = self.dir / "d.pptx"
        make_body_deck(deck, "text")
        with redirect_stderr(io.StringIO()):
            self.assertEqual(render_delta.main([str(self.dir / "nope.pptx"), "-o", str(self.dir / "o")]), 2)
            with mock.patch.object(render_delta, "find_soffice", return_value=None):
                self.assertEqual(render_delta.main([str(deck), "-o", str(self.dir / "o")]), 2)

    def test_contact_sheet_takes_real_slide_numbers_and_is_not_wider_than_its_tiles(self):
        import contact_sheet
        from PIL import Image
        files = []
        for name in ("a.png", "b.png"):
            Image.new("RGB", (160, 90), "white").save(self.dir / name)
            files.append(self.dir / name)
        out = self.dir / "s.png"
        contact_sheet.build_sheets(files, out, cols=4, thumb=200, per_sheet=12, labels=["5", "12"])
        with Image.open(out) as sheet:
            self.assertLess(sheet.width, 3 * 200)


class ExampleDeckTests(unittest.TestCase):
    def test_example_builds_and_is_orderly(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "example.pptx"
            run = subprocess.run([sys.executable, str(EXAMPLE), str(out)], capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            report = tidy_audit.measure(out)
            self.assertEqual(len(report["slides"]), 17)
            self.assertLessEqual(len(report["font_sizes"]), 9, report["font_sizes"])
            self.assertEqual(report["runs_without_size"], 0)
            self.assertLessEqual(report["near_miss"], 10)
            self.assertLessEqual(report["chars_max"], 700)
            self.assertEqual(tidy_audit.warnings(report, 9, 10, 24, 700), [])   # body fill and text-only share too

    def test_example_without_an_output_path_prints_usage(self):
        run = subprocess.run([sys.executable, str(EXAMPLE)], capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("Usage", run.stderr + run.stdout)


if __name__ == "__main__":
    unittest.main()
