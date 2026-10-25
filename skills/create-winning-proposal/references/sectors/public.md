# Public sector (public)

National/local government and public-institution procurement.
This is the repository's default assumption; other-sector guidance branches from it.

## Additional questions

| Item | Why |
|---|---|
| Evaluation table/weights and qualitative/quantitative split | Sole basis for outline priorities and space allocation |
| Qualifications (track record/certifications/finance) | Shortfalls disqualify regardless of content |
| Submission format/copies/page limit | Excess causes deductions or disqualification |
| Amendments/Q&A replies | Later material prevails when conflicting with the original notice |
| Presentation (PT) and duration | Determines whether a separately specified presentation is needed |
| Deduction/disqualification conditions | Copy explicit conditions into the compliance matrix |
| Requirement strength (mandatory/recommended/conditional) | Exceeding recommendations differs from mandatory violations; map source wording into `strength` |
| Document type (RFP/RFI/RFQ) | RFI is not a bid; respond with estimates, alternatives, clarification questions rather than commitments |

## What the proposal must prove

- Requirement-by-requirement matrix responses and locations; no mandatory requirement may be omitted.
- Qualification evidence (delivery certificates/certifications); shortfalls require conditional-bid or no-bid decisions.
- Deliverability: staff grades/experience, similar records, realistic schedule.
- Acceptance criteria/responsibility, deliverable list, acceptance timing.

## Claims requiring care

- For other-institution examples, confirm **customer-consent scope**. Residual previous-customer names cause immediate rejection.
- Preserved Korean exaggeration inputs "100%", "무중단" may be read as proposer promises even when quoting the RFP.
- Never infer applicable laws/certifications solely from institution type; use only those explicit in the notice.

## Machine checks

For `context.buyer_types` including `public` in submission stages, gates require:

- `evaluation_criteria[]`: top-level weights sum to `evaluation_total` (default 100);
  children sum to parent weights. Preserve separate pricing, multi-stage evaluation, undisclosed weights,
  cutoffs as given ([audit-schema.md](../audit-schema.md), evaluation-table item).
  **Negotiation eligibility's 85% means a ratio of the technical allocated maximum**, not total score 85.
  Technical 90:price 10 also has regulatory principles/exceptions; confirm the notice and record
  `minimum_ratio`/`weight`, never hard-code them into gates.
- Each leaf criterion has at least 1 requirement (`requirements[].criterion_ids`).
  A criterion without responses signals an omitted chapter.
- With `context.rfx_type: rfi`, no evaluation table is required (information requests are not bids);
  instead block commitments (`kind: commitment`).
- `eligibility[]` (common submission requirement): unmet/unremediable qualifications prohibit `bid`.
- With `sensitive-data` in `context.constraints`, package `metadata`, `hidden-content`,
  `stale-customer-data` must all `pass`.

Not machine-checked: strategic weight allocation, actual similarity of track records, schedule realism.
Humans judge these.
