#!/usr/bin/env python3
"""Verify the portable proposal review runtime.

Prints one JSON object: {"ready": bool, "missing": ["python:…"|"command:…", …]}.
Exit 0 when ready, 1 when anything is missing.

Usage:
    python runtime_check.py
    python runtime_check.py --python-only
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil

MODULES = ["docx", "openpyxl", "pdfplumber", "PIL", "pptx", "pypdf", "reportlab"]
COMMANDS = ["libreoffice", "pdfinfo", "pdftoppm"]


def missing(python_only: bool = False) -> list[str]:
    absent = [f"python:{name}" for name in MODULES
              if importlib.util.find_spec(name) is None]
    if not python_only:
        absent += [f"command:{name}" for name in COMMANDS
                   if shutil.which(name) is None]
    return absent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--python-only",
        action="store_true",
        help="Skip LibreOffice and Poppler command checks",
    )
    args = parser.parse_args()
    absent = missing(args.python_only)
    print(json.dumps({"ready": not absent, "missing": absent}, ensure_ascii=False))
    return 1 if absent else 0


if __name__ == "__main__":
    raise SystemExit(main())
