# Detailed comparison of five external slide skills and ProposalSkills adoption decisions

Analyzed: 2026-10-02. Pinned public-repository HEADs at inspection and read README, SKILL, references,
production/extraction/check scripts, tests, and licenses. This is not validation of all Git history, actual
external image APIs, model execution on every host, or web-presentation runtimes.
Distinguish README claims from code-confirmed behavior. No external files were copied into ProposalSkills.

## 1. Inspected versions and production methods

| Repository | Inspected commit | License evidence | Main artifact/execution path |
|---|---|---|---|
| [consulting-pptx-skill](https://github.com/carnot-tech/consulting-pptx-skill/tree/5d3b048e944f237c26690ed5f624d7773b302d96) | `5d3b048` | Root LICENSE: MIT | HTML components → static checks → Playwright render checks; separate PPTX static checks supported |
| [pptx-design-styles](https://github.com/corazzon/pptx-design-styles/tree/e9254b6b9c9bd982f6cf440b4a9197bbd3882a3b) | `e9254b6` | README says MIT; separate LICENSE not found | Color/font/layout guidance for 30 styles; no own PPTX generator |
| [codex-ppt-skill](https://github.com/ningzimu/codex-ppt-skill/tree/445b1780c85cec72da7a2c87b80a1d7cbaf726ee) | `445b178` | Root LICENSE: MIT | Generated slide images → image-based PPTX assembly with speaker notes |
| [frontend-slides](https://github.com/zarazhangrui/frontend-slides/tree/9906a34d640d2111f724544cbc50f7f130569ae1) | `9906a34` | Root LICENSE: MIT | Fixed 1920×1080 HTML stage; PPTX content extraction |
| [guizang-ppt-skill](https://github.com/op7418/guizang-ppt-skill/tree/c91369c449d34755d320a8b81d0734000d99d1ab) | `c91369c` | Root LICENSE: AGPL-3.0 | HTML web presentation, two styles, presenter/audience screens, notes/rehearsal checks |

ProposalSkills baseline: `a75d27d`. Existing strengths are editable native PPTX, compliance matrices,
numerical ledgers, output profiles, actual submission checks, hash binding, rendering/human approval.
External styles/presentation features provide no reason to replace this submission system.

## 2. Structure and quality by repository

### consulting-pptx-skill

`references/slide-rules.md`, `content-review-prompt.md`, component HTML, `check_deck.py`, and
`check_layout.mjs` separate content, form, mechanical checks, and semantic review.
Strengths: claim-first slides, relationship-appropriate patterns, title/body item-count comparison,
whole-deck story review. Linking findings to specific pages/actual problems also suits proposals.

Render checks measure browser coordinates but only for specified selectors/layouts.
Stage counts use the highest sequence number, not a complete check for missing intermediate numbers.
Fill-rate/wrapping estimates do not equal actual font-render quality. Claim-style title guidance coexists
with noun-title checks, interpreted here through existing Korean title+lead structure.

**Adopt:** relationship→existing type mapping, story/diagram conclusion/item-count comparisons, evidence-backed findings.
**Defer:** HTML pipeline import, copied Japanese banned terms, mandatory new review agents,
fixed finding counts, or model self-score quality approval.

### pptx-design-styles

`SKILL.md` offers purpose-based recommendations; `references/styles.md` collects colors/fonts/layouts/signatures
for 30 styles. Consistent tokens/selection criteria are strengths. Actual generation depends on another PPTX skill;
installing style instructions alone creates no generation/validation capability.

Some overseas fonts, dark backgrounds, neon, and mandatory decoration on every page may conflict with Korean
font availability/public output specifications. Thirty style guides do not automatically guarantee contrast,
brand fit, or reproducibility. Without a separate license file beyond README MIT notation, do not claim
asset-distribution terms were fully verified.

**Adopt:** small candidate set based on audience/medium/brand, existing palette tokens, automated RGB contrast checks.
**Defer:** all 30 themes, new global theme API, fixed overseas fonts, mandatory decoration.

### codex-ppt-skill

Stage documents/prompts/state scripts/image providers/assembly scripts under `skills/codex-ppt` separate roles.
Useful concepts: inspect representative slides before consistent production, preserve results as file evidence,
insert speaker notes during assembly. `tests/test_image_gen_models.py` validates offline requests;
it proves neither actual image-model quality nor network success.

Each slide is one full image, making individual text/table/shape editing difficult.
Ordinary PPTX text checks cannot be assumed to detect visible numbers/customer names.
Image backends/API configuration/host-subagent requirements are also unsuitable for a shared-skill execution contract.

**Adopt:** representative-slide checks when needed, notes preserved for all types, factual presentation explanations.
**Defer:** image-only PPTX default, mandatory image models/APIs/subagents, repeated approval at every image-generation stage.

### frontend-slides

Fixed stage/viewport CSS/style index/template packs/extraction scripts are linked.
Strengths: distinguish reading versus speaking density, load only selected style details, preserve ratios on small
screens. These align with ProposalSkills' three output profiles.

`extract-pptx.py` reads top-level shape text/images but does not recursively extract table cells/charts/nested groups.
Its output cannot establish complete preservation of original requirements/numbers.
No-build frontend operation is not full offline operation: HTML templates link external fonts.
Similar root/plugin-distribution material requires synchronization checks on changes.

**Adopt:** medium-specific density, split overflowing content, inspect whole deck and needed representative screens.
**Defer:** default HTML submission, direct extraction-script adoption, treating no-build as offline guarantee.

### guizang-ppt-skill

Includes two HTML templates, layout/theme references, presenter runtime, and Swiss/presenter/runtime synchronization
checks. Useful planning joins slide purpose, supplementary explanation, next-slide transition, and rehearsal.
Swiss checks separate static checks from Playwright measurement and warn when browser measurement is unavailable.
Presenter checks distinguish note/slide alignment from partial timing plans.

External fonts/CDN icons/runtime fallbacks depend on network/version availability.
WebGL/presenter synchronization are not required defaults for public-submission PPTX.
Copying AGPL-3.0 code into an existing public project is not equivalent to copying an MIT template.

**Adopt:** notes with purpose/explanation/transition, preservation of uninspected states, actual rehearsal checks.
**Defer:** HTML/JS/image/font asset copying, presenter/audience-screen servers, WebGL backgrounds,
automatic upstream-update checks on every run.

## 3. ProposalSkills defects actually reproduced and fixed

| Issue | Before | After | Validation location |
|---|---|---|---|---|
| Table-cell count mismatch | Extra cells discarded; missing cells blanked | Reject rows whose size differs from column count | `test_slide_quality.py` |
| Invalid column widths/alignment columns | Some late failures/invalid columns accepted | Validate lengths/finite positive widths/column indices | `test_slide_quality.py` |
| Lost speaker notes | Saved only in body frame | Preserved for every type/split matrix | `test_slide_quality.py` |
| Contrast rule only documented | Low-contrast token combinations could generate/pass | Same RGB check in generator/actual-file inspector | `color_contrast.py`, `test_gate_integrity.py` |
| Missing-runtime error contract | Shared checker transitive dependencies could bypass import guard | Generator/checker retain helpful dependency message/exit 2 | `test_slide_quality.py` |
| Low-contrast section numbers | Existing light color/white background about 2.35:1 | Replaced with existing primary color | Existing 3 profiles/full-pipeline tests |

No new table-data contract or weakened submission criteria. Runtime cell/width checks enforce the existing
documented JSON-array contract. Shared contrast calculation is independently implemented from
[W3C criteria](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html).
Use 3:1 at ≥18pt or bold ≥14pt, otherwise 4.5:1, comparing unrounded values.
Retain template backgrounds; explicitly use white for ordinary generated decks.

## 4. New guidance and retained contracts

Linked relationship→type selection, small style candidate sets, story/number/item-count comparison, and
purpose/explanation/transition notes in `deck-production.md` and content SKILL.
Notes must be factual; check split-matrix notes against actual generated pages.
Do not reapprove settled brands/requirements. Representative-slide review is conditional and never replaces
whole-deck visual review.

Retain flagship entry, explicit sibling invocation, buyer-spec priority, editable shapes/tables,
ledger comparison, actual file hashes, bundle checks, rendering/human approval.
No additional external dependencies/model APIs/servers/theme engines/customer material.

## 5. Validation and limitations

Synthetic checks on the pre-fix commit reproduced extra-cell loss and missing cover/section/closing notes.
TOC notes were already preserved. A PPTX containing table-cell/group text passed to frontend-slides extraction
omitted both from its content list. Twenty external Python files parsed successfully; this does not establish
full runtime testing of those repositories.

Root regression command: `python -m unittest discover -s . -p "test_*.py" -q`.
New checks cover table positive/negative controls, notes across all types, normal/low-contrast/large-text RGB,
uninspected theme/transparency/pattern backgrounds, and low-contrast blocking in actual submission PPTX.
Existing output profiles/specifications/unified submission paths are also revalidated.

Contrast checks calculate only explicit solid RGB. If themes/transparency/images/partial overlap/inherited fonts/
group backgrounds prevent determining displayed colors, record uninspected.
These checks do not approve table-cell overflow, semantic stage counts/diagram conclusions, font substitution,
or whole-deck visual quality. Actual external image generation/web presentation/audience synchronization were
not executed. Full histories/comprehensive security audits/model-specific proposal-quality scoring were not performed.

## 6. Distribution and sources

Historically distributed version 1.2.1's common skill payload identically to Codex/Claude/Grok local paths.
The installer backs up existing folders and updates only required files.
ChatGPT web/other-account cloud registration is separate; no actual Grok model execution success is claimed.

Sources are pinned commit links above and corresponding repository files.
No external code/sentences/templates/images/fonts/logos copied. Attribution does not replace external usage/distribution terms.
