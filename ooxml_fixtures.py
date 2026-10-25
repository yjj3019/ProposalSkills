"""Minimal OOXML test package builders, defined in one place. Hand-built ZIP fixtures previously omitted required parts such as [Content_Types].xml and _rels/.rels, producing positive controls that python-pptx could not open. Share required package structure with the checker to prevent files passing the gate but failing in PowerPoint. Uses zipfile only; rendering tests use documents built with python-pptx."""
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
    """Add prefixed namespace declarations to the root tag. Real OOXML declares them; the checker requires main-part XML parsing, so undeclared fragments such as `<p:presentation/>` fail unlike real files."""
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
    """Create an OOXML ZIP with required parts; parts may override main."""
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", ROOT_RELS.format(main=main))
        for name, xml in parts.items():
            # Add declarations to every XML part, as real OOXML does.
            # The checker parses body parts too; declaring only main would make the fixture
            # behave differently from a real file.
            z.writestr(name, with_namespaces(xml) if name.endswith(".xml") else xml)
    return path


def runs(text: str, tag: str = "a") -> str:
    """Split text into character-sized XML runs to reproduce split-run detection."""
    return "".join(f"<{tag}:r><{tag}:t>{ch}</{tag}:t></{tag}:r>" for ch in text)


def pptx(path: Path, parts: dict[str, str] | None = None, *,
         presentation: str = "<p:presentation/>", raw: dict[str, str] | None = None) -> Path:
    """Minimal PPTX. parts={ZIP path: paragraph text} uses split runs. Supply raw to insert XML verbatim for relationships, charts, or other structures."""
    body = {"ppt/presentation.xml": presentation}
    for name, text in (parts or {}).items():
        body[name] = f"<p:sld><p:txBody><a:p>{runs(text)}</a:p></p:txBody></p:sld>"
    body.update(raw or {})
    if not any(n.startswith("ppt/slides/slide") for n in body):
        body["ppt/slides/slide1.xml"] = "<p:sld/>"
    return _package(path, "ppt/presentation.xml", body)


def docx(path: Path, body_xml: str, extra: dict[str, str] | None = None) -> Path:
    """Minimal DOCX. extra={ZIP path: text} is written as headers."""
    parts = {"word/document.xml": f"<w:document><w:body>{body_xml}</w:body></w:document>"}
    for name, text in (extra or {}).items():
        parts[name] = f"<w:hdr><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:hdr>"
    return _package(path, "word/document.xml", parts)


def submission_pptx(path: Path, text: str) -> Path:
    """Positive submission control accepted by the actual loader and layout checks."""
    from pptx import Presentation
    from pptx.util import Inches, Pt
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    prs.core_properties.category = "proposal-deck:detailed-submission"
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    for name, value, top, size in (
            ("TITLE", "제안 내용", 0.4, 22),
            ("LEAD", "원장에 기록한 수치를 본문에 반영합니다.", 1.1, 13),
            ("BODY", text, 2.0, 11)):
        shape = slide.shapes.add_textbox(Inches(0.5), Inches(top), Inches(12), Inches(0.7))
        shape.name, shape.text = name, value
        for p in shape.text_frame.paragraphs:
            for run in p.runs:
                run.font.size = Pt(size)
    prs.save(str(path))
    return path


def xlsx(path: Path, parts: dict[str, str]) -> Path:
    """Minimal XLSX. parts inserts XML verbatim (workbook, sheet, sharedStrings)."""
    body = {"xl/workbook.xml": "<workbook><sheets/></workbook>"}
    body.update(parts)
    if not any(n.startswith("xl/worksheets/sheet") for n in body):
        body["xl/worksheets/sheet1.xml"] = "<worksheet><sheetData/></worksheet>"
    return _package(path, "xl/workbook.xml", body)
