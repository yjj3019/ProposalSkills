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

Exit codes: 0 valid, 1 invalid, 2 usage error. The validator checks structural consistency, not the truth of the
declarations, the identity or independence of a reviewer, evidence relevance, or the deliverable's quality.

Optional --verify-evidence ROOT checks explicit evidence descriptors {path, sha256} against files under ROOT.
This is a local integrity check, not an isolation boundary; filesystem changes can race a check.
Usage: python verification_report.py [--verify-evidence ROOT] REPORT.json
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path, PureWindowsPath

LEVELS = ("static", "fixture", "rendered", "live")
STATUSES = ("pass", "fail", "not-inspected")
SCORE_KEYS = {"score", "rating", "quality_score", "grade"}


def parse_report(text: str):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON field")
            result[key] = value
        return result
    def invalid_constant(_):
        raise ValueError("invalid JSON number")
    return json.loads(text, object_pairs_hook=unique, parse_constant=invalid_constant)


def validate(report_path: Path) -> tuple[list[str], str]:
    try:
        report = parse_report(report_path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, UnicodeError, RecursionError) as exc:
        return [f"cannot read report ({type(exc).__name__})"], "none"
    return validate_data(report, report_path.parent)


def validate_data(report: object, base: Path) -> tuple[list[str], str]:
    """Validate one parsed snapshot; declarations are not authentication."""
    problems: list[str] = []
    if not isinstance(report, dict):
        return ["report must be an object"], "none"
    if SCORE_KEYS & {k.lower() for k in report}:
        problems.append("score fields are not allowed; report depth by level")
    artifact = report.get("artifact")
    target = (base / artifact).resolve() if isinstance(artifact, str) and artifact else None
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


def evidence_problems(report: object, root: Path) -> list[str]:
    """Optionally match declared evidence files; the comparison does not establish what they prove."""
    if not root.is_dir() or root.is_symlink():
        return ["evidence root unavailable or linked"]
    base = root.resolve()
    if not isinstance(report, dict) or not isinstance(report.get("checks"), list):
        return ["invalid evidence declarations"]
    problems = []
    for check in report["checks"]:
        if not isinstance(check, dict):
            continue
        evidence = check.get("evidence", [])
        if not isinstance(evidence, list):
            problems.append("evidence must be a list")
            continue
        for item in evidence:
            if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
                problems.append("strict evidence needs path and sha256")
                continue
            name, digest = item["path"], item["sha256"]
            if not isinstance(name, str) or not name or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
                problems.append("invalid evidence descriptor")
                continue
            relative = Path(name)
            windows = PureWindowsPath(name)
            if relative.is_absolute() or windows.anchor or ".." in relative.parts or ".." in windows.parts or "\\" in name or ":" in name:
                problems.append("invalid evidence path")
                continue
            try:
                target = base
                for part in relative.parts:
                    target = target / part
                    if target.is_symlink() or (hasattr(target, "is_junction") and target.is_junction()):
                        raise ValueError("linked path")
                target = target.resolve(strict=True)
                if not target.is_relative_to(base) or not target.is_file():
                    raise ValueError("outside root")
                with target.open("rb") as stream:
                    content = stream.read(32 * 1024 * 1024 + 1)
                if len(content) > 32 * 1024 * 1024 or hashlib.sha256(content).hexdigest() != digest.lower():
                    raise ValueError("evidence mismatch")
            except (OSError, ValueError, RuntimeError):
                problems.append("evidence missing, linked, outside root, too large or hash mismatch")
    return problems


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    root = None
    if len(args) == 3 and args[0] == "--verify-evidence":
        root, args = Path(args[1]), args[2:]
    if len(args) != 1 or not Path(args[0]).is_file():
        print(__doc__, file=sys.stderr)
        return 2
    report_path = Path(args[0])
    if root is None:
        problems, deepest = validate(report_path)
    else:
        try:
            report = parse_report(report_path.read_text(encoding="utf-8-sig"))
            problems, deepest = validate_data(report, report_path.parent)
            problems += evidence_problems(report, root)
        except (OSError, ValueError, UnicodeError, RecursionError):
            problems, deepest = ["cannot read report"], "none"
    for problem in problems:
        print(f"[INVALID] {problem}")
    print(f"VERIFICATION-REPORT: {'INVALID' if problems else 'VALID'} (deepest passing level: {deepest})")
    if root is not None:
        print("Evidence file checks do not authenticate the reviewer or establish review quality.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
