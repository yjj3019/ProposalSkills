#!/usr/bin/env python3
"""완성도 점수 일원화(SI-15): 제안 품질 축과 제출가능성 축을 한 산식으로 산출한다.

두 skill(create-proposal-document / create-winning-proposal)과 다중 리뷰어가
'overall 수치'를 제각기 계산해 값이 갈리는 문제(예: 66.9 vs 82.6)를 없애기 위해,
동일 audit JSON에서 결정론적으로 두 축과 최종 상태를 계산한다.

- 제출가능성(readiness) 축: proposal_gate 게이트 + 세부 차원 충족률.
- 제안 품질(quality) 축: --quality 지표 파일(0~1 값)이 있을 때만 산출.
- 최종 상태(headline): 오직 게이트로 결정(open BLOCKING -> NO-GO).
  품질 점수가 높아도 게이트가 막히면 절대 GO가 되지 않는다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "skills/create-winning-proposal/scripts"))
from proposal_gate import evaluate, validate_schema  # noqa: E402


def readiness_dimensions(d: dict) -> list[tuple[str, bool]]:
    """제출가능성 세부 차원(충족 여부). 게이트 실패와 별개로 진행률을 보여준다."""
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


def quality_score(metrics: dict) -> float:
    """제안 품질(0~100). 지표는 0~1. 가중치는 audit-schema.md와 일치."""
    c = float(metrics.get("compliance_coverage", 0.0))
    s = float(metrics.get("claim_support_rate", 0.0))
    dp = float(metrics.get("defect_penalty", 0.0))
    r = float(metrics.get("rehearsal_score", 0.0))
    return round(100 * (0.4 * c + 0.3 * s + 0.2 * (1 - dp) + 0.1 * r), 1)


def score(audit: dict, metrics: dict | None) -> dict:
    schema_failures = validate_schema(audit)
    if schema_failures:
        return {"status": "INVALID", "blocking": schema_failures}
    dims = readiness_dimensions(audit)
    satisfied = sum(1 for _, ok in dims if ok)
    readiness = round(100 * satisfied / len(dims), 1)
    blocking = evaluate(audit)
    decision = audit.get("bid_decision")
    downgraded_from = None
    if blocking:
        status = "NO-GO"
        # 조건부입찰이 미결 항목으로 막히면 '결정 거부'가 아니라 다운그레이드임을 표기.
        if decision == "conditional-bid":
            downgraded_from = "CONDITIONAL-GO"
    elif decision == "conditional-bid":
        status = "CONDITIONAL-GO"
    elif audit.get("mode") == "submission":
        status = "SUBMISSION-READY"
    else:
        status = "DRAFT"
    result = {
        "status": status,
        "readiness_score": readiness,
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
    try:
        audit = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        metrics = json.loads(Path(argv[2]).read_text(encoding="utf-8")) if len(argv) > 2 else None
    except (OSError, json.JSONDecodeError) as exc:
        print(f"invalid input: {exc}", file=sys.stderr)
        return 2
    out = score(audit, metrics)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("status") in {"SUBMISSION-READY", "CONDITIONAL-GO", "DRAFT"} else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
