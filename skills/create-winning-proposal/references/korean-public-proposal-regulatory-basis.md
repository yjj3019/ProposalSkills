# Korean public proposals — official basis

This reference connects the gate rules to their official basis without reproducing statutory provisions.
Always extract concrete values from the notice for the actual procurement. Sector questions and evidence
are in [sectors/public.md](sectors/public.md); the schema is in [audit-schema.md](audit-schema.md).

## 1. Authority order when sources conflict

1. Amendment or revised notice
2. Base RFP, statement of work, or task specification
3. Official Q&A clarification, unless it explicitly supersedes the notice
4. Evaluation sheet: weights and evaluation method
5. Required submission template
6. Approved company material
7. Official instruments and guides listed below
8. General methods (`../create-best-proposal/references/external-method-boundaries.md`)

Official instruments guide how the buyer prepares a notice. They can inform interpretation, but must
not overwrite values stated in that notice. If an instrument and notice appear inconsistent, ask the
buyer and leave an input marker. Preserve this example marker verbatim:
`[NEEDS INPUT: 발주처 질의 — 항목]`.

## 2. Instruments recorded at the last check

Recorded check date: 2026-09-16. Ministry names and notice numbers can change through amendments.
Before citing an instrument for submission, recheck its current edition in the Korean National Law
Information Center's administrative-rules collection and update the check date. Korean instrument
titles and notice identifiers below are source references and are retained verbatim.

| Instrument: original title | Issuance reference recorded at the check date | Use in proposal work |
|---|---|---|
| `소프트웨어 기술성 평가기준 지침` | `과학기술정보통신부고시 제2025-18호`, effective 2025-04-17 | Technical evaluation categories and whether differentiated scoring applies |
| `(계약예규) 협상에 의한 계약체결기준` | `기획재정부계약예규 제721호`, effective 2024-09-13 | Technical/price evaluation, qualification for negotiation, and negotiation order |
| `조달청 협상에 의한 계약 제안서평가 세부기준` | `조달청지침 제379호`, effective 2026-01-26 | Evaluation panels and procedures for procurements administered by the Public Procurement Service |
| `행정기관 및 공공기관 정보시스템 구축ㆍ운영 지침` | `행정안전부고시`; confirm the current number in the law information service | Buyer duties such as required RFP content, proposal compensation, prior consultation, and classification |

Cautions:

- A later contract-rule amendment may have been issued after ministry restructuring. The number above
  was the latest posted edition found at the recorded check date and must be rechecked before citation.
- Explanatory publications such as public software RFP-writing guides and technical-evaluation guides
  are not binding instruments. Treat old editions as historical vocabulary references only.
- Local governments and public institutions may add their own contract rules. Prioritize the rules
  cited by the actual notice.

## 3. Map procurement concepts to this repository's schema

| Notice or regulatory concept | Record location | Gate behavior |
|---|---|---|
| Evaluation items, maximum weights, qualitative/quantitative distinction | `evaluation_criteria[]` | Ledger required for public submissions; totals reconciled |
| Functional, performance, security, and operational requirements | `requirements[]`, linked through `criterion_ids` | Scored items without mapped requirements are blocked |
| Bidder eligibility, experience, and certifications | `eligibility[]` | An unmet, incurable qualification prevents a bid decision |
| Page, paper, font, and file specifications | `context.constraints` + meta `output_spec` | `deck_check.py` checks slide specifications |
| Price proposal and calculation details | `numbers[]` / separate price volume | Sums and ratios are recalculated |
| Submitted files, copies, anonymous copies, and separate packages | `attachments[]` | Submission-bundle hashes and inventory reconciled |
| Negotiation qualification threshold and differentiated scoring | `minimum_ratio` / `minimum_score` / source notes | Preserved as input; no score prediction |

## 4. Values that must not be constants

These values vary by procurement. Do not put them into a skill, gate, or example as a nationwide default.

- Technical:price weighting ratio, negotiation qualification ratio, and category cutoffs
- Main-document and summary page/slide limits, and file-size limits
- Paper size (A4/A3), portrait/landscape orientation, and screen aspect ratio
- Minimum font size and line spacing
- Anonymous-copy and PDF requirements, binders, and printed-copy counts
- Number of evaluation categories, whether a presentation (PT) is required, and its duration

Do not infer a value absent from the notice. Leave it unset and record a clarification question.
For interpretation of an 85% negotiation-qualification threshold as a ratio of the technical maximum,
use the machine-check section in [sectors/public.md](sectors/public.md).

## 5. Limits

- This reference does not interpret statutory provisions. Resolve contractual judgments through an
  official buyer response or legal review.
- It does not establish amendments issued after the recorded check date. Recheck the section 2 table
  when that date is more than 6 months old.
