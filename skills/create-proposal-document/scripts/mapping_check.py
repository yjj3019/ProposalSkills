#!/usr/bin/env python3
"""조견표(요구사항 대응표) ↔ 본문 REQ-ID 양방향 일치 검사.

조견표는 마크다운 표 또는 단순 JSON을 받는다. 본문은 PPTX/DOCX/마크다운/
텍스트에서 REQ-ID를 추출한다.

사용법:
    python3 mapping_check.py matrix.md --doc 제안서.pptx
    python3 mapping_check.py matrix.json --doc outline.md --json

조견표 최소 열(마크다운): REQ-ID | … | 페이지 또는 장표
JSON 형식: [{"id":"REQ-001","page":"3"}, ...] 또는 {"requirements":[...]}

종료 코드: 0=양방향 일치, 1=불일치, 2=사용 오류.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

REQ_RE = re.compile(r"\bREQ[-_]?\d{1,4}\b", re.IGNORECASE)


def normalize_id(raw: str) -> str:
    text = raw.strip().upper().replace("_", "-")
    m = re.match(r"REQ-?(\d{1,4})", text)
    if not m:
        return text
    return f"REQ-{int(m.group(1)):03d}"


def extract_text_blocks(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pptx":
        chunks: list[str] = []
        with zipfile.ZipFile(path) as z:
            names = sorted(
                (n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)),
                key=lambda n: int(re.search(r"slide(\d+)\.xml$", n).group(1)),
            )
            for n in names:
                xml = z.read(n).decode("utf-8", "ignore")
                chunks.append(re.sub(r"<[^>]+>", " ", xml))
        return "\n".join(chunks)
    if suffix == ".docx":
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8", "ignore")
        return re.sub(r"<[^>]+>", " ", xml)
    return path.read_text(encoding="utf-8")


def parse_matrix(path: Path) -> dict[str, str]:
    """id -> page/location (may be empty string)."""
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
        rows = data["requirements"] if isinstance(data, dict) and "requirements" in data else data
        out: dict[str, str] = {}
        for row in rows:
            rid = normalize_id(str(row.get("id") or row.get("req_id") or ""))
            if not rid:
                continue
            page = str(row.get("page") or row.get("slide") or row.get("location") or "")
            out[rid] = page
        return out

    # Markdown table: find header with REQ
    lines = [ln.strip() for ln in text.splitlines() if ln.strip().startswith("|")]
    if not lines:
        # Fallback: any REQ-ID mentioned is a matrix row without page
        return {normalize_id(m.group(0)): "" for m in REQ_RE.finditer(text)}

    header_cells = [c.strip() for c in lines[0].strip("|").split("|")]
    header_l = [h.lower() for h in header_cells]
    id_idx = next((i for i, h in enumerate(header_l)
                   if "req" in h or "요구" in h or h in {"id", "번호"}), 0)
    page_idx = next((i for i, h in enumerate(header_l)
                     if "page" in h or "페이지" in h or "장표" in h or "slide" in h), None)

    out = {}
    for ln in lines[1:]:
        if re.match(r"^\|[\s:-]+\|", ln):
            continue
        cells = [c.strip() for c in ln.strip("|").split("|")]
        if id_idx >= len(cells):
            continue
        rid_match = REQ_RE.search(cells[id_idx]) or REQ_RE.search(ln)
        if not rid_match:
            continue
        rid = normalize_id(rid_match.group(0))
        page = cells[page_idx] if page_idx is not None and page_idx < len(cells) else ""
        out[rid] = page
    return out


def ids_in_doc(path: Path) -> set[str]:
    return {normalize_id(m.group(0)) for m in REQ_RE.finditer(extract_text_blocks(path))}


def check(matrix: dict[str, str], doc_ids: set[str]) -> list[str]:
    fails: list[str] = []
    matrix_ids = set(matrix)
    for rid, page in sorted(matrix.items()):
        if not page or page in {"-", "—", "TBD", "미정", ""}:
            fails.append(f"[조견표→본문] {rid}: 페이지/장표 미기재")
        if rid not in doc_ids:
            fails.append(f"[조견표→본문] {rid}: 본문에 REQ-ID 없음")
    for rid in sorted(doc_ids - matrix_ids):
        fails.append(f"[본문→조견표] {rid}: 조견표 행 없음")
    return fails


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("matrix", type=Path, help="조견표 마크다운 또는 JSON")
    ap.add_argument("--doc", type=Path, required=True, help="본문 PPTX/DOCX/MD/TXT")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if not a.matrix.is_file() or not a.doc.is_file():
        print("matrix 또는 doc 파일 없음", file=sys.stderr)
        return 2
    matrix = parse_matrix(a.matrix)
    if not matrix:
        print("조견표에서 REQ-ID를 찾지 못함", file=sys.stderr)
        return 2
    doc_ids = ids_in_doc(a.doc)
    fails = check(matrix, doc_ids)
    payload = {
        "matrix_count": len(matrix),
        "doc_count": len(doc_ids),
        "failures": fails,
        "ok": not fails,
    }
    if a.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"조견표 {len(matrix)}행 / 본문 REQ {len(doc_ids)}개")
        if fails:
            print(f"불일치 — {len(fails)}건")
            for f in fails:
                print(" -", f)
            return 1
        print("양방향 일치 (페이지 번호 정확성은 조판 후 육안 재확인)")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
