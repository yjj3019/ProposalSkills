# Phrase library (phrase-library)

The patterns below are Korean proposal examples; retain their wording and fact slots verbatim.

**Fill patterns with facts; do not copy finished sentences.** If a Korean `{슬롯}` cannot be filled with an actual fact,
do not use the sentence. Inventing facts to fill empty slots is the worst failure.

## Usage rules

1. `{}` denotes fact slots: fill only from the RFP, customer material, or verified web information.
2. Without evidence to fill a slot, follow the `[unverified]` procedure in `evidence-and-claims.md`.
3. Vary wording when repeating a pattern 3 or more times in one document to avoid conspicuous copying.

## A. Purpose and background (chapter Ⅰ)

| Use | Korean pattern |
|---|---|
| Project background (three-part logic) | `{고객}은(는) {환경 변화/현황} 상황에서 {당면 과제}에 직면해 있으며, 본 사업은 {목적}을 달성하고자 합니다.` |
| Purpose summary | `본 제안은 {핵심 요구 1~3개 요약}을 위한 {솔루션/서비스}의 {구축/제공} 방안을 제시합니다.` |
| Strategic direction | `{고객 환경 이해}를 바탕으로 {고려요소}를 반영한 {N}대 추진전략을 수립하였습니다.` |

## B. Capability and track record (chapter Ⅱ)

| Use | Korean pattern |
|---|---|
| Company introduction | `당사는 {설립연도}년 설립 이래 {전문 분야}에 전념해 온 {포지셔닝}이며, {대표 근거: 파트너 등급/고객 수/유지율}을 보유하고 있습니다.` |
| Track-record emphasis | `{산업군} {고객 수}개사 대상 {서비스} 수행 실적({기간}, 별첨 실적표 참조)을 통해 {발주처} 환경에 검증된 방법론을 적용합니다.` |
| Staff capability | `투입 인력 {N}명 전원 {자격/등급} 보유, 평균 경력 {N}년({기준일} 기준)입니다.` |
| Partnership | `{벤더} {파트너 등급} 자격으로 {혜택: 기술지원 에스컬레이션/로드맵 사전 공유/교육}을 제공받아 지원합니다.` |

## C. Technical approach (chapter Ⅲ)

| Use | Korean pattern |
|---|---|
| Architecture conclusion | `{구성 방식}으로 {품질 속성: 가용성/확장성/보안성}을 확보합니다.` Example: "관리 노드 3중화와 로드밸런서 이중화로 단일 장애점 없는 관리 체계를 구성합니다." |
| Product selection rationale | `{제품}은 {객관 지표: 시장 점유율/커뮤니티 규모/지원 기간}에서 {비교 우위}를 보이며(출처: {기관, 연도}), {고객 요구 X}에 부합합니다.` |
| Phased roadmap | `1단계({기간}) {범위} → 2단계({기간}) {범위} → 3단계({기간}) {범위}로 위험을 분산하며 확장합니다.` |
| Migration | `{현행 환경}에서 {목표 환경}으로 {방법론/도구}를 활용해 이관하며, {검증 절차}로 전환 위험을 통제합니다.` |
| Unsupported item (type C) | `현재 {기능}은 미지원이나, {대안} 적용이 가능하며 {버전/시점} 로드맵에 반영되어 있습니다.` (no blanks or evasive answers) |

## D. Support and SLA (maintenance)

| Use | Korean pattern |
|---|---|
| Support structure | `1선({전담 조직}) → 2선({본사 기술팀}) → 3선({제조사 글로벌 기술지원 조직})의 3단계 에스컬레이션 체계로 {목표: 신속한 원인 분석과 해결}을 보장합니다.` |
| SLA commitment | `심각도 {등급} 장애 시 {응답 시간} 이내 응답, {복구 목표}를 목표로 대응합니다(세부 기준: SLA 표 참조).` |
| Preventive activities | `{주기} 정기점검({N}개 항목)과 {산출물: 점검확인서/월간보고서} 제출로 장애를 사전 예방합니다.` |
| Training provision | `운영자 대상 {과정명} 교육({시간/회수})을 무상 제공하며, {벤더 공식 교육}은 {조건}으로 지원합니다.` |

## E. Schedule and management (chapter Ⅳ)

| Use | Korean pattern |
|---|---|
| Schedule commitment | `총 {기간} 중 {마일스톤}을 {시점}까지 완료합니다(전제: {가정 — 장비 납기/고객 승인 일정 등}).` |
| Risk management | `{위험 항목}에 대해 {완화 방안}을 사전 적용하고, 발생 시 {대응 절차}로 영향도를 {목표 수준} 이내로 관리합니다.` |
| Quality assurance | `{방법론/표준}에 따라 {검토 단계}를 수행하며, 산출물은 {검수 절차}를 거쳐 제출합니다.` |

## F. Expected benefits (quantitative claims)

| Use | Korean pattern |
|---|---|
| Quantitative benefit | `{항목} {수치}{단위} {개선/절감} 예상(산식: {산식}, 전제: {전제조건}).` Do not state figures without formulas and assumptions. |
| Qualitative benefit | `{활동}을 통해 {효과: 운영 표준화/기술 내재화/대응 속도 향상}을 기대할 수 있습니다.` |

## English authoring examples

Fill the patterns below with facts for English output. Apply the same discipline as Korean: if a `{slot}` cannot be filled,
do not use the sentence. Follow the English banned-word dictionary in writing-style.md. Write conclusion (answer) →
evidence → implications for the buyer.

| Purpose | English example |
|---|---|
| Customer problem | `{Current condition} causes {business/operational impact}. {Buyer} needs {target state} by {date/condition}.` |
| Core proposal | `We propose {scope and method} to achieve {measurable outcome}, while controlling {material risk}.` |
| Requirement response | `Comply. {Actor} will {action} using {method}. Evidence/acceptance: {artifact or criterion}.` |
| Partial compliance | `Partially comply. {covered scope} is met; {gap} requires {decision/change} by {owner/date}.` |
| Capability | `{Buyer need} is addressed by {mechanism}, producing {operating effect} within {scope/boundary}. Evidence: {approved source or acceptance test}.` |
| Architecture conclusion | `{configuration} removes {single point of failure}, targeting {quality attribute: availability/scalability}.` |
| Differentiation | `Unlike {defined alternative}, this approach {verifiable difference}, which enables {buyer outcome}.` |
| SLA/support | `For severity {level}, {actor} responds within {time} and targets {recovery objective} (see SLA table).` |
| Schedule | `{Phase} runs from {start} to {finish}. Exit requires {deliverable and approval}.` |
| Risk | `If {risk} occurs, {impact} follows. {Owner} reduces likelihood/impact via {control}, monitored by {indicator}.` |
| Assumption | `This schedule/cost assumes {condition}. If it changes, {impact and change process} apply.` |
| Quantitative benefit | `Estimated {figure}{unit} {improvement/saving} against {baseline} (method: {formula}, assumptions: {conditions}).` |
| Unsupported claim | `[unverified] {claim} — confirm {source, version, date, scope} before approval.` |

Brief English style rules (supplementing writing-style.md): one concept per sentence, active voice, expand acronyms on first mention
and use them consistently thereafter, conclusion first. Meet buyer page/word limits by merging low-weight sections,
not by shrinking fonts.

## Registering new phrases (library extension)

Append reusable phrases/rules at the end of this file using the schema below. Korean example values remain verbatim:

```yaml
- id: PHR-001
  category: 실적강조            # Purpose/background; capability/track record; technical approach; support/SLA; schedule/management; expected benefits
  rule: "패턴 문장 ({슬롯} 포함)"
  applies_to: [A, B, C]         # Applicable proposal types
  priority: high                # high/medium/low
  good_example: "실제 채워 쓴 좋은 예"
  bad_example: "슬롯 없이 과장한 나쁜 예"
  evidence_required: true       # Whether accompanying evidence table/source is required
  source: "출처 제안서/가이드"
  owner: "등록자"
  reviewed_at: "YYYY-MM-DD"
```
