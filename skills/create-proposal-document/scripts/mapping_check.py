#!/usr/bin/env python3
"""조견표(요구사항 대응표) ↔ 본문 REQ-ID 양방향 일치 검사.

조견표는 마크다운 표 또는 단순 JSON을 받는다. 본문은 PPTX/DOCX/마크다운/
텍스트에서 REQ-ID를 추출한다.

사용법:
    python3 mapping_check.py matrix.md --doc 제안서.pptx
    python3 mapping_check.py matrix.json --doc outline.md --json

조견표 최소 열(마크다운): REQ-ID | … | 페이지 또는 장표
JSON 형식: [{"id":"REQ-001","page":"3"}, ...] 또는 {"requirements":[...]}
같은 REQ-ID가 표기 변형을 포함해 한 표의 여러 행에 있으면 사용 오류로 거부한다.
JSON 객체 키가 중복되면 중첩 위치와 관계없이 사용 오류로 거부한다.

종료 코드: 0=양방향 일치, 1=불일치, 2=사용 오류.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

REQ_RE = re.compile(r"\bREQ[-_]?\d{1,6}\b", re.IGNORECASE)


def _unique_json_members(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON member")
        result[key] = value
    return result


def normalize_id(raw: str) -> str:
    text = raw.strip().upper().replace("_", "-")
    m = re.match(r"REQ-?(\d{1,6})", text)
    if not m:
        return text
    return f"REQ-{int(m.group(1)):03d}"


def xml_text(xml: str) -> str:
    """Text of an OOXML part: runs inside one paragraph are joined (PowerPoint and Word split "REQ-" and "001"
    into separate runs); paragraphs and cells stay apart."""
    xml = re.sub(r"</(?:a:p|w:p)>", "\n", xml)
    return re.sub(r"<[^>]+>", "", xml)


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
                chunks.append(xml_text(z.read(n).decode("utf-8", "ignore")))
        return "\n".join(chunks)
    if suffix == ".docx":
        with zipfile.ZipFile(path) as z:
            parts = ["word/document.xml"] + sorted(n for n in z.namelist() if re.match(r"word/(?:header|footer|footnotes|endnotes)\d*\.xml$", n))
            return "\n".join(xml_text(z.read(n).decode("utf-8", "ignore")) for n in parts)
    return path.read_text(encoding="utf-8")


def _markdown_cells(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    cells, cell = [], []
    i, ended_with_separator = 0, False
    while i < len(line):
        if line[i] == "\\" and i + 1 < len(line) and line[i + 1] in {"\\", "|"}:
            cell.append(line[i + 1])
            i += 2
            ended_with_separator = False
        elif line[i] == "|":
            cells.append("".join(cell).strip())
            cell = []
            i += 1
            ended_with_separator = True
        else:
            cell.append(line[i])
            i += 1
            ended_with_separator = False
    if not ended_with_separator:
        cells.append("".join(cell).strip())
    return cells


def parse_matrix(path: Path) -> dict[str, str]:
    """id -> page/location (may be empty string)."""
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text, object_pairs_hook=_unique_json_members)
        rows = data["requirements"] if isinstance(data, dict) and "requirements" in data else data
        out: dict[str, str] = {}
        if not isinstance(rows, list):
            raise ValueError("조견표 JSON은 배열 또는 requirements 배열이어야 함")
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("조견표 JSON 행은 객체여야 함")
            rid = normalize_id(str(row.get("id") or row.get("req_id") or ""))
            if not rid:
                continue
            if rid in out:
                raise ValueError(f"duplicate REQ-ID in matrix: {rid}")
            page = str(row.get("page") or row.get("slide") or row.get("location") or "")
            out[rid] = page
        return out

    # Keep tables separate: a summary and the full matrix may repeat an ID.
    tables: list[list[str]] = []
    for line in text.splitlines():
        if line.strip().startswith("|"):
            if not tables or not tables[-1]:
                tables.append([])
            tables[-1].append(line.strip())
        elif tables and tables[-1]:
            tables.append([])
    tables = [table for table in tables if table]
    if not tables:
        # Fallback: any REQ-ID mentioned is a matrix row without page
        return {normalize_id(m.group(0)): "" for m in REQ_RE.finditer(text)}

    out: dict[str, str] = {}
    with_location: set[str] = set()
    for lines in tables:
        # A first row that already holds a REQ-ID is data, not a header: a table without a header must not lose it.
        headerless = bool(REQ_RE.search(lines[0]))
        header_l = [] if headerless else [c.lower() for c in _markdown_cells(lines[0])]
        if headerless:
            first_cells = _markdown_cells(lines[0])
            id_idx = next((i for i, c in enumerate(first_cells) if REQ_RE.search(c)), 0)
        else:
            id_idx = next((i for i, h in enumerate(header_l)
                           if "req" in h or "요구" in h or h in {"id", "번호"}), 0)
        page_idx = next((i for i, h in enumerate(header_l)
                         if "page" in h or "페이지" in h or "장표" in h or "slide" in h
                         or "응답위치" in h or "대응위치" in h or "response_loc" in h), None)
        rows: dict[str, str] = {}
        for ln in (lines if headerless else lines[1:]):
            if re.match(r"^\|[\s:-]+\|", ln):
                continue
            cells = _markdown_cells(ln)
            if id_idx >= len(cells):
                continue
            rid_match = REQ_RE.search(cells[id_idx]) or REQ_RE.search(ln)
            if not rid_match:
                continue
            rid = normalize_id(rid_match.group(0))
            if rid in rows:
                raise ValueError(f"duplicate REQ-ID in matrix: {rid}")
            rows[rid] = cells[page_idx] if page_idx is not None and page_idx < len(cells) else ""
        for rid, page in rows.items():
            if page_idx is None:
                out.setdefault(rid, "")
            elif rid in with_location and out[rid] != page:
                raise ValueError(f"conflicting REQ-ID locations in matrix: {rid}")
            else:
                out[rid] = page
                with_location.add(rid)
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
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("matrix", type=Path, help="조견표 마크다운 또는 JSON")
    ap.add_argument("--doc", type=Path, required=True, help="본문 PPTX/DOCX/MD/TXT")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if not a.matrix.is_file() or not a.doc.is_file():
        print("matrix 또는 doc 파일 없음", file=sys.stderr)
        return 2
    try:
        matrix = parse_matrix(a.matrix)
        doc_ids = ids_in_doc(a.doc)
    except (zipfile.BadZipFile, KeyError, ValueError, UnicodeDecodeError) as exc:
        # BadZipFile also covers an Office file wrapped by an enterprise DRM agent
        print(f"NOT INSPECTED: 읽지 못함 ({type(exc).__name__}: {exc})", file=sys.stderr)
        return 2
    if not matrix:
        print("조견표에서 REQ-ID를 찾지 못함", file=sys.stderr)
        return 2
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
