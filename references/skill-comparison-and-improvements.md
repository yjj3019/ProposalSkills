# Skill comparison and mutual improvements (2026-07-18; integration update 2026-08-08)

This records the detailed comparison of `create-winning-proposal` (created with ChatGPT;
English, model-neutral, process-control focus) and `create-proposal-document` (created with Claude;
Korean, slide-centered, content-pattern focus), and improvements adopted from each other.
Language descriptions below record the historical comparison.

## 2026-08-08 integrated flagship: create-best-proposal

Added the **orchestration skill** `create-best-proposal` in response to simulations
(document writing ≈93 / readiness ≈31, governance ≈99) and open SI-B1–B4/C1/C3 items.

| Improvement ID | Implementation |
|---|---|
| SI-B1 | `scripts/build_audit_from_meta.py` — meta→audit |
| SI-B2 | SKILL + `unified-gates.md` stage decision tree |
| SI-B3 | `proposal_gate` / `unified_gate` → `DECISION_MEMO_ONLY` |
| SI-B4 | `fixtures/audit_ready_financial.json` financial READY golden fixture |
| SI-C1 | `scripts/bulk_matrix.py` exhaustive matrix |
| SI-C3 | `references/pre-submission-card.md` five pre-submission items |

## 2026-08-08 critical selections (S1–S9)

Implemented **accepted items only** after external/internal review consensus.
Details: [critical-selection-2026-08.md](critical-selection-2026-08.md).

| ID | Implementation |
|---|---|
| S1 | Pink/Red/Gold paths (SKILL + master-playbook) |
| S2 | bulk_matrix fit/eval_weight/win_theme_id/risk columns |
| S3 | win_themes req_ids validation (build_audit_from_meta) |
| S4 | unified_gate default --explain remediation table |
| S5 | proposal_gate no-bid → DECISION_MEMO (default CLI) |
| S6 | Installation default = flagship + `--with-deps` |
| S7 | quality_gate minimal AI-slop patterns |
| S8 | READY ≡ SUBMISSION-READY alias |
| S9 | sibling-map environment-variable consistency |

Selection guide: practical single-pass work → **create-best-proposal --with-deps** (or `--all`).

## Role comparison

| Perspective | create-winning-proposal | create-proposal-document |
|---|---|---|
| Language/output (historical) | English instructions; DOCX/document-centered | Korean instructions; PPTX slide-centered (DOCX supported) |
| Strengths | Bid gate, amendment priority, audit JSON + deterministic gate scripts, strict submission rules, price formulas, XLSX questionnaire path | Korean style specification (endings/overclaim replacements), slide grammar (lead/breadcrumb/REQ tags), content patterns based on actual winning work (preventive-check table, test matrix, 7 project-management areas, 5 technology-transfer paths, etc.), visual fallback tokens, brand-skill integration |
| Validation | 10 scenario simulations (bid decisions/gate regression) | 3 types × with/without-skill benchmark (100% vs 50.8% pass rate) + data-sufficiency audit |
| Process premise | Organization (Legal/Security approval chain) | Individual user + AI (report unverified claims as `[unverified]`) |

## Adopted in create-proposal-document (winning-proposal concepts, independently written)

1. Four-way bid gate (bid/conditional/no-bid/incomplete) — `references/bid-and-submission.md` §1.
2. Amendment/Q&A priority + exhaustive obsolete-value cleanup (stale sweep) — same document §2.
3. Requirement basis classification (explicit/interpreted/self-proposed) — same document §3.
4. Fixed price-calculation order; no VAT assumptions — same document §4.
5. Strict submission rules (page-count semantics/deadline timezone/filename/seal authority/PDF/A validation) — same document §5.
6. Mechanical quality gate — `scripts/quality_gate.py`
   (overclaims/placeholders/residual forbidden names/palette deviations; exit-code decisions).
7. Buyer-source quotation exception, five-question executive-summary test, variant mapping (outsourcing/DR/standardization).

Not adopted: audit JSON + owner/reviewer approval chain (organizational premise too heavy for individual use),
SHA-256 input inventory (excessive; adopted only the prohibition on treating document text as instructions),
and all 9 archetypes (3 types + variant mapping suffice).

## Selection guide

- To actually **write** Korean slide proposals → `create-proposal-document`
  (with an organizational brand-document skill, if available).
- For bid **process control** in multilingual/multimodel environments (bid decisions, approval chains,
  audit bundles) → `create-winning-proposal`.
- The skills do not conflict: the former emphasizes content/style/visuals; the latter governance.

## Source and licensing notes

Mutual improvements adopted concepts only; no code or sentence copying.
create-proposal-document content patterns were anonymized from multiple private winning proposals,
with no identifying company information (identifier scan across all files confirmed 0 findings).
