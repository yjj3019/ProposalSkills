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


LIST_FIELDS = ("requirements", "slides", "win_themes", "claims", "bid_conditions", "numbers",
               "evaluation_criteria",
               "unresolved_tokens", "attachments", "inputs", "defects", "eligibility",
               "regulatory_checks", "vendor_confirmations", "source_conflicts")


def _as_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _validate_meta_types(meta: dict) -> None:
    """리스트여야 할 필드가 문자열 등으로 오면 조용히 버리지 않고 오류를 낸다.
    ("requirements": "R1 R2 all approved" → requirements=[] → READY 허위 통과 차단)"""
    bad = [k for k in LIST_FIELDS if k in meta and meta[k] is not None and not isinstance(meta[k], list)]
    if bad:
        raise ValueError(f"meta fields must be arrays: {', '.join(bad)}")
    for k in ("submission", "render", "package", "checks", "flags"):
        if k in meta and meta[k] is not None and not isinstance(meta[k], dict):
            raise ValueError(f"meta field must be an object: {k}")
    # 원장 항목은 객체여야 한다. 문자열 요구 하나가 섞이면 조용히 버려져
    # 필수 요구 3건이 2건이 된 채 통과하던 유실 경로를 위치와 함께 막는다.
    for name in ("requirements", "claims", "win_themes", "eligibility", "attachments",
                 "inputs", "defects", "bid_conditions", "slides", "numbers",
                 "evaluation_criteria"):
        for i, item in enumerate(_as_list(meta.get(name))):
            if not isinstance(item, dict):
                raise ValueError(f"{name}[{i}] must be an object (got {item!r}) — "
                                 "항목을 조용히 버리지 않는다")


def _str_list(container: dict, key: str, where: str) -> list:
    """리스트만 받는다. 문자열을 list()로 감싸면 글자 단위로 쪼개져
    'TBD' → ['T','B','D']가 되고, 각 글자가 플레이스홀더 검사를 빠져나갔다."""
    value = container.get(key)
    if value is None:
        return []
    if isinstance(value, str):
        raise ValueError(f"{where}.{key} must be an array of strings "
                         f"(got a string: {value!r} — 배열로 감싼다)")
    if not isinstance(value, list):
        raise ValueError(f"{where}.{key} must be an array (got {type(value).__name__})")
    return list(value)


def _bool(container: dict, key: str, default: bool, where: str) -> bool:
    """JSON true/false만 허용. 'yes'/'no'/'pending' 등 문자열은 오류(bool('no')==True 방지)."""
    value = container.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f"{where}.{key} must be true/false (got {value!r})")
    return value


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
            "mandatory": _bool(req, "mandatory", True, f"requirement {req.get('id', '?')}"),
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
        else:
            # 슬라이드 번호만으로 근거를 만들어 주지 않는다 — 'approved 무증빙' 반낙관
            # 검사를 빌더가 우회시키던 결함. 근거는 작성자가 명시해야 한다.
            item["evidence_refs"] = []
            if req.get("slide") is not None and req.get("state") == "approved":
                warnings.append(
                    f"requirement {item['id']}: slide={req['slide']} is a location, not evidence — "
                    "set evidence_refs explicitly")
        if item["state"] == "approved" and not any(
                isinstance(r, str) and r.strip() for r in item["evidence_refs"]):
            msg = f"requirement {item['id']} approved without evidence_refs"
            if strict:
                raise ValueError(msg)
            warnings.append(msg)
        # 응답 위치는 근거와 별도 필드로 보존한다(둘을 섞으면 위치가 증거로 승격된다).
        if "response_refs" in req:
            item["response_refs"] = _str_list(req, "response_refs", f"requirement {item['id']}")
        # 발주처가 허용한 예외. 게이트가 이 필드로 '미지원인데 approved'를 판정하므로
        # 변환에서 사라지면 정당한 예외가 허위 차단된다.
        if "exception" in req:
            exc = req["exception"]
            if not isinstance(exc, dict):
                raise ValueError(f"requirement {item['id']}.exception must be an object "
                                 f"(got {type(exc).__name__})")
            item["exception"] = {
                "granted_by": exc.get("granted_by") or "",
                "evidence": _str_list(exc, "evidence", f"requirement {item['id']}.exception"),
            }
            for key in ("note", "granted_at", "scope"):
                if key in exc:
                    item["exception"][key] = exc[key]
        # Optional S2 matrix fields passthrough
        if "criterion_ids" in req:
            item["criterion_ids"] = _str_list(req, "criterion_ids", f"requirement {item['id']}")
        # 요구 강도와 조건. 변환에서 빠지면 권장이 필수로 승격되거나 조건이 사라진다.
        for key in ("strength", "condition"):
            if key in req:
                if not isinstance(req[key], str):
                    raise ValueError(f"requirement {item['id']}.{key} must be a string")
                item[key] = req[key]
        for key in ("fit", "eval_weight", "win_theme_id", "risk", "support", "text", "basis"):
            if key in req and key not in item:
                item[key] = req[key]
        out.append(item)
    return out


def _normalize_checks(meta: dict) -> dict:
    checks_in = meta.get("checks") if isinstance(meta.get("checks"), dict) else {}
    out = {}
    for name in ("consistency", "arithmetic", "submission"):
        out[name] = _bool(checks_in, name, False, "checks")
    for name, value in checks_in.items():
        out.setdefault(name, value)
    return out


def build_audit(meta: dict, strict: bool = False) -> dict:
    if not isinstance(meta, dict):
        raise ValueError("meta root must be an object")
    _validate_meta_types(meta)
    warnings: list[str] = []
    mode = meta.get("mode") or "draft"
    bid = meta.get("bid_decision") or "intake-incomplete"
    submission_in = meta.get("submission") if isinstance(meta.get("submission"), dict) else {}
    deadline = submission_in.get("deadline") or meta.get("deadline")
    submission = {
        "cleared": _bool(submission_in, "cleared", False, "submission"),
        "rehearsal_evidence": _str_list(submission_in, "rehearsal_evidence", "submission"),
        "receipt_plan": submission_in.get("receipt_plan") or "",
        "receipt_evidence": _str_list(submission_in, "receipt_evidence", "submission"),
    }
    if deadline:
        submission["deadline"] = deadline

    render_in = meta.get("render") if isinstance(meta.get("render"), dict) else {}
    render = {
        "verified": _bool(render_in, "verified", False, "render"),
        "artifact_hash": render_in.get("artifact_hash") or "",
        "tool": render_in.get("tool") or "",
        "evidence": _str_list(render_in, "evidence", "render"),
    }
    # 검사·승인 기록은 입력에 있는 것만 그대로 옮긴다. 여기서 빠지면 승인까지 마친
    # 정상 경로가 "육안 승인 없음"으로 차단된다(승인 사실을 만들어내지는 않는다).
    for flag in ("render_succeeded", "layout_checked", "visual_review_approved"):
        if flag in render_in:
            render[flag] = _bool(render_in, flag, False, "render")
    for text_field in ("visual_reviewer", "output_profile"):
        value = render_in.get(text_field)
        if value is not None:
            if not isinstance(value, str):
                raise ValueError(f"render.{text_field} must be a string (got {type(value).__name__})")
            render[text_field] = value

    package_in = meta.get("package") if isinstance(meta.get("package"), dict) else {}
    checks = dict(REQUIRED_PACKAGE_CHECKS)
    if isinstance(package_in.get("checks"), dict):
        checks.update(package_in["checks"])
    package = {
        "required": _bool(package_in, "required", mode == "submission", "package"),
        "inspected": _bool(package_in, "inspected", False, "package"),
        "artifact_hash": package_in.get("artifact_hash") or "",
        "tool": package_in.get("tool") or "",
        "checks": checks,
        "reviewer": package_in.get("reviewer") or "",
    }

    conflicts = _str_list(meta, "source_conflicts", "meta")
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
        "checks": _normalize_checks(meta),
        # 제출 후보(submission)만 렌더·패키지 검증을 기본 요구한다. draft/review/analysis는
        # 명시하지 않으면 false — 리드문 맵 단계(Pink)에서 DRAFT-READY 체크포인트에 도달할 수 있게 한다.
        "artifact_required": _bool(meta, "artifact_required", mode == "submission", "meta"),
        "render": render,
        "package": package,
        "submission": submission,
        "eligibility": _as_list(meta.get("eligibility")),
        "flags": meta.get("flags") if isinstance(meta.get("flags"), dict) else {},
        "regulatory_checks": _as_list(meta.get("regulatory_checks")),
        "vendor_confirmations": _as_list(meta.get("vendor_confirmations")),
        "win_themes": win_themes,
    }
    # 수치 원장은 게이트가 합계·비율을 다시 계산하는 입력이다 — 변환에서 잃으면
    # 제출 모드가 "원장 없이 arithmetic 자기선언"으로 차단된다.
    if meta.get("numbers") is not None:
        audit["numbers"] = _as_list(meta.get("numbers"))
    # 분류와 평가표는 게이트 요구사항을 바꾸는 입력이다 — 변환에서 잃으면 공공 제안이
    # 평가표 없이 통과하거나, 읽는 조건과 장표 규격의 불일치를 놓친다.
    if meta.get("context") is not None:
        if not isinstance(meta["context"], dict):
            raise ValueError("meta field must be an object: context")
        audit["context"] = meta["context"]
    if meta.get("evaluation_criteria") is not None:
        audit["evaluation_criteria"] = _as_list(meta.get("evaluation_criteria"))
    for field in ("proposal_archetype", "archetype_rationale"):
        if meta.get(field) is not None:
            if not isinstance(meta[field], str):
                raise ValueError(f"meta field must be a string: {field}")
            audit[field] = meta[field]
    if meta.get("sections") is not None:
        # slides[]에서 유추하지 않는다 — 그것은 요구 대응 매핑이지 목차가 아니다.
        # 부분 매핑을 목차로 읽으면 있는 절을 없다고 잡는다.
        audit["sections"] = _as_list(meta.get("sections"))
    if meta.get("evaluation_total") is not None:
        # 가격 별책 등으로 원장의 만점이 100이 아닐 때. 잃어버리면 게이트가 100을 요구한다.
        audit["evaluation_total"] = meta["evaluation_total"]
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
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    try:
        meta = json.loads(args.meta.read_text(encoding="utf-8-sig"))
        audit = build_audit(meta, strict=args.strict)
    except (OSError, ValueError) as exc:  # JSONDecodeError·UnicodeDecodeError 포함
        print(f"error: {exc}", file=sys.stderr)
        return 2
    text = json.dumps(audit, ensure_ascii=False, indent=2)
    if args.output:
        try:
            args.output.write_text(text + "\n", encoding="utf-8")
        except OSError as exc:
            print(f"error: cannot write {args.output}: {exc}", file=sys.stderr)
            return 2
        print(f"wrote {args.output}")
    else:
        print(text)
    if audit.get("_builder_warnings"):
        for w in audit["_builder_warnings"]:
            print(f"warning: {w}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
