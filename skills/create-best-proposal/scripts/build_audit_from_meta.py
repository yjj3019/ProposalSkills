#!/usr/bin/env python3
"""Build a proposal audit JSON from authoring meta (SI-B1).

Usage:
  python build_audit_from_meta.py META.json -o AUDIT.json
  python build_audit_from_meta.py META.json --strict
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_PACKAGE_CHECKS = {
    "metadata": "not-inspected",
    "notes": "not-inspected",
    "comments": "not-inspected",
    "hidden-content": "not-inspected",
    "embedded-files": "not-applicable",
    "external-links": "not-inspected",
    "macros": "not-applicable",
    "stale-customer-data": "not-inspected",
    "price-leakage": "not-inspected",
}


def _as_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _req_conflicts(meta: dict) -> list[str]:
    reqs = {r.get("id") for r in _as_list(meta.get("requirements")) if isinstance(r, dict)}
    conflicts: list[str] = []
    for slide in _as_list(meta.get("slides")):
        if not isinstance(slide, dict):
            continue
        for rid in _as_list(slide.get("req_ids")):
            if rid not in reqs:
                conflicts.append(
                    f"slide {slide.get('no', '?')} references unknown requirement {rid}")
    slide_req_ids: set[str] = set()
    for slide in _as_list(meta.get("slides")):
        if isinstance(slide, dict):
            slide_req_ids.update(
                rid for rid in _as_list(slide.get("req_ids")) if isinstance(rid, str))
    for req in _as_list(meta.get("requirements")):
        if not isinstance(req, dict):
            continue
        rid = req.get("id")
        if not rid or not req.get("mandatory"):
            continue
        slide = req.get("slide")
        refs = req.get("evidence_refs") or []
        if slide is None and rid not in slide_req_ids and not refs:
            conflicts.append(f"requirement {rid} has no slide mapping or evidence_refs")
    return conflicts


def _normalize_win_themes(meta: dict, strict: bool, warnings: list[str]) -> list[dict]:
    """S3: win themes must link to ≥1 requirement id (decorative themes rejected)."""
    reqs = {r.get("id") for r in _as_list(meta.get("requirements")) if isinstance(r, dict)}
    out: list[dict] = []
    for theme in _as_list(meta.get("win_themes")):
        if not isinstance(theme, dict):
            continue
        tid = theme.get("id") or "WT?"
        linked = [x for x in _as_list(theme.get("req_ids")) if isinstance(x, str) and x]
        unknown = [x for x in linked if x not in reqs]
        if unknown:
            msg = f"win theme {tid} references unknown requirements: {', '.join(unknown)}"
            if strict:
                raise ValueError(msg)
            warnings.append(msg)
        if not linked:
            msg = f"win theme {tid} has no req_ids (decorative theme)"
            if strict:
                raise ValueError(msg)
            warnings.append(msg)
        item = {
            "id": tid,
            "statement": theme.get("statement") or theme.get("text") or "",
            "req_ids": linked,
        }
        if theme.get("proof"):
            item["proof"] = theme["proof"]
        out.append(item)
    return out


def _normalize_requirements(meta: dict, strict: bool, warnings: list[str]) -> list[dict]:
    out: list[dict] = []
    for req in _as_list(meta.get("requirements")):
        if not isinstance(req, dict):
            continue
        item = {
            "id": req.get("id") or "R?",
            "mandatory": bool(req.get("mandatory", True)),
            "state": req.get("state") or "pending",
            "rationale": req.get("rationale") or "",
            "reviewer": req.get("reviewer") or "",
        }
        if "text" in req:
            item["text"] = req["text"]
        if "basis" in req:
            item["basis"] = req["basis"]
        refs = req.get("evidence_refs")
        if isinstance(refs, list):
            item["evidence_refs"] = refs
        elif req.get("slide") is not None:
            item["evidence_refs"] = [f"slide:{req['slide']}"]
        else:
            item["evidence_refs"] = []
        if item["state"] == "approved" and not any(
                isinstance(r, str) and r.strip() for r in item["evidence_refs"]):
            msg = f"requirement {item['id']} approved without evidence_refs"
            if strict:
                raise ValueError(msg)
            warnings.append(msg)
        # Optional S2 matrix fields passthrough
        for key in ("fit", "eval_weight", "win_theme_id", "risk", "support", "text", "basis"):
            if key in req and key not in item:
                item[key] = req[key]
        out.append(item)
    return out


def build_audit(meta: dict, strict: bool = False) -> dict:
    if not isinstance(meta, dict):
        raise ValueError("meta root must be an object")
    warnings: list[str] = []
    mode = meta.get("mode") or "draft"
    bid = meta.get("bid_decision") or "intake-incomplete"
    submission_in = meta.get("submission") if isinstance(meta.get("submission"), dict) else {}
    deadline = submission_in.get("deadline") or meta.get("deadline")
    submission = {
        "cleared": bool(submission_in.get("cleared", False)),
        "rehearsal_evidence": list(submission_in.get("rehearsal_evidence") or []),
        "receipt_plan": submission_in.get("receipt_plan") or "",
        "receipt_evidence": list(submission_in.get("receipt_evidence") or []),
    }
    if deadline:
        submission["deadline"] = deadline

    render_in = meta.get("render") if isinstance(meta.get("render"), dict) else {}
    render = {
        "verified": bool(render_in.get("verified", False)),
        "artifact_hash": render_in.get("artifact_hash") or "",
        "tool": render_in.get("tool") or "",
        "evidence": list(render_in.get("evidence") or []),
    }

    package_in = meta.get("package") if isinstance(meta.get("package"), dict) else {}
    checks = dict(REQUIRED_PACKAGE_CHECKS)
    if isinstance(package_in.get("checks"), dict):
        checks.update(package_in["checks"])
    package = {
        "required": bool(package_in.get("required", True)),
        "inspected": bool(package_in.get("inspected", False)),
        "artifact_hash": package_in.get("artifact_hash") or "",
        "tool": package_in.get("tool") or "",
        "checks": checks,
        "reviewer": package_in.get("reviewer") or "",
    }

    conflicts = list(meta.get("source_conflicts") or [])
    conflicts.extend(_req_conflicts(meta))
    win_themes = _normalize_win_themes(meta, strict, warnings)

    audit: dict[str, Any] = {
        "mode": mode,
        "bid_decision": bid,
        "bid_conditions": _as_list(meta.get("bid_conditions")),
        "requirements": _normalize_requirements(meta, strict, warnings),
        "claims": _as_list(meta.get("claims")),
        "unresolved_tokens": _as_list(meta.get("unresolved_tokens")),
        "attachments": _as_list(meta.get("attachments")),
        "source_conflicts": conflicts,
        "inputs": _as_list(meta.get("inputs")),
        "defects": _as_list(meta.get("defects")),
        "checks": meta.get("checks") if isinstance(meta.get("checks"), dict) else {
            "consistency": False, "arithmetic": False, "submission": False,
        },
        "artifact_required": bool(meta.get("artifact_required", True)),
        "render": render,
        "package": package,
        "submission": submission,
        "eligibility": _as_list(meta.get("eligibility")),
        "flags": meta.get("flags") if isinstance(meta.get("flags"), dict) else {},
        "regulatory_checks": _as_list(meta.get("regulatory_checks")),
        "vendor_confirmations": _as_list(meta.get("vendor_confirmations")),
        "win_themes": win_themes,
    }
    if meta.get("artifact_mode"):
        audit["artifact_mode"] = meta["artifact_mode"]
    if warnings:
        audit["_builder_warnings"] = warnings
    # Optional trace fields (ignored by proposal_gate if unknown... actually unknown top-level is OK)
    for key in ("title", "buyer", "proposal_type"):
        if key in meta:
            audit[f"meta_{key}"] = meta[key]
    return audit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("meta", type=Path, help="Input meta JSON")
    parser.add_argument("-o", "--output", type=Path, help="Write audit JSON here")
    parser.add_argument("--strict", action="store_true",
                        help="Fail if approved requirements lack evidence_refs")
    args = parser.parse_args(argv)
    try:
        meta = json.loads(args.meta.read_text(encoding="utf-8"))
        audit = build_audit(meta, strict=args.strict)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    text = json.dumps(audit, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.output}")
    else:
        print(text)
    if audit.get("_builder_warnings"):
        for w in audit["_builder_warnings"]:
            print(f"warning: {w}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
