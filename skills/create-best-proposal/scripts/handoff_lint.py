#!/usr/bin/env python3
"""Lint a session hand-off note (and optionally a lessons log) against the files it describes.

A hand-off is only useful if it is complete and still true. On resumption, compare it with the real files instead of
trusting it. Checks:

  - required labeled fields are present and non-empty: Path/Phase, Last verified, Next task, Open items
  - the file table (`| path | sha256 |`) lists files that exist and whose SHA-256 still matches; a mismatch is STALE and
    means the affected checks must be rerun
  - the note carries no credential-shaped or personal-data findings (reuses sensitive_scan)
  - with --lessons: every `###` entry has Issue, Root cause, Resolution and Revalidation lines

Exit codes: 0 ok, 1 problems found, 2 usage error. It checks that the note is complete and current, not that its
content is correct.

Usage: python handoff_lint.py HANDOFF.md [--root DIR] [--lessons LESSONS.md]
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

import sensitive_scan

FIELDS = ("Path/Phase", "Last verified", "Next task", "Open items")
LESSON_FIELDS = ("Issue", "Root cause", "Resolution", "Revalidation")
ROW = re.compile(r"^\|\s*([^|\s][^|]*?)\s*\|\s*([0-9a-fA-F]{64})\s*\|\s*$", re.M)


def lint_handoff(text: str, root: Path) -> list[str]:
    problems: list[str] = []
    for field in FIELDS:
        match = re.search(r"^\s*(?:[-*]\s*)?\*{0,2}" + re.escape(field) + r"\*{0,2}[ \t]*:[ \t]*(.*)$", text, re.M | re.I)  # [ \t], not \s: an empty value must not borrow the next line
        if not match or not match.group(1).strip():
            problems.append(f"missing or empty field: {field}")
    rows = ROW.findall(text)
    if not rows:
        problems.append("no file table rows (`| path | sha256 |`): the note is not tied to any file")
    for rel, expected in rows:
        target = (root / rel).resolve()
        if root.resolve() not in target.parents:
            problems.append(f"STALE? {rel}: path leaves the root")
        elif not target.is_file():
            problems.append(f"STALE {rel}: file is missing")
        elif hashlib.sha256(target.read_bytes()).hexdigest() != expected.lower():
            problems.append(f"STALE {rel}: file changed since the note was written; rerun the affected checks")
    for finding in sensitive_scan.scan_text(text, "handoff"):
        if finding.severity in {"high", "medium"}:
            problems.append(f"sensitive data in the note: {finding.kind} {finding.sample} ({finding.where})")
    return problems


def lint_lessons(text: str) -> list[str]:
    problems: list[str] = []
    entries = re.split(r"^###\s+", text, flags=re.M)[1:]
    if not entries:
        return ["no `###` lesson entries found"]
    for entry in entries:
        title = entry.splitlines()[0].strip() if entry.strip() else "?"
        for field in LESSON_FIELDS:
            if not re.search(r"\*{0,2}" + re.escape(field) + r"[^:\n]*\*{0,2}\s*:\s*\S", entry, re.I):
                problems.append(f"lesson '{title}': missing {field}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("handoff", type=Path)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--lessons", type=Path)
    args = parser.parse_args(argv)
    try:
        problems = lint_handoff(args.handoff.read_text(encoding="utf-8-sig"), args.root)
        if args.lessons:
            problems += lint_lessons(args.lessons.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError) as exc:
        print(f"Cannot read input: {type(exc).__name__}", file=sys.stderr)
        return 2
    for problem in problems:
        print(f"[PROBLEM] {problem}")
    print(f"HANDOFF-LINT: {'PROBLEMS' if problems else 'OK'} ({len(problems)})")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
