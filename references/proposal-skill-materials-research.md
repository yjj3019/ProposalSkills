# Proposal-document skill research notes

Written: 2026-07-18
Purpose: organize inputs and design for a skill standardizing proposal sentences, phrases, structure,
visual design, evidence, and review.

## 1. Conclusions

Use three layers rather than one enormous instruction document:

1. `SKILL.md`: workflow and mandatory quality gates only.
2. `references/`: separate style, proposal structure, design, evidence, and review rules.
3. `assets/`: actual DOCX templates, logos, palettes, fonts, and table/shape examples.

Fix writing priority as RFP requirements/evaluation criteria → claims/evidence → reader-specific messages →
document structure → visual design. Starting with appearance risks missed criteria and unsupported promotional copy.

## 2. Existing internal material

| Material | Reusable content | Recommended skill location |
|---|---|---|
| `docs/chatgpt-proposal-review-rules.md` | Requirements, contradictions, evidence, versions/dates, terminology, certification/regulatory review and severity | `references/review-checklist.md` |
| `claude/policies/Writing.md` | Outcome first, clarity, no exaggeration, key corporate-document questions | `references/writing-style.md` |
| `claude/modules/Proposal.md` | 11 basic chapters and business/technical/operational/risk linkage | `references/proposal-structure.md` |
| `claude/workflows/ProposalWorkflow.md` | Writing/consistency review from problem definition to finalization | `SKILL.md` |
| `claude/reviewers/ProposalReviewer.md` | Evaluator perspective, feasibility, RFP-source→proposal tracing | `references/review-checklist.md` |
| `claude/reviewers/ProposalConsistencyReviewer.md` | Requirement alignment, internal consistency, claim integrity, delivery risk | `references/review-checklist.md` |
| `docs/codex-office-agent-rules.md` | DOCX styles, heading hierarchy, render review, version preservation | `SKILL.md` and artifact-review procedure |

Internal material is a useful starting point, but actual company style/brand/standard wording and previous winning
proposals are not yet available.

## 3. Rules to adopt from external standards

### 3.1 Plain Korean and sentence standards

- Use the National Institute of Korean Language's **Basic Guide to Writing Plain Public Language** as a Korean
  reference, covering vocabulary/sentence/paragraph accuracy alongside language conventions.
- Public proposals should reflect the Framework Act on Korean Language's intent: understandable terms/sentences
  and Korean writing consistent with language rules.
- Initial rules:
  - One core idea per sentence.
  - Clear actors/actions; prefer active voice.
  - Reduce unnecessary nominalization/redundancy.
  - Expand/explain acronyms at first use, then keep notation consistent.
  - Use specialist terms only when readers need them; explain first use.
  - Prefer figures/terms/scope/responsible parties over vague modifiers.

Sources:

- [National Institute of Korean Language: Basic Guide to Writing Plain Public Language](https://korean.go.kr/common/download.do%3Bfront%3D4DC3D24A016834DD1A7392F51B61BC16?c_file_name=901b4032-ae19-4457-87b7-e0f61c04378e.pdf&file_path=etcData&o_file_name=%E2%98%85%EC%89%AC%EC%9A%B4_%EA%B3%B5%EA%B3%B5%EC%96%B8%EC%96%B4_%EC%93%B0%EA%B8%B0_%EA%B8%B0%EB%B3%B8_%EA%B8%B8%EC%9E%A1%EC%9D%B4%28%EC%B5%9C%EC%A2%85_%EB%B0%B0%ED%8F%AC%29%EB%8B%A8%EB%A9%B4.pdf)
- [National Institute of Korean Language: public language and Article 14](https://m.korean.go.kr/front/board/boardMovieView.do?b_movie_type=4&b_seq=301&board_id=14&mn_id=178&pageIndex=1&searchCondition=&searchKeyword=)
- [Plain Korean: public-language examples needing improvement](https://www.plainkorean.kr/ko/intro/notice.do?article.offset=0&articleLimit=10&articleNo=133713&mode=view)

### 3.2 International plain-language principles

ISO 24495-1:2023 is an international plain-language standard. Its full text is paid; do not reproduce it in the skill.
Reflect detailed clauses only when a legitimately purchased copy is supplied. Publicly available information supports
designing documents so readers can find, understand, and use needed information.

- [ISO 24495-1:2023 official overview](https://www.iso.org/standard/78907.html)
- [GOV.UK Functional Standards writing style guide](https://www.gov.uk/government/publications/handbook-for-standard-managers/functional-standards-writing-style-guide)
- [GOV.UK content principles research background](https://www.gov.uk/government/publications/govuk-content-principles-conventions-and-research-background/govuk-content-principles-conventions-and-research-background)

Practical GOV.UK rules to adopt:

- Short sentences/paragraphs, everyday language, concrete wording, active verbs.
- Define readers/tasks first.
- Outcome-centered requirements with clear responsible parties.
- Distinguish organizational voice (brand character) from plain language (understandability).

### 3.3 Proposal structure and evaluation alignment

Individual RFP criteria/instructions override generic outlines in procurement/public proposals.
Always create a traceability matrix before drafting.

Recommended fields:

| ID | RFP source text | Mandatory/optional | Weight | Response location | Evidence | Owner | Status |
|---|---|---|---:|---|---|---|---|

Use a common outline only when the RFP specifies none:

1. Executive summary and core proposal.
2. Customer current state/challenges.
3. Scope/principles.
4. Solution/architecture.
5. Execution/schedule.
6. Operations/support.
7. Security/quality/compliance.
8. Risks/assumptions/dependencies/exclusions.
9. Success metrics/verification.
10. Price/commercial terms (if requested).
11. Appendices/evidence.

Sources:

- [US Acquisition.gov: aligning evaluation factors and proposal instructions](https://www.acquisition.gov/node/63341/printable/pdf)
- [Korean Public Procurement Service: negotiated lump-sum contracts](https://www.pps.go.kr/kor/content.do?key=00726)
- [Korean Public Procurement Service: comprehensive review including proposal evaluation](https://www.pps.go.kr/kor/content.do?key=00730)

### 3.4 Visual design and accessibility

Safe defaults without brand specifications:

- Use Word heading styles/hierarchy; manual bold alone does not make headings.
- Prioritize readable fonts, sufficient size, consistent line spacing/margins over decoration.
- Use WCAG 2.2 contrast references: 4.5:1 normal text, 3:1 large text.
- Do not convey meaning/status by color alone; add labels/symbols/patterns.
- Tables need headers/units/sources/as-of dates.
- Figures/charts need captions/alternative descriptions.
- Show message priority through title → key sentence → evidence on each page.

Sources:

- [W3C WCAG 2.2](https://www.w3.org/TR/WCAG22/)
- [W3C: minimum contrast explanation](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum)
- [DWP research report style: Word heading styles/hierarchy](https://www.gov.uk/government/publications/dwp-research-reports-style-guide/dwp-research-reports-guidance)
- [GCA: accessible documents/presentations](https://www.gca.gov.uk/government-commercial-agency-style-guide/writing-accessible-content)

WCAG is a web standard; do not automatically claim legal compliance for printed DOCX/PDF.
Use it here only as a conservative contrast/redundant-information design reference.

## 4. Recommended skill material structure

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

Do not add scripts at this stage. Add DOCX generation/review scripts only when repeated production actually
needs the same code at least twice.

## 5. Source material to collect from the company

### Highest priority

- 3–5 recent winning proposals and 1–2 losing proposals.
- Original RFP/evaluation sheet/Q&A/output requirements.
- Official brand guide: logos/colors/fonts/minimum whitespace/prohibited examples.
- Approved company introduction/track record/certificates/partner tiers/product names/official notation.
- Legal/security/finance-approved standard wording and disclaimers/assumptions/exclusions.

### Sentence/phrase standardization

- Approved executive summaries.
- Examples of problem definitions/differentiation/expected effects/execution/risk mitigation/conclusions.
- Prohibited exaggeration/guarantees/competitor disparagement/unverified superiority-uniqueness-perfection claims.
- Glossary: Korean/English names/acronyms/first-use notation/prohibited variants.
- Number notation: dates/currencies/percentages/units/versions/ranges/rounding.
- Voice: politeness/endings/company-customer references/active-passive preference.

### Visual standardization

- Approved cover/TOC/section cover/body/table/architecture/schedule/org-chart/case pages.
- Paper size/margins/headers-footers/page numbers/heading-level fonts and sizes.
- Table/chart colors/lines/emphasis/data labels/source rules.
- Image licenses/people-customer-logo permissions/caption-alt-text rules.
- Collect DOCX and final PDF together to identify conversion breakage.

## 6. Source-material normalization standard

Do not insert collected material unchanged; normalize each rule as follows.
Korean example values are preserved verbatim:

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

This retains sources/owners/last-review dates and reduces reuse of stale certifications, track records, or product versions.

## 7. Initial phrase-library categories

Maintain fact-slot patterns rather than automatically inserting completed sentences.
Korean proposal patterns below are preserved verbatim.

| Purpose | Korean example pattern |
|---|---|
| Customer challenge | `[현재 상태]로 인해 [영향]이 발생하고 있으며, [기한/조건]까지 [목표 상태]가 필요합니다.` |
| Core proposal | `당사는 [범위]에 [방법]을 적용해 [측정 가능한 결과]를 달성하도록 제안합니다.` |
| Differentiation | `일반적인 [대안]과 달리, 본 방안은 [검증 가능한 차이]를 통해 [고객 효과]를 제공합니다.` |
| Schedule | `[단계]는 [기간] 동안 수행하며, 완료 기준은 [산출물/승인 조건]입니다.` |
| Risk | `[위험]이 발생할 경우 [영향]이 예상됩니다. [책임 주체]는 [예방/완화 조치]로 이를 관리합니다.` |
| Assumption | `본 일정과 비용은 [가정]을 전제로 하며, 변경 시 [영향/변경 절차]를 적용합니다.` |
| Insufficient evidence | `[unverified] [주장] — [출처/버전/기준일] 확인 후 확정합니다.` |

Do not use these Korean overclaim examples without objective evidence and scope:
“최고”, “완벽”, “혁신적”, “획기적”, “100%”, “무중단”, “완전 자동화”, “위험 제로”.

## 8. Quality gates

In one integrated pre-submission review, check:

1. Every mandatory RFP requirement has response locations/evidence.
2. Figures/versions/schedules/responsibilities match across summary/body/tables/figures/appendices.
3. Certification/track-record/performance/support-period/compliance claims have sources/versions/as-of dates/scope.
4. Customer challenges/proposed features connect to measurable outcomes.
5. Assumptions/dependencies/exclusions/customer responsibilities are visible.
6. Heading hierarchy/tables/captions/contrast/page flow are readable.
7. Reopened DOCX/PDF renders preserve wrapping/tables/shapes/fonts.

## 9. Next steps

Before skill creation, obtain only these three inputs:

1. Primary target: public bid/private sales/technical proposal priority.
2. One representative RFP and one approved proposal.
3. One brand guide or company DOCX template.

Then split these notes into `references/`, put actual templates in `assets/`, and run
`skill-creator` initialization/validation.
