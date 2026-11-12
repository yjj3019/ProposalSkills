#!/usr/bin/env python3
"""Report which optional runtime pieces are present.

Prints one JSON object: {"ready": bool, "missing": ["python:..."|"command:...", ...]}.
Exit 0 when nothing is missing, 1 otherwise. Mirrors requirements.txt: only python-pptx and Pillow are Python
dependencies; LibreOffice (soffice) is optional and its absence only turns the render check into NOT INSPECTED.

Usage:
    python runtime_check.py
    python runtime_check.py --python-only
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil

MODULES = ["pptx", "PIL"]
COMMANDS = [("soffice", "libreoffice"), ("pdftoppm",)]  # any name in a group satisfies it


def missing(python_only: bool = False) -> list[str]:
    absent = [f"python:{name}" for name in MODULES if importlib.util.find_spec(name) is None]
    if not python_only:
        absent += [f"command:{group[0]}" for group in COMMANDS if not any(shutil.which(n) for n in group)]
    return absent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python-only", action="store_true", help="skip the LibreOffice and Poppler command checks")
    absent = missing(parser.parse_args(argv).python_only)
    print(json.dumps({"ready": not absent, "missing": absent}, ensure_ascii=False))
    return 1 if absent else 0


if __name__ == "__main__":
    raise SystemExit(main())
