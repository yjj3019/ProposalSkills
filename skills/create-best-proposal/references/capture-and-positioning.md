# Pre-RFP capture, positioning, and proposal strategy

Use this writing form before or immediately after publication to identify emphasis and gaps.
Its output **strengthens Pink inputs**. It does not replace `bid_decision`, audit JSON, or submission gates,
and adds no audit schema fields. Keep it as a separate memo (`capture.md`).

## 1. When to use

- RFI/preliminary-specification publication.
- Presales/requirements discussion.
- Joint proposal/partner/manufacturer role allocation.
- Opportunities where competitive positioning determines the outcome.
- Capability-gap or price-position assessment.

For immediate drafting from only the final RFP, completing `decision_drivers` and `capability_gaps` in §2 suffices.

## 2. Writing form

Tag every item:

- `FACT` — confirmed by notice, official Q&A, buyer public material, or approved internal material (cite source).
- `HYPOTHESIS` — inference; include a verification method and deadline.
- `UNKNOWN` — unknown; route to formal questions/sales confirmation.

```text
opportunity_summary     Purpose, scope, schedule (mostly FACT)
decision_drivers[]      Buyer decision criteria; tag and source per item
positioning_axes[]      Our position on each axis: strength/gap/disadvantage
capability_gaps[]       Gaps against requirements; remedy (partner/staff/certification), owner, deadline
pursuit_risks[]         Risks of pursuit: schedule/eligibility/staff/price/contract terms
price_posture           known range / cost floor / commercial constraints / unknowns
```

## 3. Comparison axes (axes before competitor names)

Transition risk, service-interruption impact, operational stability, technical support, security, scalability,
compatibility, vendor dependency, comparable track record, assigned personnel, price/TCO.

Pair evidence that the buyer values an axis (`FACT`/`HYPOTHESIS`) with how we can prove our position.
Without proof, do not call it a strength.

## 4. Price strategy

Do not use Price-to-Win (estimated winning price). Record only:

- known range: official published budget/base amount.
- cost floor: internal cost floor (never include in external documents).
- commercial constraints: license unit-price structure, manufacturer terms, split deliveries.
- unknowns: unverified price variables.

## 5. Do not generate

- Unsupported competitor weaknesses or estimated competitor prices/strategies.
- Identities or dispositions of buyer decision makers.
- Nonpublic budgets or expected winning prices.
- Win probabilities/rates.

## 6. Handoff to Pink

- `FACT` in `decision_drivers` → basis for each criterion's `evaluator_question`
  ([evaluator-journey.md](evaluator-journey.md)).
- Strength axis + proof → Win Theme candidate (each theme requires `req_ids`).
- `capability_gaps` → candidate conditional conditions for the four-way bid decision (owner/deadline required).
- `HYPOTHESIS`/`UNKNOWN` → questions; never proposal-body facts.
