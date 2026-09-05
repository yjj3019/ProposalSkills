#!/usr/bin/env python3
"""제안서 기계 검수 게이트 — review-checklist.md 중 자동화 가능한 항목을 검사한다.

사용법:
    python3 quality_gate.py 제안서.pptx [--names 금지명단.txt]
        [--palette "1F3864,8FAADC,..."] [--lang ko|en|both] [--stage draft|submission]

검사 항목:
  1. 과장어(근거가 있어도 사람 검토)   3. 잔존 금지 명칭(이전 고객사 등)
  2. 플레이스홀더/미확정 마커 잔존       4. 팔레트 일탈(허용 색 외 사용, PPTX만)
검사 범위: PPTX 슬라이드·노트·레이아웃·마스터·차트·주석, DOCX 본문(텍스트박스 포함)·
  머리말·바닥글·각주·미주·주석, XLSX 셀·주석, 문서속성. 렌더에 안 보이는 영역 포함.
--lang: 과장어 사전 언어 선택(기본 ko). 영문 제안은 en, 이중언어는 both.
--stage: draft=미확정 마커([NEEDS INPUT]·입력요망)를 비차단 경고로 허용,
         submission(기본)=차단. 생성 도구 테마색 NOT INSPECTED는 항상 비차단 경고다.
종료 코드: 0=통과(경고만 있을 수 있음), 1=차단(차단 목록 출력), 2=사용 오류·검사 불가.
판정은 기계 검사일 뿐이며, 문장 맥락·설득력·법적 적정성은 사람이 검토한다.
"""
from __future__ import annotations
import argparse, re, sys, xml.etree.ElementTree as ET, zipfile
from pathlib import Path

BANNED_KO = ["최고", "완벽", "혁신적", "획기적", "100%", "무중단", "완전 자동화",
             "위험 제로", "유일한", "업계 1위"]
# 영문 관용 과장어(writing-style.md 영문 금지어 사전과 동기화). 단어 경계로 매칭한다.
BANNED_EN = ["best-in-class", "best", "world-class", "industry-leading", "market-leading",
             "leading provider", "leading solution",
             "unique", "perfect", "flawless", "innovative", "revolutionary",
             "cutting-edge", "state-of-the-art", "next-generation", "100%",
             "zero downtime", "zero risk", "fully automated", "fully compliant",
             "seamless", "effortless", "guarantee", "guaranteed", "guarantees",
             "guaranteeing", "bulletproof", "future-proof",
             "unlimited", "significant savings"]
PLACEHOLDERS = ["lorem", "xxxx", "TBD", "샘플텍스트", "placeholder", "OOO", "○○○", "p.__", "p. __", "p.XX"]
# 초안 단계 사실 슬롯 마커. 제출 단계에서는 차단(placeholder), 초안 단계에서는 경고(비차단).
# 스킬 권장 마커([NEEDS INPUT]·［입력요망］)를 게이트가 스스로 차단하던 자기충돌을 해소한다.
# '○○공사'류 익명 발주처 표기는 초안 관례이므로 draft=경고, submission=차단.
DRAFT_MARKERS = ["needs input", "입력요망", "○○", "[unverified]", "미정"]
# S7: AI-slop 최소 패턴(빈 수사·템플릿 티). 과장어와 별도. 부분 문자열 매칭.
AI_SLOP_KO = [
    "다양한 측면에서", "종합적인 솔루션", "시너지를 창출", "최적의 방안을 제시",
    "고객 맞춤형 서비스 제공", "차별화된 경쟁력", "원스톱",
]
AI_SLOP_EN = [
    "in today's fast-paced", "leverage synergies", "holistic solution",
    "delve into", "it is important to note", "game-changer", "unlock the potential",
]
# 아래 접두사로 시작하는 항목은 '비차단 경고'다(종료코드에 반영하지 않는다).
WARNING_PREFIXES = ("[NOT INSPECTED]", "[검토필요]")


# 과장어가 아닌 관용 결합(직함·기술 용어). 해당 결합은 과장어 매칭에서 제외한다.
BANNED_EXCEPTIONS = {
    "최고": [r"최고\s*(?:경영|정보|기술|보안|재무|운영|책임|위험|데이터)\s*(?:책임자|자|임원)?",
             r"최고\s*(?:등급|점수|배점|사양|버전)", r"최고\s*[0-9]"],
    "best": [r"best[\s-]+practices?", r"best[\s-]+effort"],
    "unique": [r"unique\s+(?:id|identifier|key|constraint|index|name|value)s?"],
    "innovative": [r"innovative\s+procurement"],
}


def _mask_exceptions(text: str, word: str) -> str:
    for pat in BANNED_EXCEPTIONS.get(word, []):
        text = re.sub(pat, lambda m: " " * len(m.group(0)), text, flags=re.IGNORECASE)
    return text


def banned_hits(text: str, word: str) -> bool:
    """영문은 단어 경계로, 한국어·기호 포함어는 부분 문자열로 매칭한다.
    경계에 하이픈 포함 — 'best-in-class' 안의 'best', 'industry-leading' 안의
    'leading'이 이중 검출되지 않게 한다(복합어는 자체 항목으로 검사).
    직함·기술 용어(최고정보책임자, best practice, unique identifier)는 제외한다."""
    text = _mask_exceptions(text, word)
    if re.search(r"[A-Za-z]", word):
        return re.search(r"(?<![A-Za-z-])" + re.escape(word) + r"(?![A-Za-z-])",
                         text, re.IGNORECASE) is not None
    return word in text


_XML_ENTITIES = {"&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"', "&apos;": "'"}
# 텍스트 run 요소. 같은 문단의 run은 공백 없이 이어 붙인다 — '최'+'고'가 run으로
# 갈라져도 '최고'로 매칭되게 한다(태그를 공백으로 치환하던 방식의 허위 통과 해소).
_RUN_RE = re.compile(r"<(?:a:|w:)?t(?:\s[^>]*)?>(.*?)</(?:a:|w:)?t>|<(?:a|w):(?:br|tab)\b[^>]*/?>",
                     re.DOTALL)
_PARA_END_RE = re.compile(r"</(?:a|w):p>|</si>")


def normalize_text(s: str) -> str:
    """엔티티 복원 + 모든 공백류(NBSP·전각공백 포함)를 단일 공백으로 정규화."""
    for k, v in _XML_ENTITIES.items():
        s = s.replace(k, v)
    s = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), s)
    s = re.sub(r"&#x([0-9A-Fa-f]+);", lambda m: chr(int(m.group(1), 16)), s)
    return re.sub(r"[\s\u00a0\u3000\u200b\ufeff]+", " ", s).strip()


def xml_text(xml: str) -> str:
    """OOXML 조각에서 run 텍스트만 추출. run은 붙이고, 문단 경계는 줄바꿈."""
    out: list[str] = []
    pos = 0
    for m in _RUN_RE.finditer(xml):
        # 문단 종결 태그가 사이에 있으면 줄바꿈 삽입
        if _PARA_END_RE.search(xml, pos, m.start()):
            out.append("\n")
        out.append(m.group(1) if m.group(1) is not None else " ")
        pos = m.end()
    text = "".join(out)
    if not text.strip():  # run 태그가 없는 비정형 XML은 태그 제거로 폴백
        text = re.sub(r"<[^>]+>", " ", xml)
    return "\n".join(normalize_text(line) for line in text.split("\n") if line.strip())


_CV_RE = re.compile(r"<c:v>(.*?)</c:v>", re.DOTALL)


def chart_text(xml: str) -> str:
    """차트 파트 전용 추출 — run(a:t)에 더해 캐시된 범주·계열 값(c:v)까지 읽는다.

    차트에 제목이 있으면 a:t run이 존재해 xml_text가 run 경로만 타고, 범주·계열에
    남은 이전 고객명(c:v)을 놓쳤다. 제목 유무와 무관하게 값까지 읽는다.
    """
    parts = [xml_text(xml)]
    parts += [v for v in (normalize_text(m.group(1)) for m in _CV_RE.finditer(xml)) if v]
    return "\n".join(p for p in parts if p.strip())


# 확장자별 최소 요건 — 이름만 .pptx인 ZIP이나 파트가 빠진 반쪽 패키지를 통과시키지 않는다.
# (main part, 슬라이드/시트 파트 정규식) — 관계 파트와 [Content_Types].xml은 공통 필수.
REQUIRED_PARTS = {
    ".pptx": ("ppt/presentation.xml", r"ppt/slides/slide\d+\.xml$"),
    ".docx": ("word/document.xml", None),
    ".xlsx": ("xl/workbook.xml", r"xl/worksheets/sheet\d+\.xml$"),
}


def validate_package(z: zipfile.ZipFile, suffix: str) -> None:
    """OOXML 패키지로서 실제 열 수 있는 구조인지 확인한다. 아니면 KeyError.

    파일명 하나의 존재 확인과 '정상 패키지'는 다르다. python-pptx 같은 로더는
    [Content_Types].xml이 없으면 열기를 거부하는데, 게이트가 그런 파일을 검사해
    통과시키면 열리지도 않는 산출물이 제출 준비로 올라간다.
    """
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
    for name in (main, "[Content_Types].xml"):
        try:
            ET.fromstring(z.read(name))
        except ET.ParseError as exc:
            raise KeyError(f"{name} XML 파싱 실패: {exc}") from exc


def _num(name: str) -> str:
    m = re.search(r"(\d+)\.xml$", name)
    return m.group(1) if m else "?"


def _sorted_parts(z: zipfile.ZipFile, pattern: str) -> list[str]:
    rx = re.compile(pattern)
    return sorted((n for n in z.namelist() if rx.match(n)),
                  key=lambda n: int(re.search(r"(\d+)\.xml$", n).group(1)))


def _pptx_slide_order(z: zipfile.ZipFile) -> list[str]:
    """presentation.xml의 sldIdLst 순서(실제 슬라이드 번호)로 slide 파트를 정렬한다."""
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
    # sldIdLst에 없는 잔존 slide 파트도 뒤에 붙여 검사한다(숨김·고아 슬라이드).
    ordered += [n for n in _sorted_parts(z, r"ppt/slides/slide\d+\.xml$") if n not in ordered]
    return ordered


def extract_labeled_blocks(path: Path) -> list[tuple[str, str]]:
    """(위치 라벨, 텍스트) 목록. 본문뿐 아니라 노트·레이아웃·마스터·차트(PPTX),
    머리말·바닥글·각주·미주·주석·텍스트박스(DOCX)까지 포함한다 — PDF 렌더에는
    안 보여도 원본 패키지에 남는 영역이 허위 통과의 주 경로였다."""
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
            # 최상위 문단 단위(중첩 텍스트박스 <w:p> 포함)로 분리 — 비탐욕 정규식이
            # 내부 문단에서 끊겨 뒷부분을 버리던 결함을 해소한다.
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
    """하위 호환: 라벨 없는 텍스트 블록 목록."""
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
    """모든 발견 항목을 문자열 리스트로 반환한다. WARNING_PREFIXES로 시작하는 항목은
    '비차단 경고'이며 종료코드에 반영되지 않는다(차단 여부는 blocking()이 판정)."""
    raw = {"ko": BANNED_KO, "en": BANNED_EN, "both": BANNED_KO + BANNED_EN}[lang]
    banned = list(dict.fromkeys(raw))  # 중복 제거(both의 '100%' 이중 리포트 방지), 순서 유지
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
            # 생성 도구 기본 테마의 schemeClr는 최종 HEX를 자동 판정할 수 없다 → 비차단 경고.
            fails.append("[NOT INSPECTED] 테마·마스터·레이아웃·차트 색상은 최종 HEX 해석 필요")
    return fails


def _name_in(name: str, block: str) -> bool:
    """금지 명칭 매칭: 대소문자·공백 무시('ABC 은행' ≒ 'ABC은행', 'abc bank' ≒ 'ABC Bank')."""
    squash = lambda t: re.sub(r"\s+", "", t).lower()  # noqa: E731
    key = squash(name)
    return bool(key) and key in squash(block)


def blocking(items: list[str]) -> list[str]:
    """비차단 경고(WARNING_PREFIXES)를 제외한 실제 차단 항목만 반환한다."""
    return [f for f in items if not f.startswith(WARNING_PREFIXES)]


def _utf8_console() -> None:
    """한국어 Windows(cp949) 콘솔에서 '—' 등 출력 중 UnicodeEncodeError로 죽어
    정상 문서가 BLOCKED 처리되던 결함 방지."""
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
    ap.add_argument("--names", type=Path, help="잔존 검사할 금지 명칭 목록(줄당 1개)")
    ap.add_argument("--palette", help="허용 색상 hex 콤마 목록(미지정 시 색 검사 생략)")
    ap.add_argument("--lang", choices=["ko", "en", "both"], default="ko",
                    help="과장어 사전 언어(기본 ko)")
    ap.add_argument("--stage", choices=["draft", "submission"], default="submission",
                    help="draft: 미확정 마커를 경고로 허용 / submission(기본): 차단")
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
