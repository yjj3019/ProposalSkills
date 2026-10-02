#!/usr/bin/env python3
"""수치 원장 ↔ 실제 문서 대조 — 원장의 금액·기간·수량이 문서에 그대로 있는지 확인한다.

사용법:
    python3 check_numbers.py 제안서.pptx --audit audit.json [--emit numbers.json]
    python3 check_numbers.py 제안서.pptx --numbers numbers.json

audit의 `numbers[]` 원장을 읽어 각 항목이 문서 본문에 나타나는지 검사한다.
게이트(proposal_gate)는 원장 안의 합계·비율을 계산하지만, 그 값이 실제 장표에
적힌 값과 같은지는 문서를 열어야만 알 수 있다. 이 스크립트가 그 사이를 잇는다.

한국어 제안서는 같은 수를 여러 표기로 쓴다(3,700,000,000 / 37억 / 37억원 / 3.7억).
표기 변형을 만들어 대조하고, 어느 표기로도 찾지 못하면 차단한다.

`must_appear: false`인 항목(내부 계산용 중간값)은 검사에서 제외한다.

종료 코드: 0=대조 통과(경고 가능), 1=불일치 차단, 2=사용 오류·파일 손상.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from decimal import Decimal
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from quality_gate import extract_labeled_blocks, normalize_text  # noqa: E402

WARN = "[경고]"
BLOCK = "[차단]"
# 한국어 금액 배율. 같은 숫자라도 배율이 다르면 다른 값이다.
KOREAN_UNITS = [("조", 10 ** 12), ("억", 10 ** 8), ("천만", 10 ** 7),
                ("백만", 10 ** 6), ("만", 10 ** 4), ("천", 10 ** 3)]
SCALE_RE = re.compile(r"^\s*(?:천억|백억|십억|천만|백만|십만|조|억|만|천)")
FIRST_NUMBER_RE = re.compile(r"(?<![0-9.,])[-−△]?\d[\d,]*(?:\.\d+)?")


def _trim(value: float) -> str:
    """1200000000.0 → '1200000000', 3.70 → '3.7'."""
    text = format(Decimal(str(value)), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def variants(value: float) -> list[str]:
    """한국어 제안서에서 같은 수가 쓰이는 표기들을 만든다."""
    out: list[str] = []
    if float(value).is_integer():
        n = int(value)
        out += [str(n), f"{n:,}"]
        for label, unit in KOREAN_UNITS:
            if n and n % unit == 0:
                out.append(f"{n // unit}{label}")
                out.append(f"{n // unit:,}{label}")
            elif abs(n) >= unit:
                out.append(f"{_trim(Decimal(n) / unit)}{label}")
    else:
        out += [_trim(value), format(Decimal(str(value)), ",f")]
    return sorted(set(out), key=len, reverse=True)


# 평가위원이 읽는 영역. 노트·레이아웃·마스터·문서속성은 인쇄물에 나타나지 않으므로
# "문서에 있다"의 근거가 될 수 없다(원장 수치가 노트에만 있으면 본문은 빈 채로 나간다).
BODY_LABELS = ("슬라이드", "문단", "본문", "시트")


def _is_body(label: str) -> bool:
    return any(label.startswith(prefix) for prefix in BODY_LABELS)


def document_text(path: Path, body_only: bool = True) -> str:
    blocks = extract_labeled_blocks(path)
    if body_only:
        blocks = [b for b in blocks if _is_body(b[0])]
    return normalize_text(" ".join(text for _, text in blocks))


# 수 뒤에 붙는 한국어·기호 단위. 같은 숫자라도 단위가 다르면 다른 값이다(37원 ≠ 37개월).
# 공백 없이 붙은 것만 단위로 본다. "400 VM"의 VM은 명사이고, 한국어 제안서의 단위
# 표기는 "37개월"·"37원"처럼 숫자에 붙는다 — 띄어쓴 낱말까지 단위로 보면 정상 표기를 차단한다.
UNIT_TOKEN_RE = re.compile(r"^(%|퍼센트|원|달러|KRW|USD|억|만|천|조|개월|년|월|일|주|시간|분|초|명|개|건|식|대|회|배|점|배럴|GB|TB|MB|Gbps|Mbps|VM|core|vCPU)",
                           re.IGNORECASE)
# 원장 단위 → 문서에서 허용되는 표기. 여기 없는 단위는 인접 단위를 검사하지 않는다.
UNIT_ALIASES: dict[str, set[str]] = {
    "KRW": {"원", "KRW"}, "원": {"원", "KRW"},
    "USD": {"달러", "USD"}, "달러": {"달러", "USD"},
    "%": {"%", "퍼센트"}, "퍼센트": {"%", "퍼센트"},
    "개월": {"개월", "월"}, "월": {"개월", "월"}, "년": {"년"},
    "일": {"일"}, "주": {"주"}, "시간": {"시간"},
    "명": {"명"}, "개": {"개"}, "건": {"건"}, "대": {"대"}, "회": {"회"}, "점": {"점"},
}


def _unit_conflict(after: str, unit: str) -> bool:
    """매치 바로 뒤 단위가 원장 단위와 명백히 다르면 True(같은 수·다른 뜻)."""
    allowed = UNIT_ALIASES.get(str(unit).strip())
    if not allowed:
        return False  # 모르는 단위는 판단하지 않는다 — 거짓 차단을 만들지 않는다
    m = UNIT_TOKEN_RE.match(after.lstrip() if str(unit).strip() in {"KRW", "원", "USD", "달러"} else after)
    if not m:
        return False  # 단위가 붙어 있지 않으면(표 셀 등) 판단 근거가 없다
    return m.group(1) not in allowed


def _find_spans(haystack: str, needle: str) -> list[re.Match]:
    """숫자 경계를 지켜 찾는다 — '37'이 '370'·'37.5'·'-37'에 걸리지 않게 한다."""
    literal = re.escape(needle)
    for scale, _ in KOREAN_UNITS:
        if needle.endswith(scale):
            literal = re.escape(needle[:-len(scale)]) + r"\s*" + re.escape(scale)
            break
    pattern = (r"(?<![0-9.,\-\u2212\u25b3])" + literal
               + r"(?![0-9.,]*\d)")
    return list(re.finditer(pattern, haystack))


def _found(haystack: str, needle: str, unit: str = "") -> bool:
    for m in _find_spans(haystack, needle):
        tail = haystack[m.end():m.end() + 16]
        # 배율이 매치에 포함되지 않았으면 다른 값이다: 37원 != 37억원.
        if SCALE_RE.match(tail) or _unit_conflict(tail, unit):
            continue
        if not needle[-1].isdigit() and unit not in {"", "KRW", "원"}:
            continue  # 통화 표기 변형을 기간·수량의 근거로 사용하지 않는다.
        return True
    return False


def _label_text(text: str, label: str) -> list[str]:
    """항목명 직후의 첫 수치만 대조해 같은 표의 다른 행과 섞지 않는다."""
    scopes = []
    for anchor in re.finditer(re.escape(label), text):
        tail = re.split(r"\n|[;；·]", text[anchor.end():], maxsplit=1)[0]
        tail = tail.lstrip(" \t:：=|")
        number = FIRST_NUMBER_RE.match(tail)
        if number:
            following = FIRST_NUMBER_RE.search(tail, number.end())
            scopes.append(tail[number.start():following.start() if following else len(tail)])
        else:
            scopes.append("")
    return scopes


def compare(entries: list[dict], text: str, other: str = "") -> tuple[list[str], list[dict]]:
    """(검사 항목, 항목별 결과). 원장 순서를 유지한다."""
    items: list[str] = []
    results: list[dict] = []
    for entry in entries:
        if not isinstance(entry, dict):
            items.append(f"{BLOCK} 원장 항목이 객체가 아니다")
            continue
        nid = entry.get("id", "?")
        label = entry.get("label", "")
        value = entry.get("value")
        if entry.get("must_appear") is False:
            results.append({"id": nid, "checked": False, "reason": "must_appear=false"})
            items.append(f"[정보] {nid} {label}: 문서 대조 제외(중간 계산값)")
            continue
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
            items.append(f"{BLOCK} {nid} {label}: value가 숫자가 아니다 — 대조할 수 없다")
            results.append({"id": nid, "checked": False, "matched": False})
            continue
        unit = entry.get("unit", "")
        if not isinstance(unit, str):
            items.append(f"{BLOCK} {nid}: unit이 문자열이 아니다")
            results.append({"id": nid, "checked": False, "matched": False})
            continue
        match_label = entry.get("match_label", False)
        if not isinstance(match_label, bool) or (match_label and (not isinstance(label, str) or not label.strip())):
            items.append(f"{BLOCK} {nid}: match_label은 불리언이며 항목명이 필요하다")
            results.append({"id": nid, "checked": False, "matched": False})
            continue
        scopes = _label_text(text, label) if match_label else [text]
        found = [v for v in variants(value) if any(_found(scope, v, unit) for scope in scopes)]
        if match_label and (not scopes or not all(any(_found(scope, v, unit) for v in variants(value))
                                                  for scope in scopes)):
            found = []  # 요약과 상세의 같은 항목이 서로 다른 값이면 차단한다.
        results.append({"id": nid, "checked": True, "matched": bool(found),
                        "matched_as": found[:3]})
        if found:
            items.append(f"[정보] {nid} {label}: 본문에서 확인({', '.join(found[:2])})")
            continue
        elsewhere = [v for v in variants(value) if other and _found(other, v, unit)]
        if elsewhere:
            items.append(f"{BLOCK} {nid} {label}: 값 {value}{unit}이 노트·레이아웃 등 "
                         "비본문 영역에만 있다 — 평가위원이 보는 본문에는 없다")
        else:
            items.append(f"{BLOCK} {nid} {label}: 값 {value}{unit}을 {'항목명 직후' if match_label else '본문'}에서 찾지 못했다 "
                         "— 원장과 장표 중 하나가 낡았다")
    return items, results


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("doc", type=Path, help="PPTX/DOCX/XLSX 제안서")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--audit", type=Path, help="numbers[] 원장을 담은 audit JSON")
    src.add_argument("--numbers", type=Path, help="원장 배열만 담은 JSON")
    ap.add_argument("--emit", type=Path, help="대조 결과를 JSON으로 기록")
    a = ap.parse_args(argv)

    if not a.doc.is_file():
        print(f"파일 없음: {a.doc}", file=sys.stderr)
        return 2
    source = a.audit or a.numbers
    try:
        raw = json.loads(source.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        print(f"원장을 읽을 수 없다: {exc}", file=sys.stderr)
        return 2
    entries = raw.get("numbers") if isinstance(raw, dict) else raw
    if not isinstance(entries, list):
        print("numbers 원장이 배열이 아니다", file=sys.stderr)
        return 2
    if not entries:
        print(f"{WARN} 원장이 비어 있다 — 대조할 수치가 없다")
        return 0
    try:
        blocks = extract_labeled_blocks(a.doc)
    except Exception as exc:  # 손상·미지원 파일
        print(f"검사 불가(파일 형식·손상): {exc}", file=sys.stderr)
        return 2
    text = "\n".join(normalize_text(t) for label, t in blocks if _is_body(label))
    other = normalize_text(" ".join(t for label, t in blocks if not _is_body(label)))

    items, results = compare(entries, text, other)
    for line in items:
        print(line)
    blockers = [i for i in items if i.startswith(BLOCK)]
    if a.emit:
        a.emit.write_text(json.dumps({
            "document": a.doc.name,
            "checked": sum(1 for r in results if r.get("checked")),
            "matched": sum(1 for r in results if r.get("matched")),
            "mismatched": [r["id"] for r in results if r.get("checked") and not r.get("matched")],
            "results": results,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[정보] 대조 결과 → {a.emit}")
    if blockers:
        print(f"차단 — {len(blockers)}건 (원장과 문서의 수치가 다르다)")
        return 1
    print("통과 (원장 수치가 모두 문서에 있다 — 값의 타당성은 사람이 검토)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
