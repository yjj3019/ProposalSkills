# Deck production (deck-production) — slides.json → PPTX → checks

**Do not manually recreate** visual-style.md specifications on every run. Write the plan in `slides.json`,
generate with `build_deck.py`, and check layout/render with `deck_check.py`.
The model **fills content (leads, table data, diagram elements)**; scripts fix coordinates, colors, fonts, hierarchy.

```bash
python scripts/build_deck.py slides.json -o 제안서.pptx --strict          # Generate
python scripts/deck_check.py 제안서.pptx --max-pages 40 --exclude-cover-toc \
       --require-req-ids --stage draft --render --png-dir out/png \
       --emit-render render.json                                            # Lint + render + evidence
python scripts/quality_gate.py 제안서.pptx --stage draft                    # Text review
```

Insert `render.json` into meta's `render` block to populate audit render fields
(deck_check emits `verified:true` only after successful rendering and 0 blockers).
**`visual_review_approved` is always recorded as `false`**.
A human who inspects every `out/png` thumbnail must directly set `true` and `visual_reviewer` (real name)
for submission mode to pass. Rendering and human visual approval are separate facts.

## 1. slides.json schema

The following schema preserves Korean example values and comments as source examples.

```jsonc
{
  "meta": {
    "title": "…제안서", "subtitle": "…", "doc_name": "헤더 표기 문서명",
    "buyer": "발주처(RFP 표기 그대로)", "bidder": "제안사", "date": "YYYY-MM-DD",
    "page_limit": 40,                 // If set, excess fails --strict; mismatch with output_spec.page_limit refuses generation
    "output_spec": {"source": "…"},   // Buyer-prescribed output specification — §1-2
    "require_req_ids": true,          // Warn on missing body REQ-IDs (default true; type C may use status_tag)
    "palette": {"primary": "1F3864"}, // Optional brand tokens; otherwise visual-style fallback
    "font": "맑은 고딕"
  },
  "slides": [ /* Types below */ ]
}
```

Common body-slide fields: `breadcrumb` (header outline path), `title` (noun form), `lead`
(conclusion, 1~3 lines, ≤60 characters recommended), `caption` (Korean example 그림 N./표 N. + reference date),
`source`, `req_ids` (array), `notes` (presenter notes), `status_tag`
(type C Korean example: `(완료) 26. …`).

Footer REQ-IDs retain font size and share width with captions according to list length.
Newlines inside IDs or a list exceeding the single-line area violate the rule and fail `--strict`.
Split the slide/matrix response scope instead. Captions displaced by wider ID lists also fail `--strict`.
Width is approximate: inspect caption wrapping warnings and actual rendered footer spacing.
Gantt milestone labels use short background badges. For long labels, in-bar wording, or custom palettes,
check renders for obscured schedule information and insufficient contrast.

| type | Use | Specific fields |
|---|---|---|
| `cover` | Cover | Uses meta; `title`, `subtitle` can override |
| `toc` | Contents | `items[]` — automatic two-column layout |
| `section` | Divider | `no` (Ⅰ…), `title`, `items[]` |
| `matrix` | Compliance matrix | `rows[{id,text,support,response_loc,note}]`, `rows_per_slide` (default 12, **positive integer only**); auto-split, repeated headers, Korean label "(계속 n/N)"; reconcile input/output row counts to prevent loss |
| `table` | One table | `columns[]`, `rows[[…]]` (cells per row = columns), `col_widths[]` (finite positive values, length = column count), `right_cols[]` (zero-based indices) |
| `process` | Staged process | `steps[{title,desc[]}]` — chevrons for ≤6 stages, boxes beyond |
| `zones` | Architecture | `zones[{title,items[{title,desc[]}]}]`, `legend[]` — top-down hierarchy, zone labels/cards |
| `gantt` | Schedule | `months`, `month_labels[]`, `tasks[{name,start,end,phase,label,milestones[{at,label}]}]` |
| `staff` | Staff profiles | `people[{name,role,grade,years,certs[],mm}]` |
| `cards` | Differentiators/benefits/three-part logic | `items[{title,value,desc[],evidence}]` — 2~4 columns |
| `bullets` | Text lists (minimize) | `items[]` — always warns; splitting warning beyond 450 characters |
| `closing` | Closing | `title`, `lead` |

Pair `support` common codes `O/부분/조건부/X/N/A/확인필요` with text (Korean examples:
`"O 수용"`, `"△ 조건부"`), implementing the prohibition on color-only statuses.

## 1-1. Artifact type (output_profile)

Different reading conditions require different specifications even for identical content.
Select `meta.output_profile` or `--profile` to jointly change fonts, density, table rows, matrix splitting.

| Profile | Reading conditions | Title/body/table | Lead | Density | Table rows | Matrix rows |
|---|---|---|---|---|---|---|
| `detailed-submission` (default) | Print/PDF scoring | 22/11/10pt | ≤60 characters | 600 characters | 14 | 12 |
| `presentation` | Meeting-room screen | 30/18/14pt | ≤40 characters | 250 characters | 8 | 6 |
| `executive-summary` | Screen/print summary | 26/14/12pt | ≤50 characters | 400 characters | 10 | 9 |

Specifications live only in `scripts/deck_profiles.py`, shared by generator/checker.
Generated PPTX core properties retain `proposal-deck:<프로파일>`, allowing `deck_check.py` to apply the same
criteria without arguments (`--profile` override warns on mismatch).
Minimum font sizes derive from the profile's smallest body size rather than a constant.
If font size cannot be resolved, the checker marks those runs `[NOT INSPECTED]`, returns a nonzero status, and sets `verified` and `layout_checked` to false even if rendering succeeds. Confirm the actual size and make it explicit in the source presentation, then rerun the checks.

Missing/unknown markers warn in draft and block submission. For externally generated decks, explicitly supply
`--profile`; silently passing under the loosest default would check presentations against detailed criteria (9pt/600 characters).

Density counts table-cell text. Previously, dense matrix slides counted as 0 characters, effectively disabling density warnings.

For RFPs fixing page count/minimum fonts, first shorten duplicate titles, leads, table labels.
Cards retain distinctions between risk, method, planned evidence, effect. SLA tables retain severity, measurement clock,
intake criteria, response/recovery deadlines, holiday conditions.
Keep amounts, quantities, unit prices, periods, VAT, discounts, totals in the body.
Korean notation examples: distinguish zero discount with `;할인0`, not only `/0` after a formula.
Replacing `부가세` with vague `세액` can weaken required meaning even with unchanged numbers.
Do not hide warnings by changing thresholds/profiles/stage/fonts or moving information into captions/notes/later slides.
After shortening, reconcile actual PPTX requirements, figures, formulas; inspect spacing/compressed labels in renders.
Zero density warnings never replace readability review.

Presentations do not hold detailed evidence. Generating a presentation from the same `slides.json` produces
lead-length/density warnings signaling the need to condense: retain evidence in the detailed deck/appendix,
and focus the presentation on conclusions/diagrams. Buyer templates/fonts override profiles.

## 1-2. Buyer-prescribed output specification (output_spec)

**Notice specifications > internal profiles.** Profiles are defaults only when the notice is silent.
Transfer prescribed length, font size, file size, aspect ratio into `meta.output_spec`.
No numeric defaults: omit keys absent from the notice.

Korean source-location example preserved:

```jsonc
"output_spec": {
  "source": "제안요청서 제출 규격 조항 위치",  // Required: document, page, clause
  "canvas": "16:9",                            // Optional: only 16:9 can be generated
  "page_limit": 40,                            // Optional: enforced by generator/checker
  "font_min_pt": 10,                           // Optional: checker arguments cannot lower this
  "file_size_limit_mb": 20                     // Optional: measured on the PPTX file
}
```

| Behavior | Details |
|---|---|
| Resolution | Only `deck_profiles.resolve_output_spec`; generator/checker share the function |
| Preservation | PPTX core properties `keywords` retain `proposal-output-spec:`; checker reads without arguments |
| Font floor | Raise tables/captions/headers/footers to the floor. Refuse generation if profile body is below it; choose a larger-body profile because density must change too |
| Length | With `--max-pages`, use the stricter value |
| Canvas | Recognizes but does not draw `A4-portrait`, `A4-landscape`, `A3-portrait`, `A3-landscape`, `4:3`; generator has a 16:9-only grid, so use prescribed forms or DOCX |
| Unknown values | Unknown keys/canvases/negative values refuse generation (exit 2). Broken markers block submission and warn in draft |

Submission-bundle properties (`anonymous_copy`, `price_separation`, `file_format`, `copies`, `binding`)
are rejected inside `output_spec`; record them in `attachments[]` and submission-bundle checks.

Neither A3 landscape, A4 portrait, nor 16:9 is a Korean public-sector universal standard. Each notice determines its own.

## 2. Draw diagrams with native shapes

Architecture/process/Gantt use **editable PPT shapes** (`zones/process/gantt`), not images.
Buyers often require original PPTX, reviewers need searchable/editable text, and quality_gate must inspect diagram
text for residual customer names/exaggerations. Use external images (draw.io/mermaid PNG) only when line connectivity
is central, such as network topology. Keep captions/legends/REQ-IDs as slide text and supply image alt text.

### Choose layout by relationship

First decide the lead, then select an existing type according to the relationship proving it.
Do not select decoration first and force content into it.

| Relationship | Existing type | Review criteria |
|---|---|---|
| Requirements to answers | `matrix` | Input requirements = output rows; page references agree |
| Alternatives/SLA/roles on equal criteria | `table` | Explicit row/column criteria and units; no cell loss |
| Sequence/migration/approval | `process` | Actual stage count matches title/lead |
| Hierarchy/responsibility/technical zones | `zones` | Readable boundaries/responsibilities/legend |
| Duration/overlap/completion | `gantt` | Period and dependencies agree with facts |
| Parallel differentiators/benefits/KPIs | `cards` | Same comparison basis; each figure has units/evidence |
| Delivery organization/capability | `staff` | Roles, participation periods, evidence agree |

Show recurring tasks such as quarterly inspections/semiannual training as events in execution months.
If using continuous bars, state in the legend whether they mean actual work duration or contractual availability.
If duration and frequency may be confused, use an existing `table` monthly execution matrix and reconcile detailed frequencies/schedules.

A plain structured table is also a visual. Do not impose a presentation's three-item limit on detailed submissions.
Split overflow or move it to detailed material/appendices; never solve it by shrinking fonts.

### Style selection and representative-slide inspection

Keep precedence: RFP form → provided template → brand tokens → neutral defaults.
If candidates are needed, narrow to at most 2~3 `meta.palette`/font combinations.
Detailed public submissions prioritize light backgrounds/readable tables; presentations large text/key relationships;
summaries conclusions/decision evidence.
Do not repeatedly ask about an established audience/brand. Render one representative content slide for comparison
only when a new brand or visual direction genuinely needs selection. Do not default to arbitrary foreign fonts,
neon, or full-image slides. Representative-slide inspection never replaces final all-page review.

### Content review and presenter notes

Read titles/leads in order to check problem → proposal → execution → verification, duplication, logical jumps.
Per slide, reconcile lead/diagram conclusions, stated/actual item counts, units/periods/sources,
terminology/status for the same concept, contents/matrix/body page references.
Machine passes do not establish natural-language semantic agreement. Record actual defects only as
page/target/evidence/impact/minimum correction; never determine readiness using model self-scores or defect quotas.

Save `notes` for every type: purpose, supplementary off-screen evidence, transition to the next slide.
Unverified commitments/figures are prohibited in notes too. Split matrices copy the same notes to every output page;
adjust them to actual pages. Allocate presentation time only from user-provided values; rehearse speaking/screen transitions.

### Data preservation and contrast checks

Extra/missing table cells are input errors (exit 2), never padded or discarded.
Column widths must be a finite positive array matching column count; right-aligned column indices start at 0.

Generator and `deck_check.py` share RGB contrast calculation in `color_contrast.py`.
Block below 3:1 for 18pt+ or 14pt bold+, and below 4.5:1 otherwise, including covers/dividers/table cells.
Default generated decks have explicit white backgrounds; user-template backgrounds are preserved.
Theme colors, transparency, gradients, image backgrounds, partial overlap, inherited fonts, group backgrounds
remain uninspected unless reducible to a computable solid-color combination.
RGB contrast passes do not replace render/human approval or print accessibility certification.
Use [W3C calculation criteria](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)
as design reference values; compare thresholds before rounding.

## 3. Corporate templates

`--template 사내양식.pptx` uses its masters/background/logo.
Requires 16:9 (13.333×7.5in), a Blank layout, and **zero slides**.
Reject templates retaining slides: old customer names/amounts would survive and page counts would be wrong.
Make a slide-free copy of existing forms. The coordinate grid stays fixed, so adjust template logos overlapping
header/footer areas (top 0.25~0.55in, bottom 6.95~7.25in). Pass brand tokens through `meta.palette`.

## 4. Page allocation — evaluation weights → absolute pages

With `page_limit`, allocate **slide counts**, not percentages.
Formula: weight ratio × (limit − fixed slides).
Fixed = cover 1 + contents 1 + matrix ⌈requirements/12⌉ + dividers (chapter count) + closing 1.
Check RFP counting rules; cover/contents are usually excluded.

Example: 40p limit; technical evaluation understanding 10, strategy 20, architecture 25, migration 15, management 10 (=80), 7 requirements.
Fixed = matrix 1 + dividers 5 = 6 → body 34 → understanding 4, strategy 9, architecture 10, migration 7, management 4.
Write high-weight leads first and emphasize diagrams; condense low-weight chapters into one table.

## 5. Production checks

Follow [quality-first-authoring.md](quality-first-authoring.md) for content review.
For approved/candidate PDF comparison, use optional regression tools in
[source-and-visual-evidence.md](source-and-visual-evidence.md).
Comparison results never promote human visual approval or submission status.

1. Lead map (slides.json with titles/leads only) → `build_deck.py --strict` → read leads alone to verify the story.
2. Fill body → `deck_check.py --stage draft` (warnings form the work list).
3. Submission candidate → `deck_check.py --stage submission --require-req-ids --render --emit-render` +
   `quality_gate.py --stage submission --names 금지명.txt` → reflect render.json in meta → unified_gate.
4. Human: visually inspect every PNG; open once in the buyer's PowerPoint version to check font substitution.
   Then record `visual_review_approved: true` and `visual_reviewer` (real name) in render;
   without these values submission mode cannot pass.

## 6. Limitations (never infer a pass)

- LibreOffice wrapping/font substitution can differ from PowerPoint; final verification is in PowerPoint.
- deck_check detects off-slide placement and clipping beyond 25% by coordinates, but estimates table-cell overflow/
  overlapping shapes only via density (600 characters)/fonts. Thumbnails require final visual inspection.
- Image-only slides cannot undergo text checks; marked with preserved warning label `[경고]`, requiring visual render review.

## Generated sizes and inspection floors

Profile font sizes are generation defaults; internal checks allow 1pt tolerance.
Detailed/presentation/summary body floors: 10/17/13pt; table floors: 9/13/11pt.
Buyer `font_min_pt` is enforced separately. Integrated gates recheck submission PPTX layout;
render/human approval evidence remains separately required.
