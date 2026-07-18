# Structure and design

Always use the buyer's mandatory outline first. Otherwise choose only the sections needed.

## Choose an archetype

- **Operations and support**: service scope; operating model; request/incident/escalation flow; severity and SLA; staffing and governance; reporting; transition; continuous improvement.
- **Migration and modernization**: current constraints; target state; assessment; migration waves; compatibility/data/cutover; verification and rollback; stabilization; operating handoff.
- **Platform or system build**: objectives; target architecture; functional and non-functional design; integration/data/security; implementation plan; testing and acceptance; operations.
- **Product or solution selection**: evaluation criteria; fit and gaps; architecture; lifecycle and support; implementation; risk; total value; evidence.
- **Standard product proposal**: buyer context; product role; decision criteria; differentiators; architecture; grouped capabilities; adoption and integration; operations and lifecycle; evidence; next decision.
- **Policy or standardization decision**: why standardize; policy and operational constraints; selection criteria; approved baseline; governance/security; transition; economics; decision and next step.
- **Resilience or continuity design**: business service and failure assumptions; recovery objectives; protection patterns; target architecture; orchestration; testing; operations; pattern selection; roadmap.
- **Case-led education or persuasion**: audience question; context and challenge; decision; implementation; verified outcome; transferability and limits; implications. Use only approved case evidence.
- **Outsourcing or managed service**: service boundaries; responsibility matrix; transition; organization and facilities; processes and tools; service levels; governance; exit plan.

Hybrid work may combine archetypes, but assign one primary narrative: the archetype that carries the highest evaluation weight; if weights are absent, use the one carrying the main buyer decision and delivery risk. Do not copy a prior proposal's section order when the buyer specifies another.

## Build a page-message map

For a substantial proposal, define each planned page or spread before drafting:

`page_id | evaluator_question | conclusion_headline | evidence | buyer_implication | assumptions_conditions | visual_type | requirement_ids | owner | state`

Use a conclusion headline that states the page's answer. The body should prove it with a diagram, table, calculation, schedule, or concise prose, then state the buyer implication. A topic label alone is not a conclusion.

## Public/RFP proposal

Executive summary; compliance matrix; requirement understanding; solution; delivery/schedule; governance; operations/security/compliance; risks/assumptions; outcomes/acceptance; requested commercial/evidence appendices.

## Private sales proposal

Decision summary; current impact; proposed outcome/scope; approach/differentiators; delivery/responsibilities; value/measures/risks/commercials; next decision.

## Technical proposal

Summary/goals; requirements/non-goals; current state/constraints; design; security/operations/data/migration; alternatives; delivery/testing/rollback; risks/open decisions.

## Security questionnaire/XLSX

Preserve the buyer workbook, row order, formulas, validations, hidden sheets, and formatting. Add or map fields for direct answer, compliance level, boundary/exception, evidence ID, owner, reviewer, and state. Reopen the workbook and verify formulas and hidden structures. Do not attach sensitive internal policies when a redacted citation or controlled-review reference satisfies the requirement.

## Strict page limits

Confirm whether cover, TOC, separators, appendices, and attachments count. Until confirmed, conservatively count every page in the limit and mark the assumption. Reserve pages by evaluation weight, then merge low-weight sections rather than shrinking fonts or hiding content. Track every separate package component and filename.

## Page design

- Give each page or major section one dominant message.
- Prefer `conclusion → evidence → buyer implication`; keep the headline and visual mutually consistent.
- Use architecture diagrams for boundaries and interfaces, process flows for sequence and control, matrices for repeated comparisons, timelines for phases and dependencies, and tables for accountable detail.
- Use semantic heading styles and consistent brand assets supplied by the user.
- Use tables for repeated mappings, not decorative layout.
- Label units, dates, scope, source, and baseline on charts/tables.
- Provide captions and text alternatives; never rely on color or direction alone.
- Use at least 4.5:1 contrast for normal text and 3:1 for large text as a conservative reference.
- Keep assumptions/exclusions near affected scope, schedule, or price.
- Avoid unreadable screenshots, unexplained product diagrams, ornamental closing pages, and dense text reduced to fit. Replace image-only evidence with legible, sourced content.

## Template handling

Preserve supplied DOCX styles, headers, footers, section breaks, and boilerplate. Do not overwrite the original. Render and inspect every page when layout affects submission.
