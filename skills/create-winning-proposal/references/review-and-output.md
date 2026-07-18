# Review and output

## Integrated review

Run one pass: eligibility/submission → atomic coverage → evidence/freshness → scope/schedule/units/arithmetic/price/version/responsibility → technical/security/privacy/legal feasibility → assumptions/dependencies/exclusions → readability/accessibility/rendering.

For page-based proposals, also review the page-message map: every scored evaluator question has a response location; every page has one defensible conclusion; every visual proves that conclusion; repeated diagrams use consistent terms, boundaries, units, and versions.

- **Critical**: disqualifier, mandatory miss, unsupported high-impact claim, unapproved commitment, or contradiction affecting eligibility, mandatory targets, scope, price, staffing, security, or schedule
- **Major**: important gap; a missing value becomes Critical when it creates a mandatory miss or commitment
- **Minor**: local clarity, terminology, structure, or formatting issue
- **Note**: optional improvement

Every minimal correction should name the changed fact, owner/role, decision deadline, approval, and downstream calculations/sections to update.

## Deterministic finalization gates

Block submission-ready status for unresolved bid conditions, mandatory items, material claims, commitments, tokens/comments/conflicts, attachments/signatures/forms/filenames, consistency/arithmetic/submission checks, or required render verification.

Apply render verification only when a rendered artifact is requested. Analysis-only and Markdown review tasks declare `artifact_required: false`.

For price review, show: one-time items + recurring item × term → subtotal → named discount base/amount → tax basis/amount → final total. Never infer tax inclusion.

For strict submissions, verify deadline/timezone, exact filename, attachment names, page-count semantics, signature/seal type and authority, and requested PDF/A profile/validator. Do not claim PDF/A compliance without validation evidence.

Use `scripts/proposal_gate.py audit.json`; human review still decides truth, persuasiveness, legal acceptability, and visual quality.

## Output bundle

Provide the proposal, requirement ledger, evidence manifest, review events, assumptions/dependencies/exclusions, gate report, and applicable render result. For review-only work, keep the original intact and provide targeted corrections plus explicit verification limits.
