#!/usr/bin/env python3
"""Unified completeness scoring (SI-15): calculate proposal quality and submission readiness consistently from one audit JSON, avoiding divergent overall values (for example 66.9 vs 82.6) across create-proposal-document, create-winning-proposal, and reviewers. Readiness uses proposal_gate and dimension completion. Quality is available only with a --quality metrics file (0~1). The headline depends only on the gate (open BLOCKING -> NO-GO); high quality cannot override a blocked gate."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
# Find proposal_gate in the installed tree (../../create-winning-proposal/scripts), repository tree, then PROPOSAL_GATE_PATH.
for _cand in (_HERE.parent.parent / "create-winning-proposal" / "scripts",
              _HERE.parents[2] / "skills" / "create-winning-proposal" / "scripts",
              Path(__import__("os").environ.get("PROPOSAL_GATE_PATH", "/nonexistent")).parent):
    if (_cand / "proposal_gate.py").is_file():
        sys.path.insert(0, str(_cand))
        break
from proposal_gate import evaluate, readiness, validate_schema  # noqa: E402


def readiness_dimensions(d: dict) -> list[tuple[str, bool]]:
    """Readiness dimensions and completion status; show progress separately from gate failure."""
    reqs = d.get("requirements", [])
    atts = d.get("attachments", [])
    sub = d.get("submission", {})
    pkg = d.get("package", {})
    elig = d.get("eligibility", [])
    return [
        ("bid_decision", d.get("bid_decision") in {"bid", "conditional-bid"}),
        ("requirements_approved", bool(reqs) and all(
            r.get("state") == "approved" and r.get("evidence_refs")
            for r in reqs if r.get("mandatory"))),
        ("no_unresolved_tokens", not d.get("unresolved_tokens")),
        ("no_source_conflicts", not d.get("source_conflicts")),
        ("attachments_present", all(a.get("present") for a in atts if a.get("required"))),
        ("no_open_defects", all(
            x.get("status") == "closed"
            for x in d.get("defects", []) if x.get("severity") in {"critical", "major"})),
        ("artifacts_verified", bool(d.get("render", {}).get("verified"))
            and bool(pkg.get("inspected") if pkg.get("required") else True)),
        ("submission_cleared", bool(sub.get("cleared")) and bool(sub.get("rehearsal_evidence"))
            and bool(sub.get("receipt_plan")) and bool(sub.get("deadline"))),
        ("eligibility_ledger", bool(elig) and all(
            e.get("met") for e in elig if e.get("mandatory", True))),
    ]


QUALITY_METRICS = ("compliance_coverage", "claim_support_rate", "defect_penalty", "rehearsal_score")


def validate_quality_metrics(metrics: object) -> list[str]:
    """Require all 4 metrics to be numeric (excluding bool) and within 0~1; strings and out-of-range values are INVALID."""
    if not isinstance(metrics, dict):
        return ["quality metrics root must be an object"]
    errors = []
    for name in QUALITY_METRICS:
        if name not in metrics:
            errors.append(f"missing quality metric: {name}")
            continue
        v = metrics[name]
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            errors.append(f"quality metric {name} must be a number in [0,1] (got {v!r})")
        elif not 0.0 <= float(v) <= 1.0:
            errors.append(f"quality metric {name} out of range [0,1]: {v}")
    return errors


def quality_score(metrics: dict) -> float:
    """Proposal quality (0~100), using validated 0~1 metrics and weights matching audit-schema.md."""
    c = float(metrics["compliance_coverage"])
    s = float(metrics["claim_support_rate"])
    dp = float(metrics["defect_penalty"])
    r = float(metrics["rehearsal_score"])
    return round(100 * (0.4 * c + 0.3 * s + 0.2 * (1 - dp) + 0.1 * r), 1)


def score(audit: dict, metrics: dict | None) -> dict:
    schema_failures = validate_schema(audit)
    if metrics is not None:
        schema_failures = schema_failures + validate_quality_metrics(metrics)
    if schema_failures:
        return {"status": "INVALID", "blocking": schema_failures}
    dims = readiness_dimensions(audit)
    satisfied = sum(1 for _, ok in dims if ok)
    readiness_pct = round(100 * satisfied / len(dims), 1)
    blocking = evaluate(audit)
    decision = audit.get("bid_decision")
    downgraded_from = None
    if blocking:
        status = "NO-GO"
        # Show unresolved conditional bids as a downgrade rather than rejection of the decision.
        if decision == "conditional-bid":
            downgraded_from = "CONDITIONAL-GO"
    else:
        # Use the gate decision function for labels. This script does not inspect actual files,
        # so it cannot promote a result to SUBMISSION-READY;
        # that requires hash comparison through unified_gate --doc <final-file>.
        status, _ = readiness(audit, blocking)
        if status == "SUBMISSION-READY":
            status = "AUDIT-VALID"
    result = {
        "status": status,
        "readiness_score": readiness_pct,
        "readiness_dimensions": {k: ok for k, ok in dims},
        "blocking_count": len(blocking),
        "blocking": blocking,
        "quality_score": None,
    }
    if downgraded_from:
        result["downgraded_from"] = downgraded_from
        result["downgrade_cause"] = blocking
    if metrics is not None:
        result["quality_score"] = quality_score(metrics)
    return result


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: score_completeness.py AUDIT.json [QUALITY.json]", file=sys.stderr)
        return 2
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    try:
        audit = json.loads(Path(argv[1]).read_text(encoding="utf-8-sig"))
        metrics = json.loads(Path(argv[2]).read_text(encoding="utf-8-sig")) if len(argv) > 2 else None
    except (OSError, ValueError) as exc:  # Includes JSONDecodeError and UnicodeDecodeError.
        print(f"invalid input: {exc}", file=sys.stderr)
        return 2
    try:
        out = score(audit, metrics)
    except Exception as exc:  # Gate environment errors and similar failures.
        print(f"invalid input: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if out.get("status") == "INVALID":
        return 2
    # Passing states: document unchecked (AUDIT-VALID), conditional, or each mode's <MODE>-READY.
    status = str(out.get("status", ""))
    return 0 if status in {"AUDIT-VALID", "CONDITIONAL-GO"} or status.endswith("-READY") else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
