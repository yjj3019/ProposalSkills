#!/usr/bin/env python3
"""Check that a bid-decision answer follows the answer contract in SKILL.md.

A model may skip a rule written in prose. This check does not depend on the model: it reads the finished answer and fails
when the contract is broken, so a wrong decision or a missing label is caught instead of trusted.

Contract (the answer's first non-empty line states the decision):

  BID_DECISION: intake-incomplete | bid | conditional-bid | no-bid
  STATUS: DECISION_MEMO_ONLY                  required for no-bid and intake-incomplete, and only for those
  REQUIRED_INPUTS: <item>; <item>             required for intake-incomplete (what is needed to decide)
  CONDITION: <text> | owner: <who> | deadline: <ISO 8601 with time and timezone> | accepted: yes
                                              one line per condition, required for conditional-bid

Checks:
  - the first non-empty line is a valid BID_DECISION
  - no-bid / intake-incomplete carry STATUS: DECISION_MEMO_ONLY; bid / conditional-bid do not
  - with --bidder-material absent, the decision must be intake-incomplete (no company facts means no eligibility judgment)
  - intake-incomplete lists REQUIRED_INPUTS and carries no CONDITION line (an owner or deadline would be invented)
  - conditional-bid has at least one CONDITION line, each with a real owner, an ISO deadline with timezone, and accepted: yes

It checks the form and the consistency of the answer, not whether the judgment is right. Exit codes: 0 OK, 1 problems,
2 usage error (unreadable input).

Without --bidder-material the "no bidder material" rule is not checked, and a note on stderr says so. Pass absent or present.

Usage: python check_decision_answer.py ANSWER.md [--bidder-material absent|present|unknown]
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

DECISIONS = ("intake-incomplete", "bid", "conditional-bid", "no-bid")
MEMO_DECISIONS = {"intake-incomplete", "no-bid"}
LABEL = "DECISION_MEMO_ONLY"
PLACEHOLDERS = {"", "tbd", "tba", "n/a", "na", "none", "unknown", "?", "미정", "없음", "미지정", "추후", "-"}
# An owner must be someone who can be held to the deadline. These are not: a promise to name one later, a template slot, or a role
# word with no person behind it. Matched on the owner text after case folding and stripping brackets and punctuation.
PLACEHOLDER_WORDS = ("tbd", "tbc", "tba", "to be decided", "to be determined", "to be confirmed", "to be assigned", "not decided",
                     "미정", "미확정", "미지정", "추후", "협의 예정", "지정 예정", "결정 예정", "확정 예정")
GENERIC_OWNERS = {"someone", "anyone", "somebody", "team", "the team", "owner", "the owner", "who", "responsible", "person",
                  "담당자", "담당", "팀", "관계자", "책임자", "해당 팀", "해당 부서"}


def is_placeholder_owner(raw: str) -> bool:
    value = raw.strip(MARKUP).lower()
    if value in PLACEHOLDERS:
        return True
    plain = " ".join(re.sub(r"[\s\[\]<>(){}.,;:!?*_`'\"/\\-]+", " ", value).split())
    if not plain or not re.search(r"\w", plain):      # "???", "[ ]", "--"
        return True
    if plain in PLACEHOLDERS or plain in GENERIC_OWNERS:
        return True
    if re.fullmatch(r"(?:owner|who|name|person|담당자|이름)", plain):   # an unfilled template slot such as <who> or [owner]
        return True
    return any(word in plain for word in PLACEHOLDER_WORDS)
ISO_DEADLINE = re.compile(
    r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?(?:Z|[+-](\d{2}):?(\d{2}))")


def valid_deadline(value: str) -> bool:
    """An ISO 8601 date-time with a timezone, on a date that exists (not 2026-13-45T25:61)."""
    match = ISO_DEADLINE.fullmatch(value)
    if not match:
        return False
    year, month, day, hour, minute, second, off_h, off_m = match.groups()
    try:
        datetime(int(year), int(month), int(day), int(hour), int(minute), int(second or 0))
    except ValueError:
        return False
    return off_h is None or (int(off_h) <= 23 and int(off_m) <= 59)
MARKUP = "*`#> \t_"


def _clean(line: str) -> str:
    return line.strip(MARKUP + "-").strip().strip(MARKUP).strip()


def _field(text: str, name: str) -> list[str]:
    values = []
    for line in text.splitlines():
        cleaned = _clean(line)
        match = re.match(rf"{name}\s*:\s*(.*)$", cleaned, re.I)
        if match:
            values.append(match.group(1).strip().strip(MARKUP).strip())
    return values


def check(text: str, bidder_material: str = "unknown") -> list[str]:
    problems: list[str] = []
    first = next((_clean(line) for line in text.splitlines() if _clean(line)), "")
    match = re.match(r"BID_DECISION\s*:\s*[`*]*([A-Za-z-]+)[`*]*\s*$", first)
    if not match:
        return ["the first non-empty line is not `BID_DECISION: <decision>`"]
    decision = match.group(1).lower()
    if decision not in DECISIONS:
        return [f"BID_DECISION `{decision}` is not one of {', '.join(DECISIONS)}"]

    labels = [value.strip("` ") for value in _field(text, "STATUS")]
    has_label = LABEL in labels
    if decision in MEMO_DECISIONS and not has_label:
        problems.append(f"{decision} must carry `STATUS: {LABEL}`")
    if decision not in MEMO_DECISIONS and has_label:
        problems.append(f"{decision} must not carry `STATUS: {LABEL}` (that label is for no-bid and intake-incomplete)")

    if bidder_material == "absent" and decision != "intake-incomplete":
        problems.append(f"no bidder material was supplied, so the decision must be intake-incomplete, not {decision}")

    conditions = _field(text, "CONDITION")
    if decision == "intake-incomplete":
        if not any(value for value in _field(text, "REQUIRED_INPUTS")):
            problems.append("intake-incomplete must list `REQUIRED_INPUTS: <item>; <item>`")
        if conditions:
            problems.append("intake-incomplete must not carry CONDITION lines (an owner or a deadline would be invented)")
    if decision == "conditional-bid":
        if not conditions:
            problems.append("conditional-bid needs at least one `CONDITION:` line")
        for index, condition in enumerate(conditions, 1):
            pairs = [(key.strip().lower(), value.strip()) for key, _, value in
                     (part.partition(":") for part in condition.split("|")[1:])]
            parts = dict(pairs)
            label = f"condition {index}"
            keys = [key for key, _ in pairs]
            repeated = sorted({k for k in ("owner", "deadline", "accepted") if keys.count(k) > 1})
            if repeated:
                problems.append(f"{label}: repeated field {', '.join(repeated)} (a later value would hide an earlier one)")
            if is_placeholder_owner(parts.get("owner", "")):
                problems.append(f"{label}: owner is missing or a placeholder")
            if not valid_deadline(parts.get("deadline", "").strip(MARKUP)):
                problems.append(f"{label}: deadline is not a real ISO 8601 date-time with a timezone")
            if parts.get("accepted", "").strip(MARKUP).lower() not in {"yes", "accepted", "true"}:
                problems.append(f"{label}: not accepted (`accepted: yes` is required)")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("answer", type=Path)
    parser.add_argument("--bidder-material", choices=("absent", "present", "unknown"), default="unknown")
    args = parser.parse_args(argv)
    try:
        text = args.answer.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"Cannot read input: {type(exc).__name__}", file=sys.stderr)
        return 2
    problems = check(text, args.bidder_material)
    if args.bidder_material == "unknown":
        print("NOTE: --bidder-material was not given, so the rule that missing bidder material means intake-incomplete "
              "was not checked. Pass absent or present.", file=sys.stderr)
    for problem in problems:
        print(f"[PROBLEM] {problem}")
    print(f"DECISION-ANSWER: {'PROBLEMS' if problems else 'OK'} ({len(problems)})")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
