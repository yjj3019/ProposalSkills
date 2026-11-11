#!/usr/bin/env python3
"""Check that a prose edit kept every fact: figures, dates, IDs, links, quotes, code spans, and hedges.

An edit for clarity may reword sentences; it must not change what the document commits to. This compares an
original and a revised text and lists what was lost or invented per category.

  BLOCKED (exit 1)  a figure, date, ID, link, quotation, or code span was lost or added, or a hedge
                    ("[unverified]", "추정", "TBD", ...) disappeared (uncertainty was silently turned into a claim)
  REVIEW  (exit 0)  negation words or hedges changed count in a way that may be benign; read the diff
  PASS    (exit 0)  inventories match

Heuristics on text only: PASS means the listed categories match, not that the meaning is unchanged. It does not
read tables as structure and does not judge wording. Exit 2 on usage error.

Usage: python edit_preservation.py ORIGINAL REVISED [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

UNITS = r"(?:%|퍼센트|원|억|만|천|조|명|개월|개|건|월|년|일|주|M/M|MM|GB|TB|MB|ms|초|분|시간|배|점|ea|EA|x)?"
DATE_RE = re.compile(r"\d{4}[-./]\d{1,2}[-./]\d{1,2}|\d{1,2}월\s*\d{1,2}일")
URL_RE = re.compile(r"https?://[^\s)>\]]*[^\s)>\].,;:!?'\"]")  # sentence punctuation is not part of the link
ID_RE = re.compile(r"\b[A-Z]{2,6}-\d{1,5}\b")
QUOTE_RE = re.compile(r"[\"“”]([^\"“”\n]{2,})[\"“”]")
CODE_RE = re.compile(r"```.*?```|`[^`\n]+`", re.S)
NUMBER_RE = re.compile(r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)\s*" + UNITS)
HEDGE_RE = re.compile(r"\[(?:unverified|NOT INSPECTED|TBD)\]|TBD|추정|예정|약\s?\d|가정|미확인|검토 중|협의 후", re.I)
NEGATION_RE = re.compile(r"않|없|못\s|불가|아니|\bnot\b|\bno\b|\bnever\b|\bcannot\b", re.I)
BLOCKING = ("numbers", "dates", "ids", "urls", "quotes", "code", "hedges")


def _take(pattern: re.Pattern[str], text: str, group: int = 0) -> tuple[Counter, str]:
    found = Counter(m.group(group).strip() for m in pattern.finditer(text))
    return found, pattern.sub(" ", text)


def inventory(text: str) -> dict[str, Counter]:
    text = text.replace("\r\n", "\n")
    code, text = _take(CODE_RE, text)
    urls, text = _take(URL_RE, text)
    dates, text = _take(DATE_RE, text)
    ids, text = _take(ID_RE, text)
    quotes, text = _take(QUOTE_RE, text, 1)
    hedges, text = _take(HEDGE_RE, text)
    numbers = Counter()
    for m in NUMBER_RE.finditer(text):
        numbers[m.group(0).replace(",", "").replace(" ", "")] += 1
    negations = Counter({"negation": len(NEGATION_RE.findall(text))})
    return {"numbers": numbers, "dates": dates, "ids": ids, "urls": urls, "quotes": quotes,
            "code": code, "hedges": hedges, "negations": negations}


def compare(original: str, revised: str) -> dict:
    before, after = inventory(original), inventory(revised)
    report: dict = {"lost": {}, "added": {}, "verdict": "PASS"}
    for kind in before:
        lost, added = before[kind] - after[kind], after[kind] - before[kind]
        if lost:
            report["lost"][kind] = dict(lost)
        if added:
            report["added"][kind] = dict(added)
    blocked = [k for k in BLOCKING if k in report["lost"] or (k != "hedges" and k in report["added"])]
    review = [k for k in ("negations", "hedges") if k in report["lost"] or k in report["added"]]
    if blocked:
        report["verdict"], report["blocking"] = "BLOCKED", blocked
    elif review:
        report["verdict"], report["review"] = "REVIEW", review
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("original", type=Path)
    parser.add_argument("revised", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = compare(args.original.read_text(encoding="utf-8-sig"), args.revised.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError) as exc:
        print(f"Cannot read input: {type(exc).__name__}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for label in ("lost", "added"):
            for kind, items in report[label].items():
                print(f"[{label.upper()}] {kind}: {', '.join(f'{k} x{v}' for k, v in items.items())}")
        print(f"EDIT-PRESERVATION: {report['verdict']}")
    return 1 if report["verdict"] == "BLOCKED" else 0


if __name__ == "__main__":
    sys.exit(main())
