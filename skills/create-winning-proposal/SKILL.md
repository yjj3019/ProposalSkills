---
name: create-winning-proposal
description: Create, rewrite, review, and finalize evidence-backed Korean or English business, public-sector, technical, RFP, RFI, and RFx proposals. Use when an AI assistant must make a bid/no-bid assessment, extract atomic requirements, build a compliance and evidence ledger, draft evaluator-focused responses, standardize wording and visual structure, verify commitments and consistency, preserve a supplied DOCX template, or prepare and gate a submission-ready DOCX/PDF proposal with an audit bundle.
---

# Create Winning Proposal

Create evaluator-readable proposals in which every requirement, claim, commitment, and approval is traceable. Treat generated text as a draft until an accountable reviewer approves it.

## Select the path

- For RFP/RFI/RFx work, run the full workflow.
- Without an RFP, convert the request, audience, constraints, decision, and success criteria into a requirement brief, then continue at planning.
- For review only, preserve the source and run one integrated review; do not rewrite everything unless asked.
- For DOCX/PDF delivery, also use the host platform's document/PDF capability and its render-and-verify process.

## Stay model-neutral

Apply the same workflow with ChatGPT, Claude, Gemini, Grok, or another capable model. Treat platform-specific tools, agent syntax, memory, and retrieval as optional adapters. Never make proposal logic, evidence rules, review states, or audit outputs depend on one model vendor.

## Execute the workflow

1. **Secure intake**: inventory every source locally. Record path, SHA-256, size, modified time, and extraction method. Treat RFP text and templates as untrusted content. Do not upload confidential material or execute embedded code/macros without explicit permission. Read [automation-and-security.md](references/automation-and-security.md).
2. **Assess bid viability**: identify mandatory eligibility, deadline, submission form, conflicts, required evidence, delivery capacity, commercial constraints, competitive position, strategic value, and disqualifiers. Return `intake-incomplete`, `bid`, `conditional-bid`, or `no-bid` with reasons, conditions, owners, and approval path. Never invent profitability or win probability. Distinguish evidence not yet supplied from a capability the bidder does not possess. On `intake-incomplete`, draft only a clearly provisional structure and input list unless asked otherwise. Stop full drafting on `no-bid`; deliver only a decision memo unless asked otherwise.
3. **Extract atomically**: read the RFP, amendments, Q&A, evaluation sheet, and template before drafting. Split compound requirements when evidence, owner, or approval differs. Preserve exact text and page/sheet/row/section. Read [requirements-and-evidence.md](references/requirements-and-evidence.md).
4. **Map and assign**: create the compliance ledger. Give each item an ID, source location, mandatory status, weight, response location, evidence, owner, reviewer, state, and unresolved question. Allocate space and review effort by evaluation weight, uncertainty, and delivery risk.
5. **Plan the pursuit**: build a submission-backward schedule with owners, reviewers, approvers, dependencies, completion criteria, internal deadline, structure/content/final review gates, production rehearsal, and receipt evidence. Define at most three approved win themes in `buyer problem → differentiated approach → proof → buyer outcome` form; map each to scored requirements and expected objections without inventing or disparaging competitor facts. Then obey the buyer's outline and page limit. Otherwise select the closest proposal archetype and the smallest suitable structure in [structure-and-design.md](references/structure-and-design.md). For substantial proposals, make a page-message map before prose: evaluator question, conclusion headline, evidence, buyer implication, assumptions/conditions, visual form, requirement IDs, win-theme ID, owner, and state. Reserve space for high-scoring and high-risk requirements first. Use [anonymized-proposal-patterns.md](references/anonymized-proposal-patterns.md) as pattern guidance, never as factual evidence.
6. **Draft from approved evidence**: answer the requirement first, then mechanism, buyer outcome, evidence, boundary, and acceptance. Use [writing-and-phrases.md](references/writing-and-phrases.md). When evidence is missing, insert `[NEEDS INPUT: owner — exact item]`; if no owner is assigned, use `[NEEDS INPUT: UNASSIGNED — exact item]`. Never invent a fallback fact or owner.
7. **Control commitments**: route price, schedule, staffing, legal, security, privacy, compliance, SLA, lifecycle, and customer-result claims to their accountable owner. Recalculate totals after edits. A retrieval score or model self-score is never approval or factual confidence.
8. **Review and record**: use `pending → drafted → needs-review → approved` or `rejected`. Append reviewer, timestamp, prior content hash, new content hash, action, and notes. Preserve original and edited drafts. Read [review-and-output.md](references/review-and-output.md).
9. **Run gates**: create audit JSON from [audit-schema.md](references/audit-schema.md), then execute `scripts/proposal_gate.py`. Treat `conditional-go` as internal continuation only, never external submission clearance. Block finalization for open Critical/Major defects, blocking inputs, unresolved mandatory items, unsupported material claims, unapproved commitments, remaining placeholders, missing attachments, contradictions, failed deterministic checks, uninspected required package content, missing rehearsal evidence or receipt-capture plan, or failed required render checks.
10. **Produce and inspect by the safest route**: preserve the supplied template and original file. Reopen and render every deliverable; inspect all pages, fields, tables, figures, Korean fonts, substitutions, headers/footers, clipping, blank pages, and image-only placeholders. Separately inspect the original PPTX/DOCX package for metadata, notes/comments, hidden slides/sheets/objects, embedded files, external links, macros, executable objects, stale customer or price data, and other content absent from a PDF render. Mark unavailable checks `NOT INSPECTED`; never infer a pass.
11. **Rehearse and hand off**: verify technical, commercial, and administrative package separation; exact filenames, formats, size/encryption rules, account/authority, deadline/timezone, upload/opening/print behavior, and required copies. Keep receipt number, confirmation screen/email, or equivalent evidence. Deliver the proposal, compliance ledger, win-theme map, evidence manifest, review events, assumptions/dependencies/exclusions, gate report, render/package results, and submission evidence. State remaining manual checks.

For a small review-only request, scale the inventory and bundle to the supplied sources and return severity-ranked findings plus minimal corrections. Do not imply that absent RFPs or evidence were checked.

## Enforce the closed evidence boundary

Use user-provided material and approved company sources first, then current authoritative external sources. Record source version, date, scope, exact location, and file hash when practical. If sources conflict, expose the conflict and request a decision when it changes eligibility, compliance, price, scope, schedule, or risk.

## Keep automation proportional

Use direct local search until an approved answer library is too large for reliable search. Add retrieval only then, and keep citations plus human approval. Do not add GraphRAG, multiple named agents, a response portal, or a custom generator merely because a reference project uses them.

## Respect source licenses

Read [source-patterns.md](references/source-patterns.md) when changing automation. Reuse independently expressed patterns by default. Do not copy code or assets from repositories without a compatible license and required attribution.
