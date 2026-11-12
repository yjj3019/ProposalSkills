#!/usr/bin/env python3
"""Unit tests for mapping_check.py."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
import zipfile
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "skills/create-proposal-document/scripts"))
from mapping_check import check, ids_in_doc, normalize_id, parse_matrix  # noqa: E402


class MappingCheckTests(unittest.TestCase):
    def test_normalize_id(self):
        self.assertEqual(normalize_id("req-1"), "REQ-001")
        self.assertEqual(normalize_id("REQ_12"), "REQ-012")

    def test_parse_markdown_matrix(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "matrix.md"
            path.write_text(
                "| REQ-ID | 요약 | 페이지 |\n"
                "|---|---|---|\n"
                "| REQ-001 | 랜딩존 | 3 |\n"
                "| REQ-002 | RACI | |\n",
                encoding="utf-8",
            )
            matrix = parse_matrix(path)
            self.assertEqual(matrix["REQ-001"], "3")
            self.assertEqual(matrix["REQ-002"], "")

    def test_bidirectional_failures(self):
        matrix = {"REQ-001": "3", "REQ-002": "4"}
        doc_ids = {"REQ-001", "REQ-003"}
        fails = check(matrix, doc_ids)
        self.assertTrue(any("REQ-002" in f and "본문" in f for f in fails))
        self.assertTrue(any("REQ-003" in f and "조견표" in f for f in fails))
        self.assertFalse(any("REQ-001" in f and "본문" in f for f in fails))

    def test_pptx_req_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "deck.pptx"
            with zipfile.ZipFile(path, "w") as z:
                z.writestr("ppt/slides/slide1.xml",
                           "<p><t>대응 REQ-001 및 REQ-2</t></p>")
            ids = ids_in_doc(path)
            self.assertEqual(ids, {"REQ-001", "REQ-002"})

    def test_json_matrix_and_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            matrix_path = Path(tmp) / "matrix.json"
            doc_path = Path(tmp) / "body.md"
            matrix_path.write_text(
                json.dumps({"requirements": [
                    {"id": "REQ-001", "page": "3"},
                    {"id": "REQ-002", "page": "4"},
                ]}),
                encoding="utf-8",
            )
            doc_path.write_text("본문 REQ-001 / REQ-002", encoding="utf-8")
            matrix = parse_matrix(matrix_path)
            fails = check(matrix, ids_in_doc(doc_path))
            self.assertEqual(fails, [])


class MappingCheckCliTests(unittest.TestCase):
    def run_cli(self, matrix_body, doc_name, doc_bytes):
        import io
        from contextlib import redirect_stderr, redirect_stdout
        import mapping_check
        with tempfile.TemporaryDirectory() as tmp:
            matrix = Path(tmp) / "m.json"
            matrix.write_text(matrix_body, encoding="utf-8")
            doc = Path(tmp) / doc_name
            doc.write_bytes(doc_bytes)
            err = io.StringIO()
            with mock.patch.object(sys, "argv", ["x", str(matrix), "--doc", str(doc)]),                     redirect_stderr(err), redirect_stdout(io.StringIO()):
                return mapping_check.main(), err.getvalue()

    def test_non_zip_office_file_is_not_inspected(self):
        code, err = self.run_cli('[{"id": "REQ-001", "page": "1"}]', "d.pptx", b"<## DRM ##>")
        self.assertEqual(code, 2)
        self.assertIn("NOT INSPECTED", err)

    def test_malformed_json_rows_exit_2(self):
        for body in ("[1, 2]", '{"requirements": 5}'):
            code, _ = self.run_cli(body, "d.md", b"REQ-001")
            self.assertEqual(code, 2, body)


if __name__ == "__main__":
    unittest.main()
