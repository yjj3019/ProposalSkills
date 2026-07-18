# Repository-derived patterns

Source code, tests, workflows, and licenses were inspected before these patterns were distilled.

## Adopt

- ProposalForce: requirement/question/response separation, assignee, status, compliance fields, authorization checks.
- q-flow: closed-context failure, citation records, review events, explicit state transitions, server-side export gate.
- RFP-IGNITE: deterministic missing-field/unit checks, clarification queue, separate draft/approved artifacts, recomputed totals.
- BidCraft: separate extraction assessment from response assessment, edit-distance feedback, golden retrieval evaluation.
- grant-framework: versioned proposals, staged human approvals, immutable milestone evidence.
- open-agreements: source/license sidecars, canonical registry, schema checks, deterministic postconditions, render QA.
- python-docx-template/python-docx: existing template preservation plus minimal post-processing.
- Vale organization packs: objective rules, positive/negative fixtures, exceptions, policy links, gradual gating.

## Reject

- multi-agent labels without independently useful state
- model-generated quality/confidence scores
- retrieval similarity presented as truth
- source titles without exact location, version/date, and hash
- silent default facts, neutral metrics, or fallback high scores
- UI simulations presented as implemented AI/security
- external transmission, public data access, or raw logging by default
- export without deterministic readiness gates
- wholesale translation of English style-lint rules into Korean

## License boundary

- Reuse compatible MIT/BSD concepts or code only with required notices.
- Preserve Apache-2.0 LICENSE/NOTICE and modification notices when copying.
- Treat LPPL, CC BY/SA/NC, mixed-license Gists, fonts, logos, and official templates separately.
- When no license is declared, reuse independently expressed concepts only; do not copy code or text.
