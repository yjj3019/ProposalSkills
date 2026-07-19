#!/usr/bin/env python3
"""제안서 기계 검수 게이트 — review-checklist.md 중 자동화 가능한 항목을 검사한다.

사용법:
    python3 quality_gate.py 제안서.pptx [--names 금지명단.txt]
        [--palette "1F3864,8FAADC,..."] [--lang ko|en|both] [--stage draft|submission]

검사 항목:
  1. 과장어(근거가 있어도 사람 검토)   3. 잔존 금지 명칭(이전 고객사 등)
  2. 플레이스홀더/미확정 마커 잔존       4. 팔레트 일탈(허용 색 외 사용, PPTX만)
--lang: 과장어 사전 언어 선택(기본 ko). 영문 제안은 en, 이중언어는 both.
--stage: draft=미확정 마커([NEEDS INPUT]·입력요망)를 비차단 경고로 허용,
         submission(기본)=차단. 생성 도구 테마색 NOT INSPECTED는 항상 비차단 경고다.
종료 코드: 0=통과(경고만 있을 수 있음), 1=차단(차단 목록 출력), 2=사용 오류.
판정은 기계 검사일 뿐이며, 문장 맥락·설득력·법적 적정성은 사람이 검토한다.
"""
from __future__ import annotations
import argparse, re, sys, zipfile
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
PLACEHOLDERS = ["lorem", "xxxx", "TBD", "샘플텍스트", "placeholder", "OOO", "○○○"]
# 초안 단계 사실 슬롯 마커. 제출 단계에서는 차단(placeholder), 초안 단계에서는 경고(비차단).
# 스킬 권장 마커([NEEDS INPUT]·［입력요망］)를 게이트가 스스로 차단하던 자기충돌을 해소한다.
DRAFT_MARKERS = ["needs input", "입력요망"]
# 아래 접두사로 시작하는 항목은 '비차단 경고'다(종료코드에 반영하지 않는다).
WARNING_PREFIXES = ("[NOT INSPECTED]", "[검토필요]")


def banned_hits(text: str, word: str) -> bool:
    """영문은 단어 경계로, 한국어·기호 포함어는 부분 문자열로 매칭한다.
    경계에 하이픈 포함 — 'best-in-class' 안의 'best', 'industry-leading' 안의
    'leading'이 이중 검출되지 않게 한다(복합어는 자체 항목으로 검사)."""
    if re.search(r"[A-Za-z]", word):
        return re.search(r"(?<![A-Za-z-])" + re.escape(word) + r"(?![A-Za-z-])",
                         text, re.IGNORECASE) is not None
    return word in text


def extract_blocks(path: Path) -> list[str]:
    """PPTX는 슬라이드별, DOCX는 문단(<w:p>)별로 텍스트를 추출한다."""
    with zipfile.ZipFile(path) as z:
        if path.suffix.lower() == ".pptx":
            names = sorted((n for n in z.namelist()
                            if re.match(r"ppt/slides/slide\d+\.xml$", n)),
                           key=lambda n: int(re.search(r"slide(\d+)\.xml$", n).group(1)))
            return [re.sub(r"<[^>]+>", " ", z.read(n).decode("utf-8", "ignore"))
                    for n in names]
        if path.suffix.lower() == ".docx":
            xml = z.read("word/document.xml").decode("utf-8", "ignore")
            paras = re.findall(r"<w:p[ >].*?</w:p>", xml, re.DOTALL)
            blocks = [re.sub(r"<[^>]+>", " ", p) for p in paras]
            return [b for b in blocks if b.strip()] or [re.sub(r"<[^>]+>", " ", xml)]
    raise ValueError(f"지원하지 않는 형식: {path.suffix}")


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
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def run(path: Path, names: list[str], palette: set[str], lang: str,
        stage: str = "submission") -> list[str]:
    """모든 발견 항목을 문자열 리스트로 반환한다. WARNING_PREFIXES로 시작하는 항목은
    '비차단 경고'이며 종료코드에 반영되지 않는다(차단 여부는 blocking()이 판정)."""
    raw = {"ko": BANNED_KO, "en": BANNED_EN, "both": BANNED_KO + BANNED_EN}[lang]
    banned = list(dict.fromkeys(raw))  # 중복 제거(both의 '100%' 이중 리포트 방지), 순서 유지
    is_pptx = path.suffix.lower() == ".pptx"
    fails: list[str] = []
    blocks = extract_blocks(path)
    for i, block in enumerate(blocks, 1):
        loc = (f"슬라이드 {i}" if is_pptx else f"문단 {i}") if len(blocks) > 1 else "본문"
        low = block.lower()
        for w in banned:
            if banned_hits(block, w):
                fails.append(f"[과장어] {loc}: '{w}' — 근거가 있어도 사람 승인 필요")
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
            if name and name in block:
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


def blocking(items: list[str]) -> list[str]:
    """비차단 경고(WARNING_PREFIXES)를 제외한 실제 차단 항목만 반환한다."""
    return [f for f in items if not f.startswith(WARNING_PREFIXES)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
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
    names = read_names(a.names) if a.names else []
    palette = {c.strip().upper().lstrip("#") for c in a.palette.split(",")} if a.palette else set()
    items = run(a.file, names, palette, a.lang, a.stage)
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
