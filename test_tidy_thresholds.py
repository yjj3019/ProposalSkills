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
