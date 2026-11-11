#!/usr/bin/env python3
"""Ghost-deck check: do the slide titles alone tell a claim-by-claim story, and are number claims sourced?

Reads `slides.json` (the source of truth for build_deck.py) and looks only at content slides (not
cover/toc/section/closing). The titles, read in order, are printed as the "ghost deck" so a reviewer can judge the
argument in one pass.

  BLOCKED  a title is missing, is a bare topic label, is too short to be a claim, or repeats another title
  WARN     a title looks like a noun phrase rather than a sentence; a title or lead carries a figure but the slide
           has no `source` (figures need a visible source or an explicit "assumption" marker)
  --strict turns WARN into BLOCKED

Heuristics on wording only: they cannot tell whether a claim is true or the story is persuasive. Exit codes:
0 pass (warnings possible), 1 blocked, 2 usage error.

Usage: python deck_story_check.py slides.json [--strict]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from deck_stage_gate import LABELS, MIN_TITLE, STRUCTURAL, norm

SENTENCE_END = re.compile(r"(?:다|요|함|임|음|됨|\.|[0-9%])$")
FIGURE = re.compile(r"\d[\d,]*(?:\.\d+)?\s*(?:%|퍼센트|배|명|억|만|천|건|개월|개|일|년|원|시간|분|초)")


def check(deck: dict) -> tuple[list[str], list[str], list[str]]:
    """Return (ghost deck lines, blocking problems, warnings)."""
    ghost: list[str] = []
    blocked: list[str] = []
    warnings: list[str] = []
    seen: dict[str, int] = {}
    slides = deck.get("slides") if isinstance(deck, dict) else None
    if not isinstance(slides, list):
        return ghost, ["slides.json needs a slides list"], warnings
    for index, slide in enumerate(slides, 1):
        if not isinstance(slide, dict) or slide.get("type") in STRUCTURAL:
            continue
        title = norm(slide.get("title", ""))
        ghost.append(f"{index:>3}. {title or '(no title)'}")
        if not title:
            blocked.append(f"slide {index}: no title")
            continue
        if title.lower() in LABELS or len(title) < MIN_TITLE:
            blocked.append(f"slide {index}: title is a label, not a claim: {title!r}")
        key = title.lower()
        if key in seen:
            blocked.append(f"slide {index}: title repeats slide {seen[key]}")
        seen.setdefault(key, index)
        if not SENTENCE_END.search(title):
            warnings.append(f"slide {index}: title reads as a noun phrase; state the takeaway as a sentence")
        if FIGURE.search(title + " " + str(slide.get("lead", ""))) and not norm(slide.get("source", "")):
            warnings.append(f"slide {index}: carries a figure but has no `source`")
    if not ghost:
        blocked.append("no content slides found")
    return ghost, blocked, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("slides", type=Path)
    parser.add_argument("--strict", action="store_true", help="treat warnings as blocking")
    args = parser.parse_args(argv)
    try:
        deck = json.loads(args.slides.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        print(f"Cannot read slides.json: {type(exc).__name__}", file=sys.stderr)
        return 2
    ghost, blocked, warnings = check(deck)
    print("GHOST DECK (titles only):")
    print("\n".join(ghost) or "  (none)")
    for line in blocked:
        print(f"[BLOCKED] {line}")
    for line in warnings:
        print(f"[WARN] {line}")
    failed = bool(blocked or (args.strict and warnings))
    print(f"DECK-STORY: {'BLOCKED' if failed else 'PASS'} ({len(blocked)} blocking, {len(warnings)} warning(s))")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
