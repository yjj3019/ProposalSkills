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
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from quality_gate import extract_labeled_blocks, normalize_text  # noqa: E402

WARN = "[경고]"
BLOCK = "[차단]"
# 만·억·조 단위. 조 단위 이상은 실무에서 드물지만 표기 변형 생성에는 포함한다.
KOREAN_UNITS = [("조", 10 ** 12), ("억", 10 ** 8), ("만", 10 ** 4)]


def _trim(value: float) -> str:
    """1200000000.0 → '1200000000', 3.70 → '3.7'."""
    text = f"{value:.6f}".rstrip("0").rstrip(".")
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
            elif n >= unit:
                scaled = n / unit
                if abs(scaled - round(scaled, 1)) < 1e-9:
                    out.append(f"{_trim(round(scaled, 1))}{label}")
    else:
        out += [_trim(value), f"{value:,.2f}".rstrip("0").rstrip(".")]
    return sorted(set(out), key=len, reverse=True)


def document_text(path: Path) -> str:
    return normalize_text(" ".join(text for _, text in extract_labeled_blocks(path)))


def _found(haystack: str, needle: str) -> bool:
    """숫자 경계를 지켜 찾는다 — '37'이 '370'에 걸리지 않게 한다."""
    pattern = r"(?<![0-9.,])" + re.escape(needle) + r"(?![0-9,]*\d)"
    return re.search(pattern, haystack) is not None


def compare(entries: list[dict], text: str) -> tuple[list[str], list[dict]]:
    """(검사 항목, 항목별 결과). 원장 순서를 유지한다."""
    items: list[str] = []
    results: list[dict] = []
    for entry in entries:
        nid = entry.get("id", "?")
        label = entry.get("label", "")
        value = entry.get("value")
        if entry.get("must_appear") is False:
            results.append({"id": nid, "checked": False, "reason": "must_appear=false"})
            items.append(f"[정보] {nid} {label}: 문서 대조 제외(중간 계산값)")
            continue
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            items.append(f"{BLOCK} {nid} {label}: value가 숫자가 아니다 — 대조할 수 없다")
            results.append({"id": nid, "checked": False, "matched": False})
            continue
        found = [v for v in variants(value) if _found(text, v)]
        results.append({"id": nid, "checked": True, "matched": bool(found),
                        "matched_as": found[:3]})
        if found:
            items.append(f"[정보] {nid} {label}: 문서에서 확인({', '.join(found[:2])})")
        else:
            items.append(f"{BLOCK} {nid} {label}: 값 {value}{entry.get('unit', '')}을 문서에서 찾지 못했다 "
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
        text = document_text(a.doc)
    except Exception as exc:  # 손상·미지원 파일
        print(f"검사 불가(파일 형식·손상): {exc}", file=sys.stderr)
        return 2

    items, results = compare(entries, text)
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
