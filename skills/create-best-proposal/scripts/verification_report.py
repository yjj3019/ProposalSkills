#!/usr/bin/env python3
"""Validate a verification report: which checks were really run on the saved file, and at what depth.

A report that says "checked" is only as good as what it was checked against. This validator refuses a report
that cannot be tied to the delivered file or that overstates its depth.

report.json:
  {"artifact": "deck.pptx", "artifact_sha256": "<hex>", "scope": "what was reviewed",
   "checks": [{"name": "...", "level": "static|fixture|rendered|live",
               "status": "pass|fail|not-inspected", "tool": "...", "evidence": ["file or log"], "note": ""}],
   "not_inspected": ["every check whose status is not-inspected, by name"]}

Rules
  - the artifact exists (path relative to the report) and its SHA-256 matches: checks apply to the saved output
  - level and status come from the fixed sets; a pass at "rendered" or "live" needs a tool and evidence
  - every not-inspected check is listed in `not_inspected`, and `scope` is not empty
  - no score fields (score, rating, quality_score): depth is reported by level, never as a number

Exit codes: 0 valid, 1 invalid, 2 usage error. The validator checks the report's honesty, not the deliverable.

Usage: python verification_report.py REPORT.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

LEVELS = ("static", "fixture", "rendered", "live")
STATUSES = ("pass", "fail", "not-inspected")
SCORE_KEYS = {"score", "rating", "quality_score", "grade"}


def validate(report_path: Path) -> tuple[list[str], str]:
    problems: list[str] = []
    try:
        report = json.loads(report_path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        return [f"cannot read report ({type(exc).__name__})"], "none"
    if not isinstance(report, dict):
        return ["report must be an object"], "none"
    if SCORE_KEYS & {k.lower() for k in report}:
        problems.append("score fields are not allowed; report depth by level")
    artifact = report.get("artifact")
    target = (report_path.parent / artifact).resolve() if isinstance(artifact, str) and artifact else None
    if target is None or not target.is_file():
        problems.append("artifact is missing or does not exist next to the report")
    elif hashlib.sha256(target.read_bytes()).hexdigest() != str(report.get("artifact_sha256", "")).lower():
        problems.append("artifact_sha256 does not match the file: the checks were not run on this output")
    if not str(report.get("scope", "")).strip():
        problems.append("scope is empty: say what was and was not reviewed")
    checks = report.get("checks")
    if not isinstance(checks, list) or not checks:
        return problems + ["checks must be a non-empty list"], "none"
    declared = {str(x) for x in report.get("not_inspected", [])} if isinstance(report.get("not_inspected"), list) else None
    if declared is None:
        problems.append("not_inspected must be a list (it may be empty only when every check ran)")
        declared = set()
    deepest = -1
    for i, check in enumerate(checks):
        if not isinstance(check, dict):
            problems.append(f"check {i}: must be an object")
            continue
        name = str(check.get("name", "")).strip() or f"#{i}"
        if SCORE_KEYS & {k.lower() for k in check}:
            problems.append(f"{name}: score fields are not allowed")
        level, status = check.get("level"), check.get("status")
        if level not in LEVELS or status not in STATUSES:
            problems.append(f"{name}: level must be one of {LEVELS} and status one of {STATUSES}")
            continue
        if status == "not-inspected" and name not in declared:
            problems.append(f"{name}: not-inspected but missing from not_inspected")
        if status == "pass":
            deepest = max(deepest, LEVELS.index(level))
            if level in ("rendered", "live") and not (str(check.get("tool", "")).strip() and check.get("evidence")):
                problems.append(f"{name}: a {level} pass needs a tool and evidence")
    return problems, LEVELS[deepest] if deepest >= 0 else "none"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or not Path(args[0]).is_file():
        print(__doc__, file=sys.stderr)
        return 2
    problems, deepest = validate(Path(args[0]))
    for problem in problems:
        print(f"[INVALID] {problem}")
    print(f"VERIFICATION-REPORT: {'INVALID' if problems else 'VALID'} (deepest passing level: {deepest})")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
