# Proposal skill v2: 10-run simulation report

Run date: 2026-07-18
Method: ten different raw scenarios were supplied to independent agent sessions. Each session read only
`create-winning-proposal` and its scenario, modified no files, and reported bid decisions, requirements/evidence,
structure/revisions, submission gates, and weaknesses in the skill itself.

## Results

| Run | Scenario | Decision | Key issues correctly identified | Skill issue found | Resolution adopted |
|---:|---|---|---|---|---|
| 1 | Public-sector AI consultation RFP | no-bid / review conditions | Missing performance/RTO evidence, 8-page allocation, overclaiming domestic-region scope | Insufficient distinction between missing material and ineligibility; unclear page semantics | Added `intake-incomplete`, separated eligibility/evidence, checked counted page components, prohibited expanding evidence scope |
| 2 | Private logistics optimization | conditional-bid | Blocked savings/innovation claims without baselines; pilot structure | Script always blocked conditional bids, required renders for analysis, falsely passed missing schema | Allowed approved conditional bids, added `artifact_required`, validated all required JSON fields |
| 3 | DB migration technical proposal | conditional-bid | PostgreSQL 15/16 and 12/16-week conflicts; missing zero-downtime evidence | Explicit versus inferred requirements, severity of technical contradictions, analysis render exception | Added requirement `basis`, Critical contradiction criteria, analysis-only render exception |
| 4 | Financial security questionnaire | conditional-bid | External API prohibition, blocked unverified security answers, direct XLSX responses | Proposal-centric structure; insufficient sensitive-evidence distribution guidance | XLSX security-questionnaire path, preservation of original rows/formulas/hidden sheets, redacted/controlled evidence |
| 5 | Ineligible public bid | no-bid | Did not use wording to conceal ISO/performance eligibility gaps | Full drafting possible even for clear no-bid; misunderstood internal approval; consortium exceptions | Immediate no-bid stop and decision memo, limits of internal approval, consider only permitted consortiums |
| 6 | Three-year price proposal | conditional-bid | 160 million KRW contradiction; three-year operations, discounts, VAT formulas | No standard price-calculation order | One-time + recurring cost × term → subtotal → discount basis/amount → tax → final total |
| 7 | Strict submission format | conditional-bid | DOCX preservation, signatures/attachments/PDF/A/page gates | Missing PDF/A profile/validation, signing authority, page semantics, timezone | PDF/A validation evidence, signature/seal types/authority, counted pages, deadline timezone, package checks |
| 8 | Amendment conflict | conditional-bid | Amendment priority for domestic region and 8/28; Q&A backup scope | Insufficient priority within a source tier and stale sweep | amendment>base, Q&A clarification rule, amendment acknowledgement, exhaustive obsolete-value search |
| 9 | English overseas proposal | no-bid / review conditions | Removed 100% secure, 40% guarantee, zero downtime; identified 24/7 gap | Insufficient safe replacement wording and claim-severity examples | Expanded unsafe→bounded evidence replacement table and claim classification |
| 10 | Existing proposal review | blocked | placeholder/conflict marker, 50/35 personnel, scope contradiction, security approver | Missing review-only standard, unverifiable-item handling, minimum revision fields | Proportionate review path, explicit validation scope, minimum revision rules for fact/owner/deadline/approval/recalculation |

## Recurring issues

1. **Ambiguous bid classification**: ineligibility, missing evidence, and general missing information were mixed.
   - Resolution: defined `intake-incomplete / bid / conditional-bid / no-bid` and curability/owner/deadline/approval conditions.
2. **Gate/document-rule mismatch**: conditional bids and analysis-only work were falsely blocked.
   - Resolution: supported approved conditional bids and `artifact_required: false`.
3. **False pass on missing JSON**: omitted lists could be treated as empty arrays.
   - Resolution: required top-level fields and `checks`, and added an example schema.
4. **Document-type bias**: XLSX and short review paths were weaker than DOCX proposals.
   - Resolution: added security-questionnaire/XLSX and proportionate review-only paths.
5. **Missing submission details**: page semantics, deadline timezone, signature authority, and PDF/A validation were absent.
   - Resolution: strengthened the strict submission checklist.
6. **Insufficient conflicting-source priority**: amendment and Q&A roles were unclear.
   - Resolution: defined amendment, Q&A, template, evaluation-sheet roles and stale-value sweep.
7. **Insufficient price/overclaim handling**: no exact calculation order or safe replacements.
   - Resolution: added price-calculation order and unsafe-claim replacement table.

## Regression validation

- `quick_validate.py`: `Skill is valid!`
- `python -m unittest discover -s skills/create-winning-proposal/scripts -p test_*.py -v`: 5 tests passed.
- Regression cases: valid submission pass, approved conditional-bid pass, analysis-only render exception,
  missing-schema block, multiple-failure block.

## Remaining limitations

- Not validated against real company RFPs, winning/losing proposals, branded DOCX files, price lists, or approval policies.
- Actual Korean page rendering in Microsoft Word and PDF/A validation require supplied templates.
- Legal, security, and price approvers must be designated by each organization.
- Korean automated style checks remain deterministic rules until an organizational glossary and correct/error corpora exist.
