"""CLI regressions for incomplete and malformed deck-stage evidence."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent / "skills/create-proposal-document/scripts/deck_stage_gate.py"


class DeckStageSimulationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.title = "A meaningful actionable heading."
        self.design = b"synthetic design"
        (self.root / "brief.md").write_text("brief", encoding="utf-8")
        (self.root / "design.md").write_bytes(self.design)
        self.plan = {"slides": [{"id": "S1", "action_title": self.title}]}
        self.slides = {"slides": [{"type": "bullets", "title": self.title}]}
        self.manifest = {"route": "generate", "stages": {
            "brief": {"file": "brief.md"},
            "design_spec": {"file": "design.md", "approved_by": "Reviewer",
                            "approved_sha256": hashlib.sha256(self.design).hexdigest()},
            "page_plan": {"file": "plan.json"}, "slides": {"file": "slides.json"}}}

    def run_gate(self):
        (self.root / "stages.json").write_text(json.dumps(self.manifest), encoding="utf-8")
        (self.root / "plan.json").write_text(json.dumps(self.plan), encoding="utf-8")
        return subprocess.run([sys.executable, str(SCRIPT), str(self.root)], capture_output=True,
                              env={**os.environ, "PYTHONIOENCODING": "utf-8"})

    def write_slides(self, text=None):
        (self.root / "slides.json").write_text(text if text is not None else json.dumps(self.slides), encoding="utf-8")

    def test_approval_requires_actual_nonempty_string(self):
        self.write_slides()
        self.assertEqual(self.run_gate().returncode, 0)
        for approver in (None, False, 123, [], {}):
            with self.subTest(approver=approver):
                self.manifest["stages"]["design_spec"]["approved_by"] = approver
                result = self.run_gate()
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertNotIn(b"Traceback", result.stderr)

    def test_prescribed_titles_cannot_be_empty(self):
        self.plan["slides"][0].update(action_title="", prescribed=True)
        self.slides["slides"][0]["title"] = ""
        self.write_slides()
        self.assertEqual(self.run_gate().returncode, 1)
        self.plan["slides"][0]["action_title"] = "Overview"
        self.slides["slides"][0]["title"] = "Overview"
        self.write_slides()
        self.assertEqual(self.run_gate().returncode, 0)

    def test_quick_and_edit_routes_require_readable_slides(self):
        for route in ("quick", "edit"):
            with self.subTest(route=route):
                self.manifest["route"] = route
                self.write_slides("not JSON")
                result = self.run_gate()
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertNotIn(b"Traceback", result.stderr)
                self.write_slides('{"slides":["not a slide object"]}')
                self.assertEqual(self.run_gate().returncode, 1)
                self.write_slides()
                self.assertEqual(self.run_gate().returncode, 0)

    def test_nonstring_route_is_blocked_without_traceback(self):
        self.write_slides()
        for route in ([], {}, None):
            with self.subTest(route=route):
                self.manifest["route"] = route
                result = self.run_gate()
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertNotIn(b"Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
