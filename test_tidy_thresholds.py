"""Threshold bounds for the slide tidiness audit."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pptx import Presentation

SCRIPT = Path(__file__).resolve().parent / "skills/create-proposal-document/scripts/tidy_audit.py"


class TidyThresholdTests(unittest.TestCase):
    def test_invalid_thresholds_are_usage_errors_and_boundaries_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            deck = Path(tmp) / "sample.pptx"
            presentation = Presentation()
            presentation.slides.add_slide(presentation.slide_layouts[6])
            presentation.save(deck)
            for option in ("--min-fill", "--max-text-only"):
                for value in ("nan", "inf", "-inf", "-0.1", "1.1"):
                    with self.subTest(option=option, value=value):
                        proc = subprocess.run([sys.executable, str(SCRIPT), str(deck), f"{option}={value}"],
                                              capture_output=True, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
                        self.assertEqual(proc.returncode, 2, proc.stderr.decode("utf-8", "replace"))
                        self.assertNotIn(b"Traceback", proc.stderr)
                for value in ("0", "1"):
                    with self.subTest(option=option, value=value):
                        proc = subprocess.run([sys.executable, str(SCRIPT), str(deck), option, value],
                                              capture_output=True, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
                        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))
            for option in ("--max-sizes", "--max-near-miss", "--max-rules", "--max-chars"):
                with self.subTest(option=option):
                    proc = subprocess.run([sys.executable, str(SCRIPT), str(deck), option, "-1"],
                                          capture_output=True, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
                    self.assertEqual(proc.returncode, 2, proc.stderr.decode("utf-8", "replace"))


class TidyGeometryTests(unittest.TestCase):
    """Advisory geometry checks, and the cases they must stay silent on (an overlay is not a collision)."""

    @staticmethod
    def audit(build):
        from pptx.util import Inches, Pt
        sys.path.insert(0, str(SCRIPT.parent))
        import tidy_audit
        with tempfile.TemporaryDirectory() as tmp:
            deck = Path(tmp) / "deck.pptx"
            prs = Presentation()
            prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
            slide = prs.slides.add_slide(prs.slide_layouts[6])

            def text(left, top, width, height, body, size=14):
                box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
                box.text_frame.word_wrap = True
                run = box.text_frame.paragraphs[0].add_run()
                run.text, run.font.size = body, Pt(size)
                return box

            build(slide, text, Inches)
            prs.save(deck)
            return tidy_audit.measure(deck)["slides"][0]

    def test_two_text_boxes_that_collide_are_reported(self):
        result = self.audit(lambda slide, text, inch: (text(1, 1, 4, 1, "left column text " * 4), text(3, 1.2, 4, 1, "right column text " * 4)))
        self.assertEqual(len(result["overlaps"]), 1)

    def test_wide_boxes_with_short_text_are_not_a_collision(self):
        """The example deck's cover puts two 3.4 in boxes 2.2 in apart; their short text never meets."""
        result = self.audit(lambda slide, text, inch: (text(1, 1, 4, 1, "left"), text(3, 1, 4, 1, "right")))
        self.assertEqual(result["overlaps"], [])

    def test_a_box_that_runs_off_the_slide_is_reported(self):
        result = self.audit(lambda slide, text, inch: text(11, 1, 4, 1, "wide"))
        self.assertTrue(result["off_slide"])

    def test_text_that_cannot_fit_its_box_is_reported(self):
        result = self.audit(lambda slide, text, inch: text(1, 1, 3, 0.4, "a long sentence " * 12, size=18))
        self.assertTrue(result["overflow"])

    def test_east_asian_text_is_estimated_wider_than_latin(self):
        sys.path.insert(0, str(SCRIPT.parent))
        import tidy_audit
        self.assertEqual(tidy_audit._em_width("abcd"), 2.0)
        self.assertEqual(tidy_audit._em_width("제안서"), 3.0)

    def test_intentional_overlays_are_not_reported(self):
        """Forbidden findings: a badge on a card, a label over a picture or a filled shape, ordinary spaced columns."""
        def build(slide, text, inch):
            text(1, 1, 6, 3, "card body text " * 4)
            text(1.2, 1.1, 0.8, 0.3, "NEW", size=10)                 # small badge fully inside the card
            slide.shapes.add_shape(1, inch(8), inch(1), inch(4), inch(3)).text_frame.text = ""   # filled shape, no text
            text(8.2, 1.2, 3, 0.5, "label on a shape")                 # text over a non-text shape
            text(1, 5, 5, 1, "left column")
            text(6.5, 5, 5, 1, "right column")
        result = self.audit(build)
        self.assertEqual((result["overlaps"], result["off_slide"], result["overflow"]), ([], [], []))

    def test_text_that_fits_is_not_reported(self):
        result = self.audit(lambda slide, text, inch: text(1, 1, 6, 1, "A short heading", size=24))
        self.assertEqual(result["overflow"], [])
