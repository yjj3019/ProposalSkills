# Anonymized proposal patterns

Use this reference for planning and visual composition, not as evidence for a customer-specific claim.

## Corpus and privacy boundary

These patterns were abstracted from 17 supplied Korean enterprise and public-sector proposal PDFs totaling more than 1,100 pages. The review sampled cover, contents, middle, and closing pages from every document and used text extraction only to measure broad section coverage.

No source file, page image, filename, logo, person, contact detail, customer or supplier name, exact date, unique project number, proprietary figure, verbatim sentence, or document hash is included here. Do not reconstruct, quote, or identify a source from these aggregates.

## Stable patterns observed

- The corpus separates into slide-oriented persuasion documents and A4 evaluation documents. Slide-oriented work favors a conclusion headline plus a diagram or table. A4 work favors explicit requirement, activity, deliverable, responsibility, and acceptance traceability.
- Solution, migration, and operations/support content appeared in nearly every document. Quality/security and references appeared in most; training appeared frequently. Executive summaries and explicit customer-understanding sections were less consistent, making them useful differentiators when the buyer permits them.
- Operations/support proposals repeatedly organize around service scope, request and incident flow, severity, escalation, organization, reporting, SLA, transition, and improvement.
- Migration/build proposals repeatedly follow current-state diagnosis, target architecture, phased execution, verification or rollback, stabilization, and operating handoff.
- Strong technical pages pair a conclusion-style headline with an architecture, process, comparison, schedule, or responsibility model. Weak pages use topic-only headings, tiny prose, unexplained vendor diagrams, illegible screenshots, or placeholder imagery.
- Covers and section dividers establish navigation, but decorative pages do not replace scored content. Closing pages should be omitted or minimized when page limits count them.

## Reusable narrative spine

Use this spine only when it fits the buyer's required order:

1. Show the decision and measurable outcome.
2. Demonstrate understanding of the present constraint and evaluation concern.
3. State the proposed scope, boundaries, target state, and differentiator.
4. Explain how delivery, migration, testing, and acceptance will work.
5. Prove that operations, support, security, quality, and governance are sustainable.
6. Expose responsibilities, assumptions, dependencies, risks, and rollback or exit paths.
7. Tie evidence and commitments back to requirements and the next decision.

## Page patterns

- **Decision page**: recommendation; 3–5 reasons; quantified outcomes with evidence IDs; conditions.
- **Understanding page**: observed constraint; impact; buyer priority; source location; response implication.
- **Architecture page**: boundary; components; interfaces; data/control flows; security zones; legend; assumptions.
- **Process page**: trigger; accountable role; steps; control point; output; SLA or acceptance.
- **Roadmap page**: phases; entry/exit criteria; dependencies; deliverables; decision gates; rollback.
- **Operating model page**: roles; responsibility matrix; escalation; reporting cadence; service hours; exclusions.
- **Evidence page**: requirement or claim; evidence ID; scope and date; relevance; limitation.
- **Risk page**: cause; event; effect; probability/impact; prevention; contingency; owner; trigger.

## Visual system rules

- Keep one dominant message per page and express it as a conclusion, not a noun phrase.
- Select the visual by the reasoning task: architecture for relationships, flow for sequence, matrix for comparison, timeline for dependencies, table for accountable detail.
- Repeat a small set of semantic colors and shapes; do not encode meaning by color alone.
- Label scope, version, unit, date, source, assumptions, and abbreviations where relevant.
- Keep diagram text readable at final page size. Redraw or summarize screenshots instead of enlarging low-resolution captures.
- Test Korean and symbol fonts through the final PDF renderer. Font substitution can alter line breaks, tables, and symbols even when the source application looks correct.

## Adaptation rule

Treat every pattern as a hypothesis to test against the current RFP, evaluation weights, page limit, evidence, template, and approval boundary. Buyer instructions always win. Never carry forward a prior customer's facts, commitments, architecture, pricing, performance, references, or branding.
