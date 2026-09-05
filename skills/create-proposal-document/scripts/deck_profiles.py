"""산출물 종류별 시각 규격 — build_deck.py와 deck_check.py가 함께 읽는 단일 정의.

같은 제안 내용이라도 읽는 조건이 다르면 규격이 달라야 한다. 인쇄해서 채점하는 평가용
상세본과 회의실 스크린에 띄우는 발표본에 같은 11pt 본문·600자 밀도를 강제하면, 한쪽은
반드시 잘못된다. 그렇다고 검사기와 생성기가 각자 숫자를 들고 있으면 서로 어긋난다
(실제로 표 행 경고가 생성기 14행 · 검사기 15행으로, 밀도가 450자 · 600자로 갈려 있었다).

그래서 규격은 여기 한 곳에만 둔다. 생성기는 이 값으로 그리고, 검사기는 이 값으로 검사하며,
생성된 PPTX에는 어떤 프로파일로 만들었는지 표시가 남아 검사기가 같은 기준을 적용한다.

프로파일 선택 기준:
  detailed-submission  인쇄·PDF로 평가위원이 채점하는 제안서 본문(기본값). 분량 제한 안에
                       근거를 담아야 하므로 밀도가 높다. 발주처 양식이 있으면 그것이 우선한다.
  presentation         회의실 스크린 발표본. 뒷자리에서 읽혀야 하므로 본문 18pt 이상,
                       장표당 텍스트를 크게 줄인다(ARL 권고 24pt, Microsoft 접근성 18pt 이상).
  executive-summary    임원 의사결정용 요약본. 화면·인쇄 겸용, 상세본과 발표본의 중간.
"""
from __future__ import annotations

DEFAULT_PROFILE = "detailed-submission"
# PPTX core properties에 남기는 표시. 검사기가 같은 기준을 적용하려면 파일 자체가
# 어떤 규격으로 만들어졌는지 말해야 한다(파일명·인자 전달에 기대지 않는다).
STAMP_PREFIX = "proposal-deck:"

# 도형 안 주석 — 범례와 간트 차트(BODY_G*)의 모든 텍스트. 본문 산문이 아니라 표 셀과 같은
# 소형 텍스트이며, 생성기는 이들을 sizes["table"] - 1로 그린다. 검사기도 같은 정의를
# 읽어 표 하한으로 재야 한다(본문 하한을 적용하면 정상 구성도·일정표가 차단된다).
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
        # 캡션·헤더·푸터도 14pt까지 올린다 — 스크린에서는 '작은 글씨'가 아예 안 읽힌다.
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
    """프로파일 사양을 돌려준다. 이름이 없으면 기본값, 모르는 이름이면 ValueError."""
    key = (name or DEFAULT_PROFILE).strip()
    if key not in PROFILES:
        raise ValueError(f"unknown output profile {name!r} "
                         f"(allowed: {', '.join(sorted(PROFILES))})")
    return PROFILES[key]


def min_body_font(name: str | None) -> float:
    """본문 텍스트의 최소 폰트 기준. 생성기의 본문 크기에서 유도한다.

    상수로 따로 두면 프로파일을 바꿀 때 검사기만 남아 정상 산출물을 차단한다.
    표 하한(더 작다)과 합쳐 쓰면 본문을 표 크기까지 줄인 장표가 통과하므로 나눈다.
    """
    return get(name)["sizes"]["body"] - 1


def min_table_font(name: str | None) -> float:
    """표 셀의 최소 폰트 기준. 표는 본문보다 작게 쓰는 것이 정상이다."""
    return get(name)["sizes"]["table"] - 1


def stamp(name: str) -> str:
    return f"{STAMP_PREFIX}{name}"


def read_stamp(value: object) -> tuple[str | None, str]:
    """(프로파일 이름, 상태). 상태는 known | missing | unknown.

    '표시 없음'과 '모르는 표시'를 구분한다 — 둘을 같게 처리하면 이 버전이 모르는
    규격으로 만든 덱이 가장 느슨한 기본값으로 조용히 통과한다.
    """
    if not isinstance(value, str) or not value.startswith(STAMP_PREFIX):
        return None, "missing"
    name = value[len(STAMP_PREFIX):].strip()
    if name in PROFILES:
        return name, "known"
    return None, "unknown"


def from_stamp(value: object) -> str | None:
    """호환용 — 이름만 필요할 때. 모르는 표시와 표시 없음을 구분하려면 read_stamp를 쓴다."""
    return read_stamp(value)[0]
