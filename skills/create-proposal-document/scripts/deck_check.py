#!/usr/bin/env python3
"""Proposal PPTX layout lint and render checks (automating review-checklist items 7 and 8).

Usage:
    python3 deck_check.py 제안서.pptx [--max-pages 40] [--exclude-cover-toc]
        [--render] [--png-dir out/] [--emit-render render.json] [--min-font PT]
        [--require-req-ids] [--stage draft|submission] [--profile 규격]

Always lint with python-pptx: page limit, body lead presence and length, REQ-IDs, titles, body minimum font excluding captions/headers/footers, text density including tables, table headers and row limits, empty or image-only slides. Font, density, and row limits come from deck_profiles.py. Read the PPTX profile stamp automatically or override with --profile; missing or unknown stamps block submission rather than silently selecting permissive defaults. Generated decks use named shapes; external decks use positional heuristics and are marked [휴리스틱].

--render requires LibreOffice: soffice → PDF → page count comparison → optional PNG thumbnails via --png-dir. Missing soffice records NOT INSPECTED; never assume a pass.

--emit-render writes the audit render block:
  {"verified": bool, "artifact_hash": "sha256:…", "tool": "…", "evidence": [...]}
verified is true only after successful rendering with no blockers.
Exit codes: 0=pass (warnings possible), 1=blocked, 2=usage error or damaged file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deck_profiles
import quality_gate

try:
    import color_contrast
    from pptx import Presentation
    from pptx.util import Emu
except ImportError:  # pragma: no cover
    print("python-pptx가 필요합니다: pip install python-pptx", file=sys.stderr)
    raise SystemExit(2)

# Defaults come from deck_profiles; lint() receives the actual profile criteria.
# Generator and checker share one definition to prevent numerical drift.
_DEFAULT = deck_profiles.get(deck_profiles.DEFAULT_PROFILE)
LEAD_MAX = _DEFAULT["lead_max_chars"]
DENSITY_MAX = _DEFAULT["density_max"]
TABLE_ROWS_MAX = _DEFAULT["table_rows_max"]
REQ_RE = re.compile(r"(?:REQ[-_ ]?\d+|\bR\d{1,3}\b|요구\s*[:：]\s*\S|대응\s*요구)", re.IGNORECASE)
WARN = "[경고]"
NOTE = "[NOT INSPECTED]"
BLOCK_PREFIXES = ("[차단]",)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def shape_text(shape) -> str:
    """Visible shape text, including GraphicFrame table cells. Tables lack text frames, so previously their text vanished from density counts and dense matrices appeared empty."""
    if shape.has_text_frame:
        return "\n".join(p.text for p in shape.text_frame.paragraphs).strip()
    if getattr(shape, "has_table", False) and shape.has_table:
        return "\n".join(cell.text for row in shape.table.rows for cell in row.cells).strip()
    return ""


def iter_shapes(shapes):
    for sh in shapes:
        if sh.shape_type == 6 and hasattr(sh, "shapes"):  # GROUP
            yield from iter_shapes(sh.shapes)
        else:
            yield sh


def _group_transform(group) -> tuple[float, float, float, float] | None:
    """Return group (offset_x, offset_y, scale_x, scale_y), or None if unreadable. Child left/top use local chOff/chExt coordinates; comparing without transformation misclassifies on-slide and off-slide shapes."""
    try:
        xfrm = group.element.find(
            "{http://schemas.openxmlformats.org/presentationml/2006/main}grpSpPr").find(
            "{http://schemas.openxmlformats.org/drawingml/2006/main}xfrm")
        a = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
        off, ext = xfrm.find(a + "off"), xfrm.find(a + "ext")
        ch_off, ch_ext = xfrm.find(a + "chOff"), xfrm.find(a + "chExt")
        cx, cy = int(ch_ext.get("cx")), int(ch_ext.get("cy"))
        if not cx or not cy:
            return None
        sx, sy = int(ext.get("cx")) / cx, int(ext.get("cy")) / cy
        return (int(off.get("x")) - int(ch_off.get("x")) * sx,
                int(off.get("y")) - int(ch_off.get("y")) * sy, sx, sy)
    except (AttributeError, TypeError, ValueError):
        return None


def placed_shapes(shapes, transform=(0.0, 0.0, 1.0, 1.0)):
    """Yield (shape, slide-coordinate left/top/width/height), accumulating group transforms."""
    ox, oy, sx, sy = transform
    for sh in shapes:
        if sh.shape_type == 6 and hasattr(sh, "shapes"):  # GROUP
            inner = _group_transform(sh)
            if inner is None:
                # If transforms cannot be read, inspect only the group box instead of measuring
                # children with incorrect coordinates.
                continue
            gx, gy, gsx, gsy = inner
            yield from placed_shapes(sh.shapes,
                                     (ox + gx * sx, oy + gy * sy, sx * gsx, sy * gsy))
            continue
        try:
            box = (ox + int(sh.left) * sx, oy + int(sh.top) * sy,
                   int(sh.width) * sx, int(sh.height) * sy)
        except (TypeError, ValueError):
            continue  # Skip shapes whose coordinates cannot be read, such as inherited placeholders.
        yield sh, box


def slide_kind(slide) -> str:
    names = {sh.name for sh in iter_shapes(slide.shapes)}
    if "COVER_BAND" in names and "SUBTITLE" in names:
        return "cover"
    if "COVER_BAND" in names:
        return "closing"
    if "SECTION_BAND" in names:
        return "section"
    if any(n.startswith("BODY_TOC") for n in names):
        return "toc"
    if "LEAD" in names or "TITLE" in names:
        return "body"
    return "unknown"


# Exclude only generator boilerplate (locations, numbers, captions). BODY_LEGEND contains
# author-written diagram content and remains subject to font and density checks.
META_SHAPES = {"HEADER", "FOOTER", "PAGENO", "CAPTION", "REQID", "STATUS"}
# deck_profiles defines small text (legends, Gantt labels); share that definition with
# the generator. Inspect it using the table minimum.


def _effective_pt(run, paragraph, shape) -> float | None:
    """Resolve effective font size from run, paragraph, then shape defaults. Checking run.font.size alone skipped paragraph-level sizes and let undersized slides pass."""
    for source in (run.font, paragraph.font,
                   getattr(getattr(shape, "text_frame", None), "_defRPr", None)):
        size = getattr(source, "size", None) if source is not None else None
        if size is not None:
            return size.pt
    return None


def min_font_pt(slide) -> tuple[float | None, float | None]:
    """Return (minimum body pt, minimum table pt), excluding captions, headers, and footers. Keep distinct minima so body text reduced to table size cannot pass."""
    body: list[float] = []
    table: list[float] = []
    for sh in iter_shapes(slide.shapes):
        if sh.name in META_SHAPES:
            continue
        frames: list[tuple[object, list]] = []
        if sh.has_text_frame:
            frames.append((sh.text_frame, table if deck_profiles.is_small_text(sh.name) else body))
        if getattr(sh, "has_table", False) and sh.has_table:
            for row in sh.table.rows:
                for cell in row.cells:
                    frames.append((cell.text_frame, table))
        for tf, bucket in frames:
            for p in tf.paragraphs:
                for r in p.runs:
                    if not r.text.strip():
                        continue
                    pt = _effective_pt(r, p, sh)
                    if pt is not None:
                        bucket.append(pt)
    return (min(body) if body else None, min(table) if table else None)


def out_of_bounds(prs, slide) -> list[str]:
    """Find text shapes outside slide bounds. Font and character limits alone miss invisible off-slide boxes, also absent from rendered PDFs. Inspect text shapes only because backgrounds and decorations may intentionally cross bounds."""
    sw, sh_ = int(prs.slide_width), int(prs.slide_height)
    problems: list[str] = []
    for shape, (left, top, width, height) in placed_shapes(slide.shapes):
        if not shape_text(shape).strip():
            continue
        right, bottom = left + width, top + height
        if right <= 0 or bottom <= 0 or left >= sw or top >= sh_:
            problems.append(f"'{shape.name}' 완전히 화면 밖")
            continue
        over = max(0, -left) + max(0, right - sw)
        over_v = max(0, -top) + max(0, bottom - sh_)
        if width and over / width > 0.25:
            problems.append(f"'{shape.name}' 가로 {over / width:.0%} 잘림")
        elif height and over_v / height > 0.25:
            problems.append(f"'{shape.name}' 세로 {over_v / height:.0%} 잘림")
    return problems


def detect_profile(prs) -> tuple[str | None, str]:
    """Return (profile, stamp status) from build_deck core properties. Distinguish missing from unknown stamps so unrecognized specifications cannot silently use permissive defaults."""
    try:
        raw = prs.core_properties.category
    except (AttributeError, ValueError):
        return None, "missing"
    return deck_profiles.read_stamp(raw)


def raw_stamp(prs) -> str:
    try:
        return str(prs.core_properties.category or "")
    except (AttributeError, ValueError):
        return ""


def stage_is_submission(stage: str) -> bool:
    return stage == "submission"


def lint(prs, *, max_pages: int | None, exclude_cover_toc: bool, min_font: float,
         require_req_ids: bool, stage: str, style: dict | None = None,
         min_table_font: float | None = None) -> list[str]:
    style = style or _DEFAULT
    if min_table_font is None:
        min_table_font = min(min_font, style["sizes"]["table"] - 1)
    lead_max = style["lead_max_chars"]
    density_max = style["density_max"]
    table_rows_max = style["table_rows_max"]
    items: list[str] = []
    slides = list(prs.slides)
    counted = 0
    for idx, slide in enumerate(slides, 1):
        kind = slide_kind(slide)
        # Build (name, text) pairs in one traversal. Separately zipping a name dictionary and
        # text list shifts pairs when names repeat (multiple Gantt milestones), causing wrong
        # text counts or complete omission of body text.
        pairs = [(sh.name, shape_text(sh)) for sh in iter_shapes(slide.shapes)]
        names = {name: sh for name, sh in zip((n for n, _ in pairs), iter_shapes(slide.shapes))}
        texts = [t for _, t in pairs]
        all_text = "\n".join(t for t in texts if t)
        if not (exclude_cover_toc and kind in {"cover", "toc", "closing"}):
            counted += 1
        for problem in out_of_bounds(prs, slide):
            items.append(f"[차단] 슬라이드 {idx}: {problem} — 화면 밖 내용은 렌더에도 보이지 않는다")
        contrast_problems, contrast_skipped = color_contrast.slide_issues(slide)
        items.extend(f"[차단] 슬라이드 {idx}: {problem}" for problem in contrast_problems)
        if contrast_skipped:
            items.append(f"{NOTE} 슬라이드 {idx}: 색상 대비 {contrast_skipped}개 run 미검사 "
                         "— 테마·투명도·이미지 배경·상속 폰트는 렌더 육안 확인")
        if not all_text.strip():
            pics = [sh for sh in iter_shapes(slide.shapes) if sh.shape_type == 13]
            items.append(f"{'[차단]' if not pics else WARN} 슬라이드 {idx}: "
                         f"{'빈 슬라이드' if not pics else '이미지 전용 슬라이드 — 텍스트 검사 불가, 렌더 육안 확인 필수'}")
            continue
        if kind in {"cover", "closing", "section", "toc"}:
            continue
        heuristic = not ({"TITLE", "LEAD"} <= names.keys())
        tag = " [휴리스틱]" if heuristic else ""
        if heuristic:
            # External decks: treat the top two text boxes by position as title and lead.
            ordered = sorted((sh for sh in iter_shapes(slide.shapes) if shape_text(sh)),
                             key=lambda sh: (int(sh.top or 0), int(sh.left or 0)))
            title = shape_text(ordered[0]) if ordered else ""
            lead = shape_text(ordered[1]) if len(ordered) > 1 else ""
        else:
            title = shape_text(names["TITLE"])
            lead = shape_text(names["LEAD"])
        if not title:
            items.append(f"[차단] 슬라이드 {idx}: 제목 없음{tag}")
        if not lead:
            items.append(f"[차단] 슬라이드 {idx}: 리드문 없음 — 1페이지 1메시지 원칙{tag}")
        elif len(lead) > lead_max:
            items.append(f"{WARN} 슬라이드 {idx}: 리드문 {len(lead)}자 > {lead_max}자{tag}")
        elif lead.endswith(("설명합니다.", "설명합니다", "소개합니다.", "소개합니다")):
            items.append(f"{WARN} 슬라이드 {idx}: 리드문이 결론이 아닌 안내문('{lead[-6:]}')")
        if require_req_ids:
            req_text = shape_text(names["REQID"]) if "REQID" in names else all_text
            if not REQ_RE.search(req_text):
                level = "[차단]" if stage == "submission" else WARN
                items.append(f"{level} 슬라이드 {idx}: 대응 요구사항 ID(REQ-ID) 없음{tag}")
        # Use META_SHAPES for both density and font exclusions; captions and REQ-IDs are
        # generator boilerplate rather than author-written body content.
        body_chars = (sum(len(t) for n, t in pairs if n not in META_SHAPES)
                      if not heuristic else len(all_text))
        if body_chars > density_max:
            items.append(f"{WARN} 슬라이드 {idx}: 텍스트 {body_chars}자 > {density_max}자 — 도식·표로 압축 또는 분할")
        body_pt, table_pt = min_font_pt(slide)
        for measured, floor, role in ((body_pt, min_font, "본문"),
                                      (table_pt, min_table_font, "표")):
            if measured is not None and floor is not None and measured < floor:
                items.append(f"[차단] 슬라이드 {idx}: {role} 최소 폰트 {measured:g}pt < "
                             f"{floor:g}pt — 폰트 축소로 분량 회피 금지")
        for sh in iter_shapes(slide.shapes):
            if getattr(sh, "has_table", False) and sh.has_table:
                tbl = sh.table
                header = [c.text.strip() for c in tbl.rows[0].cells]
                if not any(header):
                    items.append(f"[차단] 슬라이드 {idx}: 표 헤더 행 비어 있음")
                if len(tbl.rows) - 1 > table_rows_max:
                    items.append(f"{WARN} 슬라이드 {idx}: 표 {len(tbl.rows) - 1}행 > {table_rows_max}행 — 분할·헤더 반복")
    if max_pages is not None:
        label = "본문" if exclude_cover_toc else "전체"
        if counted > max_pages:
            items.append(f"[차단] {label} {counted}장 > 페이지 제한 {max_pages}장")
        else:
            items.append(f"[정보] {label} {counted}장 / 제한 {max_pages}장")
    else:
        items.append(f"[정보] 전체 {len(slides)}장")
    return items


def render(pptx: Path, png_dir: Path | None) -> tuple[list[str], dict]:
    """Convert with soffice to PDF, compare page counts, optionally produce PNG thumbnails; return (items, evidence)."""
    items: list[str] = []
    evidence: dict = {"tool": "", "pdf_pages": None, "png": []}
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        items.append(f"{NOTE} LibreOffice(soffice) 없음 — PDF 렌더 미수행. 사람이 PowerPoint에서 렌더 확인")
        return items, evidence
    with tempfile.TemporaryDirectory() as tmp:
        try:
            proc = subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", tmp, str(pptx)],
                                  capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240)
        except (subprocess.TimeoutExpired, OSError) as exc:
            items.append(f"[차단] 렌더 실패: {exc}")
            return items, evidence
        pdf = Path(tmp) / (pptx.stem + ".pdf")
        if proc.returncode != 0 or not pdf.is_file():
            items.append(f"[차단] 렌더 실패(soffice exit {proc.returncode}): {(proc.stderr or proc.stdout).strip()[:200]}")
            return items, evidence
        try:
            version = subprocess.run([soffice, "--version"], capture_output=True, text=True,
                                     encoding="utf-8", errors="replace", timeout=15)
            ver = version.stdout.strip() if version.returncode == 0 else ""
        except (subprocess.TimeoutExpired, OSError):
            ver = ""
        if not ver:
            items.append(f"{NOTE} LibreOffice 버전 미확인 — PDF 변환 결과로 검사 계속")
        evidence["tool"] = ver or "libreoffice"
        pages = None
        pdfinfo = shutil.which("pdfinfo")
        if pdfinfo:
            try:
                info = subprocess.run([pdfinfo, str(pdf)], capture_output=True, text=True,
                                      encoding="utf-8", errors="replace", timeout=15)
                out = info.stdout if info.returncode == 0 else ""
            except (subprocess.TimeoutExpired, OSError):
                out = ""
            if not out:
                items.append(f"{NOTE} pdfinfo 실패 — PDF 페이지 구조로 대조")
            m = re.search(r"Pages:\s+(\d+)", out)
            pages = int(m.group(1)) if m else None
        if pages is None:
            pages = len(re.findall(rb"/Type\s*/Page[^s]", pdf.read_bytes()))
        evidence["pdf_pages"] = pages
        n_slides = len(Presentation(str(pptx)).slides)
        if pages != n_slides:
            items.append(f"[차단] 렌더 페이지 {pages} ≠ 슬라이드 {n_slides} — 숨김 슬라이드·렌더 누락 확인")
        else:
            items.append(f"[정보] 렌더 OK: PDF {pages}p = 슬라이드 {n_slides}장 ({evidence['tool']})")
        if png_dir:
            try:
                png_dir.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                items.append(f"[차단] 썸네일 폴더 생성 실패: {type(exc).__name__}")
                return items, evidence
            pdftoppm = shutil.which("pdftoppm")
            if pdftoppm:
                # Isolate this run: old output must not fill missing pages in new evidence.
                fresh_png = Path(tmp) / "png"
                try:
                    fresh_png.mkdir()
                    thumbs = subprocess.run(
                        [pdftoppm, "-r", "60", "-png", str(pdf), str(fresh_png / "slide")],
                        capture_output=True, timeout=240)
                except (subprocess.TimeoutExpired, OSError) as exc:
                    items.append(f"[차단] 썸네일 변환 실패: {type(exc).__name__}")
                    return items, evidence
                images = sorted(fresh_png.glob("slide-*.png"))
                indices = [int(m.group(1)) for p in images
                           if (m := re.fullmatch(r"slide-(\d+)\.png", p.name))]
                if (thumbs.returncode != 0 or len(images) != n_slides
                        or sorted(indices) != list(range(1, n_slides + 1))
                        or any(p.stat().st_size == 0 for p in images)):
                    items.append(f"[차단] 썸네일 변환 불완전(exit {thumbs.returncode}): "
                                 f"{len(images)}장 / 필요 {n_slides}장")
                    return items, evidence
                try:
                    for image in images:
                        shutil.copyfile(image, png_dir / image.name)
                except OSError as exc:
                    items.append(f"[차단] 썸네일 저장 실패: {type(exc).__name__}")
                    return items, evidence
                evidence["png"] = [p.name for p in images]
                stale = {p.name for p in png_dir.glob("slide-*.png")} - set(evidence["png"])
                if stale:
                    items.append(f"{NOTE} 이전 썸네일 {len(stale)}장 별도 잔존 — 이번 검사 증거에서 제외")
                items.append(f"[정보] 썸네일 {len(evidence['png'])}장 → {png_dir} (육안 검사: 잘림·겹침·폰트 대체)")
            else:
                try:
                    shutil.copy(pdf, png_dir / pdf.name)
                except OSError as exc:
                    items.append(f"[차단] PDF 저장 실패: {type(exc).__name__}")
                    return items, evidence
                items.append(f"[차단] pdftoppm 없음 — 요청한 PNG 미생성. PDF만 저장({png_dir / pdf.name})")
    return items, evidence


def is_blocking(item: str) -> bool:
    return item.startswith(BLOCK_PREFIXES)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pptx", type=Path)
    ap.add_argument("--max-pages", type=int, help="Page limit (RFP)")
    ap.add_argument("--exclude-cover-toc", action="store_true", help="Exclude cover, contents, and closing slides from the page limit")
    ap.add_argument("--min-font", type=float,
                    help="Minimum body font (pt), derived from the profile by default; excludes captions, headers, and footers")
    ap.add_argument("--profile", choices=sorted(deck_profiles.PROFILES),
                    help="시각 규격을 명시한다. 생략하면 PPTX에 남은 표시를 읽고, "
                         f"표시가 없으면 {deck_profiles.DEFAULT_PROFILE}")
    ap.add_argument("--require-req-ids", action="store_true", help="Require REQ-ID labels on body slides (public/financial A/B)")
    ap.add_argument("--stage", choices=["draft", "submission"], default="submission")
    ap.add_argument("--render", action="store_true", help="Render PDF with LibreOffice and compare page counts")
    ap.add_argument("--png-dir", type=Path, help="Directory for render thumbnails (requires --render)")
    ap.add_argument("--emit-render", type=Path, help="Output JSON path for the audit render block")
    a = ap.parse_args(argv)
    if not a.pptx.is_file():
        print(f"파일 없음: {a.pptx}", file=sys.stderr)
        return 2
    try:
        prs = Presentation(str(a.pptx))
    except Exception as exc:  # Damaged PPTX packages and similar failures.
        print(f"검사 불가(파일 손상·형식): {exc}", file=sys.stderr)
        return 2
    stamped, stamp_state = detect_profile(prs)
    profile = a.profile or stamped or deck_profiles.DEFAULT_PROFILE
    # Read buyer specification stamps with the same resolver as the generator.
    try:
        raw_keywords = prs.core_properties.keywords
    except (AttributeError, ValueError):
        raw_keywords = None
    try:
        spec, spec_state = deck_profiles.read_spec_stamp(raw_keywords, profile)
    except ValueError:  # Unknown --profile and similar values.
        spec, spec_state = {}, "invalid"
    style = deck_profiles.effective_style(profile, spec)
    # Derive font minima from profiles; fixed constants measure presentations (18pt) using
    # detailed criteria (9pt), or incorrectly block valid output in the opposite direction.
    min_font = a.min_font if a.min_font is not None else style["sizes"]["body"] - 1
    min_table_font = (min(a.min_font, style["sizes"]["table"] - 1)
                      if a.min_font is not None else style["sizes"]["table"] - 1)
    # Arguments cannot lower buyer minima (RFP values > internal profiles > argument convenience).
    floor = spec.get("font_min_pt")
    if floor:
        min_font, min_table_font = max(min_font, floor), max(min_table_font, floor)
    max_pages = a.max_pages
    if spec.get("page_limit") is not None:
        max_pages = spec["page_limit"] if max_pages is None else min(max_pages, spec["page_limit"])
    # Open once with the actual loader to catch relationship/schema defects missed by structural checks.
    load_problem = quality_gate.load_check(a.pptx)
    if load_problem:
        print(f"검사 불가: {load_problem}", file=sys.stderr)
        return 2
    source = "지정" if a.profile else ("파일 표시" if stamped else "기본값 추정")
    items = [f"[정보] 규격: {style['label']}({profile}, {source}) · 최소 폰트 {min_font}pt · "
             f"표 {min_table_font}pt · 밀도 {style['density_max']}자"]
    if a.profile and stamped and a.profile != stamped:
        items.append(f"{WARN} 지정한 규격({a.profile})이 파일에 남은 표시({stamped})와 다르다 — "
                     "다른 규격으로 만든 파일을 검사하고 있는지 확인한다")
    if not a.profile and stamp_state != "known":
        # Missing or unknown stamps would select permissive defaults; submission must not pass
        # on an assumption (not inspected ≠ passed).
        detail = ("규격 표시가 없다" if stamp_state == "missing"
                  else f"이 검사기가 모르는 규격 표시({raw_stamp(prs)})다")
        level = "[차단]" if stage_is_submission(a.stage) else WARN
        items.append(f"{level} {detail} — {deck_profiles.DEFAULT_PROFILE} 기준으로 재고 있다. "
                     "`--profile`로 규격을 명시하거나 build_deck으로 다시 생성한다")
    if spec_state == "invalid":
        level = "[차단]" if stage_is_submission(a.stage) else WARN
        items.append(f"{level} 발주처 지정 규격 표시를 해석할 수 없다({str(raw_keywords)[:80]}) — "
                     "build_deck으로 다시 생성한다")
    elif spec:
        items.append(f"[정보] 발주처 지정 규격 적용: {spec['source']} · "
                     + ", ".join(f"{k}={v}" for k, v in sorted(spec.items()) if k != "source"))
        if spec.get("canvas") == "16:9":
            w_in, h_in = int(prs.slide_width) / 914400, int(prs.slide_height) / 914400
            if abs(w_in - 13.333) > 0.1 or abs(h_in - 7.5) > 0.1:
                items.append(f"[차단] 지정 캔버스 16:9와 실제 슬라이드 {w_in:.2f}×{h_in:.2f}in 불일치")
        limit_mb = spec.get("file_size_limit_mb")
        size_mb = a.pptx.stat().st_size / 1048576
        if limit_mb and size_mb > limit_mb:
            items.append(f"[차단] 파일 {size_mb:.1f}MB > 지정 한도 {limit_mb:g}MB (PPTX 기준 — 제출 형식이 "
                         "다르면 변환본도 확인)")
    items += lint(prs, max_pages=max_pages, exclude_cover_toc=a.exclude_cover_toc,
                  min_font=min_font, min_table_font=min_table_font,
                  require_req_ids=a.require_req_ids, stage=a.stage, style=style)
    evidence: dict = {}
    rendered = False
    if a.render or a.png_dir or a.emit_render:
        r_items, evidence = render(a.pptx, a.png_dir)
        items += r_items
        rendered = bool(evidence.get("tool")) and not any(is_blocking(i) for i in r_items)
    blockers = [i for i in items if is_blocking(i)]
    for i in items:
        print(i)
    if a.emit_render:
        block = {
            "verified": rendered and not blockers,
            # Successful rendering is a machine fact; visual approval is a separate human fact.
            # PDF conversion alone does not mean a person reviewed and approved the slides.
            "render_succeeded": rendered,
            "layout_checked": True,
            "visual_review_approved": False,
            "visual_reviewer": "",
            "output_profile": profile,
            "artifact_hash": sha256(a.pptx),
            "tool": f"deck_check.py + {evidence.get('tool') or 'no-renderer'}",
            "evidence": [i for i in items if not i.startswith(WARN)] + (
                [f"png:{n}" for n in evidence.get("png", [])[:3]] if evidence.get("png") else []),
        }
        if not rendered:
            block["evidence"].append("NOT INSPECTED: PDF 렌더 미수행 — verified=false")
        block["evidence"].append(
            "육안 검토 미완료: 썸네일을 확인한 뒤 visual_review_approved=true와 "
            "visual_reviewer를 사람이 기록한다")
        a.emit_render.write_text(json.dumps(block, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[정보] render 블록 → {a.emit_render} (verified={block['verified']})")
    if blockers:
        print(f"차단 — {len(blockers)}건")
        return 1
    print("통과 (레이아웃 린트" + (" + 렌더" if rendered else "") + " — 도식 의미·설득력은 사람이 검토)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
