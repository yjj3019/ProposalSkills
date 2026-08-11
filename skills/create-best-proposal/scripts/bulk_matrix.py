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


SUPPORT_CODES = {"O", "부분", "조건부", "X", "N/A", "확인필요", "", None}


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
    # CSV
    reader = csv.DictReader(text.splitlines())
    if not reader.fieldnames:
        raise ValueError("CSV has no header")
    return [dict(row) for row in reader]


def normalize(row: dict[str, Any], index: int) -> dict[str, str]:
    rid = str(row.get("id") or row.get("ID") or f"R{index:03d}")
    support = str(row.get("support") or row.get("지원여부") or "").strip()
    return {
        "id": rid,
        "section": str(row.get("section") or row.get("구분") or ""),
        "item": str(row.get("item") or row.get("항목") or ""),
        "text": str(row.get("text") or row.get("내용") or row.get("question") or ""),
        "mandatory": str(row.get("mandatory", "true")).lower() in {"1", "true", "yes", "y", "필수"},
        "support": support,
        "product": str(row.get("product") or row.get("제품명") or ""),
        "note": str(row.get("note") or row.get("추가설명") or ""),
        "source_loc": str(row.get("source_loc") or row.get("출처") or ""),
        "response_loc": str(row.get("response_loc") or row.get("응답위치") or ""),
    }


def risk_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    risk_support = {"X", "부분", "조건부", "확인필요"}
    ranked = [r for r in rows if r["support"] in risk_support or not r["support"]]
    ranked.sort(key=lambda r: (0 if r["mandatory"] else 1, r["id"]))
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
        "| ID | 구분 | 항목 | 내용 | 지원여부 | 제품명 | 추가설명 | 출처 | 응답위치 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        text = r["text"].replace("|", "\\|")
        note = r["note"].replace("|", "\\|")
        lines.append(
            f"| {r['id']} | {r['section']} | {r['item']} | {text} | "
            f"{r['support']} | {r['product']} | {note} | {r['source_loc']} | {r['response_loc']} |"
        )
    lines.append("")
    return "\n".join(lines)


def to_csv(rows: list[dict[str, str]]) -> str:
    fields = ["id", "section", "item", "text", "mandatory", "support",
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
        out.append({
            "id": r["id"],
            "mandatory": r["mandatory"],
            "state": state,
            "text": r["text"] or r["item"],
            "support": r["support"],
            "evidence_refs": [r["response_loc"]] if r["response_loc"] else [],
            "rationale": r["note"],
        })
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
