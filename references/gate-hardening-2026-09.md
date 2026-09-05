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

## 3차 (2026-09-05) — 산출물 결속·판정 단일화 (외부 정밀 진단 F01~F05 대응)

외부 진단서(고정 커밋 f346a18)의 지적을 현재 main에서 재현한 뒤 유효한 것만 수정했다.
재현 결과 F05의 `[unverified]` 미탐, F06 제작 레이어 부재, F09 scorer 미배포는 2차(PR #14)에서
이미 해소된 상태였고 `package.checks={}`의 TypeError도 재현되지 않았다. 나머지는 모두 유효했다.

**F01 산출물 해시 결속** — audit이 '어느 파일'의 기록인지 확인한다.
`unified_gate.py`가 `--doc`의 sha256을 계산해 `render/package.artifact_hash`와 대조하고,
불일치면 차단한다(검토 이후 바뀐 파일에 과거 판정 재사용 금지). `mode=submission` +
`artifact_required=true`인데 `--doc`이 없으면 차단하며, 문서 없이 audit만 볼 때는
`--audit-only`를 쓰고 최선의 결과는 `SUBMISSION-READY`가 아니라 `AUDIT-VALID`다.
제출 모드의 artifact_hash는 실제 `sha256:<64 hex>`여야 하고 render·package가 같은 파일을
가리켜야 한다(문자열 라벨 `sha256:proposal`은 차단).

**F02 단계·라벨·설명의 단일 판정** — `readiness(data, failures)` 하나가 라벨과 종료 코드를
정하고 `explain_markdown`·CLI가 같은 함수를 쓴다(draft audit이 "제출 가능"으로 설명되던 불일치
제거). `mode=submission` audit을 `--stage draft`로 낮춰 검사하는 우회는 사용 오류(exit 2),
`artifact_mode=simulation-only`는 제출 모드에서 차단.

**F03 변환·스키마 유실 차단** — `_str_list()`가 문자열을 리스트로 감싸지 않는다
(`"TBD"` → `['T','B','D']` 오변환 제거). 원장 배열의 비객체 항목은 위치와 함께 오류
(`requirements[2] must be an object`) — 문자열 요구 하나가 조용히 버려져 3건이 2건이 되던
유실 차단. `requirements[]`·`claims[]`의 id는 필수·유일이며, 열거값 검사는 `_enum_ok()`로
비문자열을 안전하게 거부한다(`mode=[]`가 트레이스백 대신 INVALID exit 2).

**F04 근거·준수·응답 위치의 분리** — 제출 모드에서 `supported|qualified` 주장은
`evidence_refs` 필수. `support=X`/`fit=GAP`인데 `state=approved`이면 차단하고, 발주처 예외는
`exception:{granted_by, evidence}`로만 인정한다. `bulk_matrix.py`는 응답 위치를
`response_refs`로 분리한다(더 이상 `evidence_refs`로 승격되지 않음).

**F05 문서 검사 범위** — `chart_text()`가 차트 파트에서 run(a:t) 외에 범주·계열 캐시(`c:v`)까지
읽는다. 제목이 있는 차트에서 범주의 잔존 고객명을 놓치던 미탐 해소(제목 없는 차트는 이전에도
탐지됐다). 확장자만 `.pptx`인 일반 ZIP은 `NOT INSPECTED` 통과가 아니라 사용 오류(exit 2)다.

**검증** — `test_gate_integrity.py` 22건 신설(정상 대조군 포함), 전체 149건 + proposal_gate 58건
+ best_proposal 11건 통과. 골든 픽스처와 테스트 베이스의 해시를 실제 digest로 교체했다.

**남은 항목(미착수)** — F06 산술·좌표 검증(unified_gate가 `checks.arithmetic`을 실제 계산과
대조하지 않는다), F07 업종 프로파일(공공·기업·학교·병원), F08 산출물 종류별 시각 규격 분리
(발표본 18pt+), F10 품질 주장의 근거(블라인드 비교 평가).

## 4차 (2026-09-05) — 외부 재점검 R01~R08 대응

3차 이후 받은 재점검 보고서의 8건을 현재 main에서 전부 재현한 뒤 수정했다. 이 중 셋은
3차에서 내가 "고쳤다"고 기록한 항목의 빈틈이었다.

**R01 검증 의무 우회** — `artifact_required=false`, 렌더 미검증, 해시 라벨 상태로도
`SUBMISSION-READY`가 나왔다. 제출 모드에서는 입력값과 무관하게 렌더 검증·해시 형식·패키지
검사를 요구하도록 바꿨다(`artifact_required = data[...] or mode == "submission"`).

**R02 열리지 않는 패키지** — `[Content_Types].xml`이 없어 python-pptx가 열지 못하는 ZIP이
제출 통과했다. `validate_package()`가 필수 파트(`[Content_Types].xml`·`_rels/.rels`·본문 파트)
존재와 main 파트 XML 파싱을 확인한다(zipfile만 사용, 의존성 추가 없음). **CI의 양성 대조군도
같은 결함이 있었다** — python-pptx로 만든 실제 파일로 교체했다. 테스트 픽스처는
`ooxml_fixtures.py` 한 곳에서 만들고, 실제 로더로 열리는지까지 검사한다.

**R03 템플릿 잔존 슬라이드** — 2장짜리 템플릿에 표지 1장을 생성하면 이전 고객명·금액이 남은
3장 파일이 나오는데 "1 slides"로 보고했다(기밀 유출 + 페이지 제한 검사 무력화). 슬라이드가 든
템플릿은 거부하고, 페이지 수는 내부 카운터가 아니라 실제 슬라이드 수로 센다.

**R04 화면 밖 배치** — 18pt 정상 폰트를 슬라이드 밖에 두어도 차단 0건이었다. `out_of_bounds()`가
텍스트 도형의 좌표를 슬라이드 경계와 대조한다(완전히 밖 또는 25% 초과 잘림 → 차단). 이 검사가
골든 덱의 간트 마일스톤 라벨이 오른쪽 여백을 넘던 실제 결함을 찾아내 함께 고쳤다.
`render_succeeded`(기계)와 `visual_review_approved`(사람)를 분리했고, 제출 모드는 후자와
`visual_reviewer` 실명을 요구한다 — PDF 변환 성공은 디자인 승인이 아니다.

**R05 행 유실** — `rows_per_slide=-1`이면 `--strict`에서도 조견표 데이터가 0행이 됐다. 양의
정수만 허용하고, 입력 행 수와 출력 행 수를 대조한다.

**R06 별칭·필드 유실** — `support="X 미수용"`은 승인 모순 검사를 빠져나갔다(`is_unsupported()`로
표기 변형을 하나로 본다). 더 심각한 것은 3차에서 만든 예외 경로가 **문서대로 쓰면 작동하지
않았다**는 점이다 — meta→audit 빌더가 `exception`과 `response_refs`를 버려서 정당한 발주처
예외가 허위 차단됐다. 두 필드를 타입 검증과 함께 보존한다.

**R07 설명문 모순** — `STATUS: AUDIT-VALID` 옆에 "게이트 결과: SUBMISSION-READY / 제출 가능."이
찍혔다. 3차의 회귀 테스트가 전부 `--no-explain`이라 보지 못했다. `explain_markdown(..., label)`이
호출자의 판정을 받고, 새 테스트는 설명 경로를 함께 검사한다.

**R08 enum 타입** — `claim.kind=[]`, `package.checks.metadata={}` 등이 TypeError로 터졌다.
모든 열거 비교를 `_enum_ok()`로 통일했다(비문자열은 조용히 거부 → 구조화된 INVALID).

### 검증
`test_gate_integrity2.py` 24건 신설(정상 대조군 포함) — 전체 183건 + proposal_gate 58건 +
best_proposal 11건 통과. CI 골든에 우회 차단·설명문 모순·템플릿 거부·행 유실 음성 대조군을
추가했다. 보고서의 재현 8건을 원래 절차대로 다시 실행해 전부 차단됨을 확인했다.

### 남은 항목
F06 산술 실측(본문 수치 vs 원장), F07 업종 프로파일, F08 산출물 종류별 시각 규격,
F10 블라인드 비교 평가. 표 셀 내부 넘침과 도형 간 가림은 여전히 썸네일 육안 검토 영역이다.

## 5차 (2026-09-05) — 수치 원장과 산술 실측 (F06 잔여)

`checks.arithmetic: true`는 사람이 기록하는 자기선언이라, 본문에 `100원 + 200원 = 900원`이
적혀 있어도 게이트가 알 수 없었다. 4차까지의 수정은 "어느 파일인지"와 "열리는 파일인지"를
닫았지만, "그 파일에 적힌 수가 맞는지"는 여전히 사람 말만 믿었다.

**수치 원장(numbers[])** — 금액·기간·수량을 `{id, label, value, unit, source}`로 적고,
`components`로 구성 요소를 연결하면 게이트가 합계를 다시 계산한다. `percent_of`+`amount`는
비율을 재계산한다. 단위가 섞인 합계, 미지의 구성 요소 참조, 중복 id, 숫자가 아닌 value는
각각 위치와 함께 오류가 된다. 허용오차는 기본 0.5%이며 항목별로 조정한다.

**자기선언의 결속** — 제출 모드에서 원장이 없으면 `checks.arithmetic: true`만으로 통과하지
못한다. 무엇을 검산했는지 보이지 않는 '검산 완료'는 검증이 아니다. draft/review는 종전대로
원장을 요구하지 않는다(체크포인트 도달성 유지).

**문서 대조(check_numbers.py)** — 게이트는 원장 안의 산술만 보므로, 그 값이 실제 장표에 적힌
값과 같은지는 문서를 열어야 안다. 한국어 제안서는 같은 수를 여러 표기로 쓰기 때문에
(`3,700,000,000` / `3700000000` / `37억` / `370,000만`) 표기 변형을 생성해 대조하고, 어느
표기로도 없으면 차단한다. 숫자 경계를 지켜 `370억`이 `37억`으로 오탐되지 않는다. 중간
계산값은 `must_appear: false`로 제외한다.

**빌더 보존** — meta→audit 변환이 `numbers`를 버리면 제출 모드가 "원장 없음"으로 차단되므로,
원장을 타입 검증과 함께 보존한다(비객체 항목은 위치와 함께 오류).

### 검증
`test_numbers_ledger.py` 18건 신설 — 전체 201건 + proposal_gate 58건 + best_proposal 11건 통과.
골든 픽스처(제출·e2e 미니 RFP)에 원장을 넣어 CI가 매번 계산하도록 했다.

### 남은 항목
F07 업종 프로파일, F08 산출물 종류별 시각 규격, F10 블라인드 비교 평가. 원장에 올리지 않은
본문 수치의 오류는 여전히 잡지 못한다(무엇을 원장에 올릴지는 작성자의 판단이다).
