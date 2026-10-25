#!/usr/bin/env python3
"""Compare the numerical ledger with the actual document: verify amounts, durations, and quantities appear unchanged.

Usage:
    python3 check_numbers.py 제안서.pptx --audit audit.json [--emit numbers.json]
    python3 check_numbers.py 제안서.pptx --numbers numbers.json

Read the audit numbers[] ledger and check every entry against the document body. proposal_gate recalculates ledger sums and ratios; this script connects those values to actual slides. Generate notation variants for Korean proposals (3,700,000,000 / 37억 / 37억원 / 3.7억); block values not found in any notation. Skip internal intermediate values marked must_appear: false.

Exit codes: 0=matched (warnings possible), 1=mismatch blocked, 2=usage error or damaged file.
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
# Korean monetary multipliers: identical digits with different scales are different values.
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
    """Generate alternate notations for the same number in Korean proposals."""
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


# Evaluators read body content. Notes, layouts, masters, and document properties are not printed,
# so they cannot prove body presence; ledger values only in notes leave the submitted body empty.
BODY_LABELS = ("슬라이드", "문단", "본문", "시트")


def _is_body(label: str) -> bool:
    return any(label.startswith(prefix) for prefix in BODY_LABELS)


def document_text(path: Path, body_only: bool = True) -> str:
    blocks = extract_labeled_blocks(path)
    if body_only:
        blocks = [b for b in blocks if _is_body(b[0])]
    return normalize_text(" ".join(text for _, text in blocks))


# Korean/symbol units after numbers: identical digits with different units differ (37원 ≠ 37개월).
# Compare attached units and clearly separated time units. As before, do not interpret spaced
# general nouns such as "400 VM"; header-only units require separate semantic comparison.
UNIT_TOKEN_RE = re.compile(r"^(%|퍼센트|원|달러|KRW|USD|억|만|천|조|영업일|분기|개월|년|월|일|주|시간|분|초|명|개|건|식|대|회|배|점|배럴|GB|TB|MB|Gbps|Mbps|VM|core|vCPU)",
                           re.IGNORECASE)
# Ledger units → allowed document forms; do not inspect adjacent units for unlisted units.
UNIT_ALIASES: dict[str, set[str]] = {
    "KRW": {"원", "KRW"}, "원": {"원", "KRW"},
    "USD": {"달러", "USD"}, "달러": {"달러", "USD"},
    "%": {"%", "퍼센트"}, "퍼센트": {"%", "퍼센트"},
    "개월": {"개월", "월"}, "월": {"개월", "월"}, "년": {"년"},
    "일": {"일"}, "영업일": {"영업일"}, "주": {"주"}, "시간": {"시간"},
    "분": {"분"}, "초": {"초"},
    "명": {"명"}, "개": {"개"}, "건": {"건"}, "대": {"대"}, "회": {"회"}, "점": {"점"},
}


# Detect spaced time units only; do not infer units from words such as "분석" or "400 VM".
SPACED_TIME_RE = re.compile(r"^\s+(영업일|개월|시간|초|분|일|주|월|년)(?![가-힣A-Za-z])")


def _unit_conflict(after: str, unit: str) -> bool:
    """True when the unit immediately following a match clearly differs from the ledger unit."""
    allowed = UNIT_ALIASES.get(str(unit).strip())
    if not allowed:
        return False  # Do not judge unknown units or create false blockers.
    currency = str(unit).strip() in {"KRW", "원", "USD", "달러"}
    m = UNIT_TOKEN_RE.match(after.lstrip() if currency else after)
    if not m and str(unit).strip() in {"초", "분", "시간", "일", "영업일", "주", "개월", "월", "년"}:
        m = SPACED_TIME_RE.match(after)
    if not m:
        return False  # Without an attached unit (for example in a table cell), evidence is insufficient.
    actual = m.group(1).upper() if currency else m.group(1)
    return actual not in allowed


def _find_spans(haystack: str, needle: str) -> list[re.Match]:
    """Respect numeric boundaries so '37' does not match '370', '37.5', or '-37'."""
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
        # A multiplier outside the match changes the value: 37원 != 37억원.
        if SCALE_RE.match(tail) or _unit_conflict(tail, unit):
            continue
        if not needle[-1].isdigit() and unit not in {"", "KRW", "원"}:
            continue  # Do not use monetary notation variants as evidence for durations or quantities.
        return True
    return False


def _label_text(text: str, label: str) -> list[str]:
    """Compare only the first number after an item label to avoid mixing table rows."""
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
    """Return (check items, per-entry results), preserving ledger order."""
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
            found = []  # Block conflicting values for the same item in summary and detail.
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
    ap.add_argument("doc", type=Path, help="PPTX/DOCX/XLSX proposal")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--audit", type=Path, help="Audit JSON containing the numbers[] ledger")
    src.add_argument("--numbers", type=Path, help="JSON containing only the ledger array")
    ap.add_argument("--emit", type=Path, help="Write comparison results as JSON")
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
    except Exception as exc:  # Damaged or unsupported files.
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
