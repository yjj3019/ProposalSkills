#!/usr/bin/env python3
"""PPTX/DOCX 원본 패키지 검사 - review-checklist §8의 자동화 가능 항목.

원본(ZIP) 패키지의 메타데이터·노트·댓글·숨김 슬라이드·외부 링크·임베드·매크로
힌트를 나열한다. 렌더(PDF 이미지) 검사는 포함하지 않는다 - LibreOffice/Poppler
경로와 사람 육안이 필요하다.

사용법:
    python3 package_inspect.py 제안서.pptx
    python3 package_inspect.py 제안서.docx --json

종료 코드: 0=차단 없음(경고·NOT INSPECTED 가능), 1=차단 항목 있음, 2=사용 오류.
판정은 기계 힌트일 뿐이며, 최종 제출 판정은 사람·형제 게이트가 한다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

WARNING_PREFIXES = ("[NOT INSPECTED]", "[경고]")
BLOCKING_PREFIXES = ("[메타데이터]", "[노트]", "[댓글]", "[숨김]", "[외부링크]",
                     "[임베드]", "[매크로]", "[가격힌트]", "[추적변경]")
MAX_UNZIPPED_BYTES = 128 * 1024 * 1024
MAX_ZIP_PARTS = 5000


def _safe_read(z: zipfile.ZipFile, name: str) -> str:
    try:
        return z.read(name).decode("utf-8", "ignore")
    except KeyError:
        return ""


def _xml_part(z: zipfile.ZipFile, name: str, findings: list[str], expected_root: str):
    data = z.read(name)
    if b"\0" in data or b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        findings.append(f"[NOT INSPECTED] {name}: 안전하지 않은 XML 선언 또는 인코딩")
        return None
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        findings.append(f"[NOT INSPECTED] {name}: XML을 읽을 수 없다")
        return None
    if root.tag.rsplit("}", 1)[-1] != expected_root:
        findings.append(f"[NOT INSPECTED] {name}: 예상하지 못한 XML 루트")
        if expected_root != "Relationships" or root.tag.rsplit("}", 1)[-1] != "Relationship":
            return None
    return root


def _relationships(z: zipfile.ZipFile, name: str, findings: list[str]) -> list[dict[str, str]]:
    root = _xml_part(z, name, findings, "Relationships")
    if root is None:
        return []
    if root.tag.rsplit("}", 1)[-1] == "Relationship":
        return [root.attrib]
    return [item.attrib for item in root if item.tag.rsplit("}", 1)[-1] == "Relationship"]


def _core_props(z: zipfile.ZipFile, findings: list[str]) -> dict[str, str]:
    xml = _safe_read(z, "docProps/core.xml")
    if not xml:
        return {}
    if "\0" in xml or "<!DOCTYPE" in xml.upper() or "<!ENTITY" in xml.upper():
        findings.append("[NOT INSPECTED] docProps/core.xml: 안전하지 않은 XML 선언 또는 인코딩")
        return {}
    props: dict[str, str] = {}
    # Namespace-tolerant: match local names in Clark or prefixed form.
    for key in ("creator", "lastModifiedBy", "title", "subject", "description",
                "keywords", "category", "revision"):
        m = re.search(
            rf"<(?:[\w.]+:)?{key}[^>]*>([^<]*)</(?:[\w.]+:)?{key}>",
            xml, re.I,
        )
        if m and m.group(1).strip():
            props[key] = m.group(1).strip()
    if not props:
        try:
            root = ET.fromstring(xml)
        except ET.ParseError:
            return {}
        for el in root.iter():
            tag = el.tag.rsplit("}", 1)[-1]
            if tag in props or tag not in {
                "creator", "lastModifiedBy", "title", "subject", "description",
                "keywords", "category", "revision",
            }:
                continue
            if (el.text or "").strip():
                props[tag] = el.text.strip()
    return props


def inspect_pptx(path: Path) -> list[str]:
    findings: list[str] = []
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        props = _core_props(z, findings)
        for key in ("creator", "lastModifiedBy"):
            if key in props:
                findings.append(f"[메타데이터] {key}={props[key]} — 제출 전 조직 정책에 맞게 정리")

        note_files = [n for n in names if re.match(r"ppt/notesSlides/notesSlide\d+\.xml$", n)]
        if note_files:
            findings.append(f"[노트] notesSlides {len(note_files)}개 — 발표 노트에 가격·내부명 잔존 여부 육안 확인")

        comment_files = [n for n in names if "comments" in n.lower() and n.endswith(".xml")]
        if comment_files:
            findings.append(f"[댓글] 댓글 파트 {len(comment_files)}개 — 제출 전 삭제·정리")

        # Hidden slides: PowerPoint stores show="0" on the <p:sld> element of the slide part itself
        hidden = 0
        for n in names:
            if re.match(r"ppt/slides/slide\d+\.xml$", n):
                slide = _xml_part(z, n, findings, "sld")
                if slide is not None:
                    show = slide.get("show", "1").strip().lower()
                    if show in {"0", "false"}:
                        hidden += 1
                    elif show not in {"1", "true"}:
                        findings.append(f"[NOT INSPECTED] {n}: show 값이 올바르지 않다")
        if hidden:
            findings.append(f"[숨김] 숨김 슬라이드 {hidden}장 — 제출 전 삭제 또는 공개 여부 확인")

        # External hyperlinks in relationships
        ext_links = 0
        rel_parts = {}
        for n in names:
            if n.endswith(".rels"):
                rel_parts[n] = _relationships(z, n, findings)
                ext_links += sum(r.get("TargetMode", "").lower() == "external"
                                 or r.get("Target", "").lower().startswith(("http://", "https://"))
                                 for r in rel_parts[n])
        if ext_links:
            findings.append(f"[외부링크] 관계 파일 외부 Target {ext_links}건 — 제출 허용 여부 확인")

        embeds = [n for n in names if n.startswith("ppt/embeddings/")]
        chart_data = {"ppt/embeddings/" + t.rsplit("/", 1)[-1]
                      for n, rels in rel_parts.items() if re.match(r"ppt/charts/_rels/[^/]+\.rels$", n)
                      for r in rels for t in [r.get("Target", "")] if "embeddings/" in t}
        attached = [n for n in embeds if n not in chart_data]
        if attached:
            findings.append(f"[임베드] embeddings/ {len(attached)}개 — 첨부 개체·원가표 혼입 여부 확인")
        if chart_data:
            findings.append(f"[차트데이터] 차트 값 워크북 {len(chart_data)}개 — 차트에 쓴 값만 들어 있는지 확인 (첨부 개체 아님)")

        if any("vbaProject" in n for n in names):
            findings.append("[매크로] vbaProject 감지 — 매크로 포함 제출은 보통 실격")

        # Soft price hints in slide XML (non-authoritative)
        price_hits = 0
        for n in names:
            if re.match(r"ppt/slides/slide\d+\.xml$", n):
                text = re.sub(r"<[^>]+>", " ", _safe_read(z, n))
                if re.search(r"(원가|할인율|공급단가|내부원가)", text):
                    price_hits += 1
        if price_hits:
            findings.append(f"[가격힌트] 슬라이드 {price_hits}장에서 원가/할인 용어 — 가격 분리 제출 시 Critical")

        findings.append("[NOT INSPECTED] 차트 캐시·스피커 오디오·커스텀 XML은 미검사")
        findings.append("[NOT INSPECTED] PDF 렌더·폰트 깨짐·잘림은 LibreOffice/Poppler + 육안")
    return findings


def inspect_docx(path: Path) -> list[str]:
    findings: list[str] = []
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        props = _core_props(z, findings)
        for key in ("creator", "lastModifiedBy"):
            if key in props:
                findings.append(f"[메타데이터] {key}={props[key]} — 제출 전 조직 정책에 맞게 정리")

        if any(n.startswith("word/comments") for n in names):
            findings.append("[댓글] word/comments* 존재 — 제출 전 삭제·정리")
        if "word/vbaProject.bin" in names or any("vbaProject" in n for n in names):
            findings.append("[매크로] vbaProject 감지 — 매크로 포함 제출은 보통 실격")
        embeds = [n for n in names if n.startswith("word/embeddings/")]
        if embeds:
            findings.append(f"[임베드] embeddings/ {len(embeds)}개 — 첨부 개체 확인")

        rel_files = [n for n in names if n.endswith(".rels")]
        ext_links = 0
        for n in rel_files:
            ext_links += sum(r.get("TargetMode", "").lower() == "external"
                             or r.get("Target", "").lower().startswith(("http://", "https://"))
                             for r in _relationships(z, n, findings))
        if ext_links:
            findings.append(f"[외부링크] 관계 파일 외부 Target {ext_links}건")

        if "word/document.xml" in names:
            document = _xml_part(z, "word/document.xml", findings, "document")
            tracked = (sum(el.tag.rsplit("}", 1)[-1] in {"ins", "del"} for el in document.iter())
                       if document is not None else
                       len(re.findall(r"<w:(?:ins|del)\b", _safe_read(z, "word/document.xml"))))
        else:
            findings.append("[NOT INSPECTED] word/document.xml: 본문이 없다")
            tracked = 0
        if tracked:
            findings.append(f"[추적변경] 수정 추적 {tracked}건 — 승인하거나 삭제한 뒤 제출")
        findings.append("[NOT INSPECTED] 숨김 텍스트·필드 코드 상세는 미검사")
        findings.append("[NOT INSPECTED] PDF 렌더·폰트 깨짐·잘림은 LibreOffice/Poppler + 육안")
    return findings


def blocking(items: list[str]) -> list[str]:
    return [f for f in items
            if not f.startswith(WARNING_PREFIXES)
            and f.startswith(BLOCKING_PREFIXES)]


def run(path: Path) -> list[str]:
    suffix = path.suffix.lower()
    if suffix not in {".pptx", ".docx"}:
        raise ValueError(f"지원하지 않는 형식: {path.suffix}")
    with zipfile.ZipFile(path) as package:
        infos = package.infolist()
        if len(infos) > MAX_ZIP_PARTS:
            raise ValueError("package has too many ZIP parts")
        if sum(info.file_size for info in infos) > MAX_UNZIPPED_BYTES:
            raise ValueError("package uncompressed size exceeds limit")
    if suffix == ".pptx":
        return inspect_pptx(path)
    return inspect_docx(path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("file", type=Path)
    ap.add_argument("--json", action="store_true", help="JSON으로 출력")
    a = ap.parse_args()
    if not a.file.is_file():
        print(f"파일 없음: {a.file}", file=sys.stderr)
        return 2
    try:
        items = run(a.file)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2
    except zipfile.BadZipFile:
        print("NOT INSPECTED: ZIP 패키지가 아님 (손상되었거나 기업 DRM으로 암호화된 파일일 수 있음)", file=sys.stderr)
        return 2
    blockers = blocking(items)
    if a.json:
        print(json.dumps(
            {"file": str(a.file), "findings": items, "blocking": blockers},
            ensure_ascii=False, indent=2,
        ))
    else:
        for item in items:
            prefix = "차단" if item in blockers else "정보"
            print(f"  [{prefix}] {item}")
        if blockers:
            print(f"차단 후보 — {len(blockers)}건 (사람·정책 최종 판정)")
            return 1
        print("패키지 힌트 검사 완료 (렌더·법적 적정성은 별도)")
    return 1 if blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
