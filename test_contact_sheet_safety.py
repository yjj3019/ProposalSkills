"""Contact sheets must not damage their own inputs or partially render invalid batches."""
from __future__ import annotations

import hashlib
import os
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

from PIL import Image


SCRIPT = Path(__file__).resolve().parent / "skills/create-proposal-document/scripts/contact_sheet.py"


class ContactSheetSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.pages = self.root / "pages"
        self.pages.mkdir()

    def page(self, number):
        path = self.pages / f"page-{number:02}.png"
        Image.new("RGB", (40, 30), "white").save(path)
        return path

    def run_sheet(self, output):
        return subprocess.run([sys.executable, str(SCRIPT), str(self.pages), "-o", str(output),
                               "--per-sheet", "12"], capture_output=True, env={**os.environ, "PYTHONIOENCODING": "utf-8"})

    def test_corrupt_thirteenth_page_leaves_no_sheet(self):
        for number in range(1, 13):
            self.page(number)
        (self.pages / "page-13.png").write_bytes(b"not an image")
        output = self.root / "sheet.png"
        result = self.run_sheet(output)
        self.assertEqual(result.returncode, 2, result.stderr.decode("utf-8", "replace"))
        self.assertFalse(output.exists())
        self.assertFalse((self.root / "sheet_1.png").exists())
        self.assertFalse((self.root / "sheet_2.png").exists())

    def test_input_cannot_be_overwritten_as_output(self):
        source = self.page(1)
        digest = hashlib.sha256(source.read_bytes()).digest()
        result = self.run_sheet(source)
        self.assertEqual(result.returncode, 2, result.stderr.decode("utf-8", "replace"))
        self.assertEqual(hashlib.sha256(source.read_bytes()).digest(), digest)
        normal = self.root / "sheet.png"
        self.assertEqual(self.run_sheet(normal).returncode, 0)
        self.assertTrue(normal.is_file())

    def test_hardlink_to_input_cannot_be_overwritten(self):
        source = self.page(1)
        alias = self.root / "alias.png"
        try:
            os.link(source, alias)
        except OSError as exc:
            self.skipTest(f"hardlinks unavailable: {exc}")
        before = source.read_bytes()
        self.assertEqual(self.run_sheet(alias).returncode, 2)
        self.assertEqual(source.read_bytes(), before)

    def test_output_hardlinks_cannot_overwrite_each_other(self):
        for number in range(1, 14):
            self.page(number)
        first, second = self.root / "sheet_1.png", self.root / "sheet_2.png"
        first.write_bytes(b"existing separate output")
        try:
            os.link(first, second)
        except OSError as exc:
            self.skipTest(f"hardlinks unavailable: {exc}")
        result = self.run_sheet(self.root / "sheet.png")
        self.assertEqual(result.returncode, 2, result.stderr.decode("utf-8", "replace"))
        self.assertEqual(first.read_bytes(), b"existing separate output")
        self.assertEqual(second.read_bytes(), b"existing separate output")

    def test_output_symlinks_cannot_overwrite_each_other(self):
        for number in range(1, 14):
            self.page(number)
        first, second = self.root / "sheet_1.png", self.root / "sheet_2.png"
        first.write_bytes(b"existing separate output")
        try:
            second.symlink_to(first)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlinks unavailable: {exc}")
        result = self.run_sheet(self.root / "sheet.png")
        self.assertEqual(result.returncode, 2, result.stderr.decode("utf-8", "replace"))
        self.assertEqual(first.read_bytes(), b"existing separate output")

    def test_independent_existing_outputs_can_be_replaced(self):
        for number in range(1, 14):
            self.page(number)
        first, second = self.root / "sheet_1.png", self.root / "sheet_2.png"
        first.write_bytes(b"old sheet one")
        second.write_bytes(b"old sheet two")
        result = self.run_sheet(self.root / "sheet.png")
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", "replace"))
        with Image.open(first) as image:
            self.assertEqual(image.format, "PNG")
        with Image.open(second) as image:
            self.assertEqual(image.format, "PNG")
        self.assertNotEqual(first.read_bytes(), second.read_bytes())

    def test_decompression_bomb_is_reported_as_uninspected(self):
        source = self.page(1)
        data = bytearray(source.read_bytes())
        data[16:24] = struct.pack(">II", 20000, 20000)
        data[29:33] = struct.pack(">I", zlib.crc32(bytes(data[12:29])))
        source.write_bytes(data)
        result = self.run_sheet(self.root / "sheet.png")
        self.assertEqual(result.returncode, 2, result.stderr.decode("utf-8", "replace"))
        self.assertIn(b"NOT INSPECTED", result.stderr)
        self.assertNotIn(b"Traceback", result.stderr)
        self.assertFalse((self.root / "sheet.png").exists())


if __name__ == "__main__":
    unittest.main()
