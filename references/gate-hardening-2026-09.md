# Gate reliability audit and fixes (2026-09)

These findings came from directly probing the gate scripts with synthetic PPTX/DOCX/XLSX files and tampered audit JSON while all 132 existing tests passed. The scope was whether the gate's promised **deterministic blocking actually worked**, rather than the document layer (outlines, patterns, or writing style). Every finding was captured as a reproduction test in `test_gate_hardening.py`.

## P0 — False passes (the gate reported a pass incorrectly)

| # | Location | Reproduction | Fix |
|---|---|---|---|
| 1 | quality_gate | Residual customer names in notes, layouts, masters, or charts → pass | Scan `ppt/notesSlides`, `slideLayouts`, `slideMasters`, `charts`, `comments`, and `docProps/core.xml` |
| 2 | quality_gate | Exaggerated language in DOCX headers, footers, footnotes, or comments → pass | Scan `word/header*`, `footer*`, `footnotes`, `endnotes`, and `comments` |
| 3 | quality_gate | Body content lost after nested text-box `<w:p>` | Split by tracking top-level paragraph depth |
| 4 | quality_gate | Split runs (`최`+`고`) or markers containing NBSP → missed | Concatenate runs without spaces and normalize whitespace |
| 5 | proposal_gate | `accepted:"pending"`, `present:"no"`, `cleared:"no"`, `verified:"failed"` → READY | Strict boolean schema validation (strings → INVALID) |
| 6 | proposal_gate | Missing or misspelled claim `kind` (`Material`) → checks skipped | Missing=material; unsupported kind=schema error |
| 7 | unified_gate | `SUBMISSION-READY` displayed for a `mode:"draft"` audit | Display only for mode=submission; otherwise `DRAFT-READY` + NOTE |
| 8 | quality_gate/unified_gate | Printing `—` crashes on Korean Windows cp949 consoles → valid document BLOCKED | Reconfigure stdout as UTF-8; child processes use `PYTHONIOENCODING=utf-8` |

## P1 — Fail-open behavior and robustness

- `evidence_refs=["[NEEDS INPUT]"]`, `artifact_hash:"TBD"`, `receipt_plan:"TBD"`, and regulatory `evidence:"TBD"` passed as evidence → placeholders (TBD·TODO·???·needs input·입력요망·미정, etc.) are no longer accepted as evidence.
- A UTF-8 BOM in the names file caused its first name to be ignored → `utf-8-sig`. Match forbidden names ignoring case and whitespace.
- Damaged/unsupported files were mixed into exit 1 (blocked) → exit 2 (inspection unavailable). Added XLSX cell/comment inspection.
- Past `bid_conditions[].deadline` still yielded CONDITIONAL-GO → added future-date validation.
- `mode:"submission"` + `conditional-bid` returned exit 0 → blocked (conditional is an internal state).
- Empty `requirements` yielded submission READY → require at least 1 mandatory requirement. Missing `mandatory` means mandatory.
- The builder silently converted the string `"requirements": "R1 R2"` to `[]` → ValueError.
- The builder manufactured `evidence_refs` from `slide:N` and bypassed anti-optimism checks → no generated evidence, plus a warning.
- Builder `bool("no") == True` → ValueError for string booleans.
- Invalid `PROPOSAL_GATE_NOW` fell back to wall-clock time → environment error, exit 2.
- score_completeness metrics lacked range/type validation (producing 157 points) → require all 4 metrics within 0~1; INVALID exit 2.
- An arbitrary .py at unified_gate `PROPOSAL_GATE_PATH` → check module functions before returning INVALID.
- bulk_matrix: blank `mandatory`=False → True. Normalize `o`/`Y`/`△`, reject unsupported codes, and preserve multiline CSV cells.
- install_skill: block `--name ../..` path escape; replace incomplete directories lacking SKILL.md; add `--force` and cache exclusions.
- proposal_gate argparse (`-h`, unsupported flags exit 2). Non-UTF-8 JSON exits 2.

## Retained behavior (confirmed intentional)

- Master-color NOT INSPECTED warnings remain nonblocking (test contract).
- Skill-directory `test_*.py` files remain in distributions for installed self-checks.

## Related documentation updates

`unified-gates.md` §3/§4/§6; `audit-schema.md` (strict booleans and conditional scope); `create-best-proposal/SKILL.md` Phase D/E; material locations in `create-proposal-document/SKILL.md`; README test section; `.github/workflows/ci.yml`.

## Round 2 (2026-09-05) — Added the slide-production layer

A dry run following the skill with a mini RFP found that Phase D (visuals/output) had only prose guidance and no tools, requiring 100% model reinvention (1,583 lines read before the first slide). Without rendering/layout checks, no gate caught page limits, leads, REQ-IDs, or reduced font sizes. Changes:

- `build_deck.py`: slides.json → PPTX. 12 layouts, fixed coordinates/tokens, role-named shapes (TITLE/LEAD/REQID…), automatic matrix splitting, `--strict` for missing leads/page limits, and `--template` for corporate templates.
- `deck_check.py`: lint leads, REQ-IDs, page counts, minimum fonts, density, and table headers; compare LibreOffice rendering; produce PNG thumbnails and audit `render` blocks (render success + 0 blockers → verified). Missing soffice means NOT INSPECTED.
- Golden `fixtures/e2e-mini-rfp/` (rfp.md/slides.json/meta.json) and 14 cases in `test_deck_pipeline.py`.
- Gate adjustment: draft/review do not require `artifact_required`, `package.required`, or `checks.submission`, allowing Pink/Red checkpoints. Submission mode is unchanged.
- Vocabulary alignment: 6 support codes (`O/부분/조건부/X/N/A/확인필요`; Korean labels are display forms); requirement states use gate vocabulary (`pending→drafted→needs-review→approved`); human-review `CONDITIONAL GO` → `FIX-AND-RECHECK` to avoid collision with gate `CONDITIONAL-GO`, plus a label mapping table.
- Moved `score_completeness.py` to create-best-proposal/scripts so it works in installed trees; retained the root entry point.
- quality_gate markers: `○○`, `[unverified]`, and `미정` warn in drafts/block in submissions; `p.__` blocks.
- Rewrote frontmatter for all 3 skills around one entry point with load-only siblings, removing duplicate router triggers.

## Round 3 (2026-09-05) — Artifact binding and unified decisions (external diagnostic F01~F05)

Reproduced findings from the external diagnostic (fixed commit f346a18) on current main, then fixed only validated issues. F05's missed `[unverified]`, F06's missing production layer, and F09's undistributed scorer had already been resolved in round 2 (PR #14); the `package.checks={}` TypeError did not reproduce. All remaining findings were valid.

**F01 Artifact hash binding** — identify which file an audit records. `unified_gate.py` calculates the sha256 of `--doc` and compares it with `render/package.artifact_hash`, blocking mismatches so changed files cannot reuse old decisions. `mode=submission` + `artifact_required=true` without `--doc` blocks. Use `--audit-only` to inspect an audit without a document; its best result is `AUDIT-VALID`, not `SUBMISSION-READY`. Submission artifact_hash must be an actual `sha256:<64 hex>`, with render/package identifying the same file; the label `sha256:proposal` blocks.

**F02 One decision for stages, labels, and explanations** — `readiness(data, failures)` determines labels and exit codes; `explain_markdown` and CLI share it, removing draft audits described as submission-ready. Downgrading a `mode=submission` audit with `--stage draft` is a usage error (exit 2). `artifact_mode=simulation-only` blocks in submission mode.

**F03 Prevent conversion/schema data loss** — `_str_list()` no longer wraps strings in lists, removing the incorrect `"TBD"` → `['T','B','D']` conversion. Non-object ledger-array entries produce errors with locations (`requirements[2] must be an object`), preventing one string requirement being dropped and 3 entries becoming 2. IDs in `requirements[]` and `claims[]` are required and unique. `_enum_ok()` safely rejects nonstring enums (`mode=[]` produces INVALID exit 2 rather than a traceback).

**F04 Separate evidence, compliance, and response locations** — submission `supported|qualified` claims require `evidence_refs`. `support=X`/`fit=GAP` with `state=approved` blocks; buyer exceptions require `exception:{granted_by, evidence}`. `bulk_matrix.py` separates response locations into `response_refs`, no longer promoting them into `evidence_refs`.

**F05 Document inspection coverage** — `chart_text()` reads category/series caches (`c:v`) as well as run(a:t) text in charts, fixing residual customer names missed in titled charts (untitled charts were already detected). An ordinary ZIP merely named `.pptx` is a usage error (exit 2), not a `NOT INSPECTED` pass.

**Verification** — added 22 cases in `test_gate_integrity.py` including positive controls; all 149 root cases + 58 proposal_gate cases + 11 best_proposal cases passed. Replaced golden-fixture and test-base hashes with actual digests.

**Remaining items (not started)** — F06 arithmetic/coordinate verification (unified_gate does not compare `checks.arithmetic` with actual calculation); F07 sector profiles (public/corporate/school/hospital); F08 output-specific visual specifications (presentations 18pt+); F10 evidence for quality claims (blind comparative evaluation).

## Round 4 (2026-09-05) — External recheck R01~R08

Reproduced all 8 findings from the post-round-3 recheck on current main, then fixed them. Three exposed gaps in items I had recorded as fixed in round 3.

**R01 Verification bypass** — `SUBMISSION-READY` was possible with `artifact_required=false`, unverified rendering, and hash labels. Submission now requires render verification, hash format, and package checks regardless of input (`artifact_required = data[...] or mode == "submission"`).

**R02 Unopenable packages** — ZIPs without `[Content_Types].xml` passed submission although python-pptx could not open them. `validate_package()` checks required parts (`[Content_Types].xml`, `_rels/.rels`, and body parts) and main-part XML parsing, using only zipfile with no new dependencies. **CI positive controls had the same defect** and were replaced with actual python-pptx files. Shared `ooxml_fixtures.py` builders now also verify actual-loader acceptance.

**R03 Residual template slides** — adding 1 cover to a 2-slide template produced a 3-slide file retaining previous customer names/amounts but reported "1 slides" (confidentiality leakage and invalid page-limit checks). Reject templates containing slides and count actual slides rather than internal counters.

**R04 Off-slide placement** — valid 18pt text entirely outside the slide produced 0 blockers. `out_of_bounds()` compares text-shape coordinates with slide bounds (fully outside or more than 25% clipped → blocked). It also found and fixed golden-deck Gantt labels crossing the right margin. Separate `render_succeeded` (machine) from `visual_review_approved` (human); submission requires the latter and the real name in `visual_reviewer`. Successful PDF conversion is not design approval.

**R05 Row loss** — `rows_per_slide=-1` reduced matrix data to 0 rows even under `--strict`. Accept only positive integers and compare input/output row counts.

**R06 Lost aliases/fields** — `support="X 미수용"` bypassed approval consistency checks; `is_unsupported()` now unifies notation variants. More seriously, round 3's exception path **did not work when following the documentation**: meta→audit dropped `exception` and `response_refs`, falsely blocking legitimate buyer exceptions. Preserve both with type validation.

**R07 Contradictory explanations** — `STATUS: AUDIT-VALID` appeared beside "게이트 결과: SUBMISSION-READY / 제출 가능." Round 3 regression tests all used `--no-explain` and missed it. `explain_markdown(..., label)` accepts the caller's decision; new tests also inspect explanations.

**R08 Enum types** — `claim.kind=[]`, `package.checks.metadata={}`, and similar inputs raised TypeError. Unify enum comparisons through `_enum_ok()` (reject nonstrings without crashing → structured INVALID).

### Verification

Added 24 cases in `test_gate_integrity2.py` including positive controls; all 183 root cases + 58 proposal_gate cases + 11 best_proposal cases passed. Added negative CI golden controls for bypass blocking, explanation contradictions, template rejection, and row loss. Repeated all 8 report reproductions using their original procedures and confirmed every one blocked.

### Remaining items

F06 actual arithmetic comparison (body values versus ledger), F07 sector profiles, F08 output-specific visual specifications, and F10 blind comparative evaluation. Table-cell overflow and overlapping shapes still require visual thumbnail review.

## Round 5 (2026-09-05) — Numerical ledger and actual arithmetic checks (remaining F06)

`checks.arithmetic: true` is a human self-declaration: the gate could not detect body text stating `100원 + 200원 = 900원`. Through round 4, fixes established which file was reviewed and whether it opened, but correctness of the numbers in that file still depended on human declarations.

**Numerical ledger (numbers[])** — record amounts, durations, and quantities as `{id, label, value, unit, source}`. Link components through `components` so the gate recalculates totals; `percent_of`+`amount` recalculates ratios. Mixed-unit totals, unknown component references, duplicate IDs, and nonnumeric values each produce errors with locations. Default tolerance is 0.5%, adjustable per entry.

**Binding self-declarations** — submission cannot pass on `checks.arithmetic: true` alone without a ledger. Claiming arithmetic completion without showing what was checked is not verification. Draft/review still do not require ledgers, preserving checkpoint reachability.

**Document comparison (check_numbers.py)** — the gate checks ledger arithmetic, but must open the document to establish that slide values match. Korean proposals use alternate notations (`3,700,000,000` / `3700000000` / `37억` / `370,000만`), so generate variants and block when none appears. Respect numeric boundaries so `370억` cannot falsely match `37억`. Exclude intermediate calculations with `must_appear: false`.

**Builder preservation** — dropping `numbers` during meta→audit would block submission as missing its ledger. Preserve the ledger with type validation; non-object entries produce errors with locations.

### Verification

Added 18 cases in `test_numbers_ledger.py`; all 201 root cases + 58 proposal_gate cases + 11 best_proposal cases passed. Added ledgers to submission/e2e mini-RFP golden fixtures for recalculation on every CI run.

### Remaining items

F07 sector profiles, F08 output-specific visual specifications, and F10 blind comparative evaluation. Errors in body values omitted from the ledger remain undetectable; authors decide what to record.

## Round 6 (2026-09-05) — Output-specific visual specifications (F08)

Imposing the same 11pt/600-character rules on printed evaluation documents and projected meeting slides necessarily fails one of them. Split specifications into profiles while ensuring **generator and checker share one definition**: this repository repeatedly suffered from the two tools maintaining divergent constants.

**deck_profiles.py** — `detailed-submission` (default, 22/11/10pt, 600 characters, 12 matrix rows); `presentation` (30/18/14pt, 250 characters, 6 rows); `executive-summary` (26/14/12pt, 400 characters, 9 rows). Fonts, lead length, density, table rows, and matrix splitting derive from one definition. Minimum font thresholds derive from the smallest body size in the profile rather than constants. Stamp core properties with `proposal-deck:<프로파일>` so checkers apply matching criteria without arguments.

Also reconciled values already divergent before implementation: table-row warnings (generator 14, checker 15) and density (bullets 450, body 600).

### Defects found in immediate adversarial self-review and fixed together

- **Density checks could not see tables.** GraphicFrame tables made `shape_text` return an empty string, counting dense matrices as 0 characters. Presentation 250-character limits did nothing on table slides. Read cell text instead; the golden presentation matrix correctly warned at 295 characters.
- **Duplicate shape names shifted density pairs.** Separately zipping a name dictionary and text list counted the wrong text or omitted the body when multiple Gantt milestones shared names. Changed to one shape traversal.
- **Legends bypassed inspection.** `BODY_LEGEND` was treated as metadata and remained below body minima. Removed the metadata exclusion and drew it at or above the body minimum.
- **Unstamped decks silently passed permissive defaults.** Distinguish missing from unknown stamps and block both at submission (warn in drafts). External decks specify criteria through `--profile`.
- **Matrices alone bypassed table-row limits.** The generator now warns when `rows_per_slide` exceeds profile limits.

### Verification

Added 25 cases in `test_output_profiles.py`: inter-profile size/density relationships, stamp round trips, table-cell density, duplicate names, legends, thresholds versus actual output, and fail-closed missing/unknown stamps. All 226 cases passed. CI generates and inspects all three profiles and confirms detailed decks block when measured against presentation criteria.

### Remaining items

F07 sector profiles and F10 blind comparative evaluation. Table-cell text overflow and shape occlusion still require visual thumbnail review.

## Round 7 (2026-09-05) — Proposal-context classification (F07, reduced scope)

Did not implement the diagnostic's 4 sector profiles as requested. This repository's value came from machine verification, while hospital/school profile prose cannot be verified. Guidance that hospital proposals should address patient safety can be written without this skill. Instead, narrowed F07 to a verifiable form by making **classification change gate requirements**.

**Classification axes (context)** — `buyer_types[]` allows multiple values (public hospitals → public+healthcare), plus `engagement`, `stage`, `reading_mode`, and `constraints[]`. Do not classify from institution names alone.

**What classification changes (machine checks)**

- Public + submission → require an `evaluation_criteria[]` ledger. Weights total 100 (±0.5); **block criteria without mapped requirements**, signaling an entirely omitted outline subject. Link requirements through `criterion_ids`.
- Compare `reading_mode` with `render.output_profile` to catch print-profile decks labeled as presentations, connecting to round 6 output profiles.
- `sensitive-data` in `constraints` → package metadata, hidden-content, and stale-customer-data checks must all be `pass`.

**Only one sector profile: public** — `references/sectors/public.md`. Most existing guidance already assumed public bidding, so this was extraction rather than invention. Corporate, education, and healthcare retain only axes/rules with empty content; README explains the gaps and how to add material. Giving unverified content the authority of a profile is worse than leaving it empty.

The check found an actual golden-fixture defect: the mini RFP evaluation table allocated 20 points to price, but no matching requirement existed in the ledger. Added the requirement.

### F10 will not be implemented

Rounds 3/4 removed unsupported scoring claims, fulfilling F10's central requirement for honesty. Remaining blind comparison requires independent evaluators. An unused evaluation harness creates only the appearance of verification and is worse than none. Close it explicitly as not performed, recorded in README under what the gate does not inspect.

### Verification

Added 21 cases in `test_context_classification.py`; all 247 cases passed. Tests also compare documented axis values with code enums.

## Round 8 (2026-09-05) — Third diagnostic (D01–D09) and public-repository hygiene

### Issues blocked in this round

**Approval records lost during conversion (D01).** `build_audit_from_meta.py` omitted `render_succeeded`, `layout_checked`, `visual_review_approved`, `visual_reviewer`, and `output_profile`, blocking valid visually approved workflows as unapproved. False blocks mirror false passes and encourage disabling gates. Copy only supplied input records without inventing approvals. This recurring conversion defect, following evidence, exceptions, and numerical ledgers, was fixed in regression tests as its third recurrence in this repository.

**Requirements disappeared when fields were removed (D02).** `layout_checked` was inspected only when present; deleting it removed the check entirely. Changed to missing = uninspected = blocked. Also block self-contradictory records such as `verified: true` + `render_succeeded: false`.

**Uncomputable ledgers passed (D04).** `Infinity`, `NaN`, self-references, ratios without `amount`, and zero denominators silently passed. Uncomputable means unverified, not passed. Relative tolerance of 0.5% permits an 18.5-million-won difference on 3.7 billion won, so currency changed to 1-won absolute tolerance. Empty submission ledgers require a `numbers_not_applicable` reason.

**Same digits, different meanings (D03).** `37` matched `37.5`, `370`, and `-37`; `37개월` counted as evidence for `37원`; **values only in notes counted as present in the document**. Include decimal points/signs in numeric boundaries, compare only units **attached** to numbers (VM in `400 VM` is treated as a noun), and limit comparison to evaluator-visible body content. Values confined to non-body content block with that explanation.

**Unopenable packages (D05).** Structural checks parsed only main and `[Content_Types].xml`, allowing broken `slide1.xml` or `_rels/.rels`. Parse relationship and body parts, and open once with python-pptx in `deck_check.py` (`quality_gate.load_check`). Loader checks apply only to final-artifact inspection to avoid tying every text-extraction path to libraries. This exposed fixture defects too: parts without namespace declarations and multi-root fragments were not real files. Aligned fixtures with real files.

**Font minima did not protect body text (D06).** `min(본문, 표) - 1` applied table minima to body text, allowing detailed body text reduced to 9pt. Separate body and small-text thresholds (`min_body_font` / `min_table_font`). Paragraph-only font sizes were omitted because `run.font.size` was None; resolve effective sizes from run → paragraph → shape. Group-local child coordinates were mistaken for slide coordinates, producing wrong bounds decisions; accumulate group transforms (`chOff`/`chExt` → `off`/`ext`). Legends/Gantt labels are small text like table cells, not body prose. Define `SMALL_TEXT_PREFIXES` only in `deck_profiles.py` so generator/checker agree.

**The installer deleted user files (D07).** Directories missing `SKILL.md` were treated as interrupted installations and removed with `rmtree`. The installer cannot distinguish leftovers from user folders. Reject nonempty directories and replace only with `--force`.

**Claimed hash agreement for uninspected files (D08).** `--audit-only` explanations read like submission approval. Claim matching hashes only after inspecting the document.

**Hollow ledgers and exemption paths (D09).** ID-only requirements/claims do not establish what an R1 approval actually approved. Require human-readable content at submission; drafts allow partial ledgers. `kind: informational`, the sole evidence-exempt classification, requires an exemption reason. Also fixed `TypeError` crashes while constructing sets from nonstring units.

### Public-repository hygiene

This public repository handles proposal material containing customer names, contacts, quotations, and internal paths. Instead of manual filtering every time, `test_repo_hygiene.py` scans all `git ls-files` and blocks local absolute paths, email addresses, internal workspace links, and credential-shaped strings. Inspect only detectable content: machines cannot decide whether a name belongs to a customer. AGENTS.md writing rules cover the rest. Removed author-local paths remaining in `references/architecture-review-10x.*`.

### Verification

Added 29 cases in `test_gate_hardening_d.py`; all 280 cases passed. This includes a **valid-path end-to-end case**: approved inputs/ledger → actual PPTX generation → layout/numerical checks → render/visual approval records for that file → meta→audit → final decision on the same file (SUBMISSION-READY). Verify that hardening preserves valid artifacts with the same priority as blocking tests.

## Round 9 (2026-09-06) — Public RFx review: rules come from source documents

Selected only verifiable findings from an external comparison of 12 public RFP/RFI documents. Items overlapping round 8 (render-field loss in conversion and false numerical matches) were already resolved and confirmed by measurement.

### Missed in round 8 — missing `output_profile`

Applied missing = uninspected = blocked to `layout_checked` but not the adjacent field. When `reading_mode` implied a specification, an invalid `render.output_profile` was caught, but **deleting it passed**. Block omission at submission and reject unknown profile names.

### Missing submission classification disables checks

`context` was optional for backward compatibility. Removing classification silently disabled public evaluation criteria, specification comparison, and sensitive-data checks: passing checks and having no checks produced the same result. Require `buyer_types` and `stage` in submission mode; drafts/reviews remain allowed.

### Evaluation methods come from source documents, not institution classifications (P0-3)

`{id, label, weight}` plus a total of 100 could not represent real notices. With only technical 90 points in the ledger and price separately bound, **the gate falsely demanded a total of 100**. Recording stage-1 technical 100 = quantitative 20 + qualitative 80 in one array yielded 200. Changed to hierarchical ledgers: top-level sum = `evaluation_total`; children sum to parent weight; undisclosed weights use `disclosed: false`; cutoffs are preserved as `minimum_ratio`/`minimum_score`. The gate checks totals without predicting evaluation scores.

The external review correctly challenged the attached proposal's fixed public-sector technical 85% and SW 90:10 assumptions. Negotiation eligibility of 85% means 85% of the **technical-evaluation maximum**, not 85 total points, and 90:10 has exceptions. Hardcoding these values would reintroduce the unsupported numbers this repository has been removing. Read source documents, record their values, and calculate only from that ledger.

### Requirement strength (P0-4)

One `mandatory` boolean gave recommended-length overruns and mandatory violations equal weight. Added `strength` (required/recommended/optional/conditional/informational), retaining `mandatory` as a derived value. Disagreement is a schema error. Conditional requirements need conditions and count as mandatory. Submitting without following a recommendation requires a reason, distinguishing omission from a deliberate exception. Terms 권장·조건부·참고 in the `필수` column of `bulk_matrix` become strength values.

### RFI is not a bid (P0-2)

The review proposed `stage=rfi-response`, but another paragraph made the better distinction: procurement stage and document kind belong on different axes. Added `context.rfx_type` (rfp/rfi/rfq). `rfi` does not require public-sector evaluation criteria, but blocks `commitment` claims to prevent estimates becoming commitments. Qualification, attachment, and format checks remain active for RFIs. Specify what differs rather than disabling checks because the document is an RFI.

### Not adopted

- **Four sector profiles.** The review itself said technologies in a case are that case's requirements, not sector-wide obligations. Applying that standard leaves insufficient evidence for profiles based on 1 example per sector. Outline branching by `engagement` (review P1-2) is a verifiable alternative and candidate for the next batch.
- **External RFx collection.** The bottleneck was representing collected material in a ledger, not collection. This batch supplied that representation.
- **Submission-bundle inspection** (named/anonymous copies and separate price volumes) and integrating `check_numbers` into the unified gate require broader schema changes and are deferred to round 10.

### Verification

Added 17 cases in `test_rfx_rules.py` and updated 2 classification-test contracts; all 298 cases passed. Reproduce public-case rules with synthetic data only; do not include original documents/source URLs because procurement links expire after closure.

## Round 10 (2026-09-06) — Submission bundles and automatic numerical comparison

The two items deferred from round 9 both remove checks that exist but nobody runs.

### Submission is a bundle, not one file

Gyeonggi Cultural Foundation-style notices distinguish named originals, anonymous copies, two electronic-file types, and sealed prices; MU Health Care-style notices require separate non-price submissions and price worksheets. The gate previously checked only `attachments[]` presence, with only the main file hash-bound. Thus **valid named originals with bidder names still in anonymous-copy notes**, or **missing price volumes**, passed.

Added `role` (proposal / proposal-anonymous / price / form / certificate / presentation / appendix / other). A role activates its rules; absent roles retain presence-only checking. Submission attachments marked `present: true` require `sha256`. Anonymous copies require identification-inspection records and reviewers; non-price artifacts require price-contamination inspection records. If multiple artifacts use submission roles, require an explicit choice of the submission file.

`unified_gate.py --bundle <폴더>` compares every attachment with actual files and hashes. Binding only the main file leaves changes to other attachments after review undetected.

Machine limits remain: identifying content in logos/images, printing, stamping, sealing, and on-site submission. Anonymous copies therefore also require a human `reviewer`.

### Integrated numerical comparison into the unified gate

Round 8 corrected `check_numbers` accuracy (decimals, units, signs, body-only scope), but the unified gate did not invoke it. Checks requiring separate manual execution do not get run. Run by default when `--doc` supplies a document and a ledger exists. Stale slide amounts block even with matching hashes. `--skip-numbers` marks submission uninspected and blocks rather than passing.

This exposed **defective positive controls**: audits containing 37억 ledgers were bound to synthetic PPTX files containing no numbers and called valid. Added matching amounts to control documents. Calling a ledger-mismatched document valid makes the comparison meaningless.

### Verification

Added 15 cases in `test_submission_bundle.py`; all 313 cases passed.

## Round 11 (2026-09-06) — Engagement type changes outlines

The external review correctly noted that `engagement` included training, consulting, and policy while flagship Phase B still selected only A implementation / B maintenance / C technical response. Classification values and production-path support are different. If only classification is checked while outlines remain unchanged, proposals with merely renamed institutions pass.

### Recorded outline archetypes in the ledger

`proposal_archetype` (build / maintenance / technical-response) records the outline actually used; the gate compares it with `context.engagement`. An implementation outline for maintenance blocks. Buyer-specified outlines pass with supporting `archetype_rationale` because RFP instructions always take precedence. Submission records for mapped engagements must identify the chosen archetype; one line suffices, and omission on both sides cannot count as valid.

With `sections[]`, check required sections per archetype. Implementation requires scope, implementation approach, schedule, testing/acceptance, and delivery organization. Match section names loosely by keywords (both "시험 및 검수" and "테스트 방안" qualify). The goal is detecting entire missing subjects, not forcing names.

**Do not infer outlines from `slides[]`.** The first implementation did so, but `slides[]` maps requirement responses, not outlines. Treating partial mappings as outlines falsely reports existing sections as missing. The golden fixture immediately exposed that false positive and the approach was reverted.

### Do not invent unsupported outlines

Five engagements are mapped (build/migrate/operate/service-improvement/product-selection). Training, consulting, and policy have no repository-backed outlines, so **do not force archetypes**, for the same reason only the public-sector profile has content. Still require a rationale when these engagements reuse IT implementation outlines. Neither force unsupported structure nor silently ignore it.

### Found an actual golden-deck defect

The new check reported **missing scope and testing/acceptance sections** in the mini-RFP golden deck, both required by standard type A. Added two slides instead of weakening the check (15→17 slides). Missing scope and acceptance criteria in implementation proposals leave room for contract disputes.

### Related cleanup

- **Reading environment ≠ document role.** Removed `individual-review → executive-summary`. Individual readers may use executive summaries or detailed technical evaluation documents; environment alone did not justify choosing a role. Retained presentation/printed-evaluation mappings because those environments effectively determine specifications.
- **`requirements.txt`.** New installers previously had to read README to discover `python-pptx`. Also documented LibreOffice as a dependency outside pip. CI uses this file too.

### Verification

Added 17 cases in `test_outline_archetypes.py`; all 330 cases passed. Added 4 outline controls in CI.

### Addendum — a full local pass coexisted with CI failure

Round 10 failed 4/4 CI jobs while all local tests passed. The cause was **coverage**, not test content. `unittest discover -s .` does not recurse into directories without `__init__.py` and therefore omits `skills/*/scripts/test_*.py`. CI runs them separately, so the local 313-case pass excluded 69 CI cases. Those included positive controls broken in round 10 (`test_best_proposal.py` also expected SUBMISSION-READY for a PPTX without ledger values).

This also caused a mistaken fix: I speculated about an unreproduced failure and patched it, fixing the same defect in a different file while CI remained red. I should have followed the rule to reproduce before fixing.

`test_skill_scripts.py` uses load_tests to include those files in root execution (401 cases). A test catches tracked test files omitted from every execution path.

## Round 12 (2026-09-06) — Make the full suite practical locally

Changed execution, preserving test content. Full runs took Linux 47 seconds / Windows 46 minutes. Impractical local runs encourage CI-only validation, which caused actual incidents in rounds 10/11: local passes coexisted with CI failures and were merged in that state.

Invocation was the cause. Each test launched a script through `subprocess`, repeating interpreter startup/imports; Windows added process creation and antivirus overhead, reaching tens of times the Linux duration.

`test_support.run_script` invokes scripts **in the same process**. All skill scripts use `main(argv) -> int`, so direct calls can capture stdout and exit codes. Return objects match `subprocess.CompletedProcess`, preserving callers.

Retained child-process paths because **the process itself is under test**:

- Console encoding, including survival in cp949 child environments.
- Propagation of exit codes to the shell.
- Direct installed execution through `python <script>`.

Generate repeatedly requested golden decks once and copy them (`build_deck_cached`). Determinism preserves test inputs while removing redundant generation cost.

Tests verify decisions remain unchanged: compare in-process/subprocess exit codes and output for identical inputs, confirm default calls spawn no child processes, and confirm isolated paths still spawn (`SpeedContractTests`). Tests catch contract violations first.

### Results

Linux 47 seconds → 21 seconds. Remaining child processes serve necessary encoding, installation, `git ls-files`, and similar checks (fewer than 20 per full run). All 404 cases passed.

## Round 13 (2026-09-06) — Gaps found with an actual proposal

The first twelve batches used repository-built fixtures. Ran one actual public-sector RHEL-standardization proposal (9 slides) in submission mode. Do not include the original document in the repository; reproduce only rules with synthetic data.

### Correct gate findings

All 18 blockers were justified, with **no excessive blocking**. Particularly accurate findings:

- Unsupported benefit claims ("관리 비용 절감·계획외 다운타임 감소") lacked `evidence_refs`, identifying a common practical reason for score deductions.
- The implementation archetype lacked scope, schedule, testing/acceptance, and delivery-organization sections; they were actually absent.
- Evaluation criteria had no mapped requirements, indicating writing without knowing what carried scores.

### Three missed issues

**Manufacturer-dependent commitments passed as bidder commitments.** "심각도1 1시간 내 대응" is valid only when the manufacturer's SLA applies to the relevant contract/subscription tier, yet placing public manufacturer documentation in `evidence_refs` let `commitment` pass. `vendor_confirmations` existed but was checked **only if authors populated it**; otherwise no requirement existed. Declaring `claims[].depends_on_vendor` now requires a same-named confirmation with `present: true`. Citation is not confirmation.

**Time-dependent claims required no reference dates.** Statements such as "2032년까지 지원" and "현재 9.8" become outdated without reference dates. The reviewed document stated "기준: 2026.07", but omission would still pass. Require `time_sensitive: true` + `as_of` (YYYY-MM). Free text ("2026년 여름") does not qualify, preventing reused slides from silently becoming stale.

**Relationships between numbers were ignored.** Correct individual SLA values do not make a correct table if initial response ≤ ongoing response or severity ordering is wrong. Added `at_most`/`at_least` and compare duration units converted to hours (minutes, hours, days, business days, weeks, months, years). Detect swapped values across units, such as `4시간` versus `2일`. Compare non-duration values only with matching units; do not compare equipment counts and people counts.

### Vocabulary additions

The document's "최첨단" escaped exaggerated-language checks. Added `최첨단·압도적·탁월한·독보적·최상위·차원이 다른`. Excluded "최상위 파트너 등급" as the actual name of a Red Hat partner grade, just as "최고 등급" was already exempt. Detect only self-promotional uses such as "최상위의 품질".

### Verification

Added 17 cases in `test_real_proposal_findings.py`; all 421 cases passed. Running the actual document again changed both gaps to blockers.
