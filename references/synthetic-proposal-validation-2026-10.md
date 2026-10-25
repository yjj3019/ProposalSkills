# Actual production validation with a synthetic RFP (2026-10-25)

## Scope

Created an editable proposal for a fully synthetic public-sector IT maintenance RFP: 22 requirements,
12 months, 34 management items, SLA/security/handoff/acceptance/training/pricing/output specifications.
The 100-point evaluation sheet was input for coverage structure; no attained score or win probability was calculated.
UI was excluded; actual PDF/PNG files were generated with PowerPoint `WithWindow=false` conversion.

Separately from the author's matrix, compared original RFP text with actual PPTX body/tables/rendered images,
including contract dates/exclusions outside numbered requirements. With no actual eligibility/track-record
material, retained `simulation-only`, `intake-incomplete`, and false human visual/submission approvals.

## Findings and changes

| Finding | Action | Revalidation |
|---|---|---|
| Required report cause/action/recurrence prevention reduced to `RCA` abbreviation | Explicitly stated all three in body; strengthened subcondition comparison guidance | Actual slide 7 response checked |
| Backup role table substituted for contact/handoff execution path | Stated primary failure→backup→PM and received-time/open-item/next-action handoff | Actual slides 5/13 checked |
| Unprovided customer problems asserted as current facts | Labeled as risks to prevent | Re-reviewed fact/assumption boundaries of three Win Themes |
| Customer effects placed in card evidence field | Separated effects from future synthetic acceptance plans | Compared actual cards/source |
| Display B type/draft classification confused with audit enums | Normalized existing schema type/stage/input/criterion fields; strengthened conversion guidance | Reran gates preserving actual open items/false approvals |
| Valid outline title (Korean example: `지원 범위와 서비스 경계`) falsely missing due to spacing | Added existing maintenance keyword variant `지원 범위` (Korean input preserved) | Spaced/unspaced forms pass; actually removed sections still block |
| Long REQ-IDs wrapped into footer on 4 slides | Reallocated bottom width while retaining font size/all IDs | Native PDF wrapping reduced 4 slides→0 |
| Red Gantt labels on dark bars | Applied short white badges to existing text shapes | Unchecked-contrast runs reduced 6→0; native PNG rechecked |

Strict builds block IDs exceeding single-line space or containing newlines, and counterexamples where widened
IDs displace captions that previously fit. Original short-ID 3.2in placement remains.
Text width is approximate; actual renders still require review for user fonts/long sources/bar wording.

No schema/dependency/approval fields added. No new semantic-completeness score/gate; confirmed comparison
procedures were incorporated into existing evaluator/revalidation/slide-production guidance.

## Actual artifact validation

| Item | Confirmed result |
|---|---|
| Requirement coverage | Compared body responses/mandatory subconditions for 22 requirements; matrix/ID labels alone were insufficient |
| Shared conditions | Contract dates, external-license procurement/equipment replacement/new implementation exclusions, budget/output specs |
| Document specs | 16:9, 24 slides, minimum 14pt, under 20MB, native shapes/text/tables without images |
| Actual conversion | 24 PPTX slides→24 PowerPoint PDF pages→24 PNGs; no missing extracted text paragraphs or off-page text |
| Numerical ledger | 45-item token comparison plus independent price/SLA relationship recalculation |
| Price | Supply amount 192,000,000 KRW + VAT 19,200,000 KRW = 211,200,000 KRW; 28,800,000 KRW below synthetic budget |
| SLA | Separate S1 calendar clock/S2 support clock; Friday 17:30 receipt→Monday 09:30 response/16:30 workaround targets recalculated (Monday assumed nonholiday) |
| Negative controls | Independently rejected total changed by 1 KRW and swapped S1 response/recovery values using formulas/row relationships |
| Persuasiveness | Reviewed three risk→execution→planned acceptance evidence→buyer-effect chains; removed wording implying actual results/effects |

Distinguished score/numerical token presence from actual semantic/formula consistency.
Automated ID/numerical passes do not complete semantic review. Three initial density warnings were resolved
in the follow-up below. Actual service SLA attainment or acceptance-test execution was not validated.

### Follow-up: density warnings resolved

| Slide | Previous characters | After shortening | Information preserved |
|---|---:|---:|---|
| 4 — Three proposal strategies | 268 | 244 | Three risks/responses/acceptance plans/effects and requirement IDs |
| 6 — SLA | 262 | 245 | S1/S2 definitions/clocks/deadlines/notifications/holiday conditions/time example |
| 18 — Price | 296 | 249 | Amounts/quantities/unit prices/12 months/0 discount/10% VAT/total/budget difference |

Retained `presentation` 250-character threshold, draft check stage, ≤24 slides/≥14pt specifications.
Reduced duplicated titles/leads/table labels without moving numbers to other slides/captions/notes.
Price-table numeric occurrence order and first three SLA rows remain; other 21 slide inputs are identical.
Passed 22 requirements/45 numbers/independent price-SLA checks and 2 negative controls again.
Actual PowerPoint rerenders of slides 4/6/18 were checked for clipping/overlap/numeric legibility.
No generator/checker runtime code, thresholds, profiles, or approval fields changed.

### Follow-up: detailed review findings and fixes

| Priority | Issue/reproduction evidence | Fix/confirmation |
|---|---|---|
| P1 | Ledger minutes/seconds matched same-number hours/minutes; business days/days indistinguishable | Compare explicit minute/second/business-day units and unambiguous spaced time forms; preserve boundaries for unitless table cells/general nouns |
| P1 | NaN/Infinity tolerance disabled sum/ratio comparison | Reject with existing finite-number validation; block incorrect sums/ratios while retaining valid zero-tolerance values |
| P2 | Assumed business day=24 hours/month=730 hours without calendar | Convert only minutes/hours/days/weeks as fixed elapsed times; block mixed business-day/month/year units, retain same-unit comparisons |
| P2 | Slide 14 quarterly restoration/semiannual training shown as continuous bars | Use existing table layout as monthly execution matrix: restoration/acceptance months 3/6/9/12, training months 6/12 only |
| P2 | No holiday arrangements between weekday support and daily backup checks | Slide 11 specifies checks including holidays, primary/backup owners, success/failure records, non-S1 support-hours versus S1 procedure |

Three numerical regression tests failed in 19 subcases before fixes. After fixes, normal/error controls and
actual PPTX response-unit substitutions through the unified gate confirmed valid passes/error blocks.
Also aligned incorrectly rejected lowercase currencies with existing case-insensitive token rules.
No new schema fields/dependencies. Mixed-duration ledgers without calendars must be updated to same-unit
values calculated from original sources.

The refined deck has 24 slides/minimum 14pt/0 density warnings; changed slides have 244 characters (11) and 203 (14).
Retained 22 requirements/45 numbers/price-SLA calculations/two negative controls.
Actual PowerPoint rerender produced 24 PDF pages/24 PNGs, with no missing paragraphs/offscreen text/footer overlap.
Inspected both changed slide images; other 22 inputs/native-render pixels are identical.
Holiday operations are proposed design, not proof of actual staffing. Synthetic material/false human approvals remain.

## Regression validation and limitations

Five `test_gate_integrity.SyntheticProposalLayoutTests` cover short-ID placement, long-ID widening/font
preservation, impossible-ID blocks, caption-displacement blocks, milestone background/contrast.
Confirmed reproduction failure before fixes and passes afterward. Full regression/hygiene/remote-CI actual
results are recorded in PR validation. A separate outline regression allows normal-title spacing while retaining
mandatory-section checks.

Generated material/logs/before-after PDF-PNG/hash ledgers remain in the validation working folder, outside
distributed skills. This single synthetic case guarantees neither all RFP/font/template quality nor real wins.
Image inspection was agent review; it replaces neither required human approval nor host UI validation.
