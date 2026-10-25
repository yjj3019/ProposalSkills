# Evidence and claims (evidence-and-claims)

Write every proposal claim on the assumption that an evaluator may request verification.
The leading reasons for rejection are **unsupported claims and internal inconsistencies**, rather than design.

## 1. Required evidence by claim type

| Claim type | Required accompanying information | Format |
|---|---|---|
| Track record (delivery examples) | Project, buyer, period, scope (product/scale) | Track-record table; state whether delivery certificates can be attached |
| Certifications and qualifications | Name, issuer, validity, quantity held | Table + attached copies; expired certifications prohibited |
| Partner tier | Vendor, tier, verification date | Attach partner commitment/certificate (common practice in analyzed samples) |
| Performance figures | Measurement environment, conditions, date, source | Limit scope with the Korean example "동일 조건 보장 아님"; include configuration specifications for BMT results |
| Product capabilities | Product, **version**, availability (GA/TP/roadmap) | Use official vendor documentation; explicitly distinguish Tech Preview |
| EOL and support period | Product, version, support end date, lifecycle policy | **Current web verification required** (EOL in reused material is usually outdated) |
| Market position | Research organization, report, year | Korean example: "OO 기준 점유율 N%(가트너, 2025)" |
| SLA and response time | Severity definitions, measurement criteria, scope | SLA table; distinguish vendor SLA from the proposer's SLA |
| Expected benefits (quantitative) | Formula, assumptions, comparison baseline | Footnote the formula; savings percentages without assumptions prohibited |

## 2. Handling unverifiable claims

For a claim whose evidence slots cannot be filled:

1. Exclude it from the body (softening it is also prohibited: a softened claim is still a claim).
2. Collect it separately with the `[unverified]` tag.
3. Report the list to the user when delivering the artifact. Korean report example:
   "다음 N건은 근거 자료가 없어 본문에서 제외했습니다. 자료를 주시면 반영합니다."
4. Once the user supplies evidence, insert the claim and its evidence on the relevant page.

## 3. Internal consistency (cross-check targets)

Figures repeated on multiple pages must agree. Compare all occurrences at the final gate:

- Staffing: summary ↔ delivery organization ↔ staff profiles ↔ effort table (M/M).
- Schedule: strategy roadmap ↔ Gantt chart ↔ milestone table.
- Product versions: product introduction ↔ architecture ↔ equipment/SW specifications ↔ licenses.
- Track-record counts: company introduction (Korean example: "N개사") ↔ track-record row count.
- SLA figures: summary ↔ detailed SLA table ↔ compliance-matrix response.

## 4. Legal and contractual wording

- Commitment phrases (Korean examples: "보장합니다", "책임집니다") become contractual terms. Do not use them without scope and assumptions.
- Identify sources for third-party responsibilities (vendor support policy, manufacturer roadmap) and mark the responsibility boundary with the Korean example "제조사 정책에 따름" (standard-product response practice).
- Do not disparage other companies or competitors. Compare only public, objective metrics with sources.
- Do not reuse customer confidential information or previous customer data (architecture, figures). Even anonymized material is prohibited if identification remains possible.

## 5. Accessibility wording

Use WCAG 2.2 contrast thresholds (4.5:1 normal text, 3:1 large text) only as **conservative design reference values**.
WCAG is a web-content standard: do not automatically claim legal conformance such as the Korean example "WCAG 준수/적합" for print, DOCX, or PDF artifacts.
Claim accessibility compliance in a proposal only after confirming the buyer's required standard (e.g., KWCAG, Korean disability discrimination legislation) and verification method.
