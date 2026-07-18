# Review and output

## Integrated review

Run one pass: eligibility/submission → atomic coverage → evidence/freshness → scope/schedule/units/arithmetic/price/version/responsibility → technical/security/privacy/legal feasibility → assumptions/dependencies/exclusions → readability/accessibility/rendering.

For page-based proposals, also review the page-message map: every scored evaluator question has a response location; every page has one defensible conclusion; every visual proves that conclusion; repeated diagrams use consistent terms, boundaries, units, and versions.

- **Critical**: disqualifier, mandatory miss, unsupported high-impact claim, unapproved commitment, or contradiction affecting eligibility, mandatory targets, scope, price, staffing, security, or schedule
- **Major**: important gap; a missing value becomes Critical when it creates a mandatory miss or commitment
- **Minor**: local clarity, terminology, structure, or formatting issue
- **Note**: optional improvement

Use review decisions consistently:

- **NO-GO**: a Critical defect or open blocking input exists; do not advance the gate or submit, though assigned correction work may continue.
- **CONDITIONAL GO**: no Critical/blocking item remains, but a Major defect is open; internal correction may continue, external submission is prohibited.
- **GO WITH MINOR**: only Minor defects remain; submit only after the accountable approver accepts the residual risk.
- **GO**: all mandatory content, production, package, and submission gates passed and the submission authority approved.

Every minimal correction should name the changed fact, owner/role, decision deadline, approval, and downstream calculations/sections to update.

## Deterministic finalization gates

Block submission-ready status for open Critical/Major defects, blocking inputs, unresolved bid conditions, mandatory items, material claims, commitments, tokens/comments/conflicts, attachments/signatures/forms/filenames, consistency/arithmetic/submission checks, required render verification, uninspected package content, or missing rehearsal evidence or receipt-capture plan. Recheck affected requirements, calculations, pages, and package contents after every fix; record closure evidence.

Apply render verification only when a rendered artifact is requested. Analysis-only and Markdown review tasks declare `artifact_required: false`.

For price review, show: one-time items + recurring item × term → subtotal → named discount base/amount → tax basis/amount → final total. Never infer tax inclusion.

For strict submissions, verify deadline/timezone, exact filename, attachment names, page-count semantics, signature/seal type and authority, and requested PDF/A profile/validator. Do not claim PDF/A compliance without validation evidence.

Separate visual inspection from package inspection. A render can reveal clipping, overlap, substitution, and pagination, but cannot clear notes, comments, hidden content, metadata, embedded files, external links, macros, or stale price/customer data. Mark unavailable checks `NOT INSPECTED`. When commercial content must be separate, any price or cost data in the technical package is Critical.

Treat content approval and submission clearance as separate gates. Rehearse upload/opening or physical production early enough to recover, and preserve a receipt number, confirmation screen/email, or equivalent proof. Content `GO` without cleared packaging and receipt handling is `SUBMISSION NOT CLEARED`.

Use `scripts/proposal_gate.py audit.json`; human review still decides truth, persuasiveness, legal acceptability, and visual quality.

## Output bundle

Provide the proposal, requirement ledger, evidence manifest, review events, assumptions/dependencies/exclusions, gate report, and applicable render result. For review-only work, keep the original intact and provide targeted corrections plus explicit verification limits.
