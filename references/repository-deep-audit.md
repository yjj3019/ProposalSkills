# Detailed analysis of public proposal-related repositories

Checked: 2026-07-18
Scope: 39 repositories/Gists listed in `proposal-related-git-repositories.md`. Inspected core source,
data models, tests, CI, output logic, licenses, and recent activity in addition to READMEs.

## Conclusions

The strongest combination is:

1. ProposalForce requirement/answer/owner/status model.
2. q-flow closed evidence, review events, and export blocking.
3. RFP-IGNITE deterministic missing-item/unit checks and approved-draft separation.
4. BidCraft separation of extraction/answer evaluation and golden-set evaluation.
5. grant-framework stage approvals and change history.
6. open-agreements source/license metadata and artifact validation.
7. Existing Word-template preservation with python-docx-template/python-docx.
8. Vale organizational rules with per-rule correct/error fixtures and incremental gates.

Do not adopt GraphRAG, multiagent systems, model self-scores, or search similarity presented as factual confidence.

## RFP/automation repositories

| Repository | Code-level inspection | Adopt | Exclusions/risks |
|---|---|---|---|
| SalesforceLabs/ProposalForce | Salesforce objects `RFP → Question → Response`, Knowledge linkage, status/owners/CSV-DOCX export, CRUD/FLS checks | Simple data model, ownership/status/compliance | Archived; no evidence versioning/export gate |
| AnshMNSoni/B2B-RFP-Agent | Gemini JSON extraction, typed SKU matching, deterministic pricing | Structured extraction boundary, derived-value recalculation | No evidence/certification/review; external transmission |
| jabessouguie/consulting-tools | Document parsers, LLM extraction, Markdown/PPTX/DOCX, anonymizer, pytest | `[NEEDS INPUT]`, anonymization, profile/template adapters | Truncated inputs, no evidence mapping, sensitive-file history |
| GideonLartey/wash-rfp-backend | PDF→Gemini JSON→PDF, size/type limits, HTML escaping, temp cleanup | Strict upload boundary, escaping/cleanup | Unsourced estimates/neutral fallback; no authentication |
| degerahmet/q-flow | Project/Question/Document/Embedding/Citation/ReviewEvent, transitions, 409 export gate | Closed evidence, review events, export blocking | Similarity misused as confidence; insufficient core tests |
| Parth-Gochhwal/RFP-IGNITE | Structured orchestrator, missing-item/unit checks, approval review, price-override recalculation, audit JSON | Deterministic validation, question queue, draft/approved separation | Unnecessary agent naming; insufficient auth/immutable audits |
| Satyapraveenv/ai-rfp-response-generator | Prompt generation, Markdown/HTML, parsed quality scores | Requirement-first outline, customization markers | Model self-score/92-point fallback; no evidence |
| Pankajkantghz/rfp-agent | RFP/Vendor/Proposal models, email IDs, Gemini evaluation | Original IDs beside normalized data | No license/auth/evidence/tests; source logs |
| bhargavhari2001-cloud/BidCraft | Multiformat extraction, RAG+rerank, editing/evaluation, DOCX/PDF, golden evaluation | Separate extraction/answer evaluation, edit distance, golden set | No license; weak RLS; title-level citations; no export gate |
| sridivya9398/AutoProposal | React mock UI/setTimeout simulation | Question-card idea only | GraphRAG/FHE/ZK/BFT, etc. unimplemented; no license |
| VaultaFoundation/grant-framework | Markdown+PR review, size-dependent approval counts, milestone evidence commit/tag | Version history, stage approvals, immutable evidence links | Public workflow unsuitable for confidential proposals; root license unclear |
| open-agreements/open-agreements | Source registry, metadata YAML, schema/postconditions, DOCX render, 100+ test/spec | Source/license sidecars, deterministic validation, render QA | Do not reuse legal-domain complexity |

## Document-generation repositories

| Repository | Decision | Key reason |
|---|---|---|
| elapouya/python-docx-template | Default template engine | Preserve Word body/headers/footers while applying Jinja variables/loops/conditions/images; split runs/complex fields need render checks |
| python-openxml/python-docx | Minimum postprocessing | Paragraph/table/style/section control; limitations for TOC/SmartArt/tracked changes |
| jgm/pandoc | Markdown-only option | `reference.docx` supplies styles, not body-template filling |
| quarto-dev/quarto-cli | Data/citation-centered technical proposals only | Strong code/cross-references; prohibit external-document execution; DOCX preservation limits |
| mherkazandjian/docxsphinx | Existing Sphinx organizations only | Main/release differences; TOC/header/footer constraints |
| JessicaTegner/pypandoc | Only if needed | Thin Python wrapper around Pandoc CLI |
| pandoc/lua-filters | Pin verified filters only | Filters execute code; quality differs by format |
| pandoc-obsidian-templates | Design reference | Fiction/academic/LaTeX focus; weak DOCX validation |
| TomBener/pandoc-templates | No dependency | Archived; Chinese academic use; DOCX tables/images TODO |
| DonnC/docxtpl | Exclude | Archived Flutter implementation; no tables/images/rich text |

## Style-automation repositories

| Repository | Decision | Key reason |
|---|---|---|
| vale-cli/vale | Verified objective rules | Markup-aware/extensible; extract canonical text from DOCX first |
| vale-cli/Microsoft | Rule-structure reference | 40 YAML rules/19 fixture groups; never apply US English policy directly to Korean |
| vale-cli/Google | Rule-structure reference | 31 rules; markup scope/exact-location tests |
| vale-cli/write-good | Suggestions only | 8 English heuristics; no Korean morphology |
| vale-cli/proselint | Categories only | Corporate speak/hedging/hyperbole, etc.; coarse fixtures |
| redhat-documentation/vale-at-red-hat | Adopt organizational operating model | Correct/error fixtures, overrides, rule-validation CI, simple YAML first |
| elastic/vale-rules | Accessibility reference | Meaningful links/no directional references; Apache NOTICE required |
| vale-cli/vale-action | Incremental adoption if needed | Start changed-line annotations; gate objective errors only |
| testthedocs/awesome-docs | Link index only | CC BY-NC 4.0 creates commercial-copying risk |

## Templates/Gists

| Item | Concepts to adopt | License/limitations |
|---|---|---|
| UBC-STAT/proposal-template | Separate metadata/content/presentation, timeline, cross-references | No license; academic; do not copy code/logos |
| r02b/Latex-PhD_Proposal_Template | Declarative cover metadata | MIT; insufficient academic semantic structure |
| YimianDai/iNSFC | Central CJK font/spacing/numbering, annual-form validation | No license; font/official-form rights risks |
| hust-latex/hustproposal | Documented source→generated class, CJK layout | LPPL 1.3c; Chinese/outdated fonts |
| donbr proposal gist | Discovery/scope/deliverables/milestones/dependencies/acceptance | CC BY 4.0, but mixed sources/contract-clause licensing complexity |
| dims TCE gist | Goals/non-goals, FR/NFR IDs, security, alternatives, test/upgrade/version history | No license; independently express concepts only |
| nelsonenzo technical spec gist | Summary/background/goals/plan/impact/privacy | No license; insufficient as standalone commercial RFP structure |

## Korean style-automation principles

Do not translate English rule lists. First automate only deterministic rules:

- Approved/forbidden company/product names and spacing variants.
- Date/currency/number/unit/version notation.
- Unresolved placeholders/conflict markers.
- Unsupported overclaims (Korean examples: 최고·유일·완벽·100%·무중단·보장).
- Named section/table/figure references instead of directional terms (Korean examples: `상기`, `아래`, `좌측`).
- Meaningful link text and alternative text.

Keep passive voice, verbosity, hedging, and readability scores as suggestions until validated on a Korean proposal corpus.

## Final architecture

1. Local input inventory and SHA-256.
2. Bid/No-Bid decision.
3. Atomic requirement ledger with source locations.
4. Approved-evidence drafts and `[NEEDS INPUT]`.
5. Deterministic state transitions and append-only review events.
6. Submission gates for obligations/evidence/commitments/attachments/placeholders/rendering.
7. Existing DOCX template filling with minimal postprocessing.
8. DOCX→PDF→page-image render validation.
9. Proposal/compliance/evidence/review/gate-report bundle.
