# ProposalSkills

모델에 종속되지 않는 제안서 문서 제작 스킬과 조사 자료를 관리합니다. 핵심 `SKILL.md`, 참조자료, 검증 스크립트는 ChatGPT, Claude, Gemini, Grok 등에서 동일하게 사용할 수 있습니다.

## 수록 스킬

| 스킬 | 성격 | 이런 작업에 사용 |
|---|---|---|
| **[`create-best-proposal`](skills/create-best-proposal/SKILL.md)** ★ 권장 | **통합 플래그십** — 콘텐츠+거버넌스 오케스트레이션, meta→audit, 통합 게이트, 대량 조견표 | 실전 제안서 작성부터 bid 판정·제출 게이트까지 **한 경로**로 끝낼 때 |
| [`create-proposal-document`](skills/create-proposal-document/SKILL.md) | 한국어 · PPTX 장표형 중심(DOCX 지원) · 수주 패턴 뱅크 | 한국어 IT 제안서 본문·문체·조견표·시각 레이어만 깊게 다룰 때 |
| [`create-winning-proposal`](skills/create-winning-proposal/SKILL.md) | 한/영 · 프로세스 통제 · audit JSON | bid/no-bid, 승인 체인, 결정론적 제출 게이트만 필요할 때 |

세 스킬은 충돌하지 않습니다. `create-best-proposal`이 나머지 둘을 오케스트레이션하며, 상세 문체·스키마 원문은 형제 스킬 `references/`를 참조합니다.

작성 품질과 제출 준비도는 별개 축입니다. 문서 스킬만 쓰면 잘 쓴 제안서가 제출 요건을 놓치고,
거버넌스 스킬만 쓰면 통과는 하지만 내용이 빈 문서가 나옵니다. 통합 스킬은 두 축을 함께 강제합니다.

> 저장소에 표기된 점수는 **구조 검사 지표**(파일·키워드·스키마 충족률)입니다. 제안서의 수주
> 가능성이나 시각 품질을 측정한 값이 아니며 외부 블라인드 평가로 검증된 바 없습니다.

## 설치

AI(Claude Code·Codex·Grok)에게 이 저장소를 주고 **"설치해줘"**라고 하면 됩니다. 저장소 루트의
[AGENTS.md](AGENTS.md)·[CLAUDE.md](CLAUDE.md)를 AI가 읽고 아래를 실행합니다.

```bash
git clone https://github.com/yjj3019/ProposalSkills.git
cd ProposalSkills
python install_skill.py --auto
```

`--auto`는 이 컴퓨터에 설치된 AI CLI를 찾아 각각의 스킬 디렉터리에 세 스킬을 모두 넣습니다.
경로를 되묻지 않습니다.

| 감지 | 설치 경로 |
|---|---|
| `~/.claude/` | `~/.claude/skills/` |
| `~/.codex/` | `~/.agents/skills/` (AGENTS.md 공용 규약) |
| `~/.grok/` | `~/.grok/skills/` |
| `~/.agents/` | `~/.agents/skills/` |
| 없음 | `~/.agents/skills/` |

설치 전에 대상만 보려면 `--list-targets`, 특정 경로에 넣으려면 `--dest <경로> --all`,
최신본으로 교체하려면 `--force`를 씁니다(기본은 기존 설치를 건드리지 않고 `Skip`).
환경변수 `AI_SKILLS_DIR`·`CODEX_HOME`이 있으면 그 경로도 대상에 포함됩니다. 설치 직후
스킬별로 `SKILL.md`·`scripts/`·`references/` 존재를 검증해 결과를 출력합니다.

세 스킬을 모두 설치하는 것이 기본입니다. 플래그십만 깔면 통합 게이트가 형제 게이트를 찾지
못해 제출 판정 경로가 끊깁니다. 개별 설치는 `--name create-proposal-document`처럼 지정합니다.

**ChatGPT 웹처럼 파일 시스템이 없는 환경**에서는 스크립트를 실행할 수 없습니다.
`skills/create-best-proposal/` 폴더를 프로젝트 지식 파일로 업로드해 작성 지침으로 쓰고,
게이트 검증은 로컬 CLI에서 수행합니다.

비판적 선정·반영 기록: [critical-selection-2026-08.md](references/critical-selection-2026-08.md) ·
게이트 신뢰성 감사·수정 3회(2026-09): [gate-hardening-2026-09.md](references/gate-hardening-2026-09.md)
— 허위 통과 하드닝 → 장표 생산 레이어 → 산출물 해시 결속·판정 단일화

## 장표 생산 파이프라인 (PPTX)

```bash
# 장표 계획(slides.json) → PPTX. 좌표·색·폰트는 스크립트가 고정, 모델은 내용만 채운다
python skills/create-proposal-document/scripts/build_deck.py slides.json -o 제안서.pptx --strict
# 레이아웃 린트(리드문·REQ-ID·페이지 수·최소 폰트) + LibreOffice 렌더 + audit용 render 블록
python skills/create-proposal-document/scripts/deck_check.py 제안서.pptx --max-pages 40 \
  --exclude-cover-toc --require-req-ids --render --png-dir out/png --emit-render render.json
# 발표본은 같은 내용으로 규격만 바꿔 생성한다(폰트·밀도·분할이 함께 바뀐다)
python skills/create-proposal-document/scripts/build_deck.py slides.json -o 발표본.pptx --profile presentation
```

산출물 종류에 따라 규격이 달라집니다. `--profile presentation|executive-summary|detailed-submission`
(또는 `meta.output_profile`)로 고르면 폰트·밀도·표 행 수·조견표 분할이 함께 바뀝니다.

| 프로파일 | 용도 | 본문 | 장표당 텍스트 | 조견표 |
|---|---|---|---|---|
| `detailed-submission`(기본) | 인쇄·PDF 채점용 상세본 | 11pt | 600자 | 12행 |
| `presentation` | 회의실 스크린 발표본 | 18pt | 250자 | 6행 |
| `executive-summary` | 임원 의사결정 요약본 | 14pt | 400자 | 9행 |

규격은 `deck_profiles.py` 한 곳에만 있고 생성기와 검사기가 같이 읽습니다(폰트·밀도·행 수가
두 도구에서 갈리지 않습니다). 생성된 PPTX에는 어떤 규격으로 만들었는지 표시가 남아
`deck_check.py`가 인자 없이도 같은 기준으로 검사합니다. **표시가 없거나 이 버전이 모르는
값이면 제출 단계에서 차단합니다** — 외부에서 만든 덱은 `--profile`로 기준을 명시해야 합니다
(가장 느슨한 기본값으로 조용히 통과시키지 않습니다). 발주처 양식이 있으면 그 규격이 우선합니다.

제작기 안전장치: 슬라이드가 남아 있는 템플릿은 **거부**합니다(이전 고객명·금액이 그대로 남고
페이지 수가 어긋납니다 — 마스터·레이아웃만 있는 빈 템플릿을 씁니다). `rows_per_slide`는 양의
정수만 허용하고, 조견표는 입력 행 수와 출력 행 수를 대조해 유실을 차단합니다. 페이지 제한은
내부 카운터가 아니라 실제 슬라이드 수로 검사합니다. `deck_check.py`는 화면 밖으로 나가거나
25% 넘게 잘린 텍스트 도형을 차단합니다.

레이아웃 12종(표지·목차·간지·조견표(자동 분할)·표·프로세스·구성도·간트·인력·카드·불릿·마무리),
스키마와 페이지 배분 공식은 [deck-production.md](skills/create-proposal-document/references/deck-production.md).
전 구간 골든 예제: [fixtures/e2e-mini-rfp](skills/create-proposal-document/fixtures/e2e-mini-rfp/).
LibreOffice(`soffice`)가 없으면 렌더는 `NOT INSPECTED`로 남고 린트만 수행한다. 의존성: `python-pptx`.

## create-best-proposal 빠른 명령

```bash
# 작성 메타 → audit JSON
python skills/create-best-proposal/scripts/build_audit_from_meta.py meta.json -o audit.json

# 유형 C 대량 조견표
python skills/create-best-proposal/scripts/bulk_matrix.py requirements.json -o matrix.md

# 통합 게이트 (audit + 실제 문서 해시 대조)
python skills/create-best-proposal/scripts/unified_gate.py audit.json --doc 제안서.pptx --stage submission
python skills/create-best-proposal/scripts/unified_gate.py audit.json --audit-only   # 문서 없이 audit만 → AUDIT-VALID

# 원장 수치 ↔ 문서 대조 (37억 / 3,700,000,000 표기 변형 인식)
python skills/create-proposal-document/scripts/check_numbers.py 제안서.pptx --audit audit.json

# 완성도 2축
python skills/create-best-proposal/scripts/score_completeness.py audit.json   # 루트 score_completeness.py도 동일
```

## 제출 판정은 실제 파일에 묶인다

audit JSON은 **사람이 한 검토의 기록**입니다. 그 기록이 어느 파일에 적용되는지 확인하지 않으면,
검토 이후 가격·기간이 바뀐 문서에 과거 판정을 그대로 재사용하게 됩니다. 그래서 제출 판정은
파일 해시에 결속됩니다.

```bash
# 1) 장표 생성 → 2) 검사하며 실제 해시가 담긴 render 블록 산출
python .../build_deck.py slides.json -o 제안서.pptx --strict
python .../deck_check.py 제안서.pptx --render --emit-render render.json   # artifact_hash 포함
# 3) render.json을 meta에 반영 → audit 생성 → 4) 그 파일과 함께 판정
python .../unified_gate.py audit.json --doc 제안서.pptx --stage submission
```

| 상태 | 의미 |
|---|---|
| `SUBMISSION-READY` | `mode=submission` audit + 전달한 파일의 sha256이 audit의 `render/package.artifact_hash`와 **일치**할 때만 |
| `AUDIT-VALID` | `--audit-only` — audit 자체는 유효하나 실제 파일을 보지 않았다. 제출 판정 아님 |
| `DRAFT-READY` 등 | 해당 모드의 게이트 통과. 내부 진행용 |
| `CONDITIONAL-GO` | 내부 계속 진행만 허용. 외부 제출 클리어 아님 |
| `BLOCKED` / `DECISION_MEMO_ONLY` / `INVALID` | 차단 / 불참 결정 / 스키마·사용 오류 |

지켜지는 규칙:

- `mode=submission`인데 `--doc`이 없으면 **차단**합니다. `artifact_required: false`를 넣어도
  제출 모드의 렌더·해시 검증 의무는 취소되지 않습니다 — 입력값 하나로 검사를 끄지 못합니다.
- 전달한 파일의 해시가 audit과 다르면 차단합니다(검토 이후 변경 감지).
- 제출 모드의 `artifact_hash`는 실제 `sha256:<64 hex>`여야 하고, render와 package가 같은 파일을
  가리켜야 합니다. `sha256:proposal` 같은 문자열 라벨은 거절됩니다.
- 전달한 파일이 **실제로 열리는 OOXML 패키지**여야 합니다. `[Content_Types].xml`·`_rels/.rels`·
  본문 파트가 없거나 XML이 깨지면 사용 오류(exit 2)입니다 — 확장자만 `.pptx`인 ZIP은 통과하지
  못합니다.
- **수치는 게이트가 다시 계산합니다.** 금액·기간·수량을 `numbers[]` 원장에 적으면 합계
  (`components`)와 비율(`percent_of`)을 게이트가 재계산합니다. 제출 모드에서는 원장 없이
  `checks.arithmetic: true` 자기선언만으로 통과하지 못합니다 — 무엇을 검산했는지 보이지 않는
  '검산 완료'는 검증이 아닙니다. 원장 값이 실제 장표에 있는지는 `check_numbers.py`가 대조합니다
  (`37억` / `3,700,000,000` 같은 한글·숫자 표기 변형까지).
- **렌더 성공과 육안 승인은 다른 사실입니다.** 제출 모드는 `render.visual_review_approved`와
  `visual_reviewer`를 요구합니다. `deck_check.py`는 이 값을 항상 `false`로 기록하고, 썸네일을
  본 사람이 직접 바꿉니다. PDF 변환이 됐다는 것은 디자인 승인이 아닙니다.
- `mode=submission` audit을 `--stage draft`로 낮춰 검사하는 우회는 사용 오류(exit 2)입니다.
- 라벨은 `proposal_gate.readiness()` 한 곳에서 나옵니다 — CLI·**조치표 본문**·점수 보고서가 같은
  판정을 씁니다. `score_completeness.py`는 파일을 보지 않으므로 최대 `AUDIT-VALID`까지만
  보고합니다.

검토 상태와 준수 상태도 분리됩니다. `support: X`(미지원)이거나 `fit: GAP`인 요구를
`state: approved`로 둘 수 없고, 발주처가 허용한 예외만 `exception: {granted_by, evidence}`로
인정합니다. 조견표의 응답 위치는 `response_refs`, 주장을 뒷받침하는 출처는 `evidence_refs`로
따로 둡니다. 상세: [audit-schema.md](skills/create-winning-proposal/references/audit-schema.md).

## 테스트

로컬 실행 전 `pip install python-pptx`(CI는 자동 설치). 없으면 `test_deck_pipeline.py`가
`ModuleNotFoundError: No module named 'pptx'`로 실패한다 — 코드 결함이 아니라 의존성 누락이다.

```bash
cd ProposalSkills
python -m unittest discover -s . -p "test_*.py" -q
python skills/create-winning-proposal/scripts/test_proposal_gate.py -q
python skills/create-best-proposal/scripts/test_best_proposal.py -q
```

GitHub Actions(`.github/workflows/ci.yml`)가 Ubuntu·Windows × Python 3.10~3.12에서 같은
스위트를 실행한다(Ubuntu에는 LibreOffice를 설치해 렌더 경로까지 검증). 골든 단계는 해시 결속
계약 자체를 검사한다 — 문서 없는 제출 판정·해시 불일치·단계 우회가 각각 차단되는지, 파일과
해시가 맞을 때만 `SUBMISSION-READY`가 나오는지 확인한다.

회귀 테스트는 세 묶음이다.

- `test_gate_hardening.py` — 허위 통과·fail-open(노트·마스터·머리말 미검사, run 분할 과장어,
  문자열 불리언, draft audit의 SUBMISSION-READY 표시, cp949 콘솔 크래시).
- `test_deck_pipeline.py` — 미니 RFP 골든으로 slides.json→PPTX→deck_check→quality_gate→
  audit→unified_gate 전 구간 고정.
- `test_gate_integrity.py` — 산출물 해시 결속, 판정 단일화, 스키마 유실, 근거·준수 분리,
  차트 범주값 추출. 정상 대조군을 함께 둬서 과민 차단도 잡는다.
- `test_output_profiles.py` — 프로파일별 폰트·밀도 차이, 파일 표시 왕복, 생성기·검사기가
  같은 정의를 읽는지(드리프트 재발 방지).
- `test_numbers_ledger.py` — 합계·비율 재계산, 원장 없는 arithmetic 자기선언 차단,
  문서 대조(한글 표기 변형·숫자 경계).
- `test_gate_integrity2.py` — 검증 의무 우회(`artifact_required:false`), 열리지 않는 패키지,
  설명문 모순(`--explain` 경로 포함), 미수용 별칭, 템플릿 잔존 슬라이드, 조견표 행 유실,
  화면 밖 배치, enum 타입 오류.

OOXML 픽스처는 `ooxml_fixtures.py` 한 곳에서 만든다. 각 테스트가 zipfile로 조립하다 보니 필수
파트가 빠진 '열리지 않는 파일'이 양성 대조군으로 쓰였기 때문이다 — 실제 로더로 열리는지까지
테스트가 확인한다.

게이트 스크립트 공통 규약: exit 0=통과, 1=차단, 2=사용 오류·손상 파일·스키마 오류. audit JSON의
불리언은 `true`/`false`만 유효하며 `"yes"` 같은 문자열은 INVALID다. 확장자만 `.pptx`인 일반
ZIP은 "텍스트 없음" 통과가 아니라 사용 오류로 거절한다.

## 게이트가 검사하지 않는 것

통과를 "제출해도 된다"로 읽으면 안 됩니다. 자동 게이트는 **구조적 완결성**만 봅니다.

- **주장의 진위** — 근거가 첨부됐는지는 보지만 그 근거가 사실인지는 사람이 판단합니다.
- **원장에 없는 수치** — 게이트는 `numbers[]`에 적힌 값만 계산하고 대조합니다. 원장에 올리지
  않은 본문 숫자의 오류는 잡지 못하므로, 금액·기간·수량은 원장에 올려야 검증됩니다.
- **표 셀 넘침·가림** — `deck_check.py`가 화면 밖 배치와 큰 잘림은 잡지만, 셀 안에서 글자가
  넘치거나 도형끼리 겹쳐 가리는 것은 PNG 썸네일로 사람이 확인해야 합니다.
- **렌더 차이** — LibreOffice와 PowerPoint는 줄바꿈·폰트 대체가 다릅니다. 최종본은 발주처가
  쓰는 PowerPoint에서 한 번 열어 확인합니다.
- **업종 적합성** — 공공·기업·학교·병원별 판단 기준은 아직 스킬에 내장되어 있지 않습니다.

## 자료

- [스킬 대조 분석과 상호 개선 반영](references/skill-comparison-and-improvements.md)
- [스킬 자료 수집 노트](references/proposal-skill-materials-research.md)
- [관련 공개 Git 저장소](references/proposal-related-git-repositories.md)
- [39개 저장소·Gist 정밀 분석](references/repository-deep-audit.md)
- [10회 시뮬레이션과 개선 결과](references/simulation-report-10-runs.md)
- 종류별 시뮬레이션 리포트: 로컬 `simulation/output/SIMULATION_REPORT.md`(저장소 미포함, `.gitignore`)
