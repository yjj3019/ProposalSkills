# Proposal structure (standard outlines by type)

Generalized from multiple winning proposals. An RFP-prescribed outline overrides these standards.
Otherwise use the standards below, placing high-weight evaluation topics earlier and giving them more space.

## Engagement → skeleton

`context.engagement` determines the skeleton; record the chosen one in audit `proposal_archetype`.
The gate compares them, blocking a build outline for maintenance work unless the buyer prescribed it
(record the basis in `archetype_rationale`).

| engagement | Skeleton | Required sections |
|---|---|---|
| `build`, `migrate` | Type A build | Project scope · build approach · schedule · testing/acceptance · delivery organization |
| `operate`, `service-improvement` | Type B maintenance | Support scope/targets · support organization · SLA · incident response |
| `product-selection` | Type C technical response | Requirements response · products/specifications · evidence |
| `education`, `consulting`, `policy` | **None** | — |

The last row is intentionally empty for the same reason this repository has only one sector profile:
there is no evidence here for education, consulting, or policy proposal outlines. State the absence rather than inventing one.
The gate asks for a rationale if an IT-build outline is reused for those engagements.

Section names are loosely matched by keyword (Korean examples "시험 및 검수" and "테스트 방안" both count as testing/acceptance).
Without `sections[]`, section checks do not run.

## Type A. Build proposal (system/platform/data center)

Korean proposal outline example (retain the proposal-language input):

```
(조견표 — 공공·금융이면 목차 직후)
Ⅰ. 제안 개요
   1. 사업의 목적 및 배경      ← Customer environmental change → challenge → project purpose (three-part logic)
   2. 사업 범위                ← Two-part table: delivery scope / management-support scope
   3. 사업 추진 전략           ← Environment → considerations → critical success factors → N strategies
   4. 제안의 특징 및 장점      ← Three perspectives: solution / delivery / proposer
   5. 기대효과                 ← Separate qualitative/quantitative benefits; quantify with formulas/assumptions
Ⅱ. 제안 업체 현황
   1. 일반 현황(연혁·재무·신용등급)  2. 조직 및 인원(기술등급·자격증)
   3. 유사사업 수행 실적(표: 사업명/발주처/기간/제품/범위)
Ⅲ. 제안 기술 부문 (at least 60% of body)
   1. 상세 추진전략(제품 소개·특장점·단계별 로드맵: 1단계→2단계→3단계)
   2. 상세 구축방안(전체 구성도 → 영역별 구성: 관리풀/컴퓨팅/스토리지/네트워크
      → 장비 명세 → 보안 → 가용성/HA → 백업·복구)
Ⅳ. 사업관리 및 품질보증
   1. 추진일정(간트)  2. 추진체계(조직도·R&R)  3. 사업관리(7대 영역)
   4. 위험요소 관리  5. 품질보증 계획
Ⅴ. 지원 부문
   1. 테스트 방안(항목표: 가용성/기능/성능/장애복구)  2. 기술이전·교육
   3. 사업종료 후 지원(유지보수 체계·SLA)  4. 기타 지원
Ⅵ. 참여 업체 및 인력
   업체별 R&R, 인력 프로필(성명/경력/자격/투입공수 M/M), 상호 협력방안
Ⅶ. 기타 (하자보수 방안 등)
별첨: 견적서, 인증서, 약어표
```

## Type B. Maintenance and technical support proposal

Korean proposal outline example:

```
조견표 (제안요건 → 수용여부 → 제안내용 → 페이지)
Ⅰ. 일반 부문: 제안개요(목적·배경/추진전략/특장점/기대효과), 일반현황, 실적
Ⅱ. 기술지원 부문
   1. 추진전략(목표·계획/전략·범위)
   2. 기술지원 방안: 지원대상 표(제품/수량/SLA등급) + 연간 기술지원 방안 표
      (운영지원: Patch·이전설치·현행화·교육·기술문의·비상대기 / 장애지원: 처리·원인분석 L1~L3)
   3. 서비스 지원 체계: 1선(전담)–2선(본사)–3선(제조사 글로벌 기술지원) 에스컬레이션 도식,
      벤더 SLA 표(심각도 1~4 × 응답시간), 파트너 인증·확약서
Ⅲ. 유지보수 관리 부문
   1. 유지보수 방안(구조진단, 작업 프로세스 정형화, SW 구성/변경, 히스토리 관리)
   2. 장애 예방/방지 대책(예방점검 항목표, 점검 산출물 양식, 위험관리 체계)
   3. 전사 과제 지원 계획(표준화 협업, 세미나, 공동 프로젝트)
Ⅳ. 사업관리 부문: 인력관리(수행조직/프로필), 수행일정, 사업관리 7대영역, 정보보호
Ⅴ. 사업지원 부문: 교육훈련(무상 운영자교육 + 벤더 유상교육 과정명 명시)
Ⅵ. 기타: 추가 제안(컨설팅·데모센터·솔루션 등 — 차별화 카드)
Ⅶ. 별첨: 입찰가격서, 자격증 사본, 약어표
```

## Type C. Technical response / standard-product selection

- Document structure = RFP item numbering. No arbitrary reordering.
- Typical order: common topics (product introduction/roadmap/support level/incident response/references/product information) →
  technical topics (basic capabilities: architecture/development/operations/performance; specialized capabilities; competitive advantages).
- **Show the corresponding item number and status in every slide corner**.
  Korean example: `(완료) 26. 플랫폼에서 수집·제공하는 Log의 범위`.
- Answer unsupported items with unsupported + alternative/roadmap, never blanks.
  Korean examples: "미지원 + 대안/로드맵", "DR 구축 사례 없음", "제조사 Support 정책에 따름" for commercial software.
- Respond to tabular questions with a **question/answer table** (standard-product response practice):
  `Number | Category | Item | Content | Supported (O/X) | Product | Additional explanation`.
  If an item has multiple detailed questions, give support status for each line.
  State constraints explicitly in Additional explanation (Korean example: "HA 구성 시 Fencing 권장 → IPMI 장치 필요").

## Mapping variant engagements (outside the three types)

| Engagement | Base type | Adjustments |
|---|---|---|
| Outsourcing/managed operations (DCO etc.) | B variant | Add service boundaries, R&R, transition/takeover, Exit |
| Staff dispatch/resident operations | B variant | Apply content-patterns §7: individual capability, work boundaries, replacement/handover, single-person dependency, individual delivery evidence |
| Migration/modernization (U2L etc.) | A variant | Replace chapter Ⅲ with content-patterns §4 methodology (Waves/gates/rollback) |
| DR/BCP/resilience design | A variant | Chapter Ⅲ: failure assumptions → recovery objectives (RTO/RPO) → protection patterns → validation |
| Standardization/policy decision support | C variant | Selection criteria → candidate comparison → recommendation → governance/transition roadmap; same comparison criteria and sources |

### Non-RFP joint initiatives/proactive proposals

Without settled purchasing requirements, label the artifact a **discovery/decision draft**, not a submission bid.
Minimum flow: `Decision needed → shared opportunity/hypotheses → target users/work →
both parties' assets/shared value → pilot scope/success criteria → Give/Get/RACI → economic scenarios →
IP/data/brand/exclusivity → risks/stop/Exit conditions → next decision/owner`.
Visually distinguish facts, hypotheses, questions, decisions, commitments.
Before approval, do not represent hypotheses as contractual terms or confirmed benefits.

## Page allocation

The overriding basis is **evaluation weight**: allocate proportionally, reserving space for high-weight/high-risk sections first.
Conventional ranges when no evaluation table exists (analyzed samples):

| Chapter | Type A (build) | Type B (maintenance) |
|---|---|---|
| Proposal overview (Ⅰ) | 8~12% | 10~15% |
| Company/track record (Ⅱ) | 8~12% | 10~15% |
| Technical/support (Ⅲ) | **55~65%** | **45~55%** |
| Management/quality (Ⅳ) | 10~15% | 10~15% |
| Support/training/other (Ⅴ~Ⅶ) | 8~12% | 15~20% |

- Compliance matrix: separate 2~5p proportional to requirement count. Exclude cover/contents/dividers from allocation,
  but check whether they count toward limits in bid-and-submission.md §5.
- If over the limit, merge low-weight chapters or move detail to appendices. Do not shrink fonts.
- Total-length guide when unrestricted: build slides 60~120p, maintenance 40~90p,
  technical responses question count × 1~2p. Unsupported expansion causes deductions:
  delete/merge first based on the lead-statement test.

## Presentation summary (PT deck) — extracting from the main proposal

The summary is a **separate document reorganized in evaluator-question order**, not a shrunken copy.

- **Slide count = presentation time**: 40~60 seconds per slide (10 minutes ≈ 10~15 slides, excluding cover/contents).
  Put Q&A backup slides in an appendix after the main presentation; they do not count as presentation content.
- **Standard flow**: conclusion (why us, 1 slide) → understanding/key problems → proposal core (2~3 differentiators) →
  execution/schedule/organization → risk/quality → commitment summary (1 condensed matrix slide) → closing.
- **Stricter one-slide/one-message**: less text than the main proposal; lead + one diagram/table.
  When consolidating body pages, condense evidence tables but retain source/reference dates.
- **Synchronize with the main proposal**: all summary figures/promises must match (cross-check required).
  No new summary-only claims. Footnote each slide's corresponding main-proposal page.
- Apply review gates 2 (lead story), 3 (exaggerations), 4 (numeric consistency against main proposal), 7 (visual), 8 (render).

## Page (slide) composition — all types

Every slide follows this top-to-bottom order; message priority must match visual order.

1. **Header**: document name + outline breadcrumb. Korean example: `Ⅲ. 제안기술 부문 > 1. 상세 추진전략`.
2. **Page title**: noun form. Korean example: "네트워크 구성 방안".
3. **Lead (governing message)**: 1~3 lines; complete sentence expressing the page's conclusion.
   Good Korean example: "관리 노드 3중화와 로드밸런서 이중화로 단일 장애점 없는 서비스를 제공합니다."
   Bad Korean example: "네트워크 구성에 대해 설명합니다." (no substantive content).
4. **Body evidence**: one diagram or 1~2 tables; favor structure over text lists.
5. **Caption/source/requirement number**: sources/reference dates for figures/quotations, corresponding REQ ID.

Lead-statement test: does reading only all slide leads establish the proposal story?
If not, delete/merge/reorder first. Do not solve it by increasing page count.
