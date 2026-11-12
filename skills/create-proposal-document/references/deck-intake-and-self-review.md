# Deck intake and self-review (ask first, look before delivering)

Use for any deck, brief or comparison, and above all when nobody will iterate with you. In one long session a deck went
through four rounds of the user's reaction: plain, then busy, then not scannable, then finished. A skill cannot count on
that. It has to ask the questions up front, look at its own output, measure it and revise before it hands anything over.
This file turns those reactions into steps. Rules for what "finished" looks like: `editorial-deck-design.md`;
what scripts cannot judge: `visual-critique.md`.

## 1. Ask first (when a person can answer)

Skip a question the request already answers. Ask at most five, each with a recommended default, in one batch (use the
host's structured-question tool with options when it has one; otherwise a short numbered list).

| # | Question | Recommended default if unanswered |
|---|---|---|
| 1 | Who reads or hears this, and what must they decide afterwards? | the person named in the request; the decision is the conclusion on slide 3 |
| 2 | How long and how deep: slide count, reading or presenting, words per slide? | 12 to 17 slides, read on screen, at most 700 characters per slide |
| 3 | Style direction: standard proposal frame, editorial, or the buyer's template? | the buyer's template if one exists, else the standard frame; editorial for briefings |
| 4 | Which sources may supply facts, and may the author's own interest be disclosed? | the owner's own documents and official vendor pages only; disclose the interest |
| 5 | Delivery: PPTX or PDF, fonts installed on the target machine, any DRM or file-size rule? | PPTX plus a PDF; named fonts only when installed, else the standard face |

Then one checkpoint before building everything: show the outline (titles read as a ghost deck) and two or three sample
slides rendered as images, and ask "this direction?" A wrong direction found at slide 3 costs minutes; at slide 17 it
costs the deck.

## 2. When nobody can answer

Do not guess silently. Write the assumptions you used (the defaults above) on the closing slide or in the notes and in
the hand-off message, build the standard path, and list the questions you would have asked.

## 3. Self-review before delivery

Build, render **every** page, then judge it against the four rungs below, in this order. Each rung has a measure and a
look.

| Rung | The reaction it stands for | Measure (`scripts/tidy_audit.py`) | What to look at |
|---|---|---|---|
| 1. Plain | "poor, half-empty" | `body fill` per slide (default at least 50%) | empty bottom halves, a lone small table, no picture anywhere |
| 2. Busy | "cluttered" | font sizes (at most 9), near-miss alignments, thin rules per slide, characters per slide | boxes that almost align, a rule under every row, wrapping with a stray word |
| 3. Not at a glance | "I still cannot see the point" | text-only content slides (default at most half) | does the title state the conclusion and does the picture prove it (`deck_story_check.py`) |
| 4. Unfinished | "not a finished product" | `deck_check.py`, `quality_gate.py`, `package_inspect.py` (author, notes, hidden slides) | clipped or overlapping text, fonts, units and dates, source on every number |

Procedure:

1. Render with `scripts/render_delta.py <deck> -o out/render`. It renders every page (cheap) but compares each slide's content
   hash with the last run and writes `changed_sheet.png`, a contact sheet of **only the slides that changed**, numbered with the real
   slide number (more than 12 changed slides split into `changed_sheet_1.png`, `changed_sheet_2.png`, and the output names every
   file). The first run writes `sheet.png` (`sheet_1.png`, ... when split) of all pages. When Office wraps its own exports in DRM, this uses LibreOffice
   (see `editorial-deck-design.md` section 7); `deck_check.py --render --png-dir` remains for a one-off check.
   `-o` must be a new or empty folder (or one the tool made): it refuses any other folder and deletes only the files it recorded as
   its own. Slides whose content is unchanged but whose picture differs (a font or engine change) are reported as `render_changed`.
2. Look at the sheet first: repeated or broken patterns, empty slides, an odd one out. Then open single pages for the slides you
   doubt and every changed page that carries a chart or a diagram. Do not look at unchanged slides again.
3. Run `tidy_audit.py`, `deck_check.py`, `quality_gate.py`, `package_inspect.py` and, for decks with text, `deck_story_check.py`.
4. Write the findings, each with why it matters and the smallest fix, ranked Critical / Major / Minor. Fix, rebuild and
   render again. Revise at least once even when the first pass looks clean: the first pass is where the rungs are found.
5. Record the review in the ledger, page by page: `scripts/review_ledger.py init <deck> -o ledger.json --png-dir out/render/pages --engine <name>`,
   then `set` each slide (viewed full or on the sheet, the four rungs, findings) and `check ledger.json` until it prints COMPLETE.
   `check` refuses a slide that was never viewed, a chart or diagram seen only on the sheet, an image older than the deck,
   a rung that is not pass or waived with a reason, an open Critical or Major finding, no revision, or a deck that changed after
   the review. It proves every page was recorded as seen, not that the judgments are right; the measures above are proxies and
   the ledger is what keeps the looking from being skipped. Cite the ledger as the evidence of a rendered-level check in
   `verification_report.py`.
6. Stop when the ledger is COMPLETE and the measures are inside their limits. A warning left on purpose needs a one-line
   reason (an agenda or a source list is text-only by nature).

## 3a. The cheap iteration loop

Reviewing cost is dominated by looking at images, not by rebuilding. Iterate like this:

1. Edit the spec (`slides.json` or the build script) and rebuild; rebuilding and rendering cost almost nothing.
2. `render_delta.py` again: it names the changed slides and builds their sheet. Look only at that.
3. `review_ledger.py sync ledger.json --png-dir out/render/pages` keeps the verdicts of unchanged slides and resets only the changed
   or new ones (it never carries a verdict onto a slide whose hash differs). Judge the reset slides, then `check`.
4. Before delivery, look once at the full `sheet.png` (`render_delta.py --full-sheet`) to catch what a change did to the whole deck.

An edit to the layout or master changes every slide hash and so resets every slide, which is correct.

## 3b. HTML preview before the PPTX (not provided yet; conditions if it is added)

Drafting in HTML and producing the PPTX only after approval saves rebuilds, but it is acceptable only if the approved preview and
the delivered PPTX cannot differ in quality. A browser and PowerPoint measure text differently, so a separately designed HTML page
will not match. Conditions: (1) one source (`slides.json` or a shared display list) that both renderers read, never HTML converted
to PPTX or the reverse; (2) the same coordinates, sizes, colors and text in both, so layout is identical by construction; (3) a parity
check that reads the PPTX back and compares shape count, text, positions and font sizes with the preview, and no PPTX is delivered
if they differ; (4) a text-fit margin measured with the real font; (5) the delivered PPTX still passes the render loop and the ledger.
Pixel-identical rendering across engines is not promised; the approval of a preview approves the layout, not the PPTX.

## 4. What to report

- What was inspected and with which engine: pages viewed at full size, contact sheet, LibreOffice or PowerPoint, and
  which checks could not run (`NOT INSPECTED`).
- The measures before and after the revision.
- Open findings and the assumptions made.
- Questions for the person that you could not answer yourself.

Never write "perfect" or "complete". Write what was verified and what was not. A rendered page that fails is a fail even
when the source passes.
