# Audit JSON schema

Populate every top-level field; do not omit empty arrays.

```json
{
  "mode": "submission",
  "artifact_mode": "submission-candidate",
  "bid_decision": "conditional-bid",
  "bid_conditions": [{"id": "B1", "owner": "Legal", "deadline": "2026-08-20T17:00:00+09:00", "accepted": true}],
  "requirements": [{"id": "R1", "mandatory": true, "state": "approved", "rationale": "", "reviewer": "Security lead"}],
  "claims": [{"id": "C1", "kind": "commitment", "status": "supported", "owner_approved": true}],
  "unresolved_tokens": [],
  "attachments": [{"name": "signature.pdf", "required": true, "present": true}],
  "source_conflicts": [],
  "inputs": [{"id": "I1", "class": "non-blocking", "status": "closed"}],
  "defects": [{"id": "D1", "severity": "major", "status": "closed", "closure_evidence": ["sha256:fixed", "page 12 rechecked"], "reviewer": "QA lead", "closed_at": "2026-07-19T12:00:00+09:00", "reverified_scope": ["R1", "page 12"]}],
  "checks": {"consistency": true, "arithmetic": true, "submission": true},
  "artifact_required": true,
  "render": {"verified": true, "render_succeeded": true, "layout_checked": true, "visual_review_approved": true, "visual_reviewer": "제안PM 김검토", "artifact_hash": "sha256:<64 hex>", "tool": "renderer version", "evidence": ["all pages reviewed"]},
  "package": {"required": true, "inspected": true, "artifact_hash": "sha256:<64 hex>", "tool": "package inspector version", "checks": {"metadata": "pass", "notes": "pass", "comments": "pass", "hidden-content": "pass", "embedded-files": "not-applicable", "external-links": "pass", "macros": "not-applicable", "stale-customer-data": "pass", "price-leakage": "pass"}, "reviewer": "QA lead"},
  "submission": {"cleared": true, "rehearsal_evidence": ["test upload opened"], "receipt_plan": "save portal confirmation", "receipt_evidence": []},
  "flags": {"financial": false},
  "regulatory_checks": [{"id": "REG1", "requirement": "전자금융 감독규정(망분리)", "status": "met", "evidence": ["점검 확인서"], "owner": "보안담당"}],
  "vendor_confirmations": [{"id": "V1", "kind": "support", "required": true, "present": true}],
  "numbers": [{"id": "N1", "label": "총 사업비", "value": 3700000000, "unit": "KRW", "source": "견적서 v3", "components": ["N2", "N3"]},
              {"id": "N2", "label": "구축비", "value": 2500000000, "unit": "KRW", "source": "견적서 v3"},
              {"id": "N3", "label": "유지보수비", "value": 1200000000, "unit": "KRW", "source": "견적서 v3"}]
}
```

- `mode`: record `submission`, `draft`, `review`, or `analysis`.
- `artifact_mode` (optional): `submission-candidate` or `simulation-only`. Keep `bid_decision` unchanged when benchmarking a no-bid RFP, including expired notices.
- `conditional-bid` passes only with an owner, timezone-aware ISO-8601 deadline, and acceptance record for every condition.
- `intake-incomplete` and `no-bid` never pass submission readiness.
- Mandatory `not-applicable` requirements need rationale and reviewer.
- Material claims need evidence as `supported`/`qualified`, or removal. Commitments additionally require owner approval.
- Open blocking inputs and Critical/Major defects block submission. `conditional-go` is only an internal review state.
- Only `blocking|non-blocking|assumption`, `critical|major|minor|note`, `open|closed` are allowed. Unknown values invalidate the audit.
- Closing Critical/Major requires closure evidence, reviewer, ISO timestamp, reverified scope.
- Use `artifact_required: false` only when no rendered artifact was requested.
- Editable Office files require package inspection `required`. Missing tools mean `inspected: false`, never a pass.
- Verified render/package states need artifact hash, tool identification, evidence/check results, reviewer. These establish a review record's existence, not the truth of its judgment.
- Failed/uninspected required package checks block submission readiness.
- Inspect properties, notes, comments, hidden content, embedded files, external links, macros, previous customer data, price leakage. Use `not-applicable` only with reviewer responsibility.
- Submission clearance needs rehearsal evidence and a receipt-evidence plan. Add actual receipt evidence after submission; never invent it beforehand.
- `win_themes` (optional): `[{id, statement, req_ids[], proof?}]`. Each theme needs nonempty `req_ids` (no decorative themes). Not mandatory gate fields, but enforced by meta-builder `--strict` and authoring discipline.
- Optional backward-compatible requirement fields: `fit` ∈ {STRONG, PARTIAL, GAP}, `eval_weight`, `win_theme_id`, `risk`, `support`, `evidence_refs` (required when approved).
- `flags`, `regulatory_checks`, `vendor_confirmations` are optional/backward-compatible; absent fields are not checked.
  - `regulatory_checks[]` status ∈ {met, gap, in-progress, not-applicable}. `gap`/`in-progress` block; `met` requires evidence. Submission with `flags.financial: true` blocks if this register is empty, preventing omitted financial regulation.
  - `vendor_confirmations[]` kind ∈ {support, supply}. `required && !present` blocks, modeling mandatory pre-contract manufacturer support/supply letters.
- Mark consistency/arithmetic/submission checks `true` only after completion or recorded non-applicability rationale.

## Anti-optimism hardening — block optimistic self-declarations

The gate validates self-reported assertions' *structural completeness*, not their *truth*.
Previously, optimistically marking requirements `approved`, attachments `present`, and submission `cleared`
could yield READY. The following three guard categories close that gap.

- **Evidence required**: a mandatory requirement with `state: approved` needs nonempty `evidence_refs: []`
  (proposal location, artifact hash, etc.). Unsupported approval self-declarations block.
  In submission, material/commitment `claims[]` with `status: supported|qualified` also block without `evidence_refs`.
- **Review state ≠ compliance**: `state` (review progress) differs from `support`/`fit` (fulfillment).
  `support: X` (or preserved Korean code `미지원`) or `fit: GAP` with `state: approved` blocks.
  A reviewer confirming unsupported status does not mean fulfillment. Only buyer-granted exceptions count;
  record `exception: {granted_by, evidence: []}`.
- **Nonacceptance aliases**: `X`, `X 미수용`, `미수용`, `미지원`, `✗`, `부적합` mean the same state;
  spelling variants cannot evade approval contradiction checks (`N/A`/`해당없음` do not mean unsupported).
  Meta→audit preserves `exception` and `response_refs`.
- **Response location ≠ evidence**: matrix response locations go in `response_refs`.
  `evidence_refs` contains supporting sources (certificates, test reports, manufacturer replies).
  `bulk_matrix.py` generates separate fields: `slide:99` is not promoted to factual evidence.
- **Context**: `{buyer_types[], engagement, stage, reading_mode, constraints[], rfx_type}`.
  Classify by axes, not institution names (public hospital → `["public","healthcare"]`).
  Gates read context to change requirements; see [sectors/README.md](sectors/README.md) for values/effects.
  Explicit RFP requirements always override classification.
  **Submission requires `buyer_types` and `stage`**: missing classification silently disables affected checks,
  so omission is not a valid default (draft/review remain backward-compatible).
- **Document type (context.rfx_type)**: `rfp` (default) | `rfi` | `rfq`, separate from purchasing `stage`.
  For `rfi`, (1) do not require an evaluation register even for public buyers, (2) block `kind: commitment` claims:
  an RFI is not a contractual proposal, so estimates must not become promises.
  Eligibility, attachments, format checks still apply; RFI does not waive qualification requirements.
- **Evaluation table (evaluation_criteria)**: array of `{id, label, weight, parent?, stage?, method?, minimum_ratio?,
  minimum_score?, disclosed?, source?}` and optional `evaluation_total` (register maximum, default 100).
  Required for public buyers in submission: weights govern outline/space/evidence, without them the author does not know what is scored.
  Do not reduce every source evaluation to a total of 100:
  - **Top-level weights sum to `evaluation_total`**. If only technical 90 is in the register and price is separate,
    record `evaluation_total: 90`, never change it to 100.
  - **Children (`parent`) sum to their parent's weight**. Preserve hierarchy, e.g., stage-1 technical 100 = quantitative 20 + qualitative 80;
    prevent double-counting parents and children together.
  - **Undisclosed weights use `disclosed: false`** without `weight`; the gate never invents 80:20.
  - Preserve cutoffs as `minimum_ratio` (fraction of allocated maximum, 0.85 = 85%) or `minimum_score`.
    The gate does not predict evaluation scores or determine technical failure. A negotiation-eligibility 85% threshold
    means 85% of the technical evaluation **allocated maximum** (76.5 when maximum is 90), not total score 85.
    Confirm applicability for each notice.
  Link requirements through `requirements[].criterion_ids` to **leaf** criteria; leaves without responses block
  as a signal of missing chapters. If `reading_mode` expects a profile, absent or mismatched `render.output_profile`
  blocks submission (missing = uninspected). Only `screen-presentation` (presentation) and `print-evaluation`
  (detailed submission) imply profiles. Do not map `individual-review`: it can mean an executive summary
  or detailed technical evaluation, so reading environment alone cannot determine document role.
- **Outline (proposal_archetype, sections, archetype_rationale)**:
  `build` | `maintenance` | `technical-response`. `context.engagement` maps build/migrate → `build`,
  operate/service-improvement → `maintenance`, product-selection → `technical-response`.
  Mismatches block unless buyer-prescribed contents are evidenced in `archetype_rationale`.
  Submission with a mapped engagement **must record the chosen skeleton**.
  If `sections[]` (`{title}` or string array) exists, check mandatory sections:
  build = scope/build approach/schedule/testing-acceptance/delivery organization;
  maintenance = support scope/support organization/SLA/incident response;
  technical response = requirements matrix/products-specifications/evidence.
  Without a register, do not check or fabricate contents; `slides[]` maps responses, not chapters, so do not infer from it.
  **This repository has no outline evidence for education/consulting/policy.**
  Do not force a type, but require rationale for reusing IT-build outlines.
- **Third-party commitments (claims[].depends_on_vendor)**: name the manufacturer/partner when promises rely on its SLA/supply conditions.
  Submission requires a same-name `vendor_confirmations` entry with `present: true`.
  **Citing public manufacturer documentation is different from obtaining confirmation that it applies to this project.**
  Korean example "심각도1 1시간 내 대응" holds only if that SLA applies to the contract/subscription tier;
  otherwise it becomes an undeliverable post-contract promise.
- **Time-sensitive claims (claims[].time_sensitive, as_of)**: lifecycle/EOL/version/certification validity claims
  that can become false need `time_sensitive: true` and `as_of` (`YYYY-MM` or `YYYY-MM-DD`).
  Free text (Korean example "2026년 여름") is not a reference date.
  Show the same date in the document so reused slides do not silently age.
- **Numeric relationships (numbers[].at_most, at_least)**: individually correct values can have incorrect relationships.
  SLA first response ≤ continuing response; response times should increase as severity decreases.
  Convert only fixed elapsed units (minutes/hours/days/weeks), e.g., preserved inputs `4시간` vs `2일`.
  Do not convert business days/months/years to fixed durations without start date, holidays, business-hour evidence.
  Compare identical units; block different units. If needed, record same-unit values calculated using the source calendar.
- **Submission bundle (attachments)**:
  `{name, required?, present?, role?, file?, format?, sha256?, copies?, channel?, anonymity_checked?, price_screened?, reviewer?}`.
  Submissions include named originals, anonymous copies, sealed pricing, separate worksheets; files have different rules.
  `role` = `proposal` | `proposal-anonymous` | `price` | `form` | `certificate` | `presentation` | `appendix` | `other`.
  Role-specific rules apply when declared. Hashes are required regardless of role.
  For `present: true` in submission:
  - Require `sha256` to identify inspected bytes.
  - `proposal-anonymous` requires `anonymity_checked: true` and `reviewer`.
    Inspect identifiers in body, notes, properties, filenames (`quality_gate.py --names`); humans inspect logos/image text.
    Warn if only an anonymous copy exists without a named original.
  - Every non-`price` artifact requires `price_screened: true`, recording technical-copy price-leakage screening.
  - Multiple artifacts for any of `proposal`, `proposal-anonymous`, `price` block; select one submission file per role.
  `unified_gate.py --bundle <폴더>` compares actual files/hashes (`file` if supplied, otherwise `name`),
  catching missing or post-review changes. Paths must be relative within the bundle;
  absolute/parent/link escapes block. Submission with an actual document and required or present attachments
  requires `--bundle`. Audit-only does not judge physical submission readiness.
- **Requirement strength (requirements[].strength)**:
  `required` | `recommended` | `optional` | `conditional` | `informational`.
  Derive from `mandatory` when absent (both omitted = `required`, fail-closed).
  Contradictions between both fields are schema errors.
  `conditional` requires `condition` identifying when it becomes mandatory and counts as mandatory.
  Unfollowed `recommended` requirements need `rationale` for submission: exceeding recommended length differs
  from mandatory violations, but omission must be distinguished from reasoned deviation.
  `bulk_matrix.py` maps Korean `필수` column values 권장·선택·조건부·참고 into strength.
- **Numeric register (numbers)**:
  `numbers[] = {id, label, value(JSON number), unit, source?, components?[], percent_of?, amount?, tolerance?(default 0.005), must_appear?}`.
  With `components`, value must equal their sum; mixed units block.
  With `percent_of`+`amount`, recalculate the ratio.
  **Submission cannot pass with `checks.arithmetic: true` alone and no register.**
  `check_numbers.py` compares values with actual documents; exclude intermediate calculations using `must_appear: false`.
  Values must be finite JSON numbers (block `Infinity`/`NaN`), with no self-reference via `components`/`percent_of`.
  `percent_of` requires finite `amount` and nonzero denominator; inability to calculate is unverified, not passed.
  Currency units (`KRW`, `원`, `USD`, etc.) use **absolute tolerance at the 1-won level**, not relative tolerance, for sum checks.
  An empty submission register requires `numbers_not_applicable` rationale.
  Document matching accepts only the **body seen by evaluators**, blocking values appearing solely in notes/layouts/masters.
  Distinguish decimals/units/sign: Korean examples `37.5개월` does not evidence `37`;
  `37개월` does not evidence `37원`; `-37` does not evidence `37`.
- **Verification duties cannot be cancelled**: `mode: submission` requires render verification, hash format,
  package checks regardless of `artifact_required`.
  `artifact_required: false` matters only in draft/review; one input cannot disable submission checks.
- **Render success ≠ visual approval**: submission requires `render.visual_review_approved: true`
  and `render.visual_reviewer` (real name). `deck_check.py` always writes false;
  the human reviewing PNGs changes it. PDF conversion success is not design approval.
- **Missing check records = uninspected**: `render.layout_checked` is **required**.
  Both false and **omission block**, closing the deletion bypass.
  Contradictory `verified: true`/`render_succeeded: false` also block.
  For PPTX output, unresolved font sizes keep `layout_checked` and `verified` false even after a successful render; verify and set the sizes explicitly before rerunning.
  `build_audit_from_meta.py` copies supplied `render_succeeded`, `layout_checked`,
  `visual_review_approved`, `visual_reviewer`, `output_profile`; it never fabricates approvals.
- **Artifact binding**: submission with `artifact_required: true` requires real matching
  `render.artifact_hash`/`package.artifact_hash` values (`sha256:<64 hex>`).
  Labels such as `sha256:proposal` block. Judge with `unified_gate.py --doc <최종파일>`;
  mismatches between the file and audit block, preventing reuse after edits.
  For document-free audit checks, use `--audit-only`; the best result is `AUDIT-VALID`, not `SUBMISSION-READY`.
  Recompare parsed audit bytes and the document's pre-first-subcheck SHA-256 before final judgment.
  Content change/deletion/read failure means `INVALID` (exit 2); unchanged quality failures remain `BLOCKED` (exit 1).
  Check actual attachments/hashes after audit evaluation. This is not file locking:
  intermediate changes reverted before comparison and changes after final comparison are not guaranteed detectable.
- **Stage enforcement**: `mode: submission` audits require `--stage submission`.
  Lowering to `--stage draft` to downgrade `[NEEDS INPUT]` into warnings is usage error (exit 2).
- **Simulation artifacts**: `artifact_mode: simulation-only` cannot pair with `mode: submission`;
  internal checks cannot become external readiness.
- **ID integrity**: every `requirements[]`/`claims[]` item needs a nonempty unique `id`;
  IDs cannot be removed to anonymize registers or duplicated to mix evidence.
- **Register content**: submission `requirements[]`/`claims[]` items need human-readable content in
  `text`, `label`, `title`, `summary`, or `description`.
  ID-only records cannot identify what an approval approves (partial draft registers remain allowed).
- **Informational exemption rationale**: `kind: informational` alone exempts `evidence_refs`;
  submission needs `rationale` explaining why evidence is unnecessary, preventing unsupported performance/track-record relabeling.
- **Deadline**: `submission.deadline` is timezone-aware ISO-8601, mandatory in submission.
  Past deadlines block against current time (injectable `PROPOSAL_GATE_NOW`, default UTC now).
  `cleared: true` cannot pass expired RFPs.
- **Placeholders are not evidence**: treat `TBD`, `TODO`, `???`, `[NEEDS INPUT]`,
  Korean placeholder inputs `입력요망`, `미정`, etc. as empty and block in
  `evidence_refs`, `render.artifact_hash/tool/evidence`, `package.artifact_hash/tool/reviewer`,
  `submission.rehearsal_evidence/receipt_plan`, `regulatory_checks[].evidence`, `defects[].closure_evidence`.
- **Strict booleans**: `accepted`, `present`, `cleared`, `verified`, `inspected`,
  `owner_approved`, `met`, `curable`, `mandatory`, `required` accept only JSON `true`/`false`.
  Strings such as `"yes"`/`"pending"`/`"no"` mean INVALID AUDIT (exit 2).
  Omitted `mandatory`/`required` default mandatory; omitted claim `kind` defaults `material` (fail-closed).
  `kind` must be `material | commitment | informational`.
- **Conditional bid scope**: `conditional-bid` yields CONDITIONAL-GO only for `mode: draft|review|analysis`.
  It blocks in `mode: submission`: conditional means internal continuation, not external clearance.
  Every `bid_conditions[].deadline` must be future.
- **Eligibility consistency**: `eligibility[] = {id, criterion, mandatory, met, curable}`.
  Submission requires the register. Unmet (`met:false`) and `curable:false` prohibits `bid`/`conditional-bid`
  (only no-bid); unmet and `curable:true` prohibits unconditional `bid` (conditional or no-bid).
  Optimistic bid declarations cannot override unremediable ineligibility.

## eligibility / conditional-bid examples (common mistakes)

**Eligibility register** — mandatory in submission. Mark each mandatory qualification met/curable.
Korean example inputs remain verbatim.

```json
"eligibility": [
  {"id": "E1", "criterion": "동종 실적 3억 이상 2건", "mandatory": true, "met": true,  "curable": true},
  {"id": "E2", "criterion": "SW사업자 등록",          "mandatory": true, "met": true,  "curable": true},
  {"id": "E3", "criterion": "정보보호 전문서비스 지정", "mandatory": false, "met": true, "rationale": "가점 항목-비필수"}
]
```

**Where remediation is recorded changes status.**
The same shortfall (Korean example "실적 1건 부족") yields different gate states depending on its location;
the author must select according to intent.

- **For CONDITIONAL-GO**: model remediation as `eligibility` (met:false, curable:true) +
  **accepted `bid_condition`**, `bid_decision:"conditional-bid"`, and `mode` draft/review.
  Do not model it as a document that must be present in today's submission. Condition deadlines must be future.
  ```json
  "mode": "draft",
  "bid_decision": "conditional-bid",
  "bid_conditions": [
    {"id": "B1", "owner": "사업총괄", "deadline": "2099-08-30T17:00:00+09:00", "accepted": true,
     "note": "컨소시엄 실적 보강으로 E-실적 기준 충족"}
  ],
  "eligibility": [{"id": "E1", "criterion": "실적 2건", "mandatory": true, "met": false, "curable": true}]
  ```
- **For legitimate NO-GO blocking**: if remediation is a mandatory document/manufacturer confirmation
  that **must be present in this envelope**, use `required:true, present:false` in `attachments`/`vendor_confirmations`.
  This hard-blocks submission even for `conditional-bid` (fail-closed, intentional).
- Separate **decision review** (`mode:"review"`) from **actual envelope submission** (`mode:"submission"`).
  Review mode does not enforce deadlines, eligibility-register presence, or submission rehearsals, fitting continuation decisions.

Unremediable shortfall: `curable:false` + `bid_decision:"no-bid"`.
For remediable gaps without accepted conditions, use no-bid or unaccepted conditional-bid (blocks),
never an optimistic unconditional bid.

## Explaining gate results — `proposal_gate.py --explain`

On blocking, output a Markdown action table explaining what to fix and why.
Route no-bid/intake-incomplete to **DECISION_MEMO** (valid nonparticipation/hold), not defects.
If unresolved conditions block conditional-bid, show the downgrade and recovery conditions
(preserved output label: `CONDITIONAL-GO → NO-GO 다운그레이드`).
`python proposal_gate.py --explain AUDIT.json`.

## Centralized completeness — `score_completeness.py` (create-best-proposal/scripts and root entry point)

Deterministically derive two axes from the same audit to eliminate reviewer-specific overall-score differences:
readiness (dimension fulfillment + gate) and quality
(with `--quality` metrics: `0.4·compliance + 0.3·claim_support + 0.2·(1−defect) + 0.1·rehearsal`).
**Only the gate determines final status**: open BLOCKING means NO-GO regardless of quality.
`python score_completeness.py AUDIT.json [QUALITY.json]`.

## Item-specific numeric matching and actual layout checks

Each integrated-gate child check has a 240-second limit.
Timeout/execution failure means `INVALID` (exit 2), never a pass.
Renderer version lookup and `pdfinfo` have 15-second limits;
on failure continue the existing PDF inspection path with a separate unverified record.
With `deck_check.py --png-dir`, the current conversion must supply a PNG for every page.
Exclude older PNGs as evidence; conversion failure, missing/empty files, or missing tools block and record
`render_succeeded:false`, `verified:false`. Human visual approval remains separate.

`numbers[].match_label` is an optional boolean (default false).
When true, at every body occurrence of `label`, compare the first number immediately afterward.
Only whitespace, colons, equals signs, table separators may intervene.
This blocks swapped values and inconsistent repeated summary/detail items.
Use the exact document label. False retains whole-body value-existence checks.
Amount variants must match the full multiplier (Korean examples: 37원 differs from 37억원).
Meta→audit preserves this field. Distinguish explicit minutes/seconds/hours/days/business days;
check spaced time units only when distinguishable from ordinary word prefixes.
Separately compare unitless cells/unsupported compound units with sources.
`tolerance` must be finite and nonnegative; NaN/Infinity cannot bypass sum/ratio checks.

For submission PPTX, `unified_gate.py --doc` directly runs `deck_check.py`.
Render success and human approval records remain required; automated layout passes do not replace them.

Layout rechecks include explicit solid RGB contrast on covers/dividers/table cells.
Block below 4.5:1 for normal text, 3:1 for 18pt+ or 14pt bold+.
Uncomputable combinations (theme colors, transparency, image backgrounds, partial overlap, inherited fonts)
remain uninspected and require rendered visual review.
