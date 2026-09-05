#!/usr/bin/env python3
"""Unit tests for package_inspect.py (no LibreOffice)."""
from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "skills/create-proposal-document/scripts"))
from package_inspect import blocking, run  # noqa: E402


def write_pptx(path: Path, *, notes: bool = False, external: bool = False,
               core_creator: str = "") -> None:
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("ppt/slides/slide1.xml", "<p><a:t>일반 본문</a:t></p>")
        z.writestr("ppt/presentation.xml", "<p:presentation/>")
        if notes:
            z.writestr("ppt/notesSlides/notesSlide1.xml", "<p>내부 메모</p>")
        if external:
            z.writestr(
                "ppt/slides/_rels/slide1.xml.rels",
                '<Relationship TargetMode="External" Target="https://example.com"/>',
            )
        if core_creator:
            z.writestr(
                "docProps/core.xml",
                f'<cp:coreProperties xmlns:dc="http://purl.org/dc/elements/1.1/">'
                f"<dc:creator>{core_creator}</dc:creator></cp:coreProperties>",
            )


class PackageInspectTests(unittest.TestCase):
    def test_notes_and_metadata_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "deck.pptx"
            write_pptx(path, notes=True, core_creator="TestAuthor")
            items = run(path)
            self.assertTrue(any("노트" in f for f in items))
            self.assertTrue(any("TestAuthor" in f for f in items))
            self.assertTrue(any("NOT INSPECTED" in f for f in items))

    def test_external_link_is_blocking_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "deck.pptx"
            write_pptx(path, external=True)
            items = run(path)
            blockers = blocking(items)
            self.assertTrue(any("외부링크" in f for f in blockers))

    def test_clean_deck_has_only_not_inspected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "deck.pptx"
            write_pptx(path)
            items = run(path)
            self.assertEqual(blocking(items), [])
            self.assertTrue(all("NOT INSPECTED" in f for f in items))


if __name__ == "__main__":
    unittest.main()
