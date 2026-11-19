#!/usr/bin/env python3
"""Report which optional runtime pieces are present.

Prints JSON with ready, missing and probe_failures. A minimal in-memory PPTX creation and command version probes
are attempted; successful probes do not guarantee a later render or access to customer files.
Exit 0 only when nothing is missing and probes pass. Mirrors requirements.txt: only python-pptx and Pillow are Python
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
import subprocess
import sys

MODULES = ["pptx", "PIL"]
COMMANDS = [("soffice", "libreoffice"), ("pdftoppm",)]  # any name in a group satisfies it


def missing(python_only: bool = False) -> list[str]:
    absent = [f"python:{name}" for name in MODULES if importlib.util.find_spec(name) is None]
    if not python_only:
        absent += [f"command:{group[0]}" for group in COMMANDS if not any(shutil.which(n) for n in group)]
    return absent


def probe(python_only: bool = False) -> list[str]:
    """Exercise tools without customer data; no result proves future execution or rendering quality."""
    failures = []
    if importlib.util.find_spec("pptx") is not None:
        try:
            result = subprocess.run([sys.executable, "-c", "from io import BytesIO; from pptx import Presentation; Presentation().save(BytesIO())"],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
            if result.returncode:
                failures.append("probe:pptx")
        except (OSError, subprocess.TimeoutExpired):
            failures.append("probe:pptx")
    if not python_only:
        for group in COMMANDS:
            executable = next((shutil.which(n) for n in group if shutil.which(n)), None)
            if executable:
                try:
                    result = subprocess.run([executable, "-v" if group[0] == "pdftoppm" else "--version"],
                                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
                    if result.returncode:
                        failures.append(f"probe:{group[0]}")
                except (OSError, subprocess.TimeoutExpired):
                    failures.append(f"probe:{group[0]}")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python-only", action="store_true", help="skip the LibreOffice and Poppler command checks")
    python_only = parser.parse_args(argv).python_only
    absent = missing(python_only)
    failures = probe(python_only)
    print(json.dumps({"ready": not absent and not failures, "missing": absent, "probe_failures": failures}, ensure_ascii=False))
    return 1 if absent or failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
