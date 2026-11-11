# Visual critique for proposal decks (art direction, honest marks, critique-and-revise)

Use with `visual-style.md` (the fixed specification) and `deck_check.py` (mechanical layout lint). This file covers
what scripts cannot judge: whether each slide makes one deliberate point and whether the visuals tell the truth.

## 1. Direction before slides

Write three lines before building: the deck's single message for the evaluator, the one accent used for emphasis,
and the reading path (title claim, then diagram or table, then source). If a design spec exists, follow it; if the
buyer prescribes a template, the template wins over taste.

## 2. One message per slide

- The title states the takeaway as a sentence (see `deck_story_check.py`; read the titles alone as a ghost deck).
- One dominant visual per slide: one diagram, one table, or one set of cards. A second message is a second slide.
- One accent color for emphasis; red stays reserved for risks and reductions (`visual-style.md`).

## 3. Honest marks

- Exact values belong in lengths and positions; area and color give only a rough impression. A bar or box must
  never be sized against the figure it shows.
- A chart or table that carries a figure shows its unit, as-of date and source on the slide.
- Axes start at zero, or the break is shown and stated. No metric appears that the source material lacks.
- A diagram's arrows and groupings must match the text claim beside it (a "phased migration" slide shows phases).

## 4. Generic-slide defaults to justify or remove

- Card grids used because they fit anything, with no relation between the cards.
- Decorative icons, stock imagery, gradients or shadows that carry no information.
- Centered everything with equal weight, so no reading path exists.
- Body text in low-contrast gray; type roles that cannot be told apart (the measurable parts are in `deck_check.py`).
- Generic captions ("핵심 역량", "최적의 솔루션") where a buyer-specific statement belongs.

## 5. Critique-and-revise loop

1. Render the saved deck (`deck_check.py --render`) and look at every page image, not the source file.
2. List findings, each with why it matters and the smallest fix, ranked Critical / Major / Minor (same scale as
   `review-checklist.md`). Do not assign a numeric score.
3. Revise once against that list, then render and list again. A revision that leaves the findings list unchanged
   did not fix anything; say so instead of claiming progress.
4. Record the result with `verification_report.py` (what was inspected, at which level, what was not inspected).

A rendered page that fails is a fail even when the source passes. Rendering is separate from human visual approval.
