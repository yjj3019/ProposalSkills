#!/usr/bin/env python3
"""Verify the portable proposal review runtime."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil

MODULES = ["docx", "openpyxl", "pdfplumber", "PIL", "pptx", "pypdf", "reportlab"]
COMMANDS = ["libreoffice", "pdfinfo", "pdftoppm"]


def missing(python_only: bool = False) -> list[str]:
    absent = [f"python:{name}" for name in MODULES if importlib.util.find_spec(name) is None]
    if not python_only:
        absent += [f"command:{name}" for name in COMMANDS if shutil.which(name) is None]
    return absent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python-only", action="store_true", help="Skip LibreOffice and Poppler checks")
    args = parser.parse_args()
    absent = missing(args.python_only)
    print(json.dumps({"ready": not absent, "missing": absent}, ensure_ascii=False))
    return bool(absent)


if __name__ == "__main__":
    raise SystemExit(main())
