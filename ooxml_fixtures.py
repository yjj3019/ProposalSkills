"""테스트용 최소 OOXML 패키지 생성기 — 한 곳에서만 정의한다.

각 테스트가 zipfile로 직접 조립하다 보니 [Content_Types].xml·_rels/.rels 같은 필수
파트가 빠진 '열리지 않는 파일'이 양성 대조군으로 쓰였다(실제로 python-pptx는 그런
파일을 열지 못한다). 검사기가 요구하는 패키지 구조와 픽스처를 한 정의로 묶어,
"게이트는 통과하는데 PowerPoint는 못 여는" 테스트가 다시 생기지 않게 한다.

python-pptx 없이도 동작한다(zipfile만 사용). 실제 렌더가 필요한 테스트는
python-pptx로 만든 문서를 쓴다.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

CONTENT_TYPES = ('<?xml version="1.0"?>'
                 '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                 '<Default Extension="xml" ContentType="application/xml"/>'
                 '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.'
                 'relationships+xml"/></Types>')
ROOT_RELS = ('<?xml version="1.0"?>'
             '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             '<Relationship Id="rId1" Target="{main}" Type="http://schemas.openxmlformats.org/'
             'officeDocument/2006/relationships/officeDocument"/></Relationships>')


NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
}


def with_namespaces(xml: str) -> str:
    """루트 태그에 접두사 네임스페이스 선언을 채운다.

    실제 OOXML은 항상 선언을 갖는다. 검사기는 main 파트의 XML 파싱 성공을 요구하므로,
    선언 없는 조각(`<p:presentation/>`)은 실제 파일과 달리 파싱에 실패한다.
    """
    start = xml.find("<")
    end = xml.find(">", start)
    if start < 0 or end < 0:
        return xml
    tag = xml[start:end]
    decls = "".join(f' xmlns:{k}="{v}"' for k, v in NS.items() if f"xmlns:{k}=" not in tag)
    closing = "/>" if xml[end - 1] == "/" else ">"
    body_start = end + 1
    tag_text = tag[:-1] if xml[end - 1] == "/" else tag
    return xml[:start] + tag_text + decls + closing + xml[body_start:]


def _package(path: Path, main: str, parts: dict[str, str]) -> Path:
    """필수 파트를 갖춘 OOXML ZIP을 만든다. parts가 main을 덮어쓸 수 있다."""
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", ROOT_RELS.format(main=main))
        for name, xml in parts.items():
            z.writestr(name, with_namespaces(xml) if name == main else xml)
    return path


def runs(text: str, tag: str = "a") -> str:
    """텍스트를 글자 단위 run으로 쪼갠 XML(run 분할 검출 재현용)."""
    return "".join(f"<{tag}:r><{tag}:t>{ch}</{tag}:t></{tag}:r>" for ch in text)


def pptx(path: Path, parts: dict[str, str] | None = None, *,
         presentation: str = "<p:presentation/>", raw: dict[str, str] | None = None) -> Path:
    """최소 PPTX. parts={zip 경로: 문단 텍스트}는 run 분할 상태로 기록한다.

    raw를 주면 XML을 그대로 넣는다(관계·차트 등 구조를 직접 짜야 할 때).
    """
    body = {"ppt/presentation.xml": presentation}
    for name, text in (parts or {}).items():
        body[name] = f"<p:sld><p:txBody><a:p>{runs(text)}</a:p></p:txBody></p:sld>"
    body.update(raw or {})
    if not any(n.startswith("ppt/slides/slide") for n in body):
        body["ppt/slides/slide1.xml"] = "<p:sld/>"
    return _package(path, "ppt/presentation.xml", body)


def docx(path: Path, body_xml: str, extra: dict[str, str] | None = None) -> Path:
    """최소 DOCX. extra={zip 경로: 텍스트}는 머리말 형식으로 기록한다."""
    parts = {"word/document.xml": f"<w:document><w:body>{body_xml}</w:body></w:document>"}
    for name, text in (extra or {}).items():
        parts[name] = f"<w:hdr><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:hdr>"
    return _package(path, "word/document.xml", parts)


def xlsx(path: Path, parts: dict[str, str]) -> Path:
    """최소 XLSX. parts는 XML을 그대로 넣는다(workbook·sheet·sharedStrings)."""
    body = {"xl/workbook.xml": "<workbook><sheets/></workbook>"}
    body.update(parts)
    if not any(n.startswith("xl/worksheets/sheet") for n in body):
        body["xl/worksheets/sheet1.xml"] = "<worksheet><sheetData/></worksheet>"
    return _package(path, "xl/workbook.xml", body)
