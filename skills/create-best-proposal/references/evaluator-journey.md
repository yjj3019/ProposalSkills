# Evaluator journey — structure proposal logic around reading order

Evaluators do not read proposals from beginning to end. They use evaluation criteria to locate pages and inspect
conclusions/evidence. Connect existing `requirements[]`, `evaluation_criteria[]`, Win Themes, and lead maps to
that reading flow. This creates no new gate; it makes Pink/Red checks concrete.

## 1. Core message model

Key slides for high-weight criteria have 7 elements:

| Element | Content | Slide location |
|---|---|---|
| `evaluator_question` | What the criterion asks (one sentence from evaluator perspective) | Writing notes; not on slide |
| `conclusion_headline` | Our conclusion | Lead |
| `evidence` | Proof (architecture/test result/track record/certification) | Body diagram/table |
| `buyer_implication` | Buyer benefit (figures/criteria if measurable) | End of lead or benefit box |
| `boundary` | Commitment scope/assumptions/exclusions | Caption/footnote |
| `req_ids` | Requirement IDs addressed | Caption |
| `criterion_ids` | Evaluation criteria addressed | Writing notes/matrix |

Questions each slide must answer:

1. What was required? → `req_ids`, matrix row.
2. What is our conclusion? → Lead.
3. Why this approach? → One-line reason versus alternatives.
4. What proves it? → Diagram/table/source.
5. What benefits the buyer? → Benefit statement.
6. What are the commitment boundaries? → Boundary caption.

For technical items, fill 3/4/6 with [technical-depth-six-questions.md](technical-depth-six-questions.md).

State current customer problems as facts only with RFP/current-state sources. Otherwise label them as risks to
prevent or assumptions to verify (Korean examples: `예방할 위험`, `확인할 가정`). Distinguish future test/acceptance
plans from existing track records/test results and state status (Korean examples: `합성 수용계획`, `검수 예정`).
Buyer benefits are expected effects, not evidence themselves. Never put benefit statements in `cards` `evidence`.

## 2. Writing order (before slide production)

1. Write one `evaluator_question` per evaluation criterion.
2. Link criteria to requirements (`criterion_ids`) and Win Themes (`req_ids`).
3. Choose key slides per criterion and write leads (`conclusion_headline`) first.
4. Assign evidence locations (diagram/table/appendix). Without evidence, mark `[NEEDS INPUT]`.
5. Create `slides.json` after this table is finalized.

Do not discover logic while filling PowerPoint. More slides cannot repair a lead map without coherent logic.

## 3. Pink check — does the skeleton establish the logic?

Read only:

Outline → leads → REQ-IDs → evaluation criteria → Win Themes → evidence locations.

Pass conditions:

- Each high-weight criterion has at least one conclusion lead.
- Reading leads alone sustains the case for choosing us.
- Every Win Theme links to both requirements and evaluation criteria.
- Leads with empty evidence locations are marked `[NEEDS INPUT]`.

## 4. Red check — can an answer be found within 10 seconds?

Choose a criterion and open its slide as an evaluator.

| Check | Failure signal | Severity |
|---|---|---|
| Can the slide be found immediately through outline/breadcrumb? | Criterion scattered across sections | Major |
| Is the lead a conclusion? | Topic introduction only (Korean example: "~에 대해 설명") | Major |
| Is supporting evidence on the same slide? | Evidence only elsewhere/appendix without reference | Major |
| Are commitment boundaries visible? | Commitment without conditions/scope | Critical (commitment) / Major |
| Is a mandatory requirement missing? | Mandatory subcondition omitted, matrix row unfilled, or missing REQ-ID | Critical |

Compare original RFP mandatory conditions with body/tables in the actual generated PPTX.
Metadata, matrix `O`, or REQ-ID labels alone do not establish coverage. Check mandatory durations,
acceptance conditions, and deliverables within each requirement individually. Record
`requirement/subcondition | actual response location/excerpt | covered/missing | revision`.
Also compare contract dates, exclusions, budget, and output specifications in business conditions outside requirement IDs.
For a report requiring cause/action/recurrence prevention, a generic RCA promise (Korean example: `RCA 제출`)
does not answer all three. A backup-role table does not replace contact/handoff arrangements: verify call paths,
received time/open items/next actions handed over. Check response locations actually exist.

Current automated ID/layout/number checks do not judge semantic completeness or persuasiveness.
Perform body comparison and rendered-image review separately; do not count unreviewed items as covered.

Red output is **coverage evidence locations + weaknesses (Critical/Major) per criterion**, with no numerical scores.

## 5. Prohibitions

- Predicting evaluation scores/rankings/win probabilities.
- Estimating unpublished score allocations.
- Disparaging competitors or asserting unsupported competitor weaknesses.
- Inferring evaluator affiliations/dispositions.

## 6. Optional narrative pattern

For an introduction or business-understanding section, the sequence below is optional.
If evaluation order is specified, it takes precedence.

Customer situation → problem/constraints → proposed conclusion → implementation → evidence → buyer benefit.
