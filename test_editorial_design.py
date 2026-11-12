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
import mapping_check  # noqa: E402
import package_inspect  # noqa: E402
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
        self.assertEqual(tidy_audit.warnings(report, 9, 10, 24, 700), [])

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

    def test_example_without_an_output_path_prints_usage(self):
        run = subprocess.run([sys.executable, str(EXAMPLE)], capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("Usage", run.stderr + run.stdout)


if __name__ == "__main__":
    unittest.main()
