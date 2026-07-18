# Anonymized proposal patterns

Use this reference for planning and visual composition, not as evidence for a customer-specific claim.

## Corpus and privacy boundary

These patterns were abstracted from 25 supplied Korean enterprise and public-sector proposal documents totaling more than 1,300 pages/slides. The corpus includes PDF and PPTX material. The review sampled cover, contents, quarter points, middle, and closing pages from every document and used text extraction only to measure broad section coverage and sentence function.

No source file, page image, filename, logo, person, contact detail, customer or supplier name, exact date, unique project number, proprietary figure, verbatim sentence, or document hash is included here. Do not reconstruct, quote, or identify a source from these aggregates.

## Stable patterns observed

- The corpus separates into slide-oriented persuasion documents and A4 evaluation documents. Slide-oriented work favors a conclusion headline plus a diagram or table. A4 work favors explicit requirement, activity, deliverable, responsibility, and acceptance traceability.
- Solution, migration, and operations/support content appeared in nearly every document. Quality/security and references appeared in most; training appeared frequently. Executive summaries and explicit customer-understanding sections were less consistent, making them useful differentiators when the buyer permits them.
- Operations/support proposals repeatedly organize around service scope, request and incident flow, severity, escalation, organization, reporting, SLA, transition, and improvement.
- Migration/build proposals repeatedly follow current-state diagnosis, target architecture, phased execution, verification or rollback, stabilization, and operating handoff.
- Standard product proposals commonly use context, product role, differentiators, architecture, capability groups, adoption, operations, and evidence. Convert this catalog order into a buyer decision flow; a feature inventory alone is not a proposal.
- Policy or standardization proposals work best when they connect the reason to standardize, selection criteria, target baseline, governance and security controls, transition roadmap, and operating economics.
- Resilience proposals progress from failure assumptions and recovery objectives to protection patterns, orchestration, validation, operating ownership, and pattern-selection criteria. A topology without recovery behavior and test evidence is incomplete.
- Case-led proposals use context, challenge, choice, implementation, result, and transferability. Treat every name, image, date, metric, quote, and architecture as restricted until reuse permission and evidence are confirmed.
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
- **Capability page**: buyer need; mechanism; operating effect; boundary; dependency; evidence. Group related functions instead of listing every feature.
- **Comparison page**: decision criteria; defined alternatives; same measurement basis; source/date; gaps; buyer implication. Do not use an unsupported winner-first table.
- **Resilience pattern page**: failure domain; protected scope; recovery objective; data protection; orchestration; test method; residual risk; owner.
- **Case page**: approved anonymous context; challenge; intervention; verified outcome; relevance; differences and limits. Omit it when permission or evidence is absent.

## Visual system rules

- Keep one dominant message per page and express it as a conclusion, not a noun phrase.
- Select the visual by the reasoning task: architecture for relationships, flow for sequence, matrix for comparison, timeline for dependencies, table for accountable detail.
- Repeat a small set of semantic colors and shapes; do not encode meaning by color alone.
- Label scope, version, unit, date, source, assumptions, and abbreviations where relevant.
- Keep diagram text readable at final page size. Redraw or summarize screenshots instead of enlarging low-resolution captures.
- Test Korean and symbol fonts through the final PDF renderer. Font substitution can alter line breaks, tables, and symbols even when the source application looks correct.
- Treat legacy connectors, embedded screenshots, and external media as portability risks. Render through the intended submission application and replace broken or unreadable objects.

## Adaptation rule

Treat every pattern as a hypothesis to test against the current RFP, evaluation weights, page limit, evidence, template, and approval boundary. Buyer instructions always win. Never carry forward a prior customer's facts, commitments, architecture, pricing, performance, references, or branding.
