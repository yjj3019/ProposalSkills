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
# 의도된 정지 결정 — 결함이 아니라 결정 메모로 제시한다.
DECISION_STOP = {"no-bid", "intake-incomplete"}
REQUIRED_PACKAGE_CHECKS = {
    "metadata", "notes", "comments", "hidden-content", "embedded-files",
    "external-links", "macros", "stale-customer-data", "price-leakage",
}
# 선택 필드(후방호환): 존재할 때만 검증한다.
OPTIONAL_ARRAY_FIELDS = {"regulatory_checks", "vendor_confirmations", "eligibility", "numbers"}
REGULATORY_STATUSES = {"met", "gap", "in-progress", "not-applicable"}
VENDOR_KINDS = {"support", "supply"}
CLAIM_KINDS = {"material", "commitment", "informational"}
# 요구 강도. 실제 공고는 필수/권장/선택/조건부/참고를 구분하는데 mandatory 불리언 하나로는
# 권장 분량 초과와 필수 위반이 같은 무게가 된다. mandatory는 후방호환으로 남긴다.
STRENGTHS = {"required", "recommended", "optional", "conditional", "informational"}
MANDATORY_STRENGTHS = {"required", "conditional"}
STRENGTH_OF_MANDATORY = {True: "required", False: "optional"}


def requirement_strength(item: dict) -> str:
    """요구 강도. strength가 없으면 mandatory에서 유도한다(미기재 = 필수, fail-closed)."""
    strength = item.get("strength")
    if isinstance(strength, str) and strength in STRENGTHS:
        return strength
    return STRENGTH_OF_MANDATORY[item.get("mandatory", True) is not False]
# 원장 항목이 무엇인지 사람이 읽을 수 있는 필드. 하나라도 있으면 된다.
LEDGER_TEXT_FIELDS = ("text", "label", "title", "summary", "description")
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
    "render": ("verified", "render_succeeded", "layout_checked", "visual_review_approved"),
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


def _enum_ok(value: object, allowed: "set[str] | frozenset[str]") -> bool:
    """열거값 검사. 비문자열(list·dict 등)은 조용히 거부한다 —
    `value in allowed`가 unhashable 입력에서 TypeError로 터지던 결함 해소."""
    return isinstance(value, str) and value in allowed


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
    if "artifact_mode" in data and not _enum_ok(data["artifact_mode"], ARTIFACT_MODES):
        failures.append(f"unsupported artifact_mode: {data['artifact_mode']}")
    for name in ("bid_conditions", "requirements", "claims", "attachments", "inputs", "defects"):
        if isinstance(data.get(name), list) and any(not isinstance(item, dict) for item in data[name]):
            failures.append(f"{name} entries must be objects")
    for condition in data.get("bid_conditions", []) if isinstance(data.get("bid_conditions"), list) else []:
        if isinstance(condition, dict) and not is_iso_datetime(condition.get("deadline")):
            failures.append(f"bid condition {condition.get('id', '?')} lacks ISO deadline with timezone")
    if "mode" in data and not _enum_ok(data["mode"], MODES):
        failures.append(f"unsupported mode: {data['mode']}")
    if "bid_decision" in data and not _enum_ok(data["bid_decision"], BID_DECISIONS):
        failures.append(f"unsupported bid_decision: {data['bid_decision']}")
    for item in data.get("inputs", []) if isinstance(data.get("inputs"), list) else []:
        if not isinstance(item, dict):
            continue
        if not _enum_ok(item.get("class"), INPUT_CLASSES):
            failures.append(f"input {item.get('id', '?')} has unsupported class: {item.get('class')}")
        if not _enum_ok(item.get("status"), ITEM_STATUSES):
            failures.append(f"input {item.get('id', '?')} has unsupported status: {item.get('status')}")
    for defect in data.get("defects", []) if isinstance(data.get("defects"), list) else []:
        if not isinstance(defect, dict):
            continue
        if not _enum_ok(defect.get("severity"), DEFECT_SEVERITIES):
            failures.append(
                f"defect {defect.get('id', '?')} has unsupported severity: {defect.get('severity')}")
        if not _enum_ok(defect.get("status"), ITEM_STATUSES):
            failures.append(f"defect {defect.get('id', '?')} has unsupported status: {defect.get('status')}")
        if _enum_ok(defect.get("severity"), {"critical", "major"}) and defect.get("status") == "closed":
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
        if isinstance(check, dict) and not _enum_ok(check.get("status"), REGULATORY_STATUSES):
            failures.append(f"regulatory check {check.get('id', '?')} has unsupported status: {check.get('status')}")
    for vc in data.get("vendor_confirmations", []) if isinstance(data.get("vendor_confirmations"), list) else []:
        if isinstance(vc, dict) and not _enum_ok(vc.get("kind"), VENDOR_KINDS):
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
    failures += validate_context(data.get("context"))
    for i, req in enumerate(data.get("requirements", []) if isinstance(data.get("requirements"), list) else []):
        if not isinstance(req, dict) or "strength" not in req:
            continue
        rid = req.get("id", i)
        strength = req["strength"]
        if not _enum_ok(strength, STRENGTHS):
            failures.append(f"requirement {rid} has unsupported strength: {strength!r} "
                            f"(allowed: {', '.join(sorted(STRENGTHS))})")
            continue
        # 두 표현이 어긋나면 어느 쪽이 맞는지 게이트가 고를 수 없다.
        if "mandatory" in req and isinstance(req["mandatory"], bool) \
                and (strength in MANDATORY_STRENGTHS) != req["mandatory"]:
            failures.append(f"requirement {rid} strength={strength} contradicts "
                            f"mandatory={req['mandatory']} — 한쪽을 지운다")
        if strength == "conditional" and _is_placeholder(req.get("condition")):
            failures.append(f"requirement {rid} is conditional but lacks a condition "
                            "— 어떤 조건에서 필수가 되는지 적는다")
    for claim in data.get("claims", []) if isinstance(data.get("claims"), list) else []:
        if isinstance(claim, dict) and "kind" in claim and not _enum_ok(claim["kind"], CLAIM_KINDS):
            failures.append(f"claim {claim.get('id', '?')} has unsupported kind: {claim['kind']}")
    # ID 무결성: 원장 항목은 식별자가 있어야 추적·대조가 성립한다. ID를 지우면
    # "요구 ?가 미승인"처럼 지목 불가능한 결함이 되거나, 중복 ID로 근거가 뒤섞인다.
    for name in ("requirements", "claims"):
        items = data.get(name)
        if not isinstance(items, list):
            continue
        seen: set[str] = set()
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            rid = item.get("id")
            if not isinstance(rid, str) or not rid.strip():
                failures.append(f"{name}[{i}] lacks a non-empty id")
            elif rid in seen:
                failures.append(f"duplicate id in {name}: {rid}")
            else:
                seen.add(rid)
            # ID만 있고 내용이 없는 껍데기 원장 차단. "요구 R1 승인"은 R1이 무엇인지
            # 적혀 있어야 검증 가능한 기록이 된다. 제출 기록에만 요구한다 — 초안 단계의
            # 부분 원장까지 막으면 작성 중에 게이트를 돌릴 수 없다.
            if data.get("mode") == "submission" \
                    and not any(not _is_placeholder(item.get(f)) for f in LEDGER_TEXT_FIELDS):
                failures.append(
                    f"{name} {rid if isinstance(rid, str) and rid.strip() else i} lacks a "
                    f"human-readable text ({'/'.join(LEDGER_TEXT_FIELDS)} 중 하나에 내용을 적는다)")
            # informational은 근거 검사를 면제받는 유일한 유형이다. 면제 사유를 적게 해서
            # 근거 없는 주장을 informational로 재분류해 빠져나가는 경로를 막는다.
            if name == "claims" and _enum_ok(item.get("kind"), {"informational"}) \
                    and _is_placeholder(item.get("rationale")):
                failures.append(
                    f"claim {item.get('id', i)} is informational but lacks a rationale "
                    "— 근거 면제 사유를 적는다(주장이면 material/commitment로 분류한다)")
    return sorted(set(failures), key=failures.index)


_DIGEST_RE = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$", re.IGNORECASE)


def is_digest(value: object) -> bool:
    """sha256:<64 hex> 형식인지. 제출 모드의 artifact_hash는 실제 파일에 대조 가능해야 한다."""
    return isinstance(value, str) and _DIGEST_RE.match(value.strip()) is not None


def normalize_digest(value: object) -> str:
    """비교용 정규화 — 접두사 제거 + 소문자. 형식이 아니면 빈 문자열."""
    if not is_digest(value):
        return ""
    return str(value).strip().lower().removeprefix("sha256:")


def _exception_granted(item: object) -> bool:
    """발주처가 허용한 예외인지 — 승인자와 근거가 모두 있어야 인정한다."""
    if not isinstance(item, dict):
        return False
    return not _is_placeholder(item.get("granted_by")) and _evidence_ok(item.get("evidence"))


def _is_number(value: object) -> bool:
    """JSON 숫자만 참(bool 제외). 문자열 "3,700,000,000"은 계산 대상이 아니다."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


# 통화 단위의 절대 허용오차. 표시 반올림(원 단위)과 수천만 원 차이를 같은 상대오차로
# 다루면 37억에 1,800만원 오차가 통과한다 — 금액은 절대값으로 좁게 본다.
CURRENCY_UNITS = {"KRW", "원", "USD", "EUR", "JPY", "달러", "엔"}
CURRENCY_ABS_TOLERANCE = 1.0


def _is_finite(value: object) -> bool:
    import math
    return _is_number(value) and math.isfinite(float(value))


def _tolerance_for(item: dict, value: float, tol: float) -> float:
    """항목 성격에 맞는 허용오차. 금액은 절대값, 그 외는 상대값."""
    if str(item.get("unit", "")).strip() in CURRENCY_UNITS:
        return CURRENCY_ABS_TOLERANCE
    return max(tol * max(abs(value), 1), 1e-9)


def check_numbers(entries: object) -> list[str]:
    """수치 원장의 산술을 실제로 계산해 검증한다.

    `checks.arithmetic: true`는 사람이 기록하는 자기선언이라, 본문에 100+200=900이
    적혀 있어도 게이트가 알 수 없었다. 원장에 값을 적고 구성 요소를 연결하면
    합계·비율을 여기서 다시 계산한다.

    entry = {id, label, value, unit, source?, components?[ids], percent_of?, tolerance?}
    """
    failures: list[str] = []
    if not isinstance(entries, list):
        return ["numbers must be an array"]
    by_id: dict[str, dict] = {}
    for i, item in enumerate(entries):
        if not isinstance(item, dict):
            failures.append(f"numbers[{i}] must be an object")
            continue
        nid = item.get("id")
        if not isinstance(nid, str) or not nid.strip():
            failures.append(f"numbers[{i}] lacks a non-empty id")
            continue
        if nid in by_id:
            failures.append(f"duplicate id in numbers: {nid}")
            continue
        by_id[nid] = item
        if not _is_finite(item.get("value")):
            failures.append(f"number {nid} value must be a finite JSON number "
                            f"(got {item.get('value')!r})")
        if not isinstance(item.get("unit"), str) or not item["unit"].strip():
            failures.append(f"number {nid} lacks a unit")
        if _is_placeholder(item.get("label")):
            failures.append(f"number {nid} lacks a label")
    for nid, item in by_id.items():
        tol = item.get("tolerance", 0.005)
        if not _is_number(tol) or tol < 0:
            failures.append(f"number {nid} tolerance must be a non-negative number")
            tol = 0.005
        if not isinstance(item.get("unit"), str):
            # 단위가 문자열이 아니면 위에서 이미 차단됐다. 여기서 계속 진행하면
            # 해시 불가 값(dict/list)이 set에 들어가 TypeError로 게이트가 죽는다.
            continue
        parts = item.get("components")
        if parts is not None:
            if not isinstance(parts, list) or not parts:
                failures.append(f"number {nid} components must be a non-empty array")
                continue
            missing = [p for p in parts if not isinstance(p, str) or p not in by_id]
            if missing:
                failures.append(f"number {nid} references unknown components: {missing}")
                continue
            if nid in parts:
                failures.append(f"number {nid} lists itself as a component — 검산이 성립하지 않는다")
                continue
            if not all(isinstance(by_id[p].get("unit"), str) for p in parts):
                continue  # 구성요소 단위가 문자열이 아니면 위에서 이미 차단됐다
            units = {by_id[p].get("unit") for p in parts} | {item.get("unit")}
            if len(units) > 1:
                failures.append(f"number {nid} mixes units in a sum: {sorted(str(u) for u in units)}")
                continue
            if not all(_is_finite(by_id[p].get("value")) for p in parts) or not _is_finite(item.get("value")):
                continue
            total = sum(by_id[p]["value"] for p in parts)
            if abs(total - item["value"]) > _tolerance_for(item, item["value"], tol):
                failures.append(
                    f"number {nid} ({item.get('label', '')}) is {item['value']} but its components "
                    f"sum to {total} — 합계가 맞지 않는다")
        base = item.get("percent_of")
        if base is not None:
            if not isinstance(base, str) or base not in by_id:
                failures.append(f"number {nid} references unknown percent_of: {base!r}")
                continue
            if item.get("unit") != "%":
                failures.append(f"number {nid} uses percent_of but its unit is not '%'")
                continue
            if base == nid:
                failures.append(f"number {nid} is a percentage of itself")
                continue
            share, whole = item.get("value"), by_id[base].get("value")
            amount = item.get("amount")
            # 계산할 수 없으면 통과가 아니라 미검증이다 — 조용히 넘기면 비율이 무검사로 남는다.
            if not _is_finite(amount):
                failures.append(f"number {nid} uses percent_of but lacks a finite 'amount' "
                                "(분자) — 검산할 수 없다")
            elif not _is_finite(whole) or whole == 0:
                failures.append(f"number {nid} percent_of {base} has a zero or non-numeric base "
                                "— 나눗셈이 성립하지 않는다")
            elif _is_finite(share):
                expected = amount / whole * 100
                if abs(expected - share) > max(tol * max(abs(share), 1), 1e-9):
                    failures.append(
                        f"number {nid} ({item.get('label', '')}) says {share}% but "
                        f"{amount}/{whole} = {expected:.4g}% — 비율이 맞지 않는다")
    return failures


# 제안 맥락 분류 축. 기관 이름 하나로 정하지 않는다 — 공공병원·국립대학처럼 속성이
# 겹치는 조직이 있고, 같은 기관이라도 사업 성격·구매 단계에 따라 필요한 근거가 다르다.
BUYER_TYPES = {"public", "private", "education", "healthcare"}
ENGAGEMENTS = {"build", "operate", "migrate", "education", "consulting",
               "service-improvement", "product-selection", "policy"}
STAGES = {"explore", "internal-review", "rfp-response", "presentation", "final-submission"}
READING_MODES = {"screen-presentation", "print-evaluation", "individual-review", "appendix"}
CONSTRAINTS = {"sensitive-data", "business-continuity", "closed-network", "regulated-industry"}
# 읽는 조건 → 장표 규격(deck_profiles). 발표라면서 인쇄용 밀도로 만든 덱을 잡는다.
READING_MODE_PROFILE = {
    "screen-presentation": "presentation",
    "print-evaluation": "detailed-submission",
    "individual-review": "executive-summary",
}
SUBMISSION_STAGES = {"rfp-response", "final-submission"}
# 문서 종류는 구매 단계와 다른 축이다. RFI 응답은 입찰이 아니지만 자격·형식 요구는
# 있을 수 있으므로, "RFI니까 검사를 끈다"가 아니라 무엇이 달라지는지를 명시한다.
RFX_TYPES = {"rfp", "rfi", "rfq"}
KNOWN_DECK_PROFILES = set(READING_MODE_PROFILE.values())


def validate_context(context: object) -> list[str]:
    """분류 축의 값 검증. 없으면 검사하지 않는다(후방호환)."""
    if context is None:
        return []
    if not isinstance(context, dict):
        return ["context must be an object"]
    failures: list[str] = []
    buyers = context.get("buyer_types")
    if buyers is not None:
        if not isinstance(buyers, list) or not buyers:
            failures.append("context.buyer_types must be a non-empty array "
                            "(복수 속성 허용: 공공병원 → [\"public\", \"healthcare\"])")
        else:
            bad = [b for b in buyers if not _enum_ok(b, BUYER_TYPES)]
            if bad:
                failures.append(f"context.buyer_types has unsupported values: {bad} "
                                f"(allowed: {', '.join(sorted(BUYER_TYPES))})")
    for field, allowed in (("engagement", ENGAGEMENTS), ("stage", STAGES),
                           ("reading_mode", READING_MODES), ("rfx_type", RFX_TYPES)):
        value = context.get(field)
        if value is not None and not _enum_ok(value, allowed):
            failures.append(f"context.{field} has unsupported value: {value!r} "
                            f"(allowed: {', '.join(sorted(allowed))})")
    limits = context.get("constraints")
    if limits is not None:
        if not isinstance(limits, list):
            failures.append("context.constraints must be an array")
        else:
            bad = [c for c in limits if not _enum_ok(c, CONSTRAINTS)]
            if bad:
                failures.append(f"context.constraints has unsupported values: {bad} "
                                f"(allowed: {', '.join(sorted(CONSTRAINTS))})")
    return failures


def check_evaluation_criteria(data: dict) -> list[str]:
    """평가표 원장. 공공 제안에서 배점표는 목차·분량·근거의 기준이다.

    항목 = {id, label, weight, parent?, stage?, minimum_ratio?, minimum_score?,
            disclosed?(기본 true), source?}
    원문의 평가 방식은 "합계 100"으로 환원되지 않는다 — 기술 90 + 가격 별책 10, 1단계
    기술평가 안의 정량 20·정성 80, 부문별 과락이 한 공고에 같이 있다. 그래서:
    - 최상위 항목의 합은 data.evaluation_total(기본 100)과 같아야 한다.
    - 하위 항목(parent)의 합은 상위 항목의 배점과 같아야 한다 — 상·하위를 한 번에 더해
      100을 넘기던 이중 합산을 막는다.
    - 배점 미공개(disclosed:false)는 weight 없이 기록한다. 게이트가 80:20을 지어내지 않는다.
    - 과락(minimum_ratio/minimum_score)은 보존만 한다. 게이트는 심사 점수를 예측하지 않는다.
    """
    entries = data.get("evaluation_criteria")
    if entries is None:
        return []
    if not isinstance(entries, list):
        return ["evaluation_criteria must be an array"]
    failures: list[str] = []
    total_scale = data.get("evaluation_total", 100)
    if not _is_number(total_scale) or total_scale <= 0:
        failures.append(f"evaluation_total must be a positive number (got {total_scale!r})")
        total_scale = 100
    by_id: dict[str, dict] = {}
    for i, item in enumerate(entries):
        if not isinstance(item, dict):
            failures.append(f"evaluation_criteria[{i}] must be an object")
            continue
        cid = item.get("id")
        if not isinstance(cid, str) or not cid.strip():
            failures.append(f"evaluation_criteria[{i}] lacks a non-empty id")
            continue
        if cid in by_id:
            failures.append(f"duplicate id in evaluation_criteria: {cid}")
            continue
        by_id[cid] = item
        if _is_placeholder(item.get("label")):
            failures.append(f"evaluation criterion {cid} lacks a label")
        disclosed = item.get("disclosed", True)
        if not isinstance(disclosed, bool):
            failures.append(f"evaluation criterion {cid} disclosed must be a boolean")
            disclosed = True
        weight = item.get("weight")
        if disclosed:
            if not _is_number(weight) or weight < 0:
                failures.append(f"evaluation criterion {cid} weight must be a non-negative number "
                                f"(got {weight!r}) — 배점이 공개되지 않았으면 disclosed:false로 적는다")
        elif weight is not None:
            failures.append(f"evaluation criterion {cid} is undisclosed but carries a weight "
                            f"({weight!r}) — 미공개 배점을 지어내지 않는다")
        ratio = item.get("minimum_ratio")
        if ratio is not None and (not _is_number(ratio) or not 0 < ratio <= 1):
            failures.append(f"evaluation criterion {cid} minimum_ratio must be in (0, 1] "
                            f"(got {ratio!r}) — 85%는 0.85로 적는다")
        score = item.get("minimum_score")
        if score is not None:
            if not _is_number(score) or score < 0:
                failures.append(f"evaluation criterion {cid} minimum_score must be a non-negative number")
            elif _is_number(weight) and score > weight:
                failures.append(f"evaluation criterion {cid} minimum_score {score} exceeds its weight {weight}")
        for field in ("source", "stage", "method"):
            if field in item and not isinstance(item[field], str):
                failures.append(f"evaluation criterion {cid} {field} must be a string")
    # 상·하위 구조
    for cid, item in by_id.items():
        parent = item.get("parent")
        if parent is None:
            continue
        if not isinstance(parent, str) or parent not in by_id:
            failures.append(f"evaluation criterion {cid} references unknown parent: {parent!r}")
            item["_bad_parent"] = True
            continue
        seen_chain = {cid}
        node = parent
        while node is not None:
            if node in seen_chain:
                failures.append(f"evaluation criterion {cid} has a cyclic parent chain")
                item["_bad_parent"] = True
                break
            seen_chain.add(node)
            node = by_id[node].get("parent") if isinstance(by_id[node].get("parent"), str) else None

    def _weights(items: list[dict]) -> tuple[float, bool]:
        """(합계, 전부 공개·숫자였는가)."""
        total, complete = 0.0, True
        for it in items:
            w = it.get("weight")
            if it.get("disclosed", True) is False or not _is_number(w):
                complete = False
            else:
                total += w
        return total, complete

    top = [it for it in by_id.values() if it.get("parent") is None]
    children: dict[str, list[dict]] = {}
    for cid, it in by_id.items():
        if isinstance(it.get("parent"), str) and not it.get("_bad_parent"):
            children.setdefault(it["parent"], []).append(it)
    if top:
        total, complete = _weights(top)
        if complete and abs(total - total_scale) > 0.5:
            failures.append(
                f"evaluation_criteria top-level weights sum to {total:g}, not {total_scale:g} "
                "— 배점표를 그대로 옮겼는지 확인한다(가격 별책이면 evaluation_total로 만점을 적는다)")
    for pid, subs in children.items():
        parent_w = by_id[pid].get("weight")
        total, complete = _weights(subs)
        if complete and _is_number(parent_w) and abs(total - parent_w) > 0.5:
            failures.append(
                f"evaluation criterion {pid} is {parent_w:g} but its sub-criteria sum to {total:g} "
                "— 하위 배점의 합이 상위 배점과 다르다")
    for it in by_id.values():
        it.pop("_bad_parent", None)
    # 배점 항목 ↔ 요구사항 연결. 대응 요구가 없는 배점은 통째로 비어 있는 목차다.
    # 하위 항목이 있는 상위는 하위로 대응하므로 말단 항목만 본다.
    referenced: set[str] = set()
    for req in data.get("requirements", []) if isinstance(data.get("requirements"), list) else []:
        if isinstance(req, dict):
            for cid in _as_str_list(req.get("criterion_ids")):
                referenced.add(cid)
    unknown = sorted(referenced - set(by_id))
    if unknown:
        failures.append(f"requirements reference unknown evaluation criteria: {unknown}")
    leaves = {cid for cid in by_id if cid not in children}
    orphan = sorted(leaves - referenced)
    if by_id and orphan:
        failures.append(f"evaluation criteria with no requirement mapped: {orphan} "
                        "— 배점 항목에 대응하는 요구가 없다(목차 누락 가능성)")
    return failures


def _as_str_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [v for v in value if isinstance(v, str) and v.strip()]
    return []


UNSUPPORTED_CODES = {"X", "미지원", "NO", "N", "불가", "미수용", "부적합"}


def is_unsupported(value: object) -> bool:
    """수용여부 표기가 '미지원'을 뜻하는지 판정한다.

    조견표는 기호와 한글 라벨을 함께 쓰므로('X', 'X 미수용', '미수용', '✗') 표기 변형을
    하나로 본다 — 별칭 하나로 승인 모순 검사를 빠져나가지 못하게 한다.
    'N/A'(해당없음)는 미지원이 아니다.
    """
    if not isinstance(value, str):
        return False
    text = value.strip().upper().replace("✗", "X").replace("Ｘ", "X")
    if not text or text in {"N/A", "NA", "해당없음", "해당 없음"}:
        return False
    tokens = {t.strip(" ()[]·-") for t in re.split(r"[\s/,]+", text)}
    return bool({t for t in tokens if t} & {c.upper() for c in UNSUPPORTED_CODES})


def readiness(data: dict, failures: list[str]) -> tuple[str, int]:
    """(표시 라벨, 종료 코드) — 목적·단계·차단 여부의 단일 판정 지점.

    CLI·explain·점수 보고서가 모두 이 함수를 쓴다. 라벨이 갈라져 draft audit이
    "제출 가능"으로 설명되던 불일치를 구조적으로 막는다.
    """
    decision = str(data.get("bid_decision", ""))
    mode = str(data.get("mode", "")) or "draft"
    if any(str(f).startswith("DECISION_MEMO_ONLY") for f in failures):
        return "DECISION_MEMO_ONLY", 1
    if decision in DECISION_STOP and failures:
        return "DECISION_MEMO_ONLY", 1
    if failures:
        return "BLOCKED", 1
    if decision == "conditional-bid":
        return "CONDITIONAL-GO", 0
    return ("SUBMISSION-READY" if mode == "submission" else f"{mode.upper()}-READY"), 0


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
        # fail-closed: 강도 미기재는 필수로 취급한다(생략으로 우회 방지).
        strength = requirement_strength(item)
        if strength not in MANDATORY_STRENGTHS:
            # 권장은 안 해도 되지만, 제출 기록에는 안 한 이유가 남아야 한다 — 권장 조건이
            # 조용히 사라지면 "권장 분량 초과"와 "잊어버림"을 구분할 수 없다.
            if strength == "recommended" and mode == "submission" \
                    and item.get("state") != "approved" and _is_placeholder(item.get("rationale")):
                failures.append(f"recommended requirement {item.get('id', '?')} is not met "
                                "and lacks a rationale — 권장 사항을 따르지 않은 사유를 적는다")
            continue
        mandatory_count += 1
        if item.get("state") == "approved":
            # 반낙관: approved 자기선언만으로는 통과 불가. 비어있지 않은 문자열 근거 필수.
            if not _evidence_ok(item.get("evidence_refs")):
                failures.append(f"requirement {item.get('id', '?')} approved without evidence_refs")
            # 검토 상태(approved)와 준수 상태(support/fit)는 다른 축이다. "미지원임을
            # 검토자가 확인했다"가 "필수 요구를 충족했다"로 승격되면 안 된다.
            fit = str(item.get("fit", "")).strip().upper()
            if (is_unsupported(item.get("support")) or fit == "GAP") \
                    and not _exception_granted(item.get("exception")):
                failures.append(
                    f"requirement {item.get('id', '?')} is approved but not met "
                    f"(support={item.get('support', '')!r}, fit={item.get('fit', '')!r}); "
                    "needs a buyer-granted exception with evidence")
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
        if not _enum_ok(claim.get("status"), {"supported", "qualified", "removed"}):
            failures.append(f"claim {claim.get('id', '?')} is unsupported")
        if kind == "commitment" and not _true(claim.get("owner_approved")):
            failures.append(f"commitment {claim.get('id', '?')} lacks owner approval")
        # 제출 모드에서는 'supported/qualified' 선언에 실제 근거가 따라와야 한다.
        # 상태 문자열만으로 통과하면 근거 없는 성능·실적 주장이 그대로 나간다.
        if mode == "submission" and _enum_ok(claim.get("status"), {"supported", "qualified"}) \
                and not _evidence_ok(claim.get("evidence_refs")):
            failures.append(
                f"claim {claim.get('id', '?')} is {claim.get('status')} without evidence_refs")

    failures.extend(f"unresolved token: {token}" for token in data["unresolved_tokens"])
    failures.extend(f"source conflict: {item}" for item in data["source_conflicts"])

    for item in data["inputs"]:
        if item.get("class") == "blocking" and item.get("status") != "closed":
            failures.append(f"blocking input {item.get('id', '?')} is open")

    for defect in data["defects"]:
        if _enum_ok(defect.get("severity"), {"critical", "major"}) and defect.get("status") != "closed":
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

    # 분류가 요구사항을 바꾼다 — 기관 속성·구매 단계·읽는 조건에 따라 필요한 근거가 다르다.
    context = data.get("context") if isinstance(data.get("context"), dict) else {}
    buyers = {b for b in _as_str_list(context.get("buyer_types"))}
    stage_ctx = context.get("stage")
    limits = set(_as_str_list(context.get("constraints")))
    rfx = context.get("rfx_type", "rfp")
    if mode == "submission":
        # 제출 기록에 분류가 없으면 분류가 바꾸는 요구사항이 전부 꺼진다. 누락은 정상값이
        # 아니라 미기재다(초안·검토 단계는 후방호환으로 허용).
        for field in ("buyer_types", "stage"):
            if context.get(field) is None:
                failures.append(f"submission requires context.{field} "
                                "— 분류가 없으면 공공 평가표·규격 대조 같은 검사가 조용히 꺼진다")
    failures.extend(check_evaluation_criteria(data))
    if rfx == "rfi":
        # RFI 응답은 계약 제안이 아니다. 추정치가 확약 문장으로 승격되면 안 된다.
        for claim in data["claims"]:
            if claim.get("kind") == "commitment":
                failures.append(f"claim {claim.get('id', '?')} is a commitment in an RFI response "
                                "— RFI에는 확약을 싣지 않는다(material + 추정 범위로 기술)")
    if "public" in buyers and rfx != "rfi" and (mode == "submission" or stage_ctx in SUBMISSION_STAGES):
        # 공공 입찰에서 배점표는 목차·분량·근거 배분의 기준이다. 없으면 무엇에 점수가
        # 걸려 있는지 모르는 채로 쓴 것이다.
        if not data.get("evaluation_criteria"):
            failures.append(
                "public procurement requires an evaluation_criteria ledger "
                "— 평가표(배점)를 옮겨 적고 각 요구를 criterion_ids로 연결한다")
    # 읽는 조건과 실제 장표 규격이 어긋나면 잡는다(발표라면서 인쇄용 밀도로 만든 덱).
    expected_profile = READING_MODE_PROFILE.get(str(context.get("reading_mode", "")))
    actual_profile = data["render"].get("output_profile")
    if actual_profile is not None and not _enum_ok(actual_profile, KNOWN_DECK_PROFILES):
        failures.append(f"render.output_profile has unsupported value: {actual_profile!r} "
                        f"(allowed: {', '.join(sorted(KNOWN_DECK_PROFILES))})")
    elif expected_profile and actual_profile is None and mode == "submission":
        # 값이 틀리면 잡고 지우면 통과하던 구멍. 누락 = 미검사 = 차단(layout_checked와 동일).
        # 초안은 아직 산출물이 없을 수 있으므로 제출 기록에만 요구한다.
        failures.append(
            f"reading_mode={context.get('reading_mode')} expects deck profile "
            f"'{expected_profile}' but render.output_profile is missing "
            "— deck_check.py --emit-render 결과의 output_profile을 옮긴다")
    elif expected_profile and actual_profile is not None and actual_profile != expected_profile:
        failures.append(
            f"reading_mode={context.get('reading_mode')} expects deck profile "
            f"'{expected_profile}' but the artifact was built as '{actual_profile}' "
            "— 발표본과 상세본 규격이 뒤바뀌었는지 확인한다")
    if "sensitive-data" in limits and mode == "submission":
        checks = data["package"].get("checks", {})
        for name in ("metadata", "hidden-content", "stale-customer-data"):
            if isinstance(checks, dict) and checks.get(name) != "pass":
                failures.append(
                    f"context.constraints includes sensitive-data: package check {name} "
                    f"must be 'pass' (got {checks.get(name)!r})")

    # 수치 원장이 있으면 산술을 게이트가 직접 계산한다. 제출 모드에서는 원장 없이
    # checks.arithmetic=true 자기선언만으로 통과하지 못한다 — 무엇을 검산했는지
    # 보이지 않는 '검산 완료'는 검증이 아니다.
    numbers = data.get("numbers")
    if numbers is not None:
        failures.extend(check_numbers(numbers))
        if mode == "submission" and isinstance(numbers, list) and not numbers:
            # 빈 원장으로 검산 의무가 사라지지 않는다. 검증할 수치가 없는 문서라면
            # 그 사실을 근거와 함께 기록한다.
            if not _evidence_ok(data.get("numbers_not_applicable")):
                failures.append(
                    "numbers ledger is empty — 금액·기간·수량이 없는 문서라면 "
                    "numbers_not_applicable에 사유를 기록한다")
    elif mode == "submission":
        failures.append(
            "checks.arithmetic is self-declared without a numbers ledger — "
            "금액·기간·수량을 numbers[]에 적으면 게이트가 합계·비율을 다시 계산한다")

    # 시뮬레이션 산출물은 내부 확인용이다 — 외부 제출 준비 상태로 승격하지 않는다.
    if mode == "submission" and data.get("artifact_mode") == "simulation-only":
        failures.append("artifact_mode 'simulation-only' cannot clear submission "
                        "(use 'submission-candidate' with a real artifact)")
    # 제출 모드에서는 artifact_required 입력값이 검증 의무를 취소하지 못한다.
    # (외부 입력 하나로 렌더·해시 검사를 통째로 건너뛰던 우회 경로 차단)
    artifact_required = data["artifact_required"] or mode == "submission"
    if artifact_required and not _true(data["render"].get("verified")):
        failures.append("render verification is missing or failed")
    if artifact_required and _true(data["render"].get("verified")):
        for field in ("artifact_hash", "tool"):
            if _is_placeholder(data["render"].get(field)):
                failures.append(f"render verification lacks {field}")
        if not _evidence_ok(data["render"].get("evidence")):
            failures.append("render verification lacks evidence")
    # 제출 모드는 자동 레이아웃 검사와 사람의 육안 승인을 둘 다 요구한다.
    # 렌더 성공(PDF 변환)은 디자인 승인이 아니다 — 미검사를 통과로 추정하지 않는다.
    if mode == "submission":
        render_block = data["render"]
        if not _true(render_block.get("layout_checked")):
            # 필드를 지우면 요구가 사라지던 구멍을 막는다(누락 = 미검사 = 차단).
            failures.append("layout check is missing — deck_check.py로 레이아웃을 검사하고 "
                            "render.layout_checked=true를 기록한다")
        if "render_succeeded" in render_block and _true(render_block.get("verified")) \
                and not _true(render_block.get("render_succeeded")):
            failures.append("render.verified=true contradicts render_succeeded=false "
                            "— 렌더가 실패했는데 검증 완료로 기록됐다")
        if not _true(render_block.get("visual_review_approved")):
            failures.append(
                "visual review is not approved — 렌더 썸네일을 사람이 확인한 뒤 "
                "render.visual_review_approved=true와 visual_reviewer를 기록한다")
        elif _is_placeholder(render_block.get("visual_reviewer")):
            failures.append("visual review lacks a named reviewer (render.visual_reviewer)")
    # 제출 모드의 해시는 실제 파일에 대조 가능해야 한다. 형식이 아니거나 render와
    # package가 서로 다른 파일을 가리키면, 검토 기록이 어느 산출물의 것인지 알 수 없다.
    if mode == "submission":
        render_hash = data["render"].get("artifact_hash")
        package_hash = data["package"].get("artifact_hash")
        for field, value in (("render", render_hash), ("package", package_hash)):
            if not is_digest(value):
                failures.append(
                    f"{field}.artifact_hash must be a sha256 digest for submission (got {value!r})")
        if is_digest(render_hash) and is_digest(package_hash) \
                and normalize_digest(render_hash) != normalize_digest(package_hash):
            failures.append("render and package artifact_hash differ — "
                            "두 검사가 서로 다른 파일을 대상으로 했다")
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
            if not _enum_ok(status, {"pass", "fail", "not-inspected", "not-applicable"}):
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


def explain_markdown(data: dict, schema_failures: list[str], failures: list[str],
                     label: str | None = None, document_verified: bool = False) -> str:
    """게이트 결과를 사람이 바로 고칠 수 있는 마크다운으로 설명한다.

    label을 주면 그 판정을 그대로 쓴다. 호출자(unified_gate)는 audit만으로는 알 수 없는
    사실 — 실제 문서를 검사했는지 — 을 알기 때문이다. 설명이 audit으로 상태를 다시
    계산하면 제목은 AUDIT-VALID인데 본문은 "제출 가능"이라고 말하는 모순이 생겼다.
    """
    if schema_failures:
        lines = ["## 게이트 결과: INVALID AUDIT (스키마 오류)", "",
                 "| # | 스키마 오류 | 조치 |", "|---|---|---|"]
        for i, f in enumerate(schema_failures, 1):
            lines.append(f"| {i} | {f} | audit-schema.md의 필드 타입·필수값을 확인한다 |")
        return "\n".join(lines)
    decision = data.get("bid_decision")
    if not failures:
        # 라벨과 설명은 같은 판정에서 나온다. 호출자가 준 label이 우선한다.
        label = label or readiness(data, failures)[0]
        mode = str(data.get("mode", "")) or "draft"
        if label == "SUBMISSION-READY" and document_verified:
            body = ("제출 가능. 모든 결정론적 게이트를 통과했고 실제 파일과 해시가 일치한다. "
                    "최종 수치·화면·패키지는 사람이 한 번 더 확인한다.")
        elif label == "SUBMISSION-READY":
            # 이 호출자는 파일을 보지 않았다 — audit만으로 제출 승인을 말하지 않는다.
            body = ("audit의 결정론적 게이트는 통과했다. **실제 파일을 검사하지 않았으므로 "
                    "제출 승인이 아니다** — `unified_gate.py --doc <최종파일>`로 해시 대조를 받는다.")
        elif label == "AUDIT-VALID":
            body = ("audit 자체는 유효하다 — **제출 판정이 아니다.** 실제 문서를 검사하지 "
                    "않았으므로 제출 준비 상태로 볼 수 없다. `--doc <최종파일>`로 다시 실행한다.")
        elif label == "CONDITIONAL-GO":
            body = ("내부 계속 진행만 가능하다 — 외부 제출 클리어가 아니다. "
                    "조건 해소 후 mode=submission audit으로 다시 판정한다.")
        else:
            body = (f"{mode} 단계 게이트를 통과했다 — 내부 진행용이다. 제출 판정은 "
                    "mode=submission audit + 실제 파일 대조로 별도로 받는다.")
        return f"## 게이트 결과: {label}\n\n{body}"
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
