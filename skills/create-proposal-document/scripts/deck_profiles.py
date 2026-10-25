"""Visual specifications by output type, shared by build_deck.py and deck_check.py. Different reading conditions require different specifications: printed evaluation documents and projected presentations cannot share 11pt body text and 600-character density. Separate generator/checker definitions previously drifted to 14/15 table rows and 450/600 characters. Define specifications once here; generators draw with them and stamp the PPTX so checkers apply the same criteria.

Profiles:
  detailed-submission: default printed/PDF proposal body for evaluation, with dense evidence within page limits; buyer templates take precedence.
  presentation: projected meeting-room slides; default body 18pt, internal minimum 17pt, and substantially less text (ARL recommends 24pt, Microsoft accessibility at least 18pt). Generation defaults and check minima are separate, with 1pt internal allowance.
  executive-summary: decision summary for screen and print, between detailed and presentation profiles.
"""
from __future__ import annotations

DEFAULT_PROFILE = "detailed-submission"
# Stamp PPTX core properties so the file itself records its specification and the checker
# can apply matching criteria without relying on filenames or forwarded arguments.
STAMP_PREFIX = "proposal-deck:"

# In-shape annotations: all legend and Gantt (BODY_G*) text is small text like table cells,
# not body prose. The generator draws these at sizes["table"] - 1; the checker must share
# this definition and use the table minimum to avoid blocking valid diagrams and schedules.
SMALL_TEXT_PREFIXES = ("BODY_LEGEND", "BODY_G")


def is_small_text(shape_name: object) -> bool:
    return isinstance(shape_name, str) and shape_name.startswith(SMALL_TEXT_PREFIXES)

PROFILES: dict[str, dict] = {
    "detailed-submission": {
        "label": "평가용 상세본",
        "note": "인쇄·PDF 채점용. 발주처 양식이 있으면 그 규격이 이 값보다 우선한다.",
        "sizes": {"title": 22, "lead": 13, "body": 11, "table": 10, "caption": 8.5,
                  "header": 9, "footer": 9, "cover_title": 32, "cover_sub": 16, "section": 28},
        "lead_max_chars": 60,
        "density_max": 600,
        "table_rows_max": 14,
        "matrix_rows_per_slide": 12,
        "bullets_max_chars": 450,
    },
    "presentation": {
        "label": "발표본",
        "note": "회의실 스크린용. 뒷자리 가독성이 기준이며, 상세 근거는 별첨·상세본으로 뺀다.",
        # Raise captions, headers, and footers to 14pt too; small print is unreadable on screens.
        "sizes": {"title": 30, "lead": 20, "body": 18, "table": 14, "caption": 14,
                  "header": 14, "footer": 14, "cover_title": 44, "cover_sub": 24, "section": 36},
        "lead_max_chars": 40,
        "density_max": 250,
        "table_rows_max": 8,
        "matrix_rows_per_slide": 6,
        "bullets_max_chars": 180,
    },
    "executive-summary": {
        "label": "임원 의사결정본",
        "note": "결정에 필요한 것만. 화면·인쇄 겸용이라 상세본과 발표본의 중간 밀도.",
        "sizes": {"title": 26, "lead": 16, "body": 14, "table": 12, "caption": 10,
                  "header": 10, "footer": 10, "cover_title": 36, "cover_sub": 20, "section": 32},
        "lead_max_chars": 50,
        "density_max": 400,
        "table_rows_max": 10,
        "matrix_rows_per_slide": 9,
        "bullets_max_chars": 300,
    },
}


def get(name: str | None) -> dict:
    """Return a profile specification; default if absent, ValueError if unknown."""
    key = (name or DEFAULT_PROFILE).strip()
    if key not in PROFILES:
        raise ValueError(f"unknown output profile {name!r} "
                         f"(allowed: {', '.join(sorted(PROFILES))})")
    return PROFILES[key]


def min_body_font(name: str | None) -> float:
    """Minimum body font derived from generator body size. Separate constants drift when profiles change, and merging with the smaller table minimum allows undersized body text to pass."""
    return get(name)["sizes"]["body"] - 1


def min_table_font(name: str | None) -> float:
    """Minimum table-cell font; tables legitimately use smaller text than body prose."""
    return get(name)["sizes"]["table"] - 1


def stamp(name: str) -> str:
    return f"{STAMP_PREFIX}{name}"


def read_stamp(value: object) -> tuple[str | None, str]:
    """Return (profile name, status): known | missing | unknown. Distinguish missing from unknown stamps so unsupported profiles cannot silently use permissive defaults."""
    if not isinstance(value, str) or not value.startswith(STAMP_PREFIX):
        return None, "missing"
    name = value[len(STAMP_PREFIX):].strip()
    if name in PROFILES:
        return name, "known"
    return None, "unknown"


# ---- Buyer-specified output specifications (output_spec) ----
# Profiles provide internal defaults; buyer page, font, file-size, and aspect-ratio rules
# take precedence. Define accepted keys here, not numerical defaults that vary by notice.
OUTPUT_SPEC_PREFIX = "proposal-output-spec:"
OUTPUT_SPEC_KEYS = {"source", "canvas", "page_limit", "font_min_pt", "file_size_limit_mb"}
# Canvases supported by the generator coordinate grid; the rest are known but unsupported.
SUPPORTED_CANVASES = {"16:9"}
KNOWN_CANVASES = SUPPORTED_CANVASES | {"4:3", "A4-portrait", "A4-landscape", "A3-portrait", "A3-landscape"}
# These belong to the submission bundle, not slides; reject with the correct location rather than ignore them.
BUNDLE_KEYS = {"anonymous_copy", "price_separation", "file_format", "copies", "binding"}


def _positive(value: object, key: str, *, integer: bool = False) -> float | int:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"output_spec.{key}는 양수여야 한다 (got {value!r})")
    if integer and int(value) != value:
        raise ValueError(f"output_spec.{key}는 정수여야 한다 (got {value!r})")
    return int(value) if integer else float(value)


def resolve_output_spec(raw: object, profile: str | None) -> dict:
    """Validate and normalize buyer specifications; absent values return {} for profile defaults. Fail closed with ValueError for unknown keys, unknown/unsupported canvases, or minima larger than profile body size; ignoring them would pass noncompliant output."""
    if raw is None or raw == {}:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"output_spec은 객체여야 한다 (got {type(raw).__name__})")
    bundle = sorted(set(raw) & BUNDLE_KEYS)
    if bundle:
        raise ValueError(f"output_spec에 제출 묶음 속성 {bundle} — attachments[]·submission bundle에 기록한다")
    unknown = sorted(set(raw) - OUTPUT_SPEC_KEYS)
    if unknown:
        raise ValueError(f"output_spec 모르는 키 {unknown} (allowed: {', '.join(sorted(OUTPUT_SPEC_KEYS))})")
    source = raw.get("source")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("output_spec.source 필수 — 공고의 규격 위치(문서·쪽·조항)를 적는다")
    spec: dict = {"source": source.strip()}
    if "canvas" in raw:
        canvas = raw["canvas"]
        if canvas not in KNOWN_CANVASES:
            raise ValueError(f"output_spec.canvas 모르는 값 {canvas!r} (known: {', '.join(sorted(KNOWN_CANVASES))})")
        if canvas not in SUPPORTED_CANVASES:
            raise ValueError(f"지정 캔버스 {canvas}는 이 생성기가 그리지 않는다(16:9 그리드 전용) "
                             "— 발주처 지정 양식 또는 DOCX 경로로 작성한다")
        spec["canvas"] = canvas
    if "page_limit" in raw:
        spec["page_limit"] = _positive(raw["page_limit"], "page_limit", integer=True)
    if "file_size_limit_mb" in raw:
        spec["file_size_limit_mb"] = _positive(raw["file_size_limit_mb"], "file_size_limit_mb")
    if "font_min_pt" in raw:
        floor = _positive(raw["font_min_pt"], "font_min_pt")
        body = get(profile)["sizes"]["body"]
        # The generator can draw body text at body-1 (cards and phase descriptions). If below the minimum,
        # density rules must change too; require a larger profile rather than merely raising sizes.
        if body - 1 < floor:
            raise ValueError(f"지정 최소 글자 {floor:g}pt > {profile or DEFAULT_PROFILE} 본문 하한 {body - 1:g}pt "
                             "— 본문이 더 큰 output_profile을 고른다")
        spec["font_min_pt"] = floor
    return spec


def effective_style(profile: str | None, spec: dict | None) -> dict:
    """Apply buyer font minima to a profile, shared by generator and checker. Since tables and legends use table-1, raise tables, captions, headers, and footers to minimum+1; resolve_output_spec already guarantees body compliance."""
    base = get(profile)
    floor = (spec or {}).get("font_min_pt")
    if not floor:
        return base
    sizes = dict(base["sizes"])
    for key in ("table", "caption", "header", "footer"):
        sizes[key] = max(sizes[key], floor + 1)
    return {**base, "sizes": sizes}


def spec_stamp(spec: dict) -> str:
    import json
    return OUTPUT_SPEC_PREFIX + json.dumps(spec, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def read_spec_stamp(value: object, profile: str | None) -> tuple[dict, str]:
    """Return (specification, status): missing | valid | invalid; invalid yields {}."""
    import json
    if not isinstance(value, str) or not value.startswith(OUTPUT_SPEC_PREFIX):
        return {}, "missing"
    try:
        return resolve_output_spec(json.loads(value[len(OUTPUT_SPEC_PREFIX):]), profile), "valid"
    except (ValueError, json.JSONDecodeError):
        return {}, "invalid"


def from_stamp(value: object) -> str | None:
    """Compatibility helper when only the name is needed; use read_stamp to distinguish unknown and missing stamps."""
    return read_stamp(value)[0]
