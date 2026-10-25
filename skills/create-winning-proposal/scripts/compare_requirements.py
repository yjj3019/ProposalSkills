#!/usr/bin/env python3
"""Compare human-matched requirement revisions; never infer IDs or approve changes."""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import sys
from pathlib import Path


def read_revision(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(value, dict) or not isinstance(value.get("requirements"), list):
        raise ValueError("Revision requires a requirements array")
    result = {}
    for item in value["requirements"]:
        if not isinstance(item, dict):
            raise ValueError("Requirement must be an object")
        for field in ("id", "text", "source_clause_label"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ValueError(f"Requirement needs non-empty {field}")
        if item["id"] in result:
            raise ValueError("Duplicate requirement ID; resolve ambiguous/split/merge matches manually")
        result[item["id"]] = item
    return result, hashlib.sha256(raw).hexdigest()


def compare(before: Path, after: Path) -> dict:
    a, a_hash = read_revision(before)
    b, b_hash = read_revision(after)
    changes = []
    for key in sorted(a.keys() | b.keys()):
        old, new = a.get(key), b.get(key)
        if old == new:
            continue
        status = "added" if old is None else "removed" if new is None else "modified"
        if old is not None and new is not None and old["text"] == new["text"]:
            status = "reference-changed"
        changes.append({"id": key, "change": status, "before": old, "after": new,
                        "diff": list(difflib.unified_diff(
                            (old["text"] if old else "").splitlines(),
                            (new["text"] if new else "").splitlines(), lineterm="")),
                        "response_and_evidence_review": "REQUIRED"})
    return {"schema_version": 1, "kind": "proposal-requirement-diff",
            "before_sha256": a_hash, "after_sha256": b_hash, "changes": changes,
            "matching": "human-assigned IDs; split/merge and uncertain matches require manual review",
            "review_status": "UNREVIEWED", "submission_approval": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = compare(args.before, args.after)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
        print(f"REVIEW-REQUIRED: {len(result['changes'])} changes")
        return 0
    except (OSError, ValueError) as exc:
        print(f"Comparison failed: {type(exc).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
