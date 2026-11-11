#!/usr/bin/env python3
"""Plain-language lint for proposal text: long sentences, undefined acronyms, self-narration, filler, passive stacks.

Complements quality_gate.py (exaggeration, placeholders, slop phrases, ambiguous commitments); it does not repeat
those lists. Reads .md/.txt directly and .pptx/.docx/.xlsx through quality_gate's extractor.

Rules (all WARN; a person decides)
  long-sentence   a sentence longer than --max-chars (default 90) characters
  acronym         an ALL-CAPS acronym (2-6 letters) whose first use is not expanded next to it, e.g. "SLA(서비스 수준 협약)"
                  or "서비스 수준 협약(SLA)"; common acronyms in ALLOWED are skipped
  self-narration  the text talks about itself ("본 장에서는", "살펴보겠습니다", "in this section")
  filler          empty connective phrases ("~하는 것이 중요합니다", "~라고 할 수 있습니다")
  passive-stack   "~되어집니다", "~이루어지게 됩니다" style double passives; name the actor instead

Heuristics only. Exit codes: 0 always when the file is read (warnings listed), 1 with --strict and any warning,
2 usage error or unreadable file.

Usage: python plain_language_check.py FILE [--max-chars 90] [--strict]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import quality_gate

ALLOWED = {"RFP", "PPT", "PPTX", "IT", "API", "PM", "QA", "UI", "UX", "DB", "OS", "PDF", "KPI", "ID", "AI", "SW", "HW", "URL", "CPU", "GPU", "SI", "ISP"}
SPLIT = re.compile(r"(?<=[.!?。])\s+|\n+")
ACRONYM = re.compile(r"(?<![A-Za-z0-9])([A-Z]{2,6})(?![A-Za-z0-9])")
NARRATION = re.compile(r"본 (?:장|절|문서|제안서)에서는|살펴보겠|알아보겠|설명드리겠|in this (?:section|chapter|document)|let's|we will (?:now )?(?:describe|discuss)", re.I)
FILLER = re.compile(r"하는 것이 중요합니다|[다라]고 (?:할 수|볼 수) 있습니다|에 있어서|것으로 사료됩니다|it is important to note")
PASSIVE = re.compile(r"되어집니다|되어지며|이루어지게 (?:됩니다|되며)|행해집니다|수행되어지")


def read_text(path: Path) -> str:
    if path.suffix.lower() in {".pptx", ".docx", ".xlsx"}:
        return "\n".join(quality_gate.extract_blocks(path))
    return path.read_text(encoding="utf-8-sig")


def expanded(text: str, start: int, end: int) -> bool:
    """True when the acronym is paired with an expansion in parentheses right next to it."""
    return text[end:end + 1] in "(（" or (text[max(0, start - 1):start] in "(（" and ")" in text[end:end + 1] + text[end:end + 2])


def lint(text: str, max_chars: int = 90) -> list[str]:
    warnings: list[str] = []
    for number, sentence in enumerate((s.strip() for s in SPLIT.split(text) if s.strip()), 1):
        if len(sentence) > max_chars:
            warnings.append(f"[long-sentence] #{number} ({len(sentence)} chars): {sentence[:50]}...")
        for rule, pattern in (("self-narration", NARRATION), ("filler", FILLER), ("passive-stack", PASSIVE)):
            found = pattern.search(sentence)
            if found:
                warnings.append(f"[{rule}] #{number}: {found.group(0)!r}")
    seen: set[str] = set()
    for match in ACRONYM.finditer(text):
        word = match.group(1)
        if word in ALLOWED or word in seen:
            continue
        seen.add(word)
        if not expanded(text, match.start(), match.end()):
            warnings.append(f"[acronym] {word}: first use is not expanded")
    return warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("file", type=Path)
    parser.add_argument("--max-chars", type=int, default=90)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    try:
        text = read_text(args.file)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print(f"Cannot read file: {type(exc).__name__}", file=sys.stderr)
        return 2
    warnings = lint(text, args.max_chars)
    for line in warnings:
        print(f"[WARN] {line}")
    print(f"PLAIN-LANGUAGE: {len(warnings)} warning(s)")
    return 1 if args.strict and warnings else 0


if __name__ == "__main__":
    sys.exit(main())
