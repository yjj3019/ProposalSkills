# 제안서 문서 제작 스킬 자료 수집 노트

작성일: 2026-07-18
목적: 제안서의 문장, 문구, 구조, 시각 디자인, 근거, 검수 방식을 규격화할 스킬의 입력 자료와 설계를 정리한다.

## 1. 결론

스킬은 하나의 거대한 지침서보다 다음 세 층으로 구성하는 것이 적합하다.

1. `SKILL.md`: 작업 순서와 필수 품질 게이트만 둔다.
2. `references/`: 문체, 제안서 구조, 디자인, 근거, 검수 규칙을 분리한다.
3. `assets/`: 실제 DOCX 템플릿, 로고, 색상표, 글꼴, 표·도형 예시를 둔다.

제안서 작성의 우선순위는 `RFP 요구사항·평가항목 → 주장과 근거 → 독자별 메시지 → 문서 구조 → 시각 디자인` 순서로 고정한다. 외형부터 만들면 평가 누락과 근거 없는 홍보 문구를 놓치기 쉽다.

## 2. 이미 보유한 내부 자료

| 자료 | 재사용할 내용 | 스킬 내 권장 위치 |
|---|---|---|
| `docs/chatgpt-proposal-review-rules.md` | 요구사항, 모순, 근거, 버전·날짜, 용어, 인증·규정 검토와 심각도 | `references/review-checklist.md` |
| `claude/policies/Writing.md` | 결과 우선, 명확성, 과장 금지, 기업 문서 핵심 질문 | `references/writing-style.md` |
| `claude/modules/Proposal.md` | 11개 기본 장과 사업·기술·운영·위험 연결 | `references/proposal-structure.md` |
| `claude/workflows/ProposalWorkflow.md` | 문제 정의부터 최종화까지의 작성·일관성 검토 절차 | `SKILL.md` |
| `claude/reviewers/ProposalReviewer.md` | 평가자 관점, 실행 가능성, 요구사항 원문→제안서 추적 | `references/review-checklist.md` |
| `claude/reviewers/ProposalConsistencyReviewer.md` | 요구사항 정렬, 내부 일관성, 주장 무결성, 납품 위험 | `references/review-checklist.md` |
| `docs/codex-office-agent-rules.md` | DOCX 스타일, 제목 계층, 렌더링 검수, 버전 보존 | `SKILL.md` 및 산출 검수 절차 |

내부 자료는 좋은 출발점이지만 실제 회사의 문체·브랜드·표준 제안 문구와 과거 수주 문서는 아직 없다.

## 3. 외부 기준에서 채택할 규칙

### 3.1 쉬운 한국어와 문장 규격

- 국립국어원의 **쉬운 공공언어 쓰기 기본 길잡이**를 한국어 기준 자료로 삼는다. 어문 규범 준수뿐 아니라 어휘·문장·단락 차원의 정확성을 함께 다룬다.
- 공공 제안서는 일반 국민이 이해하기 쉬운 용어와 문장, 어문 규범에 맞는 한글 작성을 요구하는 국어기본법 취지를 반영한다.
- 기본 규칙은 다음과 같이 시작한다.
  - 한 문장에는 핵심 생각 하나만 둔다.
  - 주체와 행동을 분명히 하고 능동형을 우선한다.
  - 불필요한 명사화와 겹말을 줄인다.
  - 약어는 첫 등장에 원문과 뜻을 쓰고 이후 표기를 통일한다.
  - 전문 용어는 독자가 필요로 할 때만 쓰고 첫 등장에 설명한다.
  - 수치·기간·범위·책임 주체를 모호한 수식어보다 우선한다.

출처:

- [국립국어원, 쉬운 공공언어 쓰기 기본 길잡이](https://korean.go.kr/common/download.do%3Bfront%3D4DC3D24A016834DD1A7392F51B61BC16?c_file_name=901b4032-ae19-4457-87b7-e0f61c04378e.pdf&file_path=etcData&o_file_name=%E2%98%85%EC%89%AC%EC%9A%B4_%EA%B3%B5%EA%B3%B5%EC%96%B8%EC%96%B4_%EC%93%B0%EA%B8%B0_%EA%B8%B0%EB%B3%B8_%EA%B8%B8%EC%9E%A1%EC%9D%B4%28%EC%B5%9C%EC%A2%85_%EB%B0%B0%ED%8F%AC%29%EB%8B%A8%EB%A9%B4.pdf)
- [국립국어원, 공공언어와 국어기본법 제14조 안내](https://m.korean.go.kr/front/board/boardMovieView.do?b_movie_type=4&b_seq=301&board_id=14&mn_id=178&pageIndex=1&searchCondition=&searchKeyword=)
- [쉬운 우리말을 쓰자, 개선이 필요한 공공언어 사례](https://www.plainkorean.kr/ko/intro/notice.do?article.offset=0&articleLimit=10&articleNo=133713&mode=view)

### 3.2 평이한 언어의 국제 원칙

ISO 24495-1:2023은 평이한 언어 문서의 국제 기준이다. 전문은 유료 표준이므로 스킬에 복제하지 않고, 정식 구입본이 제공될 경우에만 세부 조항을 반영한다. 공개 정보에서 확인 가능한 범위에서는 독자가 필요한 정보를 찾고, 이해하고, 사용할 수 있도록 설계하는 원칙을 기준으로 삼는다.

- [ISO 24495-1:2023 공식 소개](https://www.iso.org/standard/78907.html)
- [GOV.UK Functional Standards writing style guide](https://www.gov.uk/government/publications/handbook-for-standard-managers/functional-standards-writing-style-guide)
- [GOV.UK content principles 연구 배경](https://www.gov.uk/government/publications/govuk-content-principles-conventions-and-research-background/govuk-content-principles-conventions-and-research-background)

GOV.UK 자료에서 채택할 실무 규칙:

- 짧은 문장과 단락, 일상어, 구체적 표현, 능동 동사를 사용한다.
- 독자와 과업을 먼저 정의한다.
- 요구사항은 결과 중심으로 쓰고, 책임 주체를 명확히 한다.
- 조직 고유의 말투와 평이한 언어를 구분한다. 전자는 브랜드 성격이고 후자는 이해 가능성의 기준이다.

### 3.3 제안서 구조와 평가 대응

조달·공공 제안서는 범용 목차보다 개별 RFP의 평가요소와 작성 지침이 우선한다. 따라서 스킬은 초안 작성 전에 반드시 요구사항 추적표를 만든다.

권장 추적표 필드:

| ID | RFP 원문 | 필수/선택 | 배점 | 응답 위치 | 증빙 | 담당 | 상태 |
|---|---|---|---:|---|---|---|---|

공통 목차는 RFP에 별도 형식이 없을 때만 사용한다.

1. 요약 및 제안 핵심
2. 고객 현황과 과제
3. 제안 범위와 원칙
4. 해결 방안 및 아키텍처
5. 수행 방법과 일정
6. 운영·지원 체계
7. 보안·품질·규정 준수
8. 위험, 가정, 의존성, 제외사항
9. 성과지표와 검증 방법
10. 가격 또는 상업 조건(요청 시)
11. 부록과 증빙

출처:

- [미국 Acquisition.gov, RFP 개발 시 평가요소와 제안서 작성지침 정렬](https://www.acquisition.gov/node/63341/printable/pdf)
- [조달청, 협상에 의한 총액계약 개요](https://www.pps.go.kr/kor/content.do?key=00726)
- [조달청, 제안서 평가가 포함된 종합심사제](https://www.pps.go.kr/kor/content.do?key=00730)

### 3.4 문서 시각 디자인과 접근성

브랜드 규격이 없을 때의 안전한 기본값:

- 제목은 Word의 제목 스타일로 계층화하고 수동 굵게만으로 제목을 만들지 않는다.
- 본문은 장식보다 읽기 쉬운 글꼴, 충분한 크기, 일관된 행간과 여백을 우선한다.
- 본문 색 대비는 WCAG 2.2의 일반 텍스트 4.5:1, 큰 텍스트 3:1을 최소 참조값으로 둔다.
- 색상만으로 상태나 의미를 구분하지 않고 레이블·기호·패턴을 병행한다.
- 표는 머리글, 단위, 출처, 기준일을 명시한다.
- 그림·도표에는 캡션과 대체 설명을 둔다.
- 페이지마다 메시지 우선순위가 드러나도록 제목, 핵심 문장, 근거 순으로 배치한다.

출처:

- [W3C, WCAG 2.2](https://www.w3.org/TR/WCAG22/)
- [W3C, 최소 명암비 해설](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum)
- [DWP 연구보고서 스타일: Word 제목 스타일과 계층](https://www.gov.uk/government/publications/dwp-research-reports-style-guide/dwp-research-reports-guidance)
- [GCA, 접근 가능한 문서·프레젠테이션 작성](https://www.gca.gov.uk/government-commercial-agency-style-guide/writing-accessible-content)

WCAG는 웹 표준이므로 인쇄 DOCX/PDF에 법적 적합성을 자동 주장하지 않는다. 여기서는 색 대비와 정보 중복 표현을 위한 보수적 디자인 기준으로만 사용한다.

## 4. 스킬에 넣을 자료의 권장 구조

```text
create-proposal-document/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── intake-and-requirements.md
│   ├── proposal-structure.md
│   ├── writing-style.md
│   ├── phrase-library.md
│   ├── visual-style.md
│   ├── evidence-and-claims.md
│   └── review-checklist.md
└── assets/
    ├── proposal-template.docx
    ├── brand-assets/
    └── approved-examples/
```

현재 단계에서는 별도 스크립트를 만들지 않는다. 반복 생성 과정에서 실제로 같은 코드가 두 번 이상 필요해질 때만 DOCX 생성·검수 스크립트를 추가한다.

## 5. 회사에서 수집해야 할 원자료

### 최우선

- 최근 수주 제안서 3~5건과 탈락 제안서 1~2건
- 원본 RFP, 평가표, 질의응답, 제출 형식
- 회사 공식 브랜드 가이드: 로고, 색상, 글꼴, 최소 여백, 금지 사례
- 승인된 회사 소개, 실적, 인증서, 파트너 등급, 제품명과 공식 표기
- 법무·보안·재무가 승인한 표준 문구와 면책·가정·제외 문구

### 문장·문구 규격화용

- 경영진 요약의 승인 사례
- 문제 정의, 차별점, 기대효과, 수행 방안, 위험 완화, 결론 문구 사례
- 금지 표현: 과장어, 보장 표현, 경쟁사 비방, 검증되지 않은 최고·유일·완벽 표현
- 용어집: 한글명, 영문명, 약어, 첫 등장 표기, 금지 변형
- 숫자 표기: 날짜, 통화, 백분율, 단위, 버전, 범위, 반올림 규칙
- 말투: 존대 수준, 문장 종결형, 자사/고객 호칭, 능동·수동 선호

### 시각 규격화용

- 표지, 목차, 장표지, 본문, 표, 아키텍처, 일정, 조직도, 사례 페이지의 승인 예시
- 용지 크기, 여백, 머리말·꼬리말, 페이지 번호, 제목 단계별 글꼴과 크기
- 표·차트의 색상, 선, 강조, 데이터 레이블, 출처 표기 규칙
- 이미지 라이선스, 인물·고객 로고 사용 권한, 캡션과 대체 텍스트 규칙
- DOCX와 최종 PDF 샘플을 함께 수집해 변환 시 깨짐을 확인한다.

## 6. 원자료 정규화 표준

수집 자료를 그대로 넣지 말고 각 규칙을 다음 형식으로 정규화한다.

```yaml
id: WR-001
category: writing
rule: 핵심 결과를 문단 첫 문장에 쓴다.
applies_to: [executive-summary, section-opening]
priority: required
good_example: "본 사업은 장애 복구 시간을 30분 이내로 단축하는 것을 목표로 합니다."
bad_example: "당사는 혁신적인 기술을 바탕으로 최상의 서비스를 제공합니다."
evidence_required: true
source: "사내 제안서 작성 기준 v2.1, 4쪽"
owner: "제안전략팀"
reviewed_at: "YYYY-MM-DD"
```

이 구조는 규칙의 출처·책임자·최종 검토일을 남겨 오래된 인증, 실적, 제품 버전이 재사용되는 일을 줄인다.

## 7. 초기 문구 라이브러리 분류

완성 문장을 무조건 삽입하는 방식보다, 사실 입력칸이 있는 패턴으로 관리한다.

| 목적 | 패턴 |
|---|---|
| 고객 과제 | `[현재 상태]로 인해 [영향]이 발생하고 있으며, [기한/조건]까지 [목표 상태]가 필요합니다.` |
| 제안 핵심 | `당사는 [범위]에 [방법]을 적용해 [측정 가능한 결과]를 달성하도록 제안합니다.` |
| 차별점 | `일반적인 [대안]과 달리, 본 방안은 [검증 가능한 차이]를 통해 [고객 효과]를 제공합니다.` |
| 일정 | `[단계]는 [기간] 동안 수행하며, 완료 기준은 [산출물/승인 조건]입니다.` |
| 위험 | `[위험]이 발생할 경우 [영향]이 예상됩니다. [책임 주체]는 [예방/완화 조치]로 이를 관리합니다.` |
| 가정 | `본 일정과 비용은 [가정]을 전제로 하며, 변경 시 [영향/변경 절차]를 적용합니다.` |
| 근거 부족 | `[unverified] [주장] — [출처/버전/기준일] 확인 후 확정합니다.` |

“최고”, “완벽”, “혁신적”, “획기적”, “100%”, “무중단”, “완전 자동화”, “위험 제로”는 객관적 근거와 적용 범위가 없으면 사용하지 않는다.

## 8. 품질 게이트

제출 전 한 번의 통합 검수에서 다음을 확인한다.

1. 모든 필수 RFP 요구사항에 응답 위치와 증빙이 있는가.
2. 요약, 본문, 표, 그림, 부록의 수치·버전·일정·책임이 일치하는가.
3. 인증, 실적, 성능, 지원기간, 규정 준수 주장에 출처·버전·기준일·범위가 있는가.
4. 고객 과제와 제안 기능이 측정 가능한 성과로 연결되는가.
5. 가정, 의존성, 제외사항, 고객 책임이 숨겨져 있지 않은가.
6. 제목 계층, 표, 캡션, 색 대비, 페이지 흐름이 읽기 쉬운가.
7. DOCX를 다시 열고 PDF로 렌더링했을 때 줄바꿈, 표, 도형, 글꼴이 깨지지 않는가.

## 9. 다음 단계

스킬 제작 전에 사용자에게서 아래 세 가지만 받으면 된다.

1. 주 대상: 공공 입찰, 민간 영업, 기술 제안 중 우선순위
2. 대표 RFP 1건과 승인된 제안서 1건
3. 브랜드 가이드 또는 회사 템플릿 DOCX 1건

그다음 이 연구 노트를 분해해 `references/`를 만들고, 실제 템플릿을 `assets/`에 넣은 뒤 `skill-creator`의 초기화·검증 절차를 실행한다.
