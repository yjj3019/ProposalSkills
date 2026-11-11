"""HWPX (Hancom, ZIP of XML) reading in sensitive_scan, quality_gate, check_numbers and plain_language_check.

Fixtures are synthetic and built here from the public package layout (mimetype, Contents/section*.xml, content.hpf).
"""
from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "skills/create-best-proposal/scripts"))
sys.path.insert(0, str(ROOT / "skills/create-proposal-document/scripts"))
import check_numbers  # noqa: E402
import plain_language_check as plain  # noqa: E402
import quality_gate  # noqa: E402
import sensitive_scan as scan  # noqa: E402
from test_sensitive_scan import mail, valid_rrn  # noqa: E402

NS = ('xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" '
      'xmlns:opf="http://www.idpf.org/2007/opf/"')


def para(*runs: str) -> str:
    return "<hp:p>" + "".join(f"<hp:run><hp:t>{r}</hp:t></hp:run>" for r in runs) + "</hp:p>"


def table(*cells: str) -> str:
    inner = "".join(f"<hp:tc><hp:subList>{para(c)}</hp:subList></hp:tc>" for c in cells)
    return f"<hp:p><hp:run><hp:tbl><hp:tr>{inner}</hp:tr></hp:tbl></hp:run></hp:p>"


def section(*items: str) -> str:
    return f'<?xml version="1.0" encoding="UTF-8"?><hs:sec {NS}>{"".join(items)}</hs:sec>'


def hwpx(path: Path, *items: str, extra: dict[str, bytes | str] | None = None, mimetype: bytes = b"application/hwp+zip") -> Path:
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mimetype", mimetype, compress_type=zipfile.ZIP_STORED)
        z.writestr("Contents/section0.xml", section(*items))
        for name, data in (extra or {}).items():
            z.writestr(name, data)
    return path


class HwpxTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)


class SensitiveScanHwpxTests(HwpxTestCase):
    def test_number_split_across_runs_in_body_table_header_and_metadata_is_found(self):
        n = valid_rrn()
        split = para("담당 " + n[:6] + "-", n[6:])
        cell = table("셀", n[:6] + "-" + n[6:])
        header = '<?xml version="1.0"?><hm:masterPage xmlns:hm="x" ' + NS + ">" + para("머리말 010-1234-5678") + "</hm:masterPage>"
        meta = f'<opf:package {NS}><opf:metadata><opf:title>제안서</opf:title><opf:meta name="creator">{mail("hong", "corp.co.kr")}</opf:meta></opf:metadata></opf:package>'
        path = hwpx(self.dir / "a.hwpx", split, cell,
                    extra={"Contents/masterpage0.xml": header, "Contents/content.hpf": meta})
        found, unscanned, count = scan.scan_paths([path])
        self.assertEqual((count, unscanned), (1, []))
        by_part = {(f.where, f.kind) for f in found}
        self.assertIn(("Contents/section0.xml", "resident-registration-number"), by_part)
        self.assertIn(("Contents/masterpage0.xml", "mobile-phone"), by_part)
        self.assertIn(("Contents/content.hpf", "email"), by_part)
        self.assertEqual(sum(f.kind == "resident-registration-number" for f in found), 2)

    def test_clean_document_is_clean_and_bindata_is_reported_not_ignored(self):
        path = hwpx(self.dir / "b.hwpx", para("깨끗한 문서"), extra={"BinData/image1.png": b"\x89PNG"})
        found, unscanned, _ = scan.scan_paths([path])
        self.assertEqual(found, [])
        self.assertTrue(any("embedded" in u.reason and "BinData/image1.png" in u.reason for u in unscanned))

    def test_non_hwpx_zip_and_unsafe_xml_are_unscanned(self):
        bad_mime = hwpx(self.dir / "c.hwpx", para("x"), mimetype=b"application/zip")
        evil = self.dir / "d.hwpx"
        with zipfile.ZipFile(evil, "w") as z:
            z.writestr("mimetype", b"application/hwp+zip")
            z.writestr("Contents/section0.xml", '<?xml version="1.0"?><!DOCTYPE s [<!ENTITY a "b">]><s/>')
        wide = self.dir / "e.hwpx"
        with zipfile.ZipFile(wide, "w") as z:
            z.writestr("mimetype", b"application/hwp+zip")
            z.writestr("Contents/section0.xml", section(para("x")).encode("utf-16"))
        for path in (bad_mime, evil, wide):
            found, unscanned, _ = scan.scan_paths([path])
            self.assertEqual((found, bool(unscanned)), ([], True), path.name)

    def test_hwpx_is_read_in_directory_walks_but_binary_hwp_is_not(self):
        hwpx(self.dir / "ok.hwpx", para("010-2222-3333"))
        (self.dir / "old.hwp").write_bytes(b"\xd0\xcf\x11\xe0")
        found, unscanned, count = scan.scan_paths([self.dir])
        self.assertEqual(count, 1)
        self.assertEqual({f.kind for f in found}, {"mobile-phone"})
        self.assertEqual([Path(u.path).name for u in unscanned], ["old.hwp"])


class GateReadingTests(HwpxTestCase):
    def test_quality_gate_blocks_are_paragraphs_and_tables_are_not_double_counted(self):
        path = hwpx(self.dir / "g.hwpx", para("혁", "신적 방안"), table("총 36개월", "셀B"))
        blocks = quality_gate.extract_labeled_blocks(path)
        labels = [b[0] for b in blocks]
        self.assertTrue(all(label.startswith("문단") for label in labels), labels)
        text = " ".join(t for _, t in blocks)
        self.assertEqual(text.count("총 36개월"), 1)
        self.assertTrue(quality_gate.banned_hits(text, "혁신적"))  # split runs are joined first

    def test_quality_gate_rejects_a_non_hwpx_package(self):
        path = hwpx(self.dir / "h.hwpx", para("x"), mimetype=b"application/zip")
        with self.assertRaises(KeyError):
            quality_gate.extract_labeled_blocks(path)

    def test_check_numbers_and_plain_language_read_hwpx(self):
        path = hwpx(self.dir / "i.hwpx", para("본 장에서는 사업 기간은 36개월이다."))
        self.assertIn("36개월", check_numbers.document_text(path))
        self.assertTrue(any("self-narration" in w for w in plain.lint(plain.read_text(path))))


if __name__ == "__main__":
    unittest.main()
