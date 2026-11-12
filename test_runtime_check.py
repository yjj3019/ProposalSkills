"""Tests for runtime_check.py (no Docker, no LibreOffice needed)."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import runtime_check  # noqa: E402


class RuntimeCheckTests(unittest.TestCase):
    def test_python_only_reports_a_missing_module_and_no_commands(self):
        real = importlib.util.find_spec
        with mock.patch("importlib.util.find_spec", side_effect=lambda n, *a, **k: None if n == "pptx" else real(n, *a, **k)):
            absent = runtime_check.missing(python_only=True)
        self.assertIn("python:pptx", absent)
        self.assertFalse(any(item.startswith("command:") for item in absent))

    def test_full_check_reports_each_missing_command_group_once(self):
        with mock.patch("importlib.util.find_spec", return_value=object()), mock.patch("shutil.which", return_value=None):
            absent = runtime_check.missing()
        self.assertEqual(absent, ["command:soffice", "command:pdftoppm"])

    def test_either_name_of_a_group_satisfies_it(self):
        with mock.patch("importlib.util.find_spec", return_value=object()), \
                mock.patch("shutil.which", side_effect=lambda n: "/x" if n in {"libreoffice", "pdftoppm"} else None):
            self.assertEqual(runtime_check.missing(), [])

    def test_cli_prints_json_and_the_exit_code_matches(self):
        run = subprocess.run([sys.executable, str(ROOT / "runtime_check.py"), "--python-only"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
        payload = json.loads(run.stdout)
        self.assertEqual(run.returncode, 0 if payload["ready"] else 1)


if __name__ == "__main__":
    unittest.main()
