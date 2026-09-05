#!/usr/bin/env python3
"""Unit tests for runtime_check.py (python-only path; no Docker/LibreOffice)."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import runtime_check  # noqa: E402


class RuntimeCheckTests(unittest.TestCase):
    def test_python_only_reports_missing_modules(self):
        real_find = importlib.util.find_spec

        def fake_find(name, *args, **kwargs):
            if name == "pptx":
                return None
            return real_find(name, *args, **kwargs)

        with mock.patch("importlib.util.find_spec", side_effect=fake_find):
            absent = runtime_check.missing(python_only=True)
        self.assertIn("python:pptx", absent)
        self.assertFalse(any(item.startswith("command:") for item in absent))

    def test_full_check_includes_commands(self):
        with mock.patch("importlib.util.find_spec", return_value=object()):
            with mock.patch("shutil.which", return_value=None):
                absent = runtime_check.missing(python_only=False)
        self.assertTrue(all(item.startswith("command:") for item in absent))
        self.assertEqual(len(absent), len(runtime_check.COMMANDS))

    def test_cli_python_only_json(self):
        # Run as subprocess so output format stays contract-stable.
        proc = subprocess.run(
            [sys.executable, str(ROOT / "runtime_check.py"), "--python-only"],
            capture_output=True, text=True, check=False,
        )
        payload = json.loads(proc.stdout.strip())
        self.assertIn("ready", payload)
        self.assertIn("missing", payload)
        self.assertIsInstance(payload["missing"], list)
        # Exit code matches readiness.
        self.assertEqual(proc.returncode, 0 if payload["ready"] else 1)


if __name__ == "__main__":
    unittest.main()
