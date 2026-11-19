"""Cross-format regression with synthetic documents sharing a file name."""
import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import ooxml_fixtures as fixtures

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "skills/create-proposal-document/scripts"))
import cross_format_numbers as cross


class CrossFormatCollisionTests(unittest.TestCase):
    def test_single_document_rejects_duplicate_ledger_keys_without_touching_emit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            doc = fixtures.docx(root / "proposal.docx", "<w:p><w:r><w:t>36 months</w:t></w:r></w:p>")
            digest = hashlib.sha256(doc.read_bytes()).digest()
            ledger, emitted = root / "ledger.json", root / "result.json"
            emitted.write_text("preserve", encoding="utf-8")
            cases = (
                '{"numbers":[],"numbers":[{"id":"N1","value":36,"unit":"months"}]}',
                '{"numbers":[{"id":"N1","value":36,"unit":"months"},'
                '{"id":"N2","value":999,"unit":"months","must_appear":true,"must_appear":false}]}',
                r'{"numbers":[{"id":"N1","value":36,"unit":"months","must_appear":true,"must_\u0061ppear":false}]}',
                '{"numbers":[{"id":"N1","value":36,"unit":"months","label":"x","label":"x"}]}',
            )
            for raw in cases:
                with self.subTest(raw=raw):
                    ledger.write_text(raw, encoding="utf-8")
                    proc = subprocess.run([sys.executable, str(ROOT / "skills/create-proposal-document/scripts/check_numbers.py"),
                                           str(doc), "--audit", str(ledger), "--emit", str(emitted)], capture_output=True,
                                          env={**os.environ, "PYTHONIOENCODING": "utf-8"})
                    self.assertEqual(proc.returncode, 2, proc.stderr.decode("utf-8", "replace"))
                    self.assertIn(b"duplicate", proc.stderr.lower())
                    self.assertNotIn(b"Traceback", proc.stderr)
                    self.assertEqual(emitted.read_text(encoding="utf-8"), "preserve")
                    self.assertEqual(ledger.read_text(encoding="utf-8"), raw)
                    self.assertEqual(hashlib.sha256(doc.read_bytes()).digest(), digest)
            ledger.write_text('{"numbers":[{"id":"N1","value":36,"unit":"months"}]}', encoding="utf-8")
            proc = subprocess.run([sys.executable, str(ROOT / "skills/create-proposal-document/scripts/check_numbers.py"),
                                   str(doc), "--audit", str(ledger)], capture_output=True,
                                  env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))

    def test_duplicate_json_members_are_invalid_without_changing_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            doc = fixtures.docx(root / "proposal.docx", "<w:p><w:r><w:t>36 months</w:t></w:r></w:p>")
            digest = hashlib.sha256(doc.read_bytes()).digest()
            ledger = root / "ledger.json"
            valid = '{"numbers":[{"id":"N1","value":36,"unit":"months"}]}'
            cases = (
                '{"numbers":[],"numbers":[{"id":"N1","value":36,"unit":"months"}]}',
                '{"numbers":[{"id":"N1","value":36,"unit":"months"},'
                '{"id":"N2","value":999,"unit":"months","must_appear":true,"must_appear":false}]}',
                r'{"numbers":[{"id":"N1","value":36,"unit":"months","must_appear":true,"must_\u0061ppear":false}]}',
                '{"numbers":[{"id":"N1","value":36,"unit":"months","label":"x","label":"x"}]}',
            )
            for raw in cases:
                with self.subTest(raw=raw):
                    ledger.write_text(raw, encoding="utf-8")
                    proc = subprocess.run([sys.executable, str(ROOT / "skills/create-proposal-document/scripts/cross_format_numbers.py"),
                                           str(doc), "--audit", str(ledger)], capture_output=True,
                                          env={**os.environ, "PYTHONIOENCODING": "utf-8"})
                    self.assertEqual(proc.returncode, 2, proc.stderr.decode("utf-8", "replace"))
                    self.assertIn(b"duplicate", proc.stderr.lower())
                    self.assertNotIn(b"PASS", proc.stdout)
                    self.assertNotIn(b"Traceback", proc.stderr)
                    self.assertEqual(ledger.read_text(encoding="utf-8"), raw)
                    self.assertEqual(hashlib.sha256(doc.read_bytes()).digest(), digest)
            ledger.write_text(valid, encoding="utf-8")
            proc = subprocess.run([sys.executable, str(ROOT / "skills/create-proposal-document/scripts/cross_format_numbers.py"),
                                   str(doc), "--audit", str(ledger)], capture_output=True,
                                  env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))

    def test_no_compared_numbers_are_not_inspected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            doc = fixtures.docx(root / "proposal.docx", "<w:p><w:r><w:t>36 months</w:t></w:r></w:p>")
            ledger = root / "ledger.json"
            for entries in ([], [{"id": "N1", "value": 36, "unit": "months", "must_appear": False}]):
                with self.subTest(entries=entries):
                    ledger.write_text(json.dumps(entries), encoding="utf-8")
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                        self.assertEqual(cross.main([str(doc), "--numbers", str(ledger)]), 2)
                    self.assertIn("NOT INSPECTED", output.getvalue())
                    self.assertNotIn("CROSS-FORMAT-NUMBERS: PASS", output.getvalue())
            entries = [{"id": "N1", "value": 36, "unit": "months"},
                       {"id": "N2", "value": 99, "unit": "months", "must_appear": False}]
            ledger.write_text(json.dumps(entries), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cross.main([str(doc), "--numbers", str(ledger)]), 0)

    def test_equal_basenames_do_not_hide_divergence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / "first").mkdir()
            (root / "second").mkdir()
            a = fixtures.docx(root / "first" / "proposal.docx", "<w:p><w:r><w:t>36 months</w:t></w:r></w:p>")
            b = fixtures.docx(root / "second" / "proposal.docx", "<w:p><w:r><w:t>24 months</w:t></w:r></w:p>")
            ledger = root / "ledger.json"
            ledger.write_text(json.dumps([{"id": "N1", "label": "period", "value": 36, "unit": "months"}]), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = cross.main([str(a), str(b), "--numbers", str(ledger)])
            self.assertEqual(code, 1)
            self.assertIn("[DIVERGENT] N1: found elsewhere but missing in proposal.docx [2]", output.getvalue())
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cross.main([str(a), "--numbers", str(ledger)]), 0)
