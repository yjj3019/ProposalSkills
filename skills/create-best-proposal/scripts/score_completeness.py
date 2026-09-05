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

_HERE = Path(__file__).resolve().parent
# 설치 트리(../../create-winning-proposal/scripts) → 저장소 트리 → PROPOSAL_GATE_PATH 순으로 proposal_gate 탐색
for _cand in (_HERE.parent.parent / "create-winning-proposal" / "scripts",
              _HERE.parents[2] / "skills" / "create-winning-proposal" / "scripts",
              Path(__import__("os").environ.get("PROPOSAL_GATE_PATH", "/nonexistent")).parent):
    if (_cand / "proposal_gate.py").is_file():
        sys.path.insert(0, str(_cand))
        break
from proposal_gate import evaluate, readiness, validate_schema  # noqa: E402


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


QUALITY_METRICS = ("compliance_coverage", "claim_support_rate", "defect_penalty", "rehearsal_score")


def validate_quality_metrics(metrics: object) -> list[str]:
    """지표는 4개 모두 필수, 숫자(bool 제외), 0~1 범위. 범위 밖·문자열은 INVALID."""
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
    """제안 품질(0~100). 지표는 0~1(검증 후 호출). 가중치는 audit-schema.md와 일치."""
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
        # 조건부입찰이 미결 항목으로 막히면 '결정 거부'가 아니라 다운그레이드임을 표기.
        if decision == "conditional-bid":
            downgraded_from = "CONDITIONAL-GO"
    else:
        # 라벨은 게이트와 같은 판정 함수에서 나온다. 다만 이 스크립트는 실제 파일을
        # 보지 않으므로 제출 준비(SUBMISSION-READY)로 승격하지 않는다 —
        # 그 판정은 unified_gate --doc <최종파일>의 해시 대조로만 받는다.
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
    except (OSError, ValueError) as exc:  # JSONDecodeError·UnicodeDecodeError 포함
        print(f"invalid input: {exc}", file=sys.stderr)
        return 2
    try:
        out = score(audit, metrics)
    except Exception as exc:  # 게이트 환경 오류 등
        print(f"invalid input: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if out.get("status") == "INVALID":
        return 2
    # 통과 상태: 문서 미검사(AUDIT-VALID)·조건부·각 모드의 <MODE>-READY.
    status = str(out.get("status", ""))
    return 0 if status in {"AUDIT-VALID", "CONDITIONAL-GO"} or status.endswith("-READY") else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
