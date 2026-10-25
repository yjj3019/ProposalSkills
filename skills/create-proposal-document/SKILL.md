---
name: create-proposal-document
description: "Content, writing, and visual layer loaded by create-best-proposal. Provides type-specific outlines, leads, compliance matrices, content patterns, visual specifications, the slides.json-based PPTX generator (build_deck.py), layout lint (deck_check.py), and text review (quality_gate.py) for Korean IT proposals. Use directly only when the user explicitly requests writing, structure, or slide layout alone, or when create-best-proposal is unavailable."
disable-model-invocation: true
---

# Standard proposal authoring skill (create-proposal-document)

A **proposal content, structure, and quality layer** generalized from multiple actual winning IT proposals
(build, maintenance, technical-response types), independent of any company.
Responsibilities:

- **This skill**: what to write (structure, sentences, evidence, review): outlines, matrices, sentence patterns, quality gates.
- **Brand-document skill, when installed**: appearance; single source for color/font/layout tokens.
  Otherwise use neutral defaults in `references/visual-style.md`.
- **Host document tools or installed pptx/docx skills**: actual creation/editing. No specifically named skill is required.

Apply the same structure, evidence, and review rules in Claude, ChatGPT, and Codex. Use tools available in the
current session for files, Python, rendering, and image inspection; leave unavailable checks `NOT INSPECTED`.
For integrated installation, see create-best-proposal's `host-portability.md` for host-specific execution.
Standalone content review proceeds without that guide, but unexecuted checks never count as passed.

Default artifact: **PPTX slide deck**. Switch to DOCX when the buyer requires an A4 document,
keeping the same structure/sentence rules (style hierarchy: `references/visual-style.md`).

## Route selection

- **New proposal**: follow the entire sequence below.
- **Review/revise existing proposal only** (review-only): do not rewrite it wholesale.
  Diagnose using the review-only section in `references/review-checklist.md`;
  output severity-sorted (Critical/Major/Minor) findings, minimum fixes, scope, and limitations only.
- **English proposal**: sentence rules are language-independent. Use writing-style.md's English
  banned-word dictionary and `quality_gate.py --lang en` (both for bilingual output).
- **Presentation summary (PT deck)**: reorganize in evaluator-question order instead of shrinking the proposal;
  see the presentation-summary section in `references/proposal-structure.md` (slides versus time, main-proposal synchronization).

## Workflow (mandatory order)

### 0. Research first
Before choosing output tools/skills, secure the **facts**:
original RFP, customer state, product versions/EOL/roadmaps, track records, certifications.
Verify time-sensitive information (versions, support end dates, pricing policy) through web research.

### 1. Intake — read `references/intake-and-requirements.md`
- **Bid decision first**: qualifications/deadline/mandatory evidence/unacceptable clauses →
  bid/conditional/no-bid/insufficient information (`references/bid-and-submission.md` §1).
  Do not start drafting after a no-bid recommendation.
- Classify proposal: **A. Build / B. Maintenance and technical support / C. Technical response** (table below).
- Extract all RFP requirements with IDs → **compliance-matrix skeleton**.
  For amendments/Q&A, apply precedence and stale-value cleanup (bid-and-submission.md §2).
- Confirm backward-planned schedule, structure/content/final gates, owners/reviewers/approvers,
  internal deadlines, file-generation rehearsal, and receipt-evidence plan (bid-and-submission.md §8).
- First seek missing information in supplied material. If qualifications, evaluation, deadline, or mandatory
  specifications cannot be determined, retain required inputs. Never infer official length/deadline/weights,
  even unattended. Reversible internal draft organization may proceed with explicit assumptions.

| Type | Signals |
|---|---|
| A. Build | System construction, data center, platform adoption, migration |
| B. Maintenance/technical support | Maintenance, support, SLA, regular inspection, subscription renewal |
| C. Technical response | Standard-product selection, item responses, matrix-number answers, BMT |

### 2. Skeleton — read `references/proposal-structure.md`
Use the type-specific outline unless the RFP prescribes one.
After fixing the outline, first write **a one-line lead (governing message) for each page/slide**.
Reading leads alone must establish the entire argument; otherwise revise the outline.
Create at most 3 Win Themes from official evaluation criteria and approved evidence, linking high-weight pages
(bid-and-submission.md §3). No unverified competitor information or disparagement.

### 3. Draft — read `references/writing-style.md` + `references/phrase-library.md`
   (For management, inspection, testing, migration, knowledge transfer, differentiation chapters,
   also consult the validated skeletons in `references/content-patterns.md`.)
- Page sequence: **lead (1~3 lines) → evidence (diagram/table) → caption/source**. One message per page.
- **Fill patterns with facts**; never copy complete phrase-library sentences unchanged.
- Certification/track-record/performance/SLA claims follow `references/evidence-and-claims.md`
  (source, version, reference date, scope). Exclude unsupported claims from the body;
  collect them separately with `[unverified]` and report to the user.
- Public/financial proposals (types A/B): show requirement IDs on each page and reconcile bidirectionally with the matrix.

### 4. Produce slides — read `references/deck-production.md` (specification source: `visual-style.md`)
- Write `slides.json` and generate using `scripts/build_deck.py`. Scripts fix coordinates/colors/fonts/hierarchy;
  the model fills only leads/table data/diagram elements. No arbitrary colors/fonts.
- Apply deck-production.md's relationship→layout table and story review. Narrow style options by audience/medium/brand;
  proceed without extra approval questions if existing requirements suffice.
- Pass brand tokens through `meta.palette` and `--template 사내양식.pptx`; otherwise use fallback tokens.
- Use corresponding types (`matrix/table/staff/gantt/zones`) for matrices, SLAs, staffing, track records, Gantt, architecture.
  Diagrams are editable native shapes (images only for line-connection topologies).
- Run `scripts/deck_check.py` for leads, REQ-IDs, page count, minimum fonts, density, table headers, off-slide placement;
  render with LibreOffice for page comparison/PNG thumbnails. A human visually inspects thumbnails.
- Use `scripts/check_numbers.py` to reconcile audit `numbers[]` values with slides
  (recognizes variants such as `37억`/`3,700,000,000`). A stale register or slide blocks.
- Accessibility floor: normal contrast 4.5:1, large text 3:1. No color-only statuses.
  Generator/checker inspect solid RGB contrast; theme/transparency/image backgrounds remain uninspected.
- Preserve presenter `notes` on covers, contents, dividers, closing, and split matrices.
  Include purpose, supplementary explanation, transition; verify each split matrix page after generation.

### 5. Quality gates — read `references/review-checklist.md`
For content/slide quality, follow [quality-first-authoring.md](references/quality-first-authoring.md):
connect evaluation questions, execution, evidence, verification, and actually review every slide.
When needed, use optional extraction/amendment/visual-comparison tools in
[source-and-visual-evidence.md](references/source-and-visual-evidence.md).
Keep outputs as unreviewed sidecars; they never automatically update submission gates or human approvals.
Perform one integrated pre-submission review. All 8 checklist items must pass before completion.
Priorities: exhaustive matrix mapping, consistent numbers/versions/schedules, rendered inspection after PDF conversion.
Run machine-checkable items with `scripts/quality_gate.py` (banned words, placeholders, residual customer names,
palette deviations); actual submissions also apply strict rules (bid-and-submission.md §5).
Inspect the original PPTX package separately from renders; never infer a pass for unseen areas.
Submission requires closed Critical/Major/BLOCKING INPUT plus confirmed rehearsal/receipt-evidence planning.

## Recurring rules (apply everywhere)

1. **No exaggerations**: preserved Korean banned examples "최고", "완벽", "혁신적", "100%", "무중단", "위험 제로"
   require objective evidence and scope on the same page.
   Actual winning proposals pair Korean examples "최적화된", "검증된", "안정적인" with evidence tables.
2. **State assumptions/exclusions** alongside schedule/cost/performance commitments.
   Hidden assumptions become post-contract disputes.
3. **Exact customer names**: preserve buyer/system names and requirement numbers as written in the RFP.
   Residual other-customer names are immediate rejection grounds; inspect reused material.
4. **No sensitive information**: exclude secrets, credentials, other-customer identifying information
   (company names, system architecture, figures). Anonymize and run substitution checks before importing reused material.

## Material locations

- `references/` — detailed stage guides (structure, sentences, evidence, visuals, review, content patterns).
- `assets/approved-examples/` — place the organization's approved/winning proposals here.
  Empty in the distribution to exclude sensitive information.
- `assets/brand-assets/` — organization's logos/templates; installed brand-document skill tokens are the single source.
- `scripts/build_deck.py` — slides.json → PPTX generator (12 layouts, role names for shapes).
- `scripts/deck_check.py` — layout lint, render checks, audit render block output.
- `fixtures/e2e-mini-rfp/` — mini RFP → slides.json → meta.json golden example spanning the pipeline.
- `scripts/quality_gate.py` — machine review (exaggerations/placeholders/residual names/palette). Inspects PPTX/DOCX/XLSX
  bodies plus notes, layouts, masters, charts, headers/footers, footnotes, comments, document properties
  (invisible residual customer names are a major rejection path). Forbidden names ignore case/whitespace.
  Added after identical grep checks recurred across 4 simulations under the "same code 2 or more times" principle.
  Add other scripts only when they meet the same criterion.
