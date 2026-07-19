# Requirements and evidence

## Bid/no-bid gate

Check eligibility, mandatory certifications/experience, deadline, page/file/signature rules, conflicts, delivery capacity, evidence availability, commercial fit, and unacceptable terms. Classify:

- `intake-incomplete`: sources are too sparse to assess eligibility; list missing inputs without inventing owners or deadlines
- `bid`: no known blocker
- `conditional-bid`: named curable conditions, owner, decision deadline, and approval path exist
- `no-bid`: the bidder lacks a mandatory qualification/capability or an unacceptable risk cannot be cured before submission

Internal approval cannot waive a buyer's mandatory rule. Check whether consortium or subcontractor credentials are explicitly permitted before treating them as a cure. For obvious no-bid cases, stop proposal drafting and issue a short eligibility decision memo with lawful reconsideration triggers.

## Source hierarchy

1. RFP, amendments, official Q&A, evaluation sheet, mandatory template
2. User-approved company facts, policies, contracts, certifications, case studies, product documents
3. Current authoritative external sources
4. Explicit assumptions awaiting approval

Within tier 1, apply this precedence unless the issuer says otherwise: formal amendment/addendum supersedes the base RFP; official Q&A clarifies the latest controlling text and changes it only when explicit; the mandatory template controls presentation; the evaluation sheet controls scoring. Record acknowledgement of each amendment and sweep the draft for superseded dates, versions, locations, quantities, and terms. Normalize deadlines to year, date, exact time, and timezone. Never silently resolve conflicts.

## Requirement ledger

| Field | Required content |
|---|---|
| `id` | stable requirement ID |
| `exact_text` | operative source wording |
| `source` | file, hash, page/sheet/row/section |
| `basis` | explicit buyer text, interpretation, or internal recommendation |
| `mandatory` / `weight` | eligibility and scoring importance |
| `category` | technical, delivery, commercial, legal, security, format, etc. |
| `response_location` | exact proposal section/table |
| `evidence_refs` | approved evidence IDs and exact locations |
| `owner` / `reviewer` | accountable people or roles |
| `compliance` | compliant, partially-compliant, non-compliant, not-applicable, or needs-confirmation |
| `verification` | acceptance test, document, calculation, or reviewer decision |
| `state` | pending, drafted, needs-review, approved, rejected, not-applicable |
| `open_question` | exact missing decision or evidence |

- Split compound requirements when owner, evidence, or approval differs.
- Record submission mechanics as requirements.
- Map source-to-proposal, not topic-to-topic.
- `not-applicable` requires rationale and reviewer approval.
- Mandatory `partially-compliant`, `non-compliant`, or `not-applicable` decisions require rationale and accountable approval; assess disqualification risk.
- Do not broaden evidence: “domestic region available” does not prove all primary, backup, log, and disaster-recovery data stays domestic.

## Evidence and claim ledger

| Claim ID | Type | Claim | Supports | Source tier/ID/location/hash | Version/date/scope | Disclosure permission | Owner/approver | Fact status | Use status |
|---|---|---|---|---|---|---|---|---|---|

Require evidence for prices, dates, quantities, calculations, performance, savings, availability, certifications, compliance, security, privacy, lifecycle, support, customer results, comparisons, guarantees, and superlatives.

Use `[NEEDS INPUT: owner — exact item]`, a visible assumption with impact, an assigned evidence gap, or remove the claim. Preserve the generated and approved versions in review events.

Classify unresolved items as `blocking-input`, `non-blocking-input`, or `assumption`. Eligibility, mandatory compliance, price, schedule, SLA, contract, security, and required evidence are blocking unless the accountable approver documents otherwise. A prior proposal is pattern guidance only; never transfer its customer, price, staffing, schedule, architecture, result, or commitment as current evidence.

Keep artifact placeholders separate from the input ledger. Any token physically remaining in a deliverable belongs in `unresolved_tokens` and blocks finalization; a non-blocking input or visible assumption belongs only in `inputs` unless its placeholder still remains in the artifact.
