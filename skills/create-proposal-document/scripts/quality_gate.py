#!/usr/bin/env python3
"""Automated proposal quality gate for machine-checkable review-checklist.md items.

Usage:
    python3 quality_gate.py 제안서.pptx [--names 금지명단.txt]
        [--palette "1F3864,8FAADC,..."] [--lang ko|en|both] [--stage draft|submission]

Check exaggerated language (human review even with evidence), unresolved placeholders, residual forbidden names, and palette deviations (PPTX only). Scope includes PPTX slides, notes, layouts, masters, charts, comments; DOCX body including text boxes, headers, footers, footnotes, endnotes, comments; XLSX cells/comments; and document properties, including content invisible in rendered output.
--lang selects the exaggerated-language dictionary: ko (default), en, or both.
--stage draft allows unresolved markers ([NEEDS INPUT]·입력요망) as nonblocking warnings; submission (default) blocks them. Theme-color NOT INSPECTED is always nonblocking.
Exit codes: 0=pass (warnings possible), 1=blocked (list printed), 2=usage error or inspection unavailable.
These are machine checks; humans review sentence context, persuasiveness, and legal suitability.
"""
from __future__ import annotations
import argparse, re, sys, xml.etree.ElementTree as ET, zipfile
from pathlib import Path

BANNED_KO = ["최고", "완벽", "혁신적", "획기적", "100%", "무중단", "완전 자동화",
             "위험 제로", "유일한", "업계 1위",
             # Additions from actual proposal review: unsupported superlative modifiers.
             # Exclude factual names such as '최상위 등급' through BANNED_EXCEPTIONS below.
             "최첨단", "압도적", "탁월한", "독보적", "최상위", "차원이 다른"]
# English exaggerated phrases, synchronized with writing-style.md; match word boundaries.
BANNED_EN = ["best-in-class", "best", "world-class", "industry-leading", "market-leading",
             "leading provider", "leading solution",
             "unique", "perfect", "flawless", "innovative", "revolutionary",
             "cutting-edge", "state-of-the-art", "next-generation", "100%",
             "zero downtime", "zero risk", "fully automated", "fully compliant",
             "seamless", "effortless", "guarantee", "guaranteed", "guarantees",
             "guaranteeing", "bulletproof", "future-proof",
             "unlimited", "significant savings"]
PLACEHOLDERS = ["lorem", "xxxx", "TBD", "샘플텍스트", "placeholder", "OOO", "○○○", "p.__", "p. __", "p.XX"]
# Draft factual-slot markers: block placeholders at submission, warn without blocking in drafts.
# Avoid blocking the skill's own recommended markers ([NEEDS INPUT]·［입력요망］) in drafts.
# Anonymous buyer notation such as '○○공사' is a draft convention: warn in draft, block in submission.
DRAFT_MARKERS = ["needs input", "입력요망", "○○", "[unverified]", "미정"]
# S7: minimal AI-slop patterns (empty rhetoric/template language), separate from exaggeration; substring matching.
AI_SLOP_KO = [
    "다양한 측면에서", "종합적인 솔루션", "시너지를 창출", "최적의 방안을 제시",
    "고객 맞춤형 서비스 제공", "차별화된 경쟁력", "원스톱",
]
AI_SLOP_EN = [
    "in today's fast-paced", "leverage synergies", "holistic solution",
    "delve into", "it is important to note", "game-changer", "unlock the potential",
]
# These prefixes mark nonblocking warnings and do not affect exit codes.
WARNING_PREFIXES = ("[NOT INSPECTED]", "[검토필요]", "[모호확약]")

# AMBIGUOUS_COMMITMENT: bidder actions obscured by "가능/예정/검토" without who, what, when,
# or conditions. Match service actions combined with vague predicates rather than isolated words;
# exclude concrete numbers, explicit conditional subjects, and buyer subjects. Nonblocking until false positives are reviewed.
_AMBIG_ACT = r"(?:지원|대응|제공|조치|투입|교육|점검|협의|검토|추진|고려|개선|반영|수용)"
AMBIGUOUS_COMMITMENT_RE = re.compile(
    _AMBIG_ACT + r"\s*(?:이|을|를|도)?\s*"
    r"(?:가능(?:합니다|함|하다|\b|$)|(?:할|될)\s*수\s*있(?:습니다|음|다)|예정(?:입니다|임|이다)?)"
    r"|적극\s*(?:검토|협의|지원)|노력하겠습니다|최선을\s*다하겠습니다")
# Conditional clauses naming who determines execution are bounded statements (not "필요 시").
_AMBIG_CONDITION_RE = re.compile(
    r"(?:발주처|발주기관|고객|주관기관|감리|위원회)(?:가|이|의|에서)?\s*[^,.]{0,20}?"
    r"(?:승인|요청|합의|지정)(?:하는|한|할|이\s*있는)?\s*(?:경우|때|시)")
# Statements about another party's authority or functionality are not bidder commitments.
_AMBIG_OTHER_SUBJECT_RE = re.compile(r"^\s*(?:발주처|발주기관|고객|주관기관|감리|평가위원)(?:은|는|이|가)\s")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?。])\s+|\n+")


def ambiguous_commitments(text: str) -> list[str]:
    """Return original sentences that appear to contain ambiguous commitments; evaluate per sentence."""
    hits: list[str] = []
    for sentence in _SENTENCE_SPLIT_RE.split(text):
        s = sentence.strip()
        if not s or not AMBIGUOUS_COMMITMENT_RE.search(s):
            continue
        if re.search(r"\d", s) or _AMBIG_CONDITION_RE.search(s) or _AMBIG_OTHER_SUBJECT_RE.match(s):
            continue
        hits.append(s)
    return hits


# Conventional titles/technical terms are not exaggeration; exclude these combinations.
BANNED_EXCEPTIONS = {
    "최고": [r"최고\s*(?:경영|정보|기술|보안|재무|운영|책임|위험|데이터)\s*(?:책임자|자|임원)?",
             r"최고\s*(?:등급|점수|배점|사양|버전)", r"최고\s*[0-9]"],
    # Actual partner/certification grade names are factual ("최상위 파트너 등급"); retain only
    # self-promotional '최상위' uses (최상위의 품질).
    "최상위": [r"최상위\s*(?:파트너\s*)?(?:등급|레벨|티어|인증|자격)"],
    "best": [r"best[\s-]+practices?", r"best[\s-]+effort"],
    "unique": [r"unique\s+(?:id|identifier|key|constraint|index|name|value)s?"],
    "innovative": [r"innovative\s+procurement"],
}


def _mask_exceptions(text: str, word: str) -> str:
    for pat in BANNED_EXCEPTIONS.get(word, []):
        text = re.sub(pat, lambda m: " " * len(m.group(0)), text, flags=re.IGNORECASE)
    return text


def banned_hits(text: str, word: str) -> bool:
    """Match English at word boundaries and Korean/symbol terms by substring. Include hyphens in boundaries to avoid matching 'best' within 'best-in-class' or 'leading' within 'industry-leading' twice. Exclude titles and technical terms (최고정보책임자, best practice, unique identifier)."""
    text = _mask_exceptions(text, word)
    if re.search(r"[A-Za-z]", word):
        return re.search(r"(?<![A-Za-z-])" + re.escape(word) + r"(?![A-Za-z-])",
                         text, re.IGNORECASE) is not None
    return word in text


_XML_ENTITIES = {"&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"', "&apos;": "'"}
# Concatenate same-paragraph runs without spaces so split '최'+'고' still matches
# '최고'; replacing tags with spaces previously caused false passes.
_RUN_RE = re.compile(r"<(?:a:|w:)?t(?:\s[^>]*)?>(.*?)</(?:a:|w:)?t>|<(?:a|w):(?:br|tab)\b[^>]*/?>",
                     re.DOTALL)
_PARA_END_RE = re.compile(r"</(?:a|w):p>|</si>")


def normalize_text(s: str) -> str:
    """Decode entities and normalize all whitespace, including NBSP and full-width spaces, to single spaces."""
    for k, v in _XML_ENTITIES.items():
        s = s.replace(k, v)
    s = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), s)
    s = re.sub(r"&#x([0-9A-Fa-f]+);", lambda m: chr(int(m.group(1), 16)), s)
    return re.sub(r"[\s\u00a0\u3000\u200b\ufeff]+", " ", s).strip()


def xml_text(xml: str) -> str:
    """Extract run text from OOXML fragments; concatenate runs and separate paragraphs with newlines."""
    out: list[str] = []
    pos = 0
    for m in _RUN_RE.finditer(xml):
        # Insert a newline when paragraph end tags separate runs.
        if _PARA_END_RE.search(xml, pos, m.start()):
            out.append("\n")
        out.append(m.group(1) if m.group(1) is not None else " ")
        pos = m.end()
    text = "".join(out)
    if not text.strip():  # Fall back to stripping tags for irregular XML without run tags.
        text = re.sub(r"<[^>]+>", " ", xml)
    return "\n".join(normalize_text(line) for line in text.split("\n") if line.strip())


_CV_RE = re.compile(r"<c:v>(.*?)</c:v>", re.DOTALL)


def chart_text(xml: str) -> str:
    """Extract chart runs (a:t) and cached category/series values (c:v). Previously chart titles selected only the run path and hid old customer names in cached values; inspect values regardless of titles."""
    parts = [xml_text(xml)]
    parts += [v for v in (normalize_text(m.group(1)) for m in _CV_RE.finditer(xml)) if v]
    return "\n".join(p for p in parts if p.strip())


# Minimum package requirements by extension; reject renamed ZIPs and incomplete packages.
# (main part, slide/sheet part regex); relationships and [Content_Types].xml are always required.
REQUIRED_PARTS = {
    ".pptx": ("ppt/presentation.xml", r"ppt/slides/slide\d+\.xml$"),
    ".docx": ("word/document.xml", None),
    ".xlsx": ("xl/workbook.xml", r"xl/worksheets/sheet\d+\.xml$"),
}


def validate_package(z: zipfile.ZipFile, suffix: str) -> None:
    """Verify an actually openable OOXML package structure; otherwise raise KeyError. One filename is insufficient: loaders reject missing [Content_Types].xml, so passing such packages would falsely claim submission readiness."""
    spec = REQUIRED_PARTS.get(suffix)
    if spec is None:
        return
    main, part_pattern = spec
    names = set(z.namelist())
    missing = [n for n in ("[Content_Types].xml", "_rels/.rels", main) if n not in names]
    if missing:
        raise KeyError(f"{suffix} 패키지 필수 파트 없음: {', '.join(missing)} "
                       "(확장자만 바꾼 ZIP이나 손상된 패키지는 검사 대상이 아니다)")
    if part_pattern and not any(re.match(part_pattern, n) for n in names):
        raise KeyError(f"{suffix} 패키지에 본문 파트가 없다 (기대: {part_pattern})")
    bad = z.testzip()
    if bad is not None:
        raise KeyError(f"손상된 ZIP 항목: {bad}")
    # Parse relationship and body parts. Checking only two files let broken slide1.xml or
    # _rels/.rels pass even though the resulting packages could not open.
    targets = [main, "[Content_Types].xml"]
    targets += [n for n in names if n.endswith(".rels")]
    if part_pattern:
        targets += [n for n in names if re.match(part_pattern, n)]
    for name in dict.fromkeys(targets):
        try:
            ET.fromstring(z.read(name))
        except ET.ParseError as exc:
            raise KeyError(f"{name} XML 파싱 실패: {exc}") from exc
        except KeyError as exc:
            raise KeyError(f"{name} 파트를 읽을 수 없다: {exc}") from exc


def load_check(path: Path) -> str | None:
    """Open with the actual loader; return an error reason or None. Catch missing relationships and schema defects missed by validate_package. Used only for final deck_check inspection so synthetic text-extraction fixtures need not depend on loaders. Return None if the library is absent; structural checks already ran."""
    readers = {".pptx": ("pptx", "Presentation"), ".docx": ("docx", "Document"),
               ".xlsx": ("openpyxl", "load_workbook")}
    spec = readers.get(Path(path).suffix.lower())
    if spec is None:
        return None
    module_name, func_name = spec
    try:
        module = __import__(module_name)
    except ImportError:
        return None
    try:
        getattr(module, func_name)(str(path))
    except Exception as exc:  # Loader rejection means the file cannot be submitted.
        return f"{module_name}로 열 수 없는 패키지다: {type(exc).__name__}: {exc}"
    return None


def _num(name: str) -> str:
    m = re.search(r"(\d+)\.xml$", name)
    return m.group(1) if m else "?"


def _sorted_parts(z: zipfile.ZipFile, pattern: str) -> list[str]:
    rx = re.compile(pattern)
    return sorted((n for n in z.namelist() if rx.match(n)),
                  key=lambda n: int(re.search(r"(\d+)\.xml$", n).group(1)))


def _pptx_slide_order(z: zipfile.ZipFile) -> list[str]:
    """Sort slide parts by presentation.xml sldIdLst order (actual slide numbering)."""
    try:
        pres = z.read("ppt/presentation.xml").decode("utf-8", "ignore")
        rels = z.read("ppt/_rels/presentation.xml.rels").decode("utf-8", "ignore")
    except KeyError:
        return _sorted_parts(z, r"ppt/slides/slide\d+\.xml$")
    rid_to_target = {m.group(1): m.group(2) for m in re.finditer(
        r'<Relationship\b[^>]*\bId="([^"]+)"[^>]*\bTarget="([^"]+)"', rels)}
    rid_to_target.update({m.group(2): m.group(1) for m in re.finditer(
        r'<Relationship\b[^>]*\bTarget="([^"]+)"[^>]*\bId="([^"]+)"', rels)})
    ordered = []
    for rid in re.findall(r'<p:sldId\b[^>]*\br:id="([^"]+)"', pres):
        target = rid_to_target.get(rid, "")
        name = "ppt/" + target.lstrip("/").removeprefix("ppt/")
        if name in z.namelist():
            ordered.append(name)
    if not ordered:
        return _sorted_parts(z, r"ppt/slides/slide\d+\.xml$")
    # Append residual slide parts outside sldIdLst for inspection (hidden/orphan slides).
    ordered += [n for n in _sorted_parts(z, r"ppt/slides/slide\d+\.xml$") if n not in ordered]
    return ordered


def extract_labeled_blocks(path: Path) -> list[tuple[str, str]]:
    """Return (location label, text) pairs, including PPTX notes/layouts/masters/charts and DOCX headers/footers/footnotes/endnotes/comments/text boxes. Content invisible in PDF but retained in the package was a major source of false passes."""
    suffix = path.suffix.lower()
    blocks: list[tuple[str, str]] = []
    with zipfile.ZipFile(path) as z:
        validate_package(z, suffix)

        def add(label: str, name: str, extract=xml_text) -> None:
            text = extract(z.read(name).decode("utf-8", "ignore"))
            if text.strip():
                blocks.append((label, text))

        if suffix == ".pptx":
            for i, n in enumerate(_pptx_slide_order(z), 1):
                add(f"슬라이드 {i}", n)
            for n in _sorted_parts(z, r"ppt/notesSlides/notesSlide\d+\.xml$"):
                add(f"노트 {_num(n)}", n)
            for n in _sorted_parts(z, r"ppt/slideLayouts/slideLayout\d+\.xml$"):
                add(f"레이아웃 {_num(n)}", n)
            for n in _sorted_parts(z, r"ppt/slideMasters/slideMaster\d+\.xml$"):
                add(f"마스터 {_num(n)}", n)
            for n in _sorted_parts(z, r"ppt/charts/chart\d+\.xml$"):
                add(f"차트 {_num(n)}", n, chart_text)
            for n in sorted(n for n in z.namelist() if re.match(r"ppt/comments/.*\.xml$", n)):
                add("주석", n)
            core = "docProps/core.xml"
            if core in z.namelist():
                add("문서속성", core)
            return blocks
        if suffix == ".docx":
            body = z.read("word/document.xml").decode("utf-8", "ignore")
            # Split by top-level paragraphs, including nested text-box <w:p>; non-greedy regexes
            # previously stopped at inner paragraphs and discarded trailing content.
            depth, start, idx = 0, -1, 0
            for m in re.finditer(r"<w:p\b[^>]*/>|<w:p\b[^>]*>|</w:p>", body):
                tok = m.group(0)
                if tok.endswith("/>"):
                    continue
                if tok.startswith("</"):
                    depth -= 1
                    if depth == 0 and start >= 0:
                        idx += 1
                        text = xml_text(body[start:m.end()])
                        if text.strip():
                            blocks.append((f"문단 {idx}", text))
                        start = -1
                else:
                    if depth == 0:
                        start = m.start()
                    depth += 1
            if not blocks:
                text = xml_text(body)
                if text.strip():
                    blocks.append(("본문", text))
            for n in _sorted_parts(z, r"word/header\d+\.xml$"):
                add(f"머리말 {_num(n)}", n)
            for n in _sorted_parts(z, r"word/footer\d+\.xml$"):
                add(f"바닥글 {_num(n)}", n)
            for label, n in (("각주", "word/footnotes.xml"), ("미주", "word/endnotes.xml"),
                             ("주석", "word/comments.xml"), ("문서속성", "docProps/core.xml")):
                if n in z.namelist():
                    add(label, n)
            return blocks
        if suffix == ".xlsx":
            shared = []
            if "xl/sharedStrings.xml" in z.namelist():
                ss = z.read("xl/sharedStrings.xml").decode("utf-8", "ignore")
                shared = [xml_text(si) for si in re.findall(r"<si>.*?</si>", ss, re.DOTALL)]
            sheet_names = {}
            if "xl/workbook.xml" in z.namelist():
                wb = z.read("xl/workbook.xml").decode("utf-8", "ignore")
                for i, m in enumerate(re.finditer(r'<sheet\b[^>]*\bname="([^"]+)"', wb), 1):
                    sheet_names[i] = normalize_text(m.group(1))
            for n in _sorted_parts(z, r"xl/worksheets/sheet\d+\.xml$"):
                i = int(re.search(r"(\d+)\.xml$", n).group(1))
                xml = z.read(n).decode("utf-8", "ignore")
                cells: list[str] = []
                for cm in re.finditer(r'<c\b([^>]*)>(.*?)</c>', xml, re.DOTALL):
                    attrs, inner = cm.group(1), cm.group(2)
                    if 't="s"' in attrs:
                        v = re.search(r"<v>(\d+)</v>", inner)
                        if v and int(v.group(1)) < len(shared):
                            cells.append(shared[int(v.group(1))])
                    elif 't="inlineStr"' in attrs or "<is>" in inner:
                        cells.append(xml_text(inner))
                    elif 't="str"' in attrs:
                        v = re.search(r"<v>(.*?)</v>", inner, re.DOTALL)
                        if v:
                            cells.append(normalize_text(v.group(1)))
                text = "\n".join(c for c in cells if c)
                if text.strip():
                    blocks.append((f"시트 {sheet_names.get(i, i)}", text))
            for n in _sorted_parts(z, r"xl/comments\d+\.xml$"):
                add("주석", n)
            if "docProps/core.xml" in z.namelist():
                add("문서속성", "docProps/core.xml")
            return blocks
    raise ValueError(f"지원하지 않는 형식: {path.suffix} (pptx/docx/xlsx만 지원)")


def extract_blocks(path: Path) -> list[str]:
    """Backward compatibility: return text blocks without labels."""
    return [t for _, t in extract_labeled_blocks(path)]


def extract_colors(path: Path) -> tuple[set[str], bool]:
    if path.suffix.lower() != ".pptx":
        return set(), False
    colors: set[str] = set()
    unresolved_theme = False
    with zipfile.ZipFile(path) as z:
        for n in z.namelist():
            if not n.endswith(".xml") or not n.startswith("ppt/"):
                continue
            xml = z.read(n).decode("utf-8", "ignore")
            if n.startswith(("ppt/slides/", "ppt/charts/", "ppt/diagrams/")):
                colors.update(c.upper() for c in
                              re.findall(r'srgbClr val="([0-9A-Fa-f]{6})"', xml))
            if n.startswith(("ppt/theme/", "ppt/slideLayouts/", "ppt/slideMasters/")) \
                    or "schemeClr" in xml:
                unresolved_theme = True
    return colors, unresolved_theme


def read_names(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8-sig").splitlines()
            if line.strip()]


def run(path: Path, names: list[str], palette: set[str], lang: str,
        stage: str = "submission") -> list[str]:
    """Return all findings as strings. WARNING_PREFIXES identify nonblocking warnings excluded from exit-code decisions; blocking() decides blocker status."""
    raw = {"ko": BANNED_KO, "en": BANNED_EN, "both": BANNED_KO + BANNED_EN}[lang]
    banned = list(dict.fromkeys(raw))  # Deduplicate while preserving order, avoiding duplicate '100%' reports in both mode.
    slop = {"ko": AI_SLOP_KO, "en": AI_SLOP_EN, "both": AI_SLOP_KO + AI_SLOP_EN}[lang]
    fails: list[str] = []
    blocks = extract_labeled_blocks(path)
    if not blocks:
        fails.append("[NOT INSPECTED] 추출된 텍스트 없음 — 이미지 전용 문서는 렌더 검사 필수")
    for loc, block in blocks:
        low = block.lower()
        for w in banned:
            if banned_hits(block, w):
                fails.append(f"[과장어] {loc}: '{w}' — 근거가 있어도 사람 승인 필요")
        for phrase in slop:
            if phrase.lower() in low:
                fails.append(f"[AI문체] {loc}: '{phrase}' — 구체 근거·수치로 대체")
        if lang in ("ko", "both"):
            for sentence in ambiguous_commitments(block):
                fails.append(f"[모호확약] {loc}: '{sentence[:60]}' — 주체·범위·시점·조건을 붙인다")
        for p in PLACEHOLDERS:
            if p.lower() in low:
                fails.append(f"[플레이스홀더] {loc}: '{p}' 잔존")
        for m in DRAFT_MARKERS:
            if m in low:
                if stage == "submission":
                    fails.append(f"[플레이스홀더] {loc}: 미확정 마커('{m}') 잔존 — 제출 전 해결 필요")
                else:
                    fails.append(f"[검토필요] {loc}: 미확정 마커('{m}') — 초안 허용, 제출 전 해결")
        for name in names:
            if name and _name_in(name, block):
                fails.append(f"[금지 명칭] {loc}: '{name}' 잔존 — 즉시 탈락 사유")
    if palette:
        allowed = palette | {"FFFFFF", "000000"}
        colors, unresolved_theme = extract_colors(path)
        for c in sorted(colors - allowed):
            fails.append(f"[팔레트 일탈] 허용 목록 외 색상 #{c}")
        if unresolved_theme:
            # Generator theme schemeClr has no automatically known final HEX; issue nonblocking warnings.
            fails.append("[NOT INSPECTED] 테마·마스터·레이아웃·차트 색상은 최종 HEX 해석 필요")
    return fails


def _name_in(name: str, block: str) -> bool:
    """Match forbidden names ignoring case and whitespace ('ABC 은행' ≒ 'ABC은행', 'abc bank' ≒ 'ABC Bank')."""
    squash = lambda t: re.sub(r"\s+", "", t).lower()  # noqa: E731
    key = squash(name)
    return bool(key) and key in squash(block)


def blocking(items: list[str]) -> list[str]:
    """Return actual blockers, excluding nonblocking WARNING_PREFIXES warnings."""
    return [f for f in items if not f.startswith(WARNING_PREFIXES)]


def _utf8_console() -> None:
    """Prevent valid documents becoming BLOCKED when Korean Windows cp949 consoles raise UnicodeEncodeError while printing characters such as '—'."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main() -> int:
    _utf8_console()
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", type=Path)
    ap.add_argument("--names", type=Path, help="Forbidden-name list to inspect for residual content (one per line)")
    ap.add_argument("--palette", help="Comma-separated allowed color HEX values (skip color checks if omitted)")
    ap.add_argument("--lang", choices=["ko", "en", "both"], default="ko",
                    help="Exaggerated-language dictionary language (default ko)")
    ap.add_argument("--stage", choices=["draft", "submission"], default="submission",
                    help="draft: allow unresolved markers as warnings / submission (default): block")
    a = ap.parse_args()
    if not a.file.is_file():
        print(f"파일 없음: {a.file}", file=sys.stderr); return 2
    if a.names and not a.names.is_file():
        print(f"금지 명칭 파일 없음: {a.names}", file=sys.stderr); return 2
    names = read_names(a.names) if a.names else []
    palette = {c.strip().upper().lstrip("#") for c in a.palette.split(",") if c.strip()} \
        if a.palette else set()
    if palette and any(not re.fullmatch(r"[0-9A-F]{6}", c) for c in palette):
        print(f"팔레트 형식 오류(6자리 hex만): {sorted(palette)}", file=sys.stderr); return 2
    try:
        items = run(a.file, names, palette, a.lang, a.stage)
    except (ValueError, zipfile.BadZipFile, KeyError, OSError) as e:
        print(f"검사 불가(파일 형식·손상): {e}", file=sys.stderr); return 2
    blockers = blocking(items)
    warnings = [f for f in items if f.startswith(WARNING_PREFIXES)]
    for w in warnings:
        print("  경고:", w)
    if blockers:
        print(f"차단 — {len(blockers)}건"); [print(" -", f) for f in blockers]; return 1
    print("통과 (기계 검사 항목 한정 — 리드문 스토리·일관성·렌더 확인은 별도 수행)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
