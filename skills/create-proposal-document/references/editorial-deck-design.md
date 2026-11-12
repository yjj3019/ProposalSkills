# Editorial deck design (tidy, at-a-glance, measured)

Use with `visual-style.md` (fixed tokens) and `visual-critique.md` (what scripts cannot judge). This file records what
review rounds on a real comparison deck showed makes a deck look finished instead of busy, and how to measure it.
A buyer-prescribed template or brand skill always wins over these defaults.

Result of applying it to one 17-slide deck, measured with `scripts/tidy_audit.py`:

| Measure | First draft | Final |
|---|---|---|
| Distinct font sizes | 25 | 8 |
| Near-miss alignments | 17 | 1 |
| Thin rules (hairlines) | 206 | 30 |
| Characters on the densest slide | 729 | 574 |

## 1. Why a deck looks "messy" (diagnosis before restyling)

Three causes, in the order they showed up:

1. **Too many type sizes and weights**, so no hierarchy is readable (25 sizes). Fix with a fixed scale (section 2).
2. **Almost-aligned boxes and uneven row spacing.** Eyes see the 0.03 in miss before they see the content (section 3).
3. **Decoration standing in for structure**: a rule under every row, shadowed cards, progress trackers, pills. Each is
   small, together they cut the page into fragments (section 4). Whitespace separates better than a line.

A fourth cause is content, not style: a slide that must be *read* instead of *seen* (section 5).

## 2. Type scale (nine steps, nothing else)

| Role | Size (pt) | Face |
|---|---|---|
| Footer, source, page number | 8.5 | sans regular |
| Caps label, table header | 9.5 | sans medium, letter-spaced |
| Body, table cell, caption | 11 | sans regular |
| Item heading, lead line | 13 | sans medium / light |
| Column heading, model name | 16 | serif semibold |
| Index number, vendor name | 24 | serif or numeral face |
| Slide title | 27 | serif semibold, tracking -30 |
| Key figure | 34 | numeral face |
| Cover or closing title, hero stat | 44 | serif semibold |

- At most five font families: sans regular, sans medium, sans light, serif semibold, one numeral face.
- Set the East Asian and complex-script typeface explicitly (`a:ea`, `a:cs`). python-pptx `font.name` writes only the
  Latin typeface, so Korean text silently falls back to the theme font and looks different on every machine.
- Emphasis comes from face and size, not bold flags and not color. Color carries identity (one color per vendor or
  option) and status, nothing else.
- Body copy never goes below 11 pt; small gray light-weight text fails at presentation distance.

## 3. Grid and rhythm

- One content block per slide: it starts at the same y on every slide and ends at the same y (for example 2.25 in
  and 6.75 in on a 7.5 in slide). Title, lead and kicker sit above it, source and page number below.
- Lists, tables and charts divide that block evenly: `rows = n`, `pitch = (bottom - top) / n`. Never hand-place rows.
- Every numbered list uses the same geometry: index column, heading, body at fixed x offsets, so a reader's eye keeps
  one left edge across slides.
- A heading and its description are one text box with two paragraphs, not two boxes. This removes the drift that
  produces near-miss alignments.
- Boxes in one row share `(y, height)` and are anchored middle.
- Snap every coordinate to a 0.05 in grid; run `tidy_audit.py` and fix each near-miss rather than nudging by eye.

## 4. Decluttering rules

- Hairlines only under column headers and table headers; separate rows with space. Table row lines are allowed, but
  fainter than header rules.
- No shadows, no card grids, no pills, no progress tracker once an agenda slide exists.
- Index numerals are quieter than the headings they number (16 pt, muted accent, not 24 pt bold).
- Line icons only where they label a repeated category, drawn as strokes, with one color per vendor.
- Generated cover art is allowed (thin ribbon lines, no stock photography, no logos or marks of third parties).

## 5. At-a-glance patterns

Pick the pattern that lets the reader see the conclusion before reading a sentence. The title states the conclusion;
the picture proves it.

| Question the slide answers | Pattern | Honest-marks rule |
|---|---|---|
| Which option leads, on which items? | Head-to-head scoreboard: item, value A, value B, a three-position track with the winner dot, verdict | State the verdict rule on the slide (lower price, wider documented coverage) and balance the item set so each side leads on several |
| How big is the difference? | Bars on a real axis (tokens, dollars), the break marked where a rule changes | Length equals value; mark the axis ticks; no pairing that implies equal capability |
| Is a capability present? | Yes/no matrix with large check and cross marks, one caption each | A blank means "not verified", never "no" |
| Which option for which situation? | Three-way triage: A first, B first, evaluate both, each with 2-3 situations and one line of evidence | Name the evidence, not a score |
| How are criteria weighted? | One stacked bar split by weight | Mark the weights as an example |
| What are the risks and the answers? | Two columns: risk, response, one line each | Every risk has a response |
| How do two directions differ? | Keyword rows with an icon, a keyword and one short line per option | Facts the vendor's own documents state; no marketing adjectives |

Headline-with-fact: a strength or caveat names the fact ("1M 토큰까지 같은 단가"), the line below gives the qualifier
or evidence. Do not write a heading that needs its description to mean anything.

## 6. Copy discipline

- Titles are full sentences (`deck_story_check.py` reads them as a ghost deck). Leads are one sentence with a period.
- List fragments and table cells carry no period; keep them to one line at body width, two at most.
- Use one register throughout: sentences end in the polite form, fragments end in nouns.
- Expand an acronym at first use (MCP, ZDR, HIPAA). Caps labels such as `OPENAI` trip `plain_language_check.py`;
  that warning is a false positive for styled labels.
- Cut until no line wraps with one or two words left over.

## 7. Verify by looking (render loop)

1. Build, then render every page. LibreOffice to PDF, then PNG with Poppler `pdftoppm` or PyMuPDF; `deck_check.py
   --render --png-dir` does the same. View every image, not the source.
2. If Office is installed, also ask the real engine: for each shape compare `TextFrame2.TextRange.BoundHeight` with
   `Shape.Height` and test whether the shape lies inside the slide. This catches overflow the PDF path can hide.
3. Run `scripts/tidy_audit.py deck.pptx`. Defaults: at most 9 font sizes, 10 near-misses, 24 thin rules and 700
   characters on one slide. Thresholds are advisory; a slide that exceeds them needs a reason.
4. Revise once against the findings list, render again and compare. A revision that leaves the list unchanged did not
   fix anything.

Enterprise DRM caveat: an agent such as NASCA can encrypt every file an Office process writes (even a PNG exported by
PowerPoint, header `<## NASC`), while LibreOffice output stays readable. Render with LibreOffice when an exported image
will not open, and say which engine produced the image. A system Python whose python-pptx template was encrypted needs
a virtual environment outside the DRM-managed paths (`build_deck.py` names this when it detects the header).

## 8. Portability

The example uses Noto Serif KR, Noto Sans KR and Georgia by name; they are not bundled (SIL Open Font License for the
Noto families). Another machine without them substitutes fonts and changes line breaks. Share a PDF, or rerun the
render check on the target machine.

## 9. Reference implementation

`assets/examples/ai-model-comparison/make_deck.py` builds the 17-slide deck these rules came from, with the primitives
(text stacks, rules, icons, table and chart helpers, generated art) in one file. Copy the primitives, not the content.
