#!/usr/bin/env python3
"""Decide whether an automatic fix-and-recheck loop may continue, from a log of attempts.

Repeating a failing step does not fix a missing tool, missing eligibility evidence, or a pending approval. This
turns that rule into a verdict so the loop cannot quietly keep going.

attempts.json: {"max_attempts": 3, "same_cause_limit": 3,
                "attempts": [{"failures": ["REQ-004:no-evidence"], "passed": ["layout", "numbers"]}, ...]}
(`failures` and `passed` are stable check ids; the same id must mean the same check in every attempt.)

Verdicts, first match wins:
  DONE              the last attempt has no failures
  STOP-REGRESSION   a check that passed earlier fails now; the last fix broke something (fix that first)
  STOP-SAME-CAUSE   one failure id appears in the last `same_cause_limit` attempts in a row (default 3)
  STOP-BUDGET       `max_attempts` attempts were used and failures remain (default 3)
  CONTINUE          otherwise

On any STOP, report the hypothesis, the attempts, the failure evidence, the blocker and the inputs needed; never
lower a stage or remove a check to make the failure disappear. Exit codes: 0 DONE or CONTINUE, 1 STOP-*, 2 usage
or invalid input.

Usage: python retry_guard.py attempts.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def verdict(data: dict) -> tuple[str, str]:
    attempts = data.get("attempts")
    if not isinstance(attempts, list) or not attempts or not all(isinstance(a, dict) for a in attempts):
        raise ValueError("attempts must be a non-empty list of objects")
    for key in ("max_attempts", "same_cause_limit"):
        if key in data and not (isinstance(data[key], int) and not isinstance(data[key], bool) and data[key] >= 1):
            raise ValueError(f"{key} must be a positive integer")
    maximum, same_limit = data.get("max_attempts", 3), data.get("same_cause_limit", 3)
    fail = [set(map(str, a.get("failures") or [])) for a in attempts]
    passed = [set(map(str, a.get("passed") or [])) for a in attempts]
    if not fail[-1]:
        return "DONE", "no failures remain"
    earlier_passes = set().union(*passed[:-1]) if len(passed) > 1 else set()
    regressed = sorted(fail[-1] & earlier_passes)
    if regressed:
        return "STOP-REGRESSION", "passed earlier, fails now: " + ", ".join(regressed)
    if len(fail) >= same_limit:
        repeated = sorted(set.intersection(*fail[-same_limit:]))
        if repeated:
            return "STOP-SAME-CAUSE", f"same failure in the last {same_limit} attempts: " + ", ".join(repeated)
    if len(attempts) >= maximum:
        return "STOP-BUDGET", f"{len(attempts)} attempts used; failures remain: " + ", ".join(sorted(fail[-1]))
    return "CONTINUE", "failures remain: " + ", ".join(sorted(fail[-1]))


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        name, reason = verdict(json.loads(Path(args[0]).read_text(encoding="utf-8-sig")))
    except (OSError, ValueError) as exc:
        print(f"Invalid input: {exc}", file=sys.stderr)
        return 2
    print(f"RETRY-GUARD: {name} ({reason})")
    return 1 if name.startswith("STOP") else 0


if __name__ == "__main__":
    sys.exit(main())
