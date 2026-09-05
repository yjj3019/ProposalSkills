# 게이트 신뢰성 감사와 수정 (2026-09)

기존 테스트 132개 전부 통과 상태에서, 합성 PPTX/DOCX/XLSX와 변조 audit JSON으로 게이트 스크립트를
직접 찔러 본 결과다. 문서 레이어(목차·패턴·문체)가 아니라 **게이트가 약속한 "결정론적 차단"이
실제로 성립하는지**만 봤다. 발견 항목은 전부 `test_gate_hardening.py`에 재현 테스트로 고정했다.

## P0 — 허위 통과 (게이트가 "통과"라고 말했지만 틀린 경우)

| # | 위치 | 재현 | 수정 |
|---|---|---|---|
| 1 | quality_gate | 노트·레이아웃·마스터·차트에 잔존 고객명 → 통과 | `ppt/notesSlides`, `slideLayouts`, `slideMasters`, `charts`, `comments`, `docProps/core.xml` 스캔 |
| 2 | quality_gate | DOCX 머리말·바닥글·각주·주석에 과장어 → 통과 | `word/header*`, `footer*`, `footnotes`, `endnotes`, `comments` 스캔 |
| 3 | quality_gate | 텍스트박스 중첩 `<w:p>` 뒤 본문 유실 | 최상위 문단 깊이 추적으로 분할 |
| 4 | quality_gate | run 분할(`최`+`고`), NBSP 포함 마커 → 미탐지 | run을 공백 없이 결합, 공백류 정규화 |
| 5 | proposal_gate | `accepted:"pending"`, `present:"no"`, `cleared:"no"`, `verified:"failed"` → READY | 엄격 불리언 스키마 검증(문자열 → INVALID) |
| 6 | proposal_gate | claim `kind` 누락·오타(`Material`) → 검사 생략 | 누락=material, 미지원 kind=스키마 오류 |
| 7 | unified_gate | `mode:"draft"` audit에 `SUBMISSION-READY` 표시 | mode=submission일 때만 표시, 그 외 `DRAFT-READY` + NOTE |
| 8 | quality_gate/unified_gate | 한국어 Windows cp949 콘솔에서 `—` 출력 크래시 → 정상 문서 BLOCKED | stdout UTF-8 재구성, 자식 프로세스 `PYTHONIOENCODING=utf-8` |

## P1 — fail-open·견고성

- `evidence_refs=["[NEEDS INPUT]"]`, `artifact_hash:"TBD"`, `receipt_plan:"TBD"`, 규제 `evidence:"TBD"`가
  근거로 통과 → 플레이스홀더(TBD·TODO·???·needs input·입력요망·미정 등)는 근거로 인정하지 않음.

- names 파일 UTF-8 BOM으로 첫 명칭 무시 → `utf-8-sig`. 금지 명칭 대소문자·공백 무시 매칭.
- 손상·미지원 파일이 exit 1(차단)로 섞임 → exit 2(검사 불가). XLSX 셀·주석 검사 추가.
- `bid_conditions[].deadline` 과거여도 CONDITIONAL-GO → 미래 검증 추가.
- `mode:"submission"` + `conditional-bid` exit 0 → 차단(조건부는 내부 상태).
- 빈 `requirements`로 submission READY → 필수 요구 1건 이상 요구. `mandatory` 누락=필수.
- 빌더가 `"requirements": "R1 R2"` 문자열을 조용히 `[]`로 → ValueError.
- 빌더가 `slide:N`을 `evidence_refs`로 조작해 반낙관 검사 우회 → 근거 미생성 + 경고.
- 빌더 `bool("no") == True` → 문자열 불리언 ValueError.
- `PROPOSAL_GATE_NOW` 형식 오류 시 벽시계 폴백 → 환경 오류 exit 2.
- score_completeness 지표 범위·타입 미검증(157점 산출) → 4개 필수·0~1 검증, INVALID exit 2.
- unified_gate `PROPOSAL_GATE_PATH`에 임의 .py → 모듈 함수 존재 확인 후 INVALID.
- bulk_matrix: 공란 `mandatory`=False → True. `o`/`Y`/`△` 정규화, 미지원 코드 오류. CSV 다중행 셀 보존.
- install_skill: `--name ../..` 경로 이탈 차단, SKILL.md 없는 불완전 디렉터리 교체, `--force`, 캐시 제외.
- proposal_gate argparse(`-h`, 미지원 플래그 exit 2). 비UTF-8 JSON exit 2.

## 유지 사항 (의도된 동작으로 확인)

- 마스터 색상 NOT INSPECTED 경고는 비차단으로 유지(테스트 계약).
- 스킬 디렉터리 내 `test_*.py`는 설치 후 자가검증용으로 배포본에 포함.

## 관련 문서 갱신

`unified-gates.md` §3·§4·§6, `audit-schema.md`(엄격 불리언·조건부 범위), `create-best-proposal/SKILL.md`
Phase D·E, `create-proposal-document/SKILL.md` 자료 위치, README 테스트 절, `.github/workflows/ci.yml`.

## 2차 (2026-09-05) — 장표 생산 레이어 추가

미니 RFP로 스킬을 그대로 따라간 드라이런 결과, Phase D(시각·산출)가 텍스트 지침만 있고 도구가
없어 100% 모델 재발명이었고(슬라이드 1장 전 1,583줄 열람), 렌더·레이아웃 검사가 없어 페이지 제한·
리드문·REQ-ID·폰트 축소를 어떤 게이트도 잡지 못했다. 반영:

- `build_deck.py`: slides.json → PPTX. 레이아웃 12종, 좌표·토큰 고정, 도형 역할명(TITLE/LEAD/REQID…)
  부여, 조견표 자동 분할, `--strict`(리드문 누락·페이지 제한), `--template` 사내 양식.
- `deck_check.py`: 리드문·REQ-ID·페이지 수·최소 폰트·밀도·표 헤더 린트 + LibreOffice 렌더 대조·PNG
  썸네일 + audit `render` 블록 출력(렌더 성공+차단 0 → verified). soffice 없으면 NOT INSPECTED.
- 골든 `fixtures/e2e-mini-rfp/`(rfp.md·slides.json·meta.json)와 `test_deck_pipeline.py` 14건.
- 게이트 조정: draft/review 모드는 `artifact_required`·`package.required`·`checks.submission`을 요구하지
  않는다(Pink/Red 체크포인트 도달 가능). submission 모드는 변경 없음.
- 어휘 통일: 수용여부 6코드(`O/부분/조건부/X/N/A/확인필요`, 한글 라벨은 표시형), 요구 상태는 게이트
  어휘(`pending→drafted→needs-review→approved`), 사람 검토 판정 `CONDITIONAL GO`→`FIX-AND-RECHECK`
  (게이트 `CONDITIONAL-GO`와 이름 충돌 제거) + 게이트 라벨 대응표.
- `score_completeness.py`를 create-best-proposal/scripts로 이동(설치 트리에서 동작), 루트는 진입점 유지.
- quality_gate 마커: `○○`·`[unverified]`·`미정`(초안 경고/제출 차단), `p.__`(차단).
- 3 스킬 frontmatter를 "단일 진입점 + 형제는 로드 전용"으로 재작성(라우터 중복 트리거 제거).
