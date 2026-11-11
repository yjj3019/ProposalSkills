# AI-tell review (generic-pattern removal that keeps every fact)

Use after a draft exists and before the quality gates in `review-checklist.md`. The goal is to remove
machine-generic phrasing and layout habits from a proposal while keeping every number, quote, source and
commitment exactly as supplied. It is a purpose-and-evidence review. It never judges authorship and never
tries to beat an AI detector.

## Principles

1. **Purpose test**: when a device repeats (a three-card row, a slogan opener, an emphasis phrase), state in one plain
   sentence what it does for this proposal. A device that would suit any proposal is cut or justified.
2. **Specificity test**: a habit that shows up in unrelated places (same opener, same closer, always three items)
   only raises a suspicion. If there is a genuine reason for it, keep it.
3. **Facts stay**: figures, quotes, certifications and commitments are the payload. Restate them or remove the
   sentence. Never add a metric, reference or source that the supplied material does not contain.
4. **Direction stays**: remove the tell and stop. A flat result means the buyer-specific message is missing; add
   it from the RFP, not from filler.
5. **Style review is not verification**: a clean pass does not make a claim supported, a gate approved, or a
   submission ready. `proposal_gate.py` and `quality_gate.py` still decide.

## Checklist (Korean examples, labeled)

- [ ] Contrast slogans: "단순한 X가 아니라 Y" with no evidence after it. Replace with the concrete claim and its source.
- [ ] Empty emphasis: "혁신적인", "최적의", "차별화된" without a metric, reference or mechanism. Name the mechanism or delete.
- [ ] Repeated openers or closers across slides ("본 제안은 ~을 위해 ~하겠습니다" on every page). Vary by content, or merge.
- [ ] Stacked hedges ("~할 수 있을 것으로 기대됩니다" chained). Keep only the hedge that matches a real uncertainty and mark it.
- [ ] Colon lists and always-three groupings that exist for rhythm, not because there are three items.
- [ ] Decoration: emoji, ornamental bold, or banner headings. The visual style comes from `visual-style.md`.
- [ ] First sentence repeats the slide title. Let the title carry it; start with the decision or evidence.
- [ ] Unattributed figures or superlatives ("국내 최초", "업계 최고"). Add the source and as-of date, or remove them.
- [ ] Passive, actor-less commitments ("점검이 수행됩니다"). Name the actor, the deadline and the deliverable.

## Report format (all four blocks required)

| Block | Content |
|---|---|
| Changed | Each edit and where it was made |
| Kept | Facts, figures, commitments and structure deliberately preserved |
| Evidence | Source documents or logs behind the kept claims |
| Uncovered | What could not be checked (mark `[NOT INSPECTED]` or `[unverified]`; never leave blank) |

A report with an empty Evidence or Uncovered block is incomplete. Report the AI-tell pass separately from the
gate results; do not merge them into one pass/fail line.
