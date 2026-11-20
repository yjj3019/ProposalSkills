"""Malformed render state must be refused before existing output changes."""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "skills/create-proposal-document/scripts"))
import render_delta  # noqa: E402


class RenderDeltaStateSafetyTests(unittest.TestCase):
    def check_metadata_links_are_refused(self, symbolic):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            deck = root / "deck.pptx"
            deck.write_bytes(b"synthetic")
            for name in ("render_state.json", "delta.json"):
                with self.subTest(name=name, symbolic=symbolic):
                    out = root / name.replace(".json", "")
                    out.mkdir()
                    outside = root / (name + ".outside")
                    contents = b'{"tool":"render_delta"}' if name == "render_state.json" else b"user data"
                    outside.write_bytes(contents)
                    if name != "render_state.json":
                        (out / "render_state.json").write_text('{"tool":"render_delta"}', encoding="utf-8")
                    try:
                        if symbolic:
                            (out / name).symlink_to(outside)
                        else:
                            os.link(outside, out / name)
                    except (OSError, NotImplementedError) as exc:
                        self.skipTest(f"links unavailable: {exc}")
                    with mock.patch.object(render_delta, "find_soffice", return_value="fake"), \
                         mock.patch.object(render_delta, "to_pdf") as render, \
                         contextlib.redirect_stderr(io.StringIO()) as err:
                        self.assertEqual(render_delta.main([str(deck), "-o", str(out)]), 2)
                    self.assertIn("NOT INSPECTED", err.getvalue())
                    self.assertIn("link", err.getvalue().lower())
                    render.assert_not_called()
                    self.assertEqual(outside.read_bytes(), contents)
                    self.assertFalse((out / "pages").exists())

    def test_hardlinked_metadata_is_refused(self):
        self.check_metadata_links_are_refused(False)

    def test_symlinked_metadata_is_refused(self):
        self.check_metadata_links_are_refused(True)

    def test_regular_owned_metadata_is_allowed(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp).resolve()
            (out / "render_state.json").write_text('{"tool":"render_delta"}', encoding="utf-8")
            (out / "delta.json").write_text("old result", encoding="utf-8")
            self.assertIsNone(render_delta.claim_output(out))

    def test_malformed_state_is_rejected_without_touching_output(self):
        cases = ([], {"tool": "render_delta", "slides": ["bad"]},
                 {"tool": "render_delta", "slides": [{"hash": []}]},
                 {"tool": "render_delta", "slides": [{"hash": "h", "image": []}]},
                 {"tool": "render_delta", "created": [None]},
                 {"tool": "render_delta", "pages": [None]},
                 {"tool": "render_delta", "environment": ["bad"]},
                 {"tool": "render_delta", "page_hashes": "bad"})
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            deck, out = root / "deck.pptx", root / "render"
            deck.write_bytes(b"synthetic")
            out.mkdir()
            sentinel = out / "keep.txt"
            sentinel.write_bytes(b"user data")
            state = out / "render_state.json"
            for value in cases:
                with self.subTest(state=value):
                    raw = json.dumps(value).encode()
                    state.write_bytes(raw)
                    with mock.patch.object(render_delta, "find_soffice", return_value="fake"), \
                         mock.patch.object(render_delta, "to_pdf") as render, \
                         contextlib.redirect_stderr(io.StringIO()) as err:
                        code = render_delta.main([str(deck), "-o", str(out)])
                    self.assertEqual(code, 2)
                    self.assertIn("NOT INSPECTED", err.getvalue())
                    self.assertTrue("state" in err.getvalue() or "not created by render_delta" in err.getvalue())
                    render.assert_not_called()
                    self.assertEqual(state.read_bytes(), raw)
                    self.assertEqual(sentinel.read_bytes(), b"user data")


if __name__ == "__main__":
    unittest.main()
