# Quality gates (review-checklist)

Run one integrated review before submission. **All 8 items must pass before declaring completion.**
After failure, fix and recheck the failed items; after structural changes, recheck everything.

## Review-only requests — when not writing a new proposal

For review/revision of an existing proposal, apply the 8 gates **as diagnosis rather than drafting**.

1. **Preserve the original**: do not rewrite the entire document. Report findings and minimum corrections
   (except when the user requests comprehensive revision).
2. **Proportionate scope**: review supplied material only. Do not claim to have reviewed absent RFP/evidence; state unchecked scope.
3. Sort results by **severity**:
   - **Critical**: disqualification, mandatory omission, unsupported high-impact claim, unapproved commitment,
     or contradictions affecting eligibility, mandatory targets, scope, price, staffing, security, schedule.
   - **Major**: significant gap; promote to Critical if the missing value causes mandatory omission or conflicting commitments.
   - **Minor**: local clarity, terminology, structure, or formatting issue.
   - **Note**: optional improvement.

**Minimum correction format**: for each finding, specify the changed fact / owner-role / decision deadline /
approval requirement / dependent calculations and sections to update.
Korean example: "투입인력 50↔35 모순 → M/M표 기준으로 재산정, owner=PM, 기한=제출 3일 전, 요약·조직도·프로필 3처 동기화".

**Unverifiable items**: do not assert truth/falsehood from insufficient source material (e.g., which figure is correct,
whether an approver exists). Mark `[unverified]` or missing and request user confirmation.
Initially scan placeholders, exaggerations, and residual names with `scripts/quality_gate.py`.
Deliver original + severity-sorted findings + minimum corrections + scope/limitations.

## Eight review items

### 1. Exhaustive requirement mapping (compliance matrix)
- [ ] Every requirements-register row is review-approved (Korean display: "검수완료").
- [ ] Matrix page numbers match final layout and were updated afterward.
- [ ] Partial/X responses have reasons and alternatives in Notes.
- [ ] Body-page REQ-IDs ↔ matrix agree bidirectionally.

### 2. Lead-statement story
- [ ] Reading every slide lead alone establishes the proposal logic.
- [ ] No content-free leads (Korean example: "~에 대해 설명합니다").
- [ ] One page, one message; split pages containing two.
- [ ] The overview answers five questions: buyer decision / current problem and impact /
      what is proposed and why / measurable outcome and risk / next step.

### 3. Exaggeration and evidence
- [ ] Search Korean banned-word inputs: 최고·완벽·혁신적·획기적·100%·무중단·완전 자동화·위험 제로·유일한.
      Check same-page objective evidence/scope for each hit; otherwise replace.
- [ ] Every track-record, certification, performance, SLA claim has source, reference date, scope.
- [ ] The `[unverified]` list is empty or reported to the user.

### 4. Internal consistency of figures, versions, schedules
- [ ] Staffing: summary ↔ organization ↔ profiles ↔ M/M agree.
- [ ] Schedule: roadmap ↔ Gantt ↔ milestones agree.
- [ ] Versions: introduction ↔ architecture ↔ specifications ↔ licenses agree.
- [ ] EOL/support-end dates verified current on the web.

### 5. Customer names and reused material
- [ ] Buyer/system names exactly match the RFP.
- [ ] **Search all previous customer names** (grep against the reused source's name list): 0 remain.
- [ ] Reused dates/staff/track records refreshed to current values.

### 6. Format requirements (RFP rules)
- [ ] Page/length limits met (excess causes deduction/disqualification).
- [ ] Submission format (PPTX/PDF/print), cover fields, contents comply.
- [ ] Required attachments (quotation, certification copies, commitment letters) reconciled.

### 7. Visual specifications (visual-style + brand skill) — machine check: `deck_check.py`
- [ ] `deck_check.py --require-req-ids --max-pages N`: 0 blockers (leads, REQ-IDs, pages, minimum fonts, table headers).
- [ ] All colors use prescribed palette (brand tokens or neutral defaults); 0 arbitrary colors.
- [ ] Fonts are prescribed or official fallbacks (one-line notice for temporary fallback).
- [ ] No color-only statuses/categories; labels/symbols accompany them.
- [ ] Tables have headers/units/sources/reference dates; figures have captions/alt text.
- [ ] 0 remaining placeholders (preserved test inputs: lorem·xxxx·샘플·TBD).

### 8. Final render — machine check: `deck_check.py --render --png-dir out/png --emit-render render.json`
- [ ] PDF page count equals slide count; reflect `render.json` `verified:true` in meta.render.
- [ ] Visually inspect every `out/png` image: 0 clipped text, broken fonts, overflowing tables.
- [ ] Contents page numbers equal actual pages.
- [ ] 0 exposed secrets/credentials/internal hostnames (mask findings as `****`).
- [ ] Separately inspect source metadata, notes, comments, hidden content, attachments, external links, macros.
- [ ] For separated pricing, 0 price/cost/discount-rate disclosures anywhere in the technical package.
- [ ] Uninspectable package items marked `[NOT INSPECTED]`.
- [ ] All Critical/Major/BLOCKING INPUT items Closed with resolution evidence.
- [ ] File opening/upload or print rehearsal and receipt-evidence plan confirmed.

## Running the review

- Text checks for 1/3/5/7 use `scripts/quality_gate.py`
  (exaggerations/placeholders/residual names/palette deviations in one run, judged by exit code).
  Example: `python3 scripts/quality_gate.py 제안서.pptx --names 이전고객명.txt --palette "1F3864,8FAADC,D6E0F0,EDF1F8,C00000,1F7A3D,202020,595959"`
- For 2/4, make lead lists and numeric comparison tables and compare visually.
- For 8: `deck_check.py --render` (LibreOffice) → PNG thumbnails → human visual review.
  Without soffice, leave `NOT INSPECTED` and inspect directly in PowerPoint.
- Report item-level pass/fail and corrections concisely to the user.

## Standard scores and statuses (reviewer convergence)

Fix these rules so reviewers do not diverge on numbers/status for the same proposal.

1. Always report **two separate axes**, never one merged score:
   - **Authoring quality (0~100)**: requirements, evidence, persuasion, execution, visual, security.
   - **Submission readiness (0~100)**: mandatory inputs, approvals, evidence, render, package, file rules, rehearsal.
2. **Only readiness gates determine status**, regardless of writing quality.
   - `SUBMISSION-READY`: 0 unresolved BLOCKING + render/package/rehearsal confirmed.
   - `CONDITIONAL-GO`: only when **all** remaining conditions have owner, deadline, and accepted status.
   - `NO-GO`: any unresolved BLOCKING or expired deadline → **default**.
   - Draft/discovery stages use `DRAFT`/`DISCOVERY` (outside submission framing).
   - Example: an unaccepted BLOCKING input means `NO-GO`, not `CONDITIONAL-GO`.
3. If a one-line score is needed, give authoring X / readiness Y **together**. Put status first if readiness
   gates fail. Preserved Korean output example: "NO-GO · 작성 88 / 준비도 20".
4. Use the same status vocabulary as create-winning-proposal audit (cross-skill compatibility).

## Unresolved markers and gate stages (quality_gate --stage)

Unfilled factual slots use `[NEEDS INPUT]` in notes and the Korean marker `［입력요망］` in PPTX bodies.
Distinguish stages:

- `quality_gate.py … --stage draft`: unresolved markers are **nonblocking warnings** (draft review).
- `--stage submission` (default): unresolved markers **block** (none may remain in a submission).
- `[NOT INSPECTED]` for default theme colors is always a **nonblocking warning**; normal generated decks
  must not be blocked despite a complete palette. A human separately checks final HEX values.

### Stage decision tree
- Still filling facts (draft circulation/internal review)? → `--stage draft`. Markers warn and identify gaps.
- Is this artifact a real submission candidate? → `--stage submission` (default). Any marker blocks; no blanks in submissions.
- Rule: could this be sent to the customer unchanged? Yes → submission; no → draft.
  If unclear, inspect strictly as submission, then reclassify warnings under draft criteria.

### Centralize completeness figures in score_completeness.py

For completeness-score requests, run `create-best-proposal/scripts/score_completeness.py` (same entry point at repository root).
It calculates readiness and quality using one formula; **gates determine status** (BLOCKING means NO-GO even with high quality).
This single standard removes reviewer score differences.

Governance anti-optimism guards (unsupported approved states, expired deadlines, unremediable ineligibility)
follow create-winning-proposal [audit-schema.md](../../create-winning-proposal/references/audit-schema.md).
