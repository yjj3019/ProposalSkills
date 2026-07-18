# Public repository patterns

Checked 2026-07-18. Use these as design evidence, not as proof that a project is production-ready.

| Source | Pattern retained | Decision |
|---|---|---|
| `SalesforceLabs/ProposalForce` | RFP → question → response model; assignee, status, trusted answer library, DOCX export | Retain the item model. Repository is archived; do not depend on it. BSD-3-Clause |
| `degerahmet/q-flow` | closed-context answers, citations, confidence, human review, audit events, export gate | Retain evidence boundary, approval states, and export gate. Skip its event-driven/RAG stack. MIT |
| `Parth-Gochhwal/RFP-IGNITE` | governance, human approval, auditability, commitment control | Retain governance. Skip multi-agent orchestration unless separate roles prove necessary. MIT |
| `Satyapraveenv/ai-rfp-response-generator` | compliance matrix, conclusion-first writing, editable extraction, draft warning | Retain matrix and drafting principles. Treat performance claims as unverified. MIT |
| `bhargavhari2001-cloud/BidCraft` | extraction, knowledge matching, confidence-directed review, DOCX output | Retain workflow ideas only. No detected license; do not copy code. |
| `sridivya9398/AutoProposal` | centralized approved knowledge | Retain only knowledge governance. No detected license; skip GraphRAG and multi-agent claims. |
| `elapouya/python-docx-template` | populate a complex Word template with tagged fields | Prefer when a stable company template exists. LGPL-2.1 |
| `python-openxml/python-docx` | native DOCX creation and targeted modification | Use for minimal post-processing or validation. MIT |
| `jgm/pandoc` / `quarto-dev/quarto-cli` | source/style separation and reproducible publishing | Optional for Markdown-first or data-heavy proposals. |
| `vale-cli/vale` | organization-specific terminology and prose checks | Add only after recurring rules justify automation. MIT |
| `open-agreements/open-agreements` | source and license metadata on reusable templates | Retain provenance discipline. Apache-2.0 |

The skill requires no external runtime. Add retrieval only when direct search fails at scale, DOCX templating when a stable template exists, and prose linting when organization-specific rules recur.
