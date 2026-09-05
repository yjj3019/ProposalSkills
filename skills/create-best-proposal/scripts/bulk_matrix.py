#!/usr/bin/env python3
"""Build full requirement / response matrices for type-C proposals (SI-C1).

Usage:
  python bulk_matrix.py requirements.json -o matrix.md --summary-rows 8
  python bulk_matrix.py requirements.csv -o matrix.csv --format csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


SUPPORT_CODES = {"O", "부분", "조건부", "X", "N/A", "확인필요", ""}
# 입력 표기 정규화(대소문자·동의어). 목록 밖 코드는 오류로 거절한다 — 'o'/'Y' 같은
# 미정규화 값이 '미기입'으로 분류돼 위험 행에서 빠지던 fail-open 방지.
SUPPORT_ALIASES = {
    "O": "O", "0": "O", "○": "O", "Y": "O", "YES": "O", "지원": "O", "수용": "O", "FULL": "O",
    "부분": "부분", "PARTIAL": "부분", "P": "부분", "△": "부분", "부분지원": "부분", "부분수용": "부분",
    "조건부": "조건부", "CONDITIONAL": "조건부", "C": "조건부",
    "X": "X", "×": "X", "N": "X", "NO": "X", "미지원": "X", "불가": "X",
    "N/A": "N/A", "NA": "N/A", "해당없음": "N/A", "-": "N/A",
    "확인필요": "확인필요", "TBD": "확인필요", "?": "확인필요", "검토": "확인필요",
    "": "",
}


def normalize_support(value: Any, rid: str) -> str:
    raw = str(value if value is not None else "").strip()
    code = SUPPORT_ALIASES.get(raw.upper(), SUPPORT_ALIASES.get(raw))
    if code is None:
        raise ValueError(
            f"row {rid}: unknown support code {raw!r} (allowed: {sorted(c for c in SUPPORT_CODES if c)})")
    return code


def normalize_mandatory(value: Any) -> bool:
    """미기입·공란은 필수(True)로 취급한다(fail-closed)."""
    if isinstance(value, bool):
        return value
    text = str(value if value is not None else "").strip().lower()
    if text in {"", "1", "true", "yes", "y", "필수", "m", "mandatory", "o"}:
        return True
    if text in {"0", "false", "no", "n", "선택", "optional", "권고", "x"}:
        return False
    raise ValueError(f"unknown mandatory value {value!r}")


def load_rows(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
        if isinstance(data, dict) and "requirements" in data:
            data = data["requirements"]
        if not isinstance(data, list):
            raise ValueError("JSON must be a list or {requirements: [...]}")
        rows = []
        for i, item in enumerate(data, 1):
            if not isinstance(item, dict):
                raise ValueError(f"row {i} must be an object")
            rows.append(item)
        return rows
    # CSV — 따옴표 안 줄바꿈(다중행 셀)을 보존하기 위해 splitlines 대신 io.StringIO 사용
    import io
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if not reader.fieldnames:
        raise ValueError("CSV has no header")
    return [dict(row) for row in reader]


def normalize(row: dict[str, Any], index: int) -> dict[str, str]:
    rid = str(row.get("id") or row.get("ID") or f"R{index:03d}")
    support = normalize_support(row.get("support", row.get("지원여부")), rid)
    # S2: optional industry matrix columns (fit / eval weight / win theme / risk)
    fit = str(row.get("fit") or row.get("적합") or "").strip().upper()
    if fit in {"STRONG", "S", "강"}:
        fit = "STRONG"
    elif fit in {"PARTIAL", "P", "부분"}:
        fit = "PARTIAL"
    elif fit in {"GAP", "G", "공백"}:
        fit = "GAP"
    return {
        "id": rid,
        "section": str(row.get("section") or row.get("구분") or ""),
        "item": str(row.get("item") or row.get("항목") or ""),
        "text": str(row.get("text") or row.get("내용") or row.get("question") or ""),
        "mandatory": normalize_mandatory(row.get("mandatory", row.get("필수"))),
        "support": support,
        "fit": fit,
        "eval_weight": str(row.get("eval_weight") or row.get("배점") or ""),
        "win_theme_id": str(row.get("win_theme_id") or row.get("theme") or ""),
        "risk": str(row.get("risk") or row.get("위험") or ""),
        "product": str(row.get("product") or row.get("제품명") or ""),
        "note": str(row.get("note") or row.get("추가설명") or ""),
        "source_loc": str(row.get("source_loc") or row.get("출처") or ""),
        "response_loc": str(row.get("response_loc") or row.get("응답위치") or ""),
    }


def risk_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    risk_support = {"X", "부분", "조건부", "확인필요"}
    ranked = [
        r for r in rows
        if r["support"] in risk_support or not r["support"] or r.get("fit") == "GAP"
    ]
    ranked.sort(key=lambda r: (0 if r["mandatory"] else 1, 0 if r.get("fit") == "GAP" else 1, r["id"]))
    return ranked


def to_markdown(rows: list[dict[str, str]], summary_rows: int) -> str:
    counts = Counter(r["support"] or "(미기입)" for r in rows)
    lines = [
        f"# 조견표 매트릭스 ({len(rows)}건 전수)",
        "",
        "## 지원 통계",
        "",
        "| 지원여부 | 건수 |",
        "|---|---:|",
    ]
    for key, n in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"| {key} | {n} |")
    risks = risk_rows(rows)[:summary_rows]
    lines += [
        "",
        f"## 요약 장표용 Top {len(risks)} (리스크·미기입 우선)",
        "",
        "| ID | 항목 | 지원 | 비고 |",
        "|---|---|---|---|",
    ]
    for r in risks:
        item = r["item"] or r["text"][:40]
        lines.append(f"| {r['id']} | {item} | {r['support'] or '미기입'} | {r['note'][:60]} |")
    lines += [
        "",
        f"> 전체 {len(rows)}건은 아래 전수 표(또는 별첨 파일)를 따른다.",
        "",
        "## 전수 매트릭스",
        "",
        "| ID | 구분 | 항목 | 내용 | 지원 | fit | 배점 | theme | 위험 | 제품 | 비고 | 출처 | 응답위치 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        text = r["text"].replace("|", "\\|")
        note = r["note"].replace("|", "\\|")
        lines.append(
            f"| {r['id']} | {r['section']} | {r['item']} | {text} | "
            f"{r['support']} | {r.get('fit', '')} | {r.get('eval_weight', '')} | "
            f"{r.get('win_theme_id', '')} | {r.get('risk', '')} | {r['product']} | "
            f"{note} | {r['source_loc']} | {r['response_loc']} |"
        )
    lines.append("")
    return "\n".join(lines)


def to_csv(rows: list[dict[str, str]]) -> str:
    fields = ["id", "section", "item", "text", "mandatory", "support",
              "fit", "eval_weight", "win_theme_id", "risk",
              "product", "note", "source_loc", "response_loc"]
    from io import StringIO
    buf = StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in fields})
    return buf.getvalue()


def to_audit_requirements(rows: list[dict[str, str]]) -> list[dict]:
    """Sidecar for build_audit_from_meta / audit requirements[]."""
    out = []
    for r in rows:
        state = "pending"
        if r["support"] == "O":
            state = "drafted"
        elif r["support"] in {"X", "N/A"}:
            state = "drafted"
        item = {
            "id": r["id"],
            "mandatory": r["mandatory"],
            "state": state,
            "text": r["text"] or r["item"],
            "support": r["support"],
            "evidence_refs": [r["response_loc"]] if r["response_loc"] else [],
            "rationale": r["note"],
        }
        if r.get("fit"):
            item["fit"] = r["fit"]
        if r.get("eval_weight"):
            item["eval_weight"] = r["eval_weight"]
        if r.get("win_theme_id"):
            item["win_theme_id"] = r["win_theme_id"]
        if r.get("risk"):
            item["risk"] = r["risk"]
        out.append(item)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path)
    ap.add_argument("-o", "--output", type=Path)
    ap.add_argument("--format", choices=["md", "csv", "json"], default="md")
    ap.add_argument("--summary-rows", type=int, default=8)
    ap.add_argument("--audit-sidecar", type=Path,
                    help="Also write requirements[] JSON for audit meta")
    args = ap.parse_args(argv)
    try:
        raw = load_rows(args.input)
        rows = [normalize(r, i) for i, r in enumerate(raw, 1)]
    except (OSError, json.JSONDecodeError, ValueError, csv.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.format == "md":
        body = to_markdown(rows, args.summary_rows)
    elif args.format == "csv":
        body = to_csv(rows)
    else:
        body = json.dumps(rows, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(body if body.endswith("\n") else body + "\n", encoding="utf-8")
        print(f"wrote {args.output} ({len(rows)} rows)")
    else:
        print(body)
    if args.audit_sidecar:
        side = to_audit_requirements(rows)
        args.audit_sidecar.write_text(
            json.dumps(side, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.audit_sidecar}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
