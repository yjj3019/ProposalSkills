---
name: create-winning-proposal
description: Create, rewrite, review, and finalize evidence-backed Korean or English business, public-sector, technical, RFP, RFI, and RFx proposals. Use when Codex must analyze an RFP, build a compliance matrix, draft proposal sections, standardize wording and visual structure, verify claims and consistency, preserve a supplied DOCX template, or prepare a submission-ready DOCX/PDF proposal.
---

# Create Winning Proposal

Build evaluator-readable proposals that trace every material claim and requirement. Treat AI output as a draft until an accountable reviewer approves it.

## Choose the path

- For an RFP/RFI/RFx response, follow the full workflow.
- For a proposal without an RFP, create a compact requirement brief from the user request, audience, constraints, and success criteria, then continue at drafting.
- For review only, preserve the source and run the review gates once. Do not rewrite the entire document unless asked.
- For DOCX/PDF delivery, also use the relevant document or PDF skill and complete its render-and-verify workflow.

## Execute the workflow

1. **Intake**: identify buyer, evaluators, decision, proposal type, language, submission format, deadline, page limit, mandatory template, and source hierarchy. Ask only for missing information that materially changes the response.
2. **Extract**: read the RFP and attachments before drafting. Capture instructions, evaluation factors, requirements, deliverables, dates, quantities, dependencies, exclusions, and required evidence. Read [requirements-and-evidence.md](references/requirements-and-evidence.md).
3. **Map**: create a compliance matrix. Give every requirement an ID, exact source location, mandatory status, score/weight, response location, evidence, owner, and state. Never infer coverage from a generic section title.
4. **Plan**: use the buyer's required outline. If none exists, select the smallest suitable structure from [structure-and-design.md](references/structure-and-design.md). Allocate space according to evaluation weight and risk.
5. **Draft**: lead with the conclusion, connect each capability to the buyer outcome, quantify only when supported, and expose assumptions. Apply [writing-and-phrases.md](references/writing-and-phrases.md).
6. **Ground**: use supplied and approved sources first. Attach source, version, date, and scope to sensitive claims. If evidence is missing, write `[unverified]`, convert the claim to an assumption, or place it in the evidence gap list. Do not invent facts.
7. **Review**: run one integrated pass using [review-and-output.md](references/review-and-output.md). Block finalization while a mandatory requirement is uncovered, a material claim is unsupported, or a contradiction remains unresolved.
8. **Produce**: preserve the supplied template. Use heading styles, table headers, captions, alt text, sufficient contrast, and consistent terms. Reopen and render DOCX/PDF output; inspect page breaks, tables, figures, fonts, headers, footers, and blank pages.
9. **Handoff**: deliver the proposal, compliance matrix, evidence gaps, assumptions, and verification result. State any manual checks still required.

## Enforce approval states

Use `unanswered → drafted → needs-review → approved` for every requirement. Permit `not-applicable` only with a written reason. Do not mark a generated response approved. Do not export a submission-ready artifact while any mandatory item remains outside `approved`.

## Keep the evidence boundary closed

Base factual answers only on user-provided material, approved organizational sources, or current authoritative sources. If no relevant evidence exists, say so. A confidence score never substitutes for evidence or review.

## Avoid unnecessary machinery

Do not add RAG, vector databases, GraphRAG, multiple agents, a response portal, or a custom DOCX generator for a one-off proposal. Add retrieval only when the approved answer library is too large for reliable direct search. Prefer a supplied Word template and native document tooling.

## Use repository-derived patterns carefully

Read [source-patterns.md](references/source-patterns.md) when changing this skill or evaluating automation architecture. Reuse ideas, not third-party code or branding, unless its license and attribution requirements are satisfied.
