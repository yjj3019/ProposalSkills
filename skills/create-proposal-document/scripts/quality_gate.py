#!/usr/bin/env python3
"""제안서 기계 검수 게이트 — review-checklist.md 중 자동화 가능한 항목을 검사한다.

사용법:
    python3 quality_gate.py 제안서.pptx [--names 금지명단.txt]
        [--palette "1F3864,8FAADC,..."] [--lang ko|en|both]

검사 항목:
  1. 과장어(근거 태그 없이 사용)      3. 잔존 금지 명칭(이전 고객사 등)
  2. 플레이스홀더 잔존                 4. 팔레트 일탈(허용 색 외 사용, PPTX만)
--lang: 과장어 사전 언어 선택(기본 ko). 영문 제안은 en, 이중언어는 both.
종료 코드: 0=통과, 1=차단(실패 목록 출력), 2=사용 오류.
판정은 기계 검사일 뿐이며, 문장 맥락·설득력·법적 적정성은 사람이 검토한다.
"""
from __future__ import annotations
import argparse, re, sys, zipfile
from pathlib import Path

BANNED_KO = ["최고", "완벽", "혁신적", "획기적", "100%", "무중단", "완전 자동화",
             "위험 제로", "유일한", "업계 1위"]
# 영문 관용 과장어(writing-style.md 영문 금지어 사전과 동기화). 단어 경계로 매칭한다.
BANNED_EN = ["best-in-class", "best", "world-class", "industry-leading", "leading",
             "unique", "perfect", "flawless", "innovative", "revolutionary",
             "cutting-edge", "state-of-the-art", "next-generation", "100%",
             "zero downtime", "zero risk", "fully automated", "fully compliant",
             "seamless", "effortless", "guarantee", "guaranteed", "guarantees",
             "guaranteeing", "bulletproof", "future-proof",
             "unlimited", "significant savings"]
PLACEHOLDERS = ["lorem", "xxxx", "TBD", "샘플텍스트", "placeholder", "OOO", "○○○",
                "[]", "NEEDS INPUT"]
# 같은 텍스트 블록에 근거 표기가 있으면 과장어를 허용한다(스킬 규칙: 근거 병기 시 사용 가능)
EVIDENCE_MARKS = ["출처", "기준", "근거", "산식", "전제", "인용",
                  "source", "evidence", "baseline", "verified", "measured"]


def banned_hits(text: str, word: str) -> bool:
    """영문은 단어 경계로, 한국어·기호 포함어는 부분 문자열로 매칭한다.
    경계에 하이픈 포함 — 'best-in-class' 안의 'best', 'industry-leading' 안의
    'leading'이 이중 검출되지 않게 한다(복합어는 자체 항목으로 검사)."""
    if re.search(r"[A-Za-z]", word):
        return re.search(r"(?<![A-Za-z-])" + re.escape(word) + r"(?![A-Za-z-])",
                         text, re.IGNORECASE) is not None
    return word in text


def extract_blocks(path: Path) -> list[str]:
    """근거 병기 판정은 '같은 블록' 단위다.
    PPTX는 슬라이드별, DOCX는 문단(<w:p>)별로 쪼갠다 — 문서 전체를 1블록으로 보면
    근거어 1회가 문서 내 모든 과장어를 면제하는 과잉 관용이 생기므로 문단 단위로 정밀화."""
    with zipfile.ZipFile(path) as z:
        if path.suffix.lower() == ".pptx":
            names = sorted(n for n in z.namelist()
                           if re.match(r"ppt/slides/slide\d+\.xml$", n))
            return [re.sub(r"<[^>]+>", " ", z.read(n).decode("utf-8", "ignore"))
                    for n in names]
        if path.suffix.lower() == ".docx":
            xml = z.read("word/document.xml").decode("utf-8", "ignore")
            paras = re.findall(r"<w:p[ >].*?</w:p>", xml, re.DOTALL)
            blocks = [re.sub(r"<[^>]+>", " ", p) for p in paras]
            return [b for b in blocks if b.strip()] or [re.sub(r"<[^>]+>", " ", xml)]
    raise ValueError(f"지원하지 않는 형식: {path.suffix}")


def extract_colors(path: Path) -> set[str]:
    if path.suffix.lower() != ".pptx":
        return set()
    colors: set[str] = set()
    with zipfile.ZipFile(path) as z:
        for n in z.namelist():
            if re.match(r"ppt/slides/slide\d+\.xml$", n):
                xml = z.read(n).decode("utf-8", "ignore")
                colors.update(c.upper() for c in
                              re.findall(r'srgbClr val="([0-9A-Fa-f]{6})"', xml))
    return colors


def run(path: Path, names: list[str], palette: set[str], lang: str) -> list[str]:
    raw = {"ko": BANNED_KO, "en": BANNED_EN, "both": BANNED_KO + BANNED_EN}[lang]
    banned = list(dict.fromkeys(raw))  # 중복 제거(both의 '100%' 이중 리포트 방지), 순서 유지
    is_pptx = path.suffix.lower() == ".pptx"
    fails: list[str] = []
    blocks = extract_blocks(path)
    for i, block in enumerate(blocks, 1):
        loc = (f"슬라이드 {i}" if is_pptx else f"문단 {i}") if len(blocks) > 1 else "본문"
        low = block.lower()
        has_evidence = any(m.lower() in low for m in EVIDENCE_MARKS)
        for w in banned:
            if banned_hits(block, w) and not has_evidence:
                fails.append(f"[과장어] {loc}: '{w}' — 같은 블록에 근거 표기 없음")
        for p in PLACEHOLDERS:
            if p.lower() in low:
                fails.append(f"[플레이스홀더] {loc}: '{p}' 잔존")
        for name in names:
            if name and name in block:
                fails.append(f"[금지 명칭] {loc}: '{name}' 잔존 — 즉시 탈락 사유")
    if palette:
        allowed = palette | {"FFFFFF", "000000"}
        for c in sorted(extract_colors(path) - allowed):
            fails.append(f"[팔레트 일탈] 허용 목록 외 색상 #{c}")
    return fails


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("file", type=Path)
    ap.add_argument("--names", type=Path, help="잔존 검사할 금지 명칭 목록(줄당 1개)")
    ap.add_argument("--palette", help="허용 색상 hex 콤마 목록(미지정 시 색 검사 생략)")
    ap.add_argument("--lang", choices=["ko", "en", "both"], default="ko",
                    help="과장어 사전 언어(기본 ko)")
    a = ap.parse_args()
    if not a.file.is_file():
        print(f"파일 없음: {a.file}", file=sys.stderr); return 2
    names = a.names.read_text(encoding="utf-8").split() if a.names else []
    palette = {c.strip().upper().lstrip("#") for c in a.palette.split(",")} if a.palette else set()
    fails = run(a.file, names, palette, a.lang)
    if fails:
        print(f"차단 — {len(fails)}건"); [print(" -", f) for f in fails]; return 1
    print("통과 (기계 검사 항목 한정 — 리드문 스토리·일관성·렌더 확인은 별도 수행)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
