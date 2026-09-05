#!/usr/bin/env python3
"""Return 0 only when a proposal audit JSON passes deterministic gates."""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_FIELDS = {
    "mode", "bid_decision", "bid_conditions", "requirements", "claims",
    "unresolved_tokens", "attachments", "source_conflicts", "checks",
    "inputs", "defects", "artifact_required", "render", "package", "submission",
}
ARRAY_FIELDS = {
    "bid_conditions", "requirements", "claims", "unresolved_tokens",
    "attachments", "source_conflicts", "inputs", "defects",
}
OBJECT_FIELDS = {"checks", "render", "package", "submission"}
MODES = {"submission", "draft", "review", "analysis"}
BID_DECISIONS = {"bid", "conditional-bid", "intake-incomplete", "no-bid"}
INPUT_CLASSES = {"blocking", "non-blocking", "assumption"}
DEFECT_SEVERITIES = {"critical", "major", "minor", "note"}
ITEM_STATUSES = {"open", "closed"}
ARTIFACT_MODES = {"submission-candidate", "simulation-only"}
REQUIRED_PACKAGE_CHECKS = {
    "metadata", "notes", "comments", "hidden-content", "embedded-files",
    "external-links", "macros", "stale-customer-data", "price-leakage",
}
# 선택 필드(후방호환): 존재할 때만 검증한다.
OPTIONAL_ARRAY_FIELDS = {"regulatory_checks", "vendor_confirmations", "eligibility"}
REGULATORY_STATUSES = {"met", "gap", "in-progress", "not-applicable"}
VENDOR_KINDS = {"support", "supply"}
CLAIM_KINDS = {"material", "commitment", "informational"}
# 엄격 불리언 필드: JSON true만 참. "yes"/"pending"/"no" 같은 문자열은 스키마 오류로
# 거절한다(진리값 평가로 비어있지 않은 문자열이 통과하던 P0 허위 통과 차단).
STRICT_BOOL_FIELDS = {
    "bid_conditions": ("accepted",),
    "requirements": ("mandatory",),
    "claims": ("owner_approved",),
    "attachments": ("required", "present"),
    "vendor_confirmations": ("required", "present"),
    "eligibility": ("met", "curable", "mandatory"),
}
STRICT_BOOL_OBJECT_FIELDS = {
    "render": ("verified",),
    "package": ("required", "inspected"),
    "submission": ("cleared",),
}


def _true(value: object) -> bool:
    return value is True


# 근거·해시 자리에 들어온 플레이스홀더. 'TBD'나 '[NEEDS INPUT]'은 근거가 아니다.
_PLACEHOLDER_RE = re.compile(
    r"(?:^|[^A-Za-z])(?:tbd|tba|todo|n/?a|xxx+|\?\?+|lorem|placeholder|dummy)(?:$|[^A-Za-z])"
    r"|needs\s*input|입력\s*요망|미정|추후|확인\s*필요|○○○|OOO",
    re.IGNORECASE)


def _is_placeholder(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return True
    return _PLACEHOLDER_RE.search(value) is not None


def _evidence_ok(values: object) -> bool:
    """비어 있지 않고, 플레이스홀더가 아닌 문자열 근거가 1개 이상."""
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list):
        return False
    return any(isinstance(v, str) and not _is_placeholder(v) for v in values)


class GateEnvironmentError(RuntimeError):
    """실행 환경 오류(PROPOSAL_GATE_NOW 형식 등) — 게이트 판정이 아닌 사용 오류."""


def reference_now() -> datetime:
    """기준 현재시각. 결정론적 테스트를 위해 PROPOSAL_GATE_NOW(ISO)로 주입 가능."""
    override = os.environ.get("PROPOSAL_GATE_NOW")
    if override:
        try:
            dt = datetime.fromisoformat(override.replace("Z", "+00:00"))
        except ValueError as exc:
            # 조용히 벽시계로 폴백하면 테스트가 실제 시각으로 통과해 버린다 → 명시 오류.
            raise GateEnvironmentError(f"PROPOSAL_GATE_NOW is not ISO datetime: {override!r}") from exc
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def deadline_in_future(value: str) -> bool:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt > reference_now()


def is_iso_datetime(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return "T" in value and parsed.tzinfo is not None
    except ValueError:
        return False


def validate_schema(data: object) -> list[str]:
    if not isinstance(data, dict):
        return ["audit root must be an object"]
    failures = [f"missing field: {name}" for name in sorted(REQUIRED_FIELDS - data.keys())]
    failures += [f"{name} must be an array" for name in sorted(ARRAY_FIELDS)
                 if name in data and not isinstance(data[name], list)]
    failures += [f"{name} must be an object" for name in sorted(OBJECT_FIELDS)
                 if name in data and not isinstance(data[name], dict)]
    if "artifact_required" in data and not isinstance(data["artifact_required"], bool):
        failures.append("artifact_required must be a boolean")
    if "artifact_mode" in data and data["artifact_mode"] not in ARTIFACT_MODES:
        failures.append(f"unsupported artifact_mode: {data['artifact_mode']}")
    for name in ("bid_conditions", "requirements", "claims", "attachments", "inputs", "defects"):
        if isinstance(data.get(name), list) and any(not isinstance(item, dict) for item in data[name]):
            failures.append(f"{name} entries must be objects")
    for condition in data.get("bid_conditions", []) if isinstance(data.get("bid_conditions"), list) else []:
        if isinstance(condition, dict) and not is_iso_datetime(condition.get("deadline")):
            failures.append(f"bid condition {condition.get('id', '?')} lacks ISO deadline with timezone")
    if "mode" in data and data["mode"] not in MODES:
        failures.append(f"unsupported mode: {data['mode']}")
    if "bid_decision" in data and data["bid_decision"] not in BID_DECISIONS:
        failures.append(f"unsupported bid_decision: {data['bid_decision']}")
    for item in data.get("inputs", []) if isinstance(data.get("inputs"), list) else []:
        if not isinstance(item, dict):
            continue
        if item.get("class") not in INPUT_CLASSES:
            failures.append(f"input {item.get('id', '?')} has unsupported class: {item.get('class')}")
        if item.get("status") not in ITEM_STATUSES:
            failures.append(f"input {item.get('id', '?')} has unsupported status: {item.get('status')}")
    for defect in data.get("defects", []) if isinstance(data.get("defects"), list) else []:
        if not isinstance(defect, dict):
            continue
        if defect.get("severity") not in DEFECT_SEVERITIES:
            failures.append(
                f"defect {defect.get('id', '?')} has unsupported severity: {defect.get('severity')}")
        if defect.get("status") not in ITEM_STATUSES:
            failures.append(f"defect {defect.get('id', '?')} has unsupported status: {defect.get('status')}")
        if defect.get("severity") in {"critical", "major"} and defect.get("status") == "closed":
            if not _evidence_ok(defect.get("closure_evidence")):
                failures.append(f"defect {defect.get('id', '?')} lacks closure evidence")
            if not defect.get("reviewer"):
                failures.append(f"defect {defect.get('id', '?')} lacks closure reviewer")
            if not is_iso_datetime(defect.get("closed_at")):
                failures.append(f"defect {defect.get('id', '?')} lacks ISO closed_at")
            if not isinstance(defect.get("reverified_scope"), list) or not defect["reverified_scope"]:
                failures.append(f"defect {defect.get('id', '?')} lacks reverified scope")
    package = data.get("package")
    if isinstance(package, dict) and "checks" in package and not isinstance(package["checks"], dict):
        failures.append("package checks must be an object")
    render = data.get("render")
    if isinstance(render, dict) and "evidence" in render and not isinstance(render["evidence"], list):
        failures.append("render evidence must be an array")
    for name in OPTIONAL_ARRAY_FIELDS:
        if name in data and not isinstance(data[name], list):
            failures.append(f"{name} must be an array")
        elif isinstance(data.get(name), list) and any(not isinstance(x, dict) for x in data[name]):
            failures.append(f"{name} entries must be objects")
    if "flags" in data and not isinstance(data["flags"], dict):
        failures.append("flags must be an object")
    for check in data.get("regulatory_checks", []) if isinstance(data.get("regulatory_checks"), list) else []:
        if isinstance(check, dict) and check.get("status") not in REGULATORY_STATUSES:
            failures.append(f"regulatory check {check.get('id', '?')} has unsupported status: {check.get('status')}")
    for vc in data.get("vendor_confirmations", []) if isinstance(data.get("vendor_confirmations"), list) else []:
        if isinstance(vc, dict) and vc.get("kind") not in VENDOR_KINDS:
            failures.append(f"vendor confirmation {vc.get('id', '?')} has unsupported kind: {vc.get('kind')}")
    # eligibility met/curable 불리언 검증은 STRICT_BOOL_FIELDS에서 일괄 수행한다.
    sub = data.get("submission")
    if isinstance(sub, dict) and "deadline" in sub and not is_iso_datetime(sub["deadline"]):
        failures.append("submission deadline must be ISO datetime with timezone")
    for list_name, keys in STRICT_BOOL_FIELDS.items():
        items = data.get(list_name)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            for key in keys:
                if key in item and not isinstance(item[key], bool):
                    label = {"eligibility": "eligibility"}.get(list_name, list_name[:-1])
                    failures.append(
                        f"{label} {item.get('id', item.get('name', '?'))}."
                        f"{key} must be a boolean (got {item[key]!r})")
    for obj_name, keys in STRICT_BOOL_OBJECT_FIELDS.items():
        obj = data.get(obj_name)
        if not isinstance(obj, dict):
            continue
        for key in keys:
            if key in obj and not isinstance(obj[key], bool):
                failures.append(f"{obj_name}.{key} must be a boolean (got {obj[key]!r})")
    for claim in data.get("claims", []) if isinstance(data.get("claims"), list) else []:
        if isinstance(claim, dict) and "kind" in claim and claim["kind"] not in CLAIM_KINDS:
            failures.append(f"claim {claim.get('id', '?')} has unsupported kind: {claim['kind']}")
    return sorted(set(failures), key=failures.index)


def evaluate(data: dict) -> list[str]:
    failures = validate_schema(data)
    if failures:
        return failures

    decision = data["bid_decision"]
    mode = data["mode"]
    if decision == "conditional-bid":
        if not data["bid_conditions"]:
            failures.append("conditional-bid requires conditions")
        for condition in data["bid_conditions"]:
            if not condition.get("owner") or not condition.get("deadline") \
                    or not _true(condition.get("accepted")):
                failures.append(f"bid condition {condition.get('id', '?')} is not accepted")
            elif not deadline_in_future(condition["deadline"]):
                failures.append(
                    f"bid condition {condition.get('id', '?')} deadline has passed: {condition['deadline']}")
        if mode == "submission":
            # 조건부는 내부 계속 진행 상태일 뿐, 외부 제출 클리어가 아니다.
            failures.append("submission mode requires bid_decision 'bid' (conditional-bid is internal only)")
    elif decision != "bid":
        failures.append("bid_decision must be 'bid' or accepted 'conditional-bid'")

    mandatory_count = 0
    for item in data["requirements"]:
        # fail-closed: mandatory 미기재는 필수로 취급한다(생략으로 우회 방지).
        if item.get("mandatory", True) is False:
            continue
        mandatory_count += 1
        if item.get("state") == "approved":
            # 반낙관: approved 자기선언만으로는 통과 불가. 비어있지 않은 문자열 근거 필수.
            if not _evidence_ok(item.get("evidence_refs")):
                failures.append(f"requirement {item.get('id', '?')} approved without evidence_refs")
            continue
        if item.get("state") == "not-applicable" and item.get("rationale") and item.get("reviewer"):
            continue
        failures.append(f"requirement {item.get('id', '?')} is not approved")
    if mode == "submission" and mandatory_count == 0:
        failures.append("submission requires at least one mandatory requirement in the ledger")

    for claim in data["claims"]:
        # kind 미기재는 material로 취급한다(생략으로 우회 방지).
        kind = claim.get("kind", "material")
        if kind not in {"material", "commitment"}:
            continue
        if claim.get("status") not in {"supported", "qualified", "removed"}:
            failures.append(f"claim {claim.get('id', '?')} is unsupported")
        if kind == "commitment" and not _true(claim.get("owner_approved")):
            failures.append(f"commitment {claim.get('id', '?')} lacks owner approval")

    failures.extend(f"unresolved token: {token}" for token in data["unresolved_tokens"])
    failures.extend(f"source conflict: {item}" for item in data["source_conflicts"])

    for item in data["inputs"]:
        if item.get("class") == "blocking" and item.get("status") != "closed":
            failures.append(f"blocking input {item.get('id', '?')} is open")

    for defect in data["defects"]:
        if defect.get("severity") in {"critical", "major"} and defect.get("status") != "closed":
            failures.append(f"{defect.get('severity')} defect {defect.get('id', '?')} is open")

    for attachment in data["attachments"]:
        if attachment.get("required", True) is not False and not _true(attachment.get("present")):
            failures.append(f"missing attachment: {attachment.get('name', '?')}")

    # submission 체크(파일명·형식·부수 등 제출 규정)는 제출 모드에서만 요구한다. draft/review에서
    # 요구하면 Pink/Red 체크포인트가 구조적으로 도달 불가능해진다(consistency·arithmetic은 전 모드).
    required_checks = ("consistency", "arithmetic") + (("submission",) if mode == "submission" else ())
    for name in required_checks:
        if data["checks"].get(name) is not True:
            failures.append(f"check failed or missing: {name}")

    if data["artifact_required"] and not _true(data["render"].get("verified")):
        failures.append("render verification is missing or failed")
    if data["artifact_required"] and _true(data["render"].get("verified")):
        for field in ("artifact_hash", "tool"):
            if _is_placeholder(data["render"].get(field)):
                failures.append(f"render verification lacks {field}")
        if not _evidence_ok(data["render"].get("evidence")):
            failures.append("render verification lacks evidence")
    package_required = _true(data["package"].get("required")) or mode == "submission"
    if package_required and not _true(data["package"].get("inspected")):
        failures.append("package inspection is missing or failed")
    if package_required and _true(data["package"].get("inspected")):
        for field in ("artifact_hash", "tool", "reviewer"):
            if _is_placeholder(data["package"].get(field)):
                failures.append(f"package inspection lacks {field}")
        if not data["package"].get("checks"):
            failures.append("package inspection lacks checks")
        for name, status in data["package"].get("checks", {}).items():
            if status not in {"pass", "fail", "not-inspected", "not-applicable"}:
                failures.append(f"package check {name} has unsupported status: {status}")
            elif status == "fail" or (data["mode"] == "submission" and status == "not-inspected"):
                failures.append(f"package check {name} is {status}")
        if data["mode"] == "submission":
            for name in sorted(REQUIRED_PACKAGE_CHECKS - data["package"].get("checks", {}).keys()):
                failures.append(f"missing required package check: {name}")
    if data["mode"] == "submission":
        if not _true(data["submission"].get("cleared")):
            failures.append("submission is not cleared")
        if not _evidence_ok(data["submission"].get("rehearsal_evidence")):
            failures.append("submission rehearsal evidence is missing")
        if _is_placeholder(data["submission"].get("receipt_plan")):
            failures.append("submission receipt plan is missing")

    # 반낙관 가드 1: 마감일 vs 현재일. 제출 모드는 마감일 필수이며 과거이면 차단.
    deadline = data["submission"].get("deadline")
    if data["mode"] == "submission" and not deadline:
        failures.append("submission deadline is missing")
    elif deadline and is_iso_datetime(deadline) and not deadline_in_future(deadline):
        failures.append(f"submission deadline has passed: {deadline}")

    # 반낙관 가드 3: 계량 자격 일관성. 미충족+치유불가면 bid 금지,
    # 미충족+치유가능이면 단독 bid 금지(조건부입찰/불참만 허용). 제출 모드는 원장 필수.
    eligibility = data.get("eligibility", [])
    for e in eligibility:
        if e.get("mandatory", True) is False or _true(e.get("met")):
            continue
        # fail-closed: curable 미지정은 보수적으로 '치유불가'로 취급(생략으로 우회 방지).
        if not _true(e.get("curable")):
            if decision != "no-bid":
                failures.append(
                    f"eligibility {e.get('id', '?')} unmet and incurable; bid not permitted")
        elif decision == "bid":
            failures.append(
                f"eligibility {e.get('id', '?')} unmet; requires conditional-bid or no-bid")
    if data["mode"] == "submission" and not eligibility:
        failures.append("submission requires eligibility ledger")

    # 제조사 확약(vendor_confirmations): 필수인데 미제출이면 차단(계약 전 독소조항 대응).
    for vc in data.get("vendor_confirmations", []):
        if vc.get("required", True) is not False and not _true(vc.get("present")):
            failures.append(f"vendor confirmation {vc.get('id', '?')} ({vc.get('kind', '?')}) is missing")

    # 금융 등 규제 완료증거(regulatory_checks): 명시적 gap/in-progress는 차단,
    # met는 증거 필요. 금융 플래그가 켜진 제출 건은 규제 검사 목록이 반드시 있어야 한다.
    reg_checks = data.get("regulatory_checks", [])
    for check in reg_checks:
        status = check.get("status")
        if status in {"gap", "in-progress"}:
            failures.append(f"regulatory check {check.get('id', '?')} is {status}")
        elif status == "met" and not _evidence_ok(check.get("evidence")):
            failures.append(f"regulatory check {check.get('id', '?')} claims met without evidence")
    if data.get("flags", {}).get("financial") and data["mode"] == "submission" and not reg_checks:
        failures.append("financial submission requires regulatory_checks")
    return failures


DECISION_STOP = {"no-bid", "intake-incomplete"}


def remediation_hint(failure: str) -> str:
    """차단 사유별 '무엇을 고칠지' 한 줄 조치 힌트. 작성자가 바로 행동하게 한다."""
    f = failure.lower()
    table = [
        ("approved without evidence_refs", "해당 요구에 근거(evidence_refs: 제안서 위치·산출물 해시)를 채운다"),
        ("deadline has passed", "마감이 지났다 — 제출 불가. 차기 공고 대응 또는 no-bid로 전환한다"),
        ("deadline is missing", "submission.deadline(ISO/tz)을 RFP 마감으로 채운다"),
        ("requires eligibility ledger", "eligibility 원장(기준·보유값·치유수단)을 작성한다"),
        ("incurable; bid not permitted", "치유 불가 자격 미달 — bid를 no-bid로 정정한다"),
        ("requires conditional-bid or no-bid", "치유 가능 미달 — accepted 조건을 단 conditional-bid로 바꾼다"),
        ("vendor confirmation", "제조사 기술지원·공급 확약서를 확보해 present=true로 갱신한다"),
        ("regulatory check", "해당 규제 항목을 met+증거로 완결하거나 gap을 해소한다"),
        ("missing attachment", "누락 필수 서식을 제출물에 포함한다"),
        ("missing required package check", "패키지 무결성 검사 항목을 수행해 결과를 기록한다"),
        ("is not approved", "해당 필수 요구를 검토자 승인(approved) 상태로 완결한다"),
        ("is not cleared", "제출 리허설·접수 증적 계획을 완료해 submission.cleared=true로 한다"),
        ("rehearsal evidence", "제출 파일 생성·업로드 리허설을 수행하고 증적을 남긴다"),
        ("receipt plan", "접수 확인(수신증) 캡처 계획을 채운다"),
        ("unresolved token", "미해결 토큰(NEEDS INPUT 등)을 실제 값으로 채운다"),
        ("source conflict", "수정공고·Q&A 우선순위로 충돌 값을 정리한다"),
        ("blocking input", "미결 blocking 입력을 확보해 closed 처리한다"),
        ("defect", "미해결 Critical/Major 결함을 조치·재검증한다"),
        ("owner approval", "커밋먼트(약속) 항목에 책임 owner 승인을 받는다"),
        ("must be 'bid'", "no-bid/intake-incomplete는 제출 대상이 아니다 — 결정 메모로 종료한다"),
        ("conditional-bid is internal only", "조건을 모두 해소한 뒤 bid_decision=bid로 정정하거나 mode=draft로 내부 진행한다"),
        ("at least one mandatory requirement", "요구 원장이 비었다 — RFP 필수 요구를 추출해 requirements에 채운다"),
        ("bid condition", "조건 owner·ISO 기한(미래)·accepted=true를 채우거나 기한을 재협의한다"),
    ]
    for key, hint in table:
        if key in f:
            return hint
    return "해당 항목을 audit-schema.md 기준으로 완결한다"


def explain_markdown(data: dict, schema_failures: list[str], failures: list[str]) -> str:
    """게이트 결과를 사람이 바로 고칠 수 있는 마크다운으로 설명한다."""
    if schema_failures:
        lines = ["## 게이트 결과: INVALID AUDIT (스키마 오류)", "",
                 "| # | 스키마 오류 | 조치 |", "|---|---|---|"]
        for i, f in enumerate(schema_failures, 1):
            lines.append(f"| {i} | {f} | audit-schema.md의 필드 타입·필수값을 확인한다 |")
        return "\n".join(lines)
    decision = data.get("bid_decision")
    if not failures:
        return "## 게이트 결과: READY\n\n제출 가능. 모든 결정론적 게이트를 통과했다."
    # no-bid·intake-incomplete는 '의도된 정지'이므로 결함이 아니라 결정 메모로 제시한다.
    if decision in DECISION_STOP:
        residual = [f for f in failures if "must be 'bid'" not in f.lower()
                    and "check failed or missing: submission" not in f.lower()]
        lines = [f"## 게이트 결과: DECISION_MEMO ({decision})", "",
                 f"이 audit은 **{decision}** 결정이다 — 제출하지 않는 것이 정상이며, 아래는 결함이 아니라 결정 근거다.",
                 "", "| # | 판단 근거 | 비고 |", "|---|---|---|"]
        basis = residual or ["자격·마감·필수 증빙 미충족으로 참여하지 않음"]
        for i, f in enumerate(basis, 1):
            lines.append(f"| {i} | {f} | 정상적인 불참/보류 결정 |")
        return "\n".join(lines)
    header = "## 게이트 결과: BLOCKED"
    if decision == "conditional-bid":
        header += "\n\n> 주의: `conditional-bid`이지만 미결 항목으로 **CONDITIONAL-GO → NO-GO 다운그레이드**됨. 아래를 해소하면 CONDITIONAL-GO로 회복된다."
    lines = [header, "", "| # | 차단 사유 | 조치 |", "|---|---|---|"]
    for i, f in enumerate(failures, 1):
        lines.append(f"| {i} | {f} | {remediation_hint(f)} |")
    return "\n".join(lines)


def _utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv: list[str]) -> int:
    import argparse
    _utf8_console()
    ap = argparse.ArgumentParser(
        prog="proposal_gate.py",
        description="Deterministic proposal submission gate. exit 0=READY/CONDITIONAL-GO, "
                    "1=BLOCKED/DECISION_MEMO, 2=invalid audit or usage error.")
    ap.add_argument("audit", type=Path, help="audit JSON (see references/audit-schema.md)")
    ap.add_argument("--explain", action="store_true", help="print Markdown remediation table")
    try:
        ns = ap.parse_args(argv[1:])
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2
    explain = ns.explain
    try:
        data = json.loads(ns.audit.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:  # JSONDecodeError·UnicodeDecodeError 포함
        print(f"invalid audit file: {exc}", file=sys.stderr)
        return 2
    schema_failures = validate_schema(data)
    try:
        failures = [] if schema_failures else evaluate(data)
    except GateEnvironmentError as exc:
        print(f"gate environment error: {exc}", file=sys.stderr)
        return 2
    if explain:
        print(explain_markdown(data, schema_failures, failures))
        return 2 if schema_failures else (1 if failures else 0)
    if schema_failures:
        print("INVALID AUDIT")
        for failure in schema_failures:
            print(f"- {failure}")
        return 2
    if failures:
        decision = data.get("bid_decision")
        # S5: no-bid/intake-incomplete는 기본 CLI에서도 의도 정지로 표기 (explain 없이도).
        if decision in DECISION_STOP:
            print("DECISION_MEMO")
            for failure in failures:
                if failure == "bid_decision must be 'bid' or accepted 'conditional-bid'":
                    print(
                        f"- DECISION_MEMO_ONLY: bid_decision={decision}; "
                        "full proposal drafting blocked; deliver decision memo only")
                else:
                    print(f"- {failure}")
        else:
            print("BLOCKED")
            for failure in failures:
                print(f"- {failure}")
        return 1
    if data.get("bid_decision") == "conditional-bid":
        print("CONDITIONAL-GO")
        print("internal continuation only — not external submission clearance")
    else:
        print("READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
