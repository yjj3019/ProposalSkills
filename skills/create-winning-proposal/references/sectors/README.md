# Sector profiles — what exists and what does not

## Why only one?

Institution-type profiles add value **only when verifiable**. Any model can produce obvious advice
such as addressing patient safety in hospital proposals without this repository.
The skill must contribute nonobvious practical knowledge, which cannot be invented or verified after fabrication.

There is therefore **only one profile: public (`public.md`)**.
Most repository guidance already assumes public procurement; this gathers existing scattered knowledge rather than inventing new material.

For private enterprise, education, and healthcare, provide **classification axes and gate rules only**;
content is intentionally empty. Practitioners should fill it from actual delivery experience.
An empty profile is preferable to lending unverified information credibility under a profile label.

## Classify by axes, not names

One institution name is insufficient. Public hospitals and national universities have overlapping properties;
even within an institution, evidence needs differ by engagement and purchasing stage.
Record audit `context`; the gate reads it to change requirements.

| Axis | Values | Effect |
|---|---|---|
| `buyer_types[]` | `public` `private` `education` `healthcare` (multiple) | Public requires an evaluation register |
| `engagement` | `build` `operate` `migrate` `education` `consulting` `service-improvement` `product-selection` `policy` | Select outline archetype |
| `stage` | `explore` `internal-review` `rfp-response` `presentation` `final-submission` | Determines submission-stage checks |
| `reading_mode` | `screen-presentation` `print-evaluation` `individual-review` `appendix` | Compare with deck_profiles |
| `constraints[]` | `sensitive-data` `business-continuity` `closed-network` `regulated-industry` | Sensitive data requires three package checks to `pass` |
| `rfx_type` | `rfp` (default) `rfi` `rfq` | RFI waives evaluation table and blocks `commitment`; eligibility/format checks remain |

Submission (`mode: submission`) **requires** `buyer_types` and `stage`.
Missing context silently disables the table's checks, so omission is not a valid default.

Explicit RFP/contract/form requirements always override this classification.
When classification is ambiguous, leave it unresolved and ask rather than guessing.

## Adding a profile

Follow `public.md`: additional questions, what the proposal must prove, reviewers,
claims requiring care, and **which items machines can check**.
If the last part is empty, the profile is guidance rather than a gate; document that limit.

Applicable laws/certifications depend on scope, data, jurisdiction, reference date.
Never impose them universally based solely on institution type.
