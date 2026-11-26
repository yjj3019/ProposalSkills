# Provenance record: ideas from twelve public repositories and one article (2026-11-27)

A development record, not legal advice. It states what was read, which ideas were adopted and which were not, so the licensing
position is auditable before any code or text was written (AGENTS.md).

## How the review was done

Twelve repositories were cloned shallowly into a scratchpad and read; nothing from them was executed. Their README figures (for
example token savings) were read, not verified. A Notion article on prompting Claude could not be fetched (the link returned 404);
its body was pasted by the user and is a secondary summary, so its numbers and version claims are not verified.

## Licensing position

- Everything adopted is an **idea implemented independently**. No source file, test, document wording or data was copied or
  translated. No third-party notice is carried because no third-party text is carried.
- MIT: ppt-master, planning-with-files, refactoring-ui-skill, TokenEconomizer, motionforge and the animation repositories.
  Apache-2.0: knowledge-work-plugins (root) and each `anthropics/skills` skill (its own `LICENSE.txt`; the repository has no root
  license, and its `THIRD_PARTY_NOTICES` lists GPLv3 components, so nothing from it is copied).
- `refactoring-ui-skill` is an unofficial derivative of a commercial book. Only the *shape* of its evaluation records is taken
  (a case, what must and must not be said); none of its rules or wording.
- If text or code were later copied, the source license's notice rules apply and this record is updated first.

## Adopted (idea, then independent implementation here)

| Source (license) | Idea | Implementation here |
|---|---|---|
| `anthropics/knowledge-work-plugins` go/no-go guidance (Apache-2.0) | Bid decision as ordered checks, cheapest disqualifier first, ending in delivery capacity ("winning what you cannot deliver is worse than losing") | `create-proposal-document/references/bid-and-submission.md` §1; the `BID_DECISION` answer contract is unchanged |
| `refactoring-ui-skill` eval cases (MIT), skill-creator `run_loop.py` train/test split (Apache-2.0) | Keep the input beside its result; judge a description edit on cases it was not tuned on | `references/manual-eval-prompts.md`; `holdout` lists in `references/trigger-eval-cases.json` and `trigger_eval_run.py --set holdout` |
| `ppt-master` visual-review rules on overflow, text collision and element conflict (MIT) | Check shape geometry, not only fonts | `tidy_audit.py` advisory checks: shape off the slide, text boxes that overlap, estimated text overflow |
| `refactoring-ui-skill` forbidden-output cases (MIT) | A check needs cases it must stay silent on | `test_tidy_thresholds.py`: intentional overlays (badge on a card, label on a picture) are not flagged |

## Already covered here, not adopted again

`ppt-master` routes and design approval (`deck_stage_gate.py`); `planning-with-files` plan files and resume (`handoff_lint.py`,
lessons log, which bind the note to a hash); `motionforge` hash-bound QA report (`review_ledger.py`, `unified_gate.py`); the
Notion article's advice on a short `CLAUDE.md`, pass/fail checks and a second-session review (already so).

## Not adopted

- `microsoft/TokenEconomizer`: runtime hooks and a judge model for session cost; same reason as the earlier rejection of text
  compression (evidence loss, external model).
- skill-creator description-optimisation loop and blind comparator: unbounded model calls; no independent evaluator exists here.
- `anthropics/skills` pptx XSD validators: schema redistribution terms not verified.
- Animation and graphics repositories (motion, three.quarks, manim, hairline, motion-design-skill): unrelated to python-pptx decks.

## Not read

ppt-master was read through its SKILL.md, routing table and visual-review rules only; skill-creator through its file list and
`run_loop.py`; TokenEconomizer through its README and layout; knowledge-work-plugins through `grant-rfp-writer` and
`proposal-builder`. The agentskills.io specification was not read.
