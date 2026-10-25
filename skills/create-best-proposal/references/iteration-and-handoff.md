# Iterative production, revalidation, and session handoff

Read when trying a new design or continuing long production while retaining existing phases A–E and submission gates.
Do not create separate record files or additional approval stages for ordinary short reviews.

## 1. Pilot uncertain designs with representative slides

For a new brand/template/font or unverified layout, inspect around 3 representative slides before filling the full body.
The count is not mandatory: use enough to expose risks. Examples: a body slide with lead/source, the densest
table/matrix, and actual architecture/process types. A simple content update to an approved template may skip this.
Include long REQ-ID lists and Gantt milestones to check bottom wrapping, page-number spacing, and text/bar contrast.

- Use the final `meta.output_profile`, `meta.output_spec`, palette, and template.
- Generate/check with existing `build_deck.py --strict` and `deck_check.py --stage draft --render`.
  Give `--png-dir`/`--emit-render` pilot-only paths so final evidence is not overwritten.
- Inspect PNG clipping/table overflow/overlap/font substitution/reading distance. Proceed to full production when
  there are no fixes, or when the requested user design decision has been obtained.
- Without rendering tools, leave visual validation `NOT INSPECTED`. A pilot pass does not establish full-deck
  review, visual approval, or submission status. Final artifacts still undergo every Phase D/E check.

## 2. Rerun checks according to the change

For each work unit, first specify target REQ-IDs/evaluation criteria, files/slides, and completion criteria.
Follow `write → applicable check → fix findings → recheck` and inspect actual results.
Record commands/exit codes/output paths with input/artifact versions or hashes.

| Change | Recheck |
|---|---|
| RFP/amendment/Q&A/evaluation sheet | Phase A source/bid decision and stale sweep → affected REQ-IDs/evaluation links/body/matrix |
| Amounts/terms/quantities/SLA | Update numerical ledger and related body/PT/appendices together → arithmetic/`check_numbers.py`/unified gate |
| Content/fonts/tables/layout/template | Regenerate PPTX → layout/render checks → changed and adjacent/split slides |
| Missing response/evidence-effect confusion | Compare RFP subconditions with actual PPTX → revise text/matrix together → inspect new render |
| Final document/attachments | New hashes → review/approval records for those files → regenerate audit → `unified_gate.py --doc ... --bundle ... --stage submission` |

Visual review of every final slide and existing approval conditions still apply.
Never copy old approval to a new hash or automatically set `visual_review_approved` true.
Review the changed actual files and check final render/package/attachment hashes identify the same candidate.
An `--audit-only` pass does not validate a changed file for submission.

Before retrying rendering, distinguish log/tool/font/input errors. After 3 fix/revalidation failures with the
same cause, stop automatic repetition and report hypothesis, attempts, failure evidence, blocker, and needed inputs.
Repeated execution does not resolve missing tools, eligibility evidence, or pending approval.
Never lower stage or remove check/requirement/evidence/approval fields to eliminate blocks.

## 3. Independent review and unavailable tools

For Red review of long proposals or high-risk commitments, use a different reviewer or independent context when
available. Limit inputs to current RFP/evaluation sheet/ledgers/actual submission candidate, target slides, and
check results. Do not supply the author's self-evaluation as the correct answer.
Record severity, REQ-ID/slide/evidence location, and minimum required action.
If delegation is unavailable, state that limitation and review directly without claiming independent review.
Agent opinions do not replace mechanical checks or required human visual/submission approvals.

## 4. Preserve state and lessons only for long work

For multiple sessions, prefer existing progress records in the user's working folder.
Never record customer material in installed skills/plugins or public repositories.
Update only at milestones, important decisions, blockers, and handoff.

Handoff records include:

- Current path (Full/Pink/Red/Gold, etc.)/Phase, last verified work unit, next minimum task.
- RFP/amendment priorities/versions, ledger/slides.json/meta/audit/candidate locations and versions/hashes.
- Actually executed commands/exit codes/result locations, failures/uninspected items, remaining Critical/Major findings.
- Open decisions/blockers/needed inputs/owners, approval scope, reviewed file hashes.

On resumption, compare records with actual files/hashes/latest amendments instead of assuming they are true.
Rerun affected checks if files changed or check evidence cannot be found.
Do not assume fixed context-usage percentages. Handoff through these records when requirements/judgment become unclear.

Accumulate only confirmed repeated-failure causes, solutions, and revalidation results briefly; read only relevant
entries on similar future work. Never promote one customer's exceptions, hypotheses, or failed remedies to universal rules.
These are project-operation records, not new audit approval fields or automatic-pass evidence.
