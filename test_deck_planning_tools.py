"""plan_coverage (compare slide plans by requirement coverage) and palette_from_image (reference image -> contrast-safe tokens)."""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "skills/create-proposal-document/scripts"))
import build_deck  # noqa: E402
import palette_from_image as palette  # noqa: E402
import plan_coverage as coverage  # noqa: E402

MATRIX = """| REQ-ID | 요구사항 | 장표 |
|---|---|---|
| REQ-001 | 구축 | 3 |
| REQ-002 | 이관 | 4 |
| REQ-003 | 보안 | 5 |
| REQ-004 | 운영 | 6 |
"""


def run(module, argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = module.main(argv)
    return code, out.getvalue(), err.getvalue()


class PlanCoverageTests(unittest.TestCase):
    ids = {"REQ-001", "REQ-002", "REQ-003", "REQ-004"}

    def test_answered_listed_only_and_unknown_are_told_apart(self):
        text = ("## 슬라이드 1\nREQ-001: 노드 12대를 8개월 안에 구축하는 일정과 근거를 보인다\n"
                "| REQ-002 | |\n"
                "REQ-009: 공고에 없는 요구를 인용한 줄이라 알 수 없는 ID로 잡힌다\n")
        info = coverage.analyse_plan(text, self.ids)
        self.assertEqual(info["answered"], {"REQ-001"})
        self.assertEqual(info["listed_only"], {"REQ-002"})
        self.assertEqual(info["unknown"], {"REQ-009"})

    def test_id_spellings_are_normalised(self):
        info = coverage.analyse_plan("REQ_1 이 요구에 대한 충분히 긴 메시지가 같은 줄에 있다\n", self.ids)
        self.assertEqual(info["answered"], {"REQ-001"})

    def test_union_only_in_and_gaps(self):
        a = "REQ-001 구축 일정과 근거를 충분히 설명하는 문장\nREQ-002 이관 방식과 검증 절차를 설명하는 문장\n"
        b = "REQ-002 이관 방식과 검증 절차를 설명하는 문장\nREQ-003 보안 통제 항목과 증빙을 설명하는 문장\n"
        report = coverage.compare(self.ids, {"A": a, "B": b}, {i: 1.0 for i in self.ids})
        self.assertEqual(report["union_coverage_percent"], 75.0)
        self.assertEqual(report["only_in"], {"A": ["REQ-001"], "B": ["REQ-003"]})
        self.assertEqual(report["covered_by_no_plan"], ["REQ-004"])
        self.assertEqual(report["base_plan"], "A")
        self.assertEqual(report["take_from_other_plans"], ["REQ-003"])

    def test_weights_change_the_winner(self):
        a = "REQ-001 구축 일정과 근거를 충분히 설명하는 문장\nREQ-002 이관 방식과 검증 절차를 설명하는 문장\n"
        b = "REQ-003 보안 통제 항목과 증빙을 설명하는 문장\n"
        equal = coverage.compare(self.ids, {"A": a, "B": b}, {i: 1.0 for i in self.ids})
        weighted = coverage.compare(self.ids, {"A": a, "B": b},
                                    {"REQ-001": 1, "REQ-002": 1, "REQ-003": 20, "REQ-004": 1})
        self.assertEqual(equal["base_plan"], "A")
        self.assertEqual(weighted["base_plan"], "B")

    def test_cli_exit_codes_and_unknown_id_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "matrix.md").write_text(MATRIX, encoding="utf-8")
            (tmp / "a.md").write_text("REQ-001 구축 일정과 근거를 충분히 설명하는 문장\n", encoding="utf-8")
            (tmp / "b.md").write_text("REQ-002 이관 방식과 검증 절차를 설명하는 문장\n", encoding="utf-8")
            (tmp / "c.md").write_text("REQ-077 공고에 없는 요구를 충분히 길게 인용한 문장\n", encoding="utf-8")
            code, out, _ = run(coverage, [str(tmp / "matrix.md"), str(tmp / "a.md"), str(tmp / "b.md")])
            self.assertEqual(code, 0)
            self.assertIn("union coverage: 50.0%", out)
            self.assertEqual(run(coverage, [str(tmp / "matrix.md"), str(tmp / "a.md"), str(tmp / "c.md")])[0], 1)
            self.assertEqual(run(coverage, [str(tmp / "matrix.md"), str(tmp / "a.md"), str(tmp / "b.md"),
                                            "--min-coverage", "90"])[0], 1)
            self.assertEqual(run(coverage, [str(tmp / "matrix.md"), str(tmp / "a.md")])[0], 2, "needs two plans")
            self.assertEqual(run(coverage, [str(tmp / "matrix.md"), str(tmp / "a.md"), str(tmp / "missing.md")])[0], 2)

    def test_weights_must_match_the_matrix(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "w.json"
            path.write_text(json.dumps({"REQ-001": 5}), encoding="utf-8")
            with self.assertRaises(ValueError):
                coverage.load_weights(path, self.ids)
            path.write_text(json.dumps({"REQ-001": 5, "REQ-002": 5, "REQ-003": 5, "REQ-004": -1}), encoding="utf-8")
            with self.assertRaises(ValueError):
                coverage.load_weights(path, self.ids)


def make_image(path: Path, bands):
    image = Image.new("RGB", (200, 100), bands[0][0])
    draw, x = ImageDraw.Draw(image), 0
    for color, width in bands:
        draw.rectangle([x, 0, x + width, 100], fill=color)
        x += width
    image.save(path)


class PaletteTests(unittest.TestCase):
    def test_built_in_palettes_pass_their_own_check(self):
        """If the shipped defaults failed, the check would be wrong, not the defaults."""
        for theme in (None, "editorial"):
            with self.subTest(theme=theme):
                self.assertEqual(palette.check_palette(palette.default_palette(theme)), [])

    def test_derived_palettes_always_pass_the_check(self):
        cases = {
            "warm-and-teal": [((230, 120, 40), 90), ((30, 150, 150), 60), ((250, 245, 235), 50)],
            "bright-yellow": [((255, 230, 0), 150), ((255, 255, 255), 50)],
            "light-blue": [((120, 190, 255), 140), ((255, 255, 255), 60)],
            "pastel": [((250, 220, 225), 120), ((220, 235, 250), 80)],
            "gray": [((120, 120, 120), 100), ((200, 200, 200), 100)],
            "white": [((255, 255, 255), 200)],
            "black": [((0, 0, 0), 200)],
        }
        with tempfile.TemporaryDirectory() as tmp:
            for name, bands in cases.items():
                with self.subTest(image=name):
                    path = Path(tmp) / f"{name}.png"
                    make_image(path, bands)
                    derived, _ = palette.derive(palette.dominant_colors(path), palette.default_palette())
                    self.assertEqual(set(derived), set(palette.DERIVED))
                    self.assertEqual(palette.check_palette({**palette.default_palette(), **derived}), [])

    def test_a_bright_seed_is_darkened_and_the_change_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "yellow.png"
            make_image(path, [((255, 230, 0), 200)])
            derived, notes = palette.derive(palette.dominant_colors(path), palette.default_palette())
            self.assertNotEqual(derived["primary"], "FFE600")
            self.assertTrue(any("darkened" in note for note in notes))

    def test_a_colorless_image_keeps_the_default_hue_and_says_so(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gray.png"
            make_image(path, [((120, 120, 120), 200)])
            derived, notes = palette.derive(palette.dominant_colors(path), palette.default_palette())
            self.assertEqual(derived["primary"], palette.default_palette()["primary"])
            self.assertTrue(any("no usable color" in note for note in notes))

    def test_derivation_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.png"
            make_image(path, [((230, 120, 40), 90), ((30, 150, 150), 60), ((250, 245, 235), 50)])
            runs = [palette.derive(palette.dominant_colors(path), palette.default_palette()) for _ in range(3)]
            self.assertEqual(runs[0], runs[1])
            self.assertEqual(runs[1], runs[2])

    def test_check_flags_low_contrast_and_bad_hex(self):
        base = palette.default_palette()
        low = palette.check_palette({**base, "primary": "FFE600"})
        self.assertTrue(any("white" in problem and "primary" in problem for problem in low))
        self.assertTrue(palette.check_palette({**base, "muted": "BBBBBB"}))
        self.assertIn("not a 6-digit hex", palette.check_palette({**base, "primary": "navy"})[0])
        self.assertEqual(palette.check_palette({**base, "primary": "#1f3864"}), [])

    def test_cli_derive_and_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_image(tmp / "i.png", [((230, 120, 40), 120), ((30, 150, 150), 80)])
            out_path = tmp / "palette.json"
            code, out, _ = run(palette, [str(tmp / "i.png"), "--out", str(out_path)])
            self.assertEqual(code, 0)
            derived = json.loads(out)["palette"]
            self.assertEqual(json.loads(out_path.read_text(encoding="utf-8"))["palette"], derived)
            self.assertEqual(run(palette, ["--check", str(out_path)])[0], 0)
            slides = tmp / "slides.json"
            slides.write_text(json.dumps({"meta": {"palette": {"primary": "FFE600"}}, "slides": []}), encoding="utf-8")
            code, out, _ = run(palette, ["--check", str(slides)])
            self.assertEqual((code, "PALETTE: PROBLEMS" in out), (1, True))
            (tmp / "notimage.png").write_bytes(b"not an image")
            self.assertEqual(run(palette, [str(tmp / "notimage.png")])[0], 2)
            self.assertEqual(run(palette, [])[0], 2)
            self.assertEqual(run(palette, [str(tmp / "i.png"), "--check", str(out_path)])[0], 2)


class BuildDeckPaletteTests(unittest.TestCase):
    def builder(self, pal):
        return build_deck.DeckBuilder({"meta": {"palette": pal}, "slides": []}, None, False)

    def test_low_contrast_palette_is_a_warning_not_a_failure(self):
        warnings = self.builder({"primary": "FFE600"}).warnings
        self.assertTrue(any("meta.palette" in warning and "primary" in warning for warning in warnings))

    def test_invalid_hex_is_rejected_with_a_clear_message(self):
        with self.assertRaisesRegex(ValueError, "meta.palette: .*not a 6-digit hex"):
            self.builder({"primary": "navy"})

    def test_a_derived_palette_adds_no_palette_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "i.png"
            make_image(path, [((230, 120, 40), 120), ((30, 150, 150), 80)])
            derived, _ = palette.derive(palette.dominant_colors(path), palette.default_palette())
        self.assertFalse([w for w in self.builder(derived).warnings if "meta.palette" in w])

    def test_without_a_palette_nothing_changes(self):
        deck = build_deck.DeckBuilder({"meta": {}, "slides": []}, None, False)
        self.assertFalse([w for w in deck.warnings if "meta.palette" in w])


if __name__ == "__main__":
    unittest.main()
