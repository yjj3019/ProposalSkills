#!/usr/bin/env python3
"""Check one numbers ledger against every delivered format (PPTX, DOCX, XLSX, HWPX) and show where they disagree.

A proposal is often delivered as a deck, a report, a spreadsheet and an HWPX summary built from the same facts. A figure
corrected in one file and forgotten in another is the classic late error. This runs the existing ledger comparison
(`check_numbers.py`: Korean notation variants, unit checks) on each file and reports a per-format result plus the
ledger ids that are found in some files but missing from others.

Exit codes: 0 every ledger value was found in every file, 1 at least one value is missing somewhere, 2 usage error or an
unreadable file. A pass means the values appear in each file, not that they are correct or in the right place.

Usage: python cross_format_numbers.py DOC [DOC ...] (--audit audit.json | --numbers numbers.json)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import check_numbers as cn


def check_document(path: Path, entries: list[dict]) -> tuple[list[str], dict[str, bool]]:
    """Return (blocking lines, {ledger id: matched}) for one file."""
    blocks = cn.extract_labeled_blocks(path)
    body = "\n".join(cn.normalize_text(t) for label, t in blocks if cn._is_body(label))
    other = cn.normalize_text(" ".join(t for label, t in blocks if not cn._is_body(label)))
    items, results = cn.compare(entries, body, other)
    blockers = [i for i in items if i.startswith(cn.BLOCK)]
    matched = {str(r["id"]): bool(r.get("matched")) for r in results if r.get("checked")}
    return blockers, matched


def divergent(per_document: dict[str, dict[str, bool]]) -> dict[str, list[str]]:
    """Ledger ids found in some documents but not in others: {id: [documents missing it]}."""
    ids = {i for matched in per_document.values() for i in matched}
    out = {}
    for ledger_id in sorted(ids):
        present = [d for d, m in per_document.items() if m.get(ledger_id)]
        missing = [d for d, m in per_document.items() if ledger_id in m and not m[ledger_id]]
        if present and missing:
            out[ledger_id] = missing
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("docs", nargs="+", type=Path)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--audit", type=Path)
    source.add_argument("--numbers", type=Path)
    args = parser.parse_args(argv)
    try:
        raw = json.loads((args.audit or args.numbers).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        print(f"Cannot read the ledger: {exc}", file=sys.stderr)
        return 2
    entries = raw.get("numbers") if isinstance(raw, dict) else raw
    if not isinstance(entries, list):
        print("The numbers ledger must be an array", file=sys.stderr)
        return 2
    per_document: dict[str, dict[str, bool]] = {}
    failed = False
    for doc in args.docs:
        try:
            blockers, matched = check_document(doc, entries)
        except Exception as exc:  # damaged or unsupported file: never counted as a pass
            print(f"[UNREADABLE] {doc.name}: {exc}", file=sys.stderr)
            return 2
        per_document[doc.name] = matched
        failed |= bool(blockers)
        print(f"{doc.name}: {sum(matched.values())}/{len(matched)} ledger values found"
              + ("" if not blockers else f" ({len(blockers)} blocking)"))
    for ledger_id, missing in divergent(per_document).items():
        print(f"[DIVERGENT] {ledger_id}: found elsewhere but missing in {', '.join(missing)}")
    print(f"CROSS-FORMAT-NUMBERS: {'BLOCKED' if failed else 'PASS'} ({len(args.docs)} file(s))")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
