# Intake and requirements management

Most proposal failures are determined during intake, before drafting.
Follow this sequence and produce three artifacts: ①proposal overview card ②requirements register ③compliance-matrix skeleton.

## 1. Proposal overview card (items to confirm with the user)

| Item | Question | Notes |
|---|---|---|
| Buyer/project | Exact official names? | Use RFP spelling; no arbitrary abbreviations |
| Proposal type | Build (A) / maintenance and technical support (B) / technical response (C)? | Classification table in SKILL.md |
| Deadline/submission format | Date/time, PPTX/PDF/printed copies, page limit? | Exceeding the page limit causes deductions/disqualification |
| Evaluation | Technical:price weights, evaluation table, presentation (PT)? | Evaluation items determine outline priorities |
| Delivery arrangement | Sole bidder/consortium, manufacturer (vendor) roles? | Reflect in roles and responsibilities (R&R) |
| Competition | Competitors, incumbent (defending/challenging)? | Determines differentiation strength |
| Budget/period | Budget, delivery period, maintenance years? | Basis for schedule and effort estimates |
| Reusable material | Existing proposals, track records, staff profiles? | Residual customer-name check required |

When answers are unavailable, including unattended execution: infer type from the classification table; assume a slide deck of 60~120p
(40~90p for maintenance) and PPTX+PDF delivery, and **state the assumptions at the beginning of the artifact**.

## 2. Requirements register (exhaustive extraction)

Give every RFP requirement an ID and one table row. Scan all proposal requests, evaluation items,
scope of work, and attached specifications. Capture requirements hidden in body text as well.
Korean source-pattern examples: "~하여야 함", "~제시할 것", "~포함되어야 함".

Korean example requirement inputs and display statuses are retained below:

| ID | Category | Requirement (source summary) | Mandatory/optional | Response page | Status |
|---|---|---|---|---|---|
| REQ-001 | 기술 | 분산파일시스템 기반 블록/파일/오브젝트 제공 | 필수 | Ⅲ-2 | 작성완료 |
| REQ-002 | 관리 | 월 1회 정기점검 및 확인서 제출 | 필수 | Ⅲ-1 | 작성중 |

- Preserve RFP requirement numbers when present (the buyer's questionnaire numbering takes priority).
  Otherwise assign REQ-nnn.
- Use the gate vocabulary for status: `pending` (not drafted) → `drafted` (in progress) → `needs-review` (draft complete, awaiting review)
  → `approved` (review complete) / `rejected` / `not-applicable` (reason and reviewer required). Every row must be `approved` before submission.
  Korean display annotations such as `approved(검수완료)` are allowed. In the example above, '작성완료·작성중' correspond to `needs-review` and `drafted`.

For joint initiatives, proactive proposals, or discovery without an RFP, do not force requirements into a final form.
Instead use a register with `Item ID | Type (fact/hypothesis/question/decision/commitment) | Content | Evidence | Owner | Status`.
Separate hypotheses and questions from agreed decisions and commitments. Promote only approved decisions and commitments
to the requirements register when converting to an external proposal.

## 3. Compliance matrix (proposal requirements response)

Public-sector and financial proposals conventionally **place the compliance matrix at the beginning of the body**.
(Many analyzed financial/group-company samples place 3~5 pages immediately after the contents.)

Korean response example:

| Requirement | Acceptance | Proposal response | Proposal page | Notes |
|---|---|---|---|---|
| 리눅스 시스템에 대한 장애대응 및 예방활동 | O | 장애 대응·예방 활동 방안 제안 | Ⅱ-2 (P.28~34) | |

Authoring rules:
- Use only the six common acceptance codes: `O` (compliant) / `부분` (partially compliant) / `조건부` (conditionally compliant) /
  `X` (unsupported) / `N/A` (not applicable) / `확인필요`. Korean parenthetical terms are display synonyms that bulk_matrix.py
  normalizes to codes. For partial, conditional, X, and N/A responses, the Notes must contain reasons and alternatives.
  Filling everything with O while the body cannot support it is the worst outcome: evaluators follow page references to verify.
- Update page numbers after final layout (a final quality-gate item).
- For type C (technical responses), the matrix is the document structure: arrange pages in RFP item order
  and show the corresponding number in each slide corner (Korean example: "(완료) 26. 플랫폼에서 수집·제공하는 Log의 범위").

### Large tabular RFPs and prescribed placement

Do not combine requirements into one O when there are 100 or more rows, or when evidence, owner, or acceptance differs within a functional group.
Split into `Source detail ID | Source location | Requirement | Module | Mandatory? | Response | Evidence ID |
Exceptions/assumptions | Body page | Status`. Put group-level summary conditions in the body and split the exhaustive detailed
register into consecutive appendices. Repeat headers and the Korean continuation label "계속" across pages.
A buyer-prescribed matrix location overrides the convention of placing it first. After final layout,
check that omissions, duplicates, and broken page back-references each total 0.

## 4. Reused-material intake checks

Before importing pages from an existing proposal, replace and verify:
1. **Customer/system names** — a previous customer's name remaining is immediate grounds for rejection.
2. **Product versions, EOL, roadmap** — refresh material dated to the source proposal
   (recheck OS/platform versions and support end dates on the web).
3. **Staffing, track record, financial figures** — refresh reference dates and exclude departed staff.
