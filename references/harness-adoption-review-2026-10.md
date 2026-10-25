# Production harness comparison and selective adoption review

## Scope and decision criteria

Against ProposalSkills `52639d1382053c46d3eb9480e4ac130aa19d5bdb` as of 2026-10-24,
reviewed the supplied AI-Harness stage execution, document production, and handoff methods.
The comparison repository is private. No original text, code, or internal material is reproduced;
necessary operational concepts were independently written for ProposalSkills' existing check tools.
External claims about the comparison target's products, research, or tool support are not evidence for this adoption.

Criteria: duplication of existing functionality, actual execution, submission-decision reliability,
model/host neutrality, and procedural cost. Distinguish instruction improvements from runtime features.

## Already covered by the current structure

| Layer | Implementation/guidance inspected | Decision |
|---|---|---|
| Entry/scope | Flagship Full/Pink/Red/Gold/Review-only paths; explicit sibling invocation | Do not replace with a generic harness development loop |
| Staged production | Intake/bid → ledgers/skeleton → body → production/checks → audit/submission | Reuse Phase A–E rather than add a stage runner |
| Reproducible artifacts | `build_deck.py`, `deck_profiles.py`, specified output | No reason to add model-controlled free coordinates |
| Actual validation | `deck_check.py`, `quality_gate.py`, `check_numbers.py`, `proposal_gate.py`, `unified_gate.py` | Retain concrete checks rather than unsupported self-evaluation |
| Approval binding | Render/package/attachment hashes; separate rendering/human visual approval; distinct audit-only state | Never replace with an external harness's generic PASS |
| Distribution/regression | Shared skills + host manifests; install validation; root test discovery | No new host/dependency/automatic installation |

Primary evidence: [flagship](../skills/create-best-proposal/SKILL.md),
[unified gate](../skills/create-best-proposal/scripts/unified_gate.py),
[checker](../skills/create-proposal-document/scripts/deck_check.py),
[schema/submission contract](../skills/create-winning-proposal/references/audit-schema.md),
[test discovery](../test_skill_scripts.py), [installer](../install_skill.py),
[packaging](../package_plugin.py).

Also inspected meta→audit input types/review-record preservation, generator error returns/specification display,
profile/buyer-spec parsers, and joint three-skill installation/distribution linkage read-only.
No additional reproducible defects beyond execution-reliability items were confirmed in this scope.
This does not guarantee a defect-free repository or actual plugin invocation on external hosts.

## Selections

| Candidate | Decision | Adoption/exclusion reason |
|---|---|---|
| Render representative slides before full production | Conditional adoption | Only uncertain new designs; no mandatory fixed 3 slides or per-task extra approval |
| Write → check → fix → recheck | Strengthen | Reuse tools; specify rechecks for RFP/numerical/visual/attachment changes |
| Independent evaluation | Strengthen | Specify separate reviewer/context conditions in Red and limitations without tools; never replace human approval |
| Repeated-failure limit | Adopt | After 3 same-cause failures, report hypothesis/evidence/blocker; repetition cannot cure missing tools/approval |
| Session handoff/failure learning | Conditional adoption | Existing records only for long work; hashes/commands/uninspected/next work, checked against files on resume |
| Learning logs/progress files every time | Exclude | Cost for short reviews; risk customer material remains in installation/public repository |
| Comparison target's JavaScript loop runner | Exclude | Inspected implementation prints stage names; no test/check calls or actual retry control |
| Fixed context-usage threshold | Exclude | Host observation/behavior differences unverified; use consistency and transferable evidence |
| Generic PASS/automatic visual approval | Exclude | Weaker than existing actual-artifact/evidence/human-approval submission contract |

Execution guidance appears once in [iteration, revalidation, and handoff](../skills/create-best-proposal/references/iteration-and-handoff.md),
linked from flagship/master playbook.

## Documentation inconsistency corrected alongside this work

The master playbook listed `READY/CONDITIONAL-GO` together for Gold, risking confusion between internal-only
conditional status and submission approval. Gold now explicitly requires `SUBMISSION-READY` for actual file/bundle;
`AUDIT-VALID`, `DRAFT-READY`, and `REVIEW-READY` are separated as non-submittable.
Existing gate code already enforces this boundary; status vocabulary is unchanged.

## Runtime reliability strengthened

- Consolidated three `unified_gate.py` child checks into a shared execution function with 240-second limits
  and `INVALID` on timeout/execution failure, reducing indefinite validation waits.
- Limited `deck_check.py` version/PDF information queries to 15 seconds each. Optional metadata failure is
  disclosed as unknown while existing PDF page comparison remains. Existing regex-based PDF-structure limits remain.
- Requested PNGs are newly converted in a temporary folder; check success code/per-page files/nonempty output
  before copying. Old PNGs can no longer fill missing pages. Missing PNG tools/conversion failure/incomplete
  output block. Old files are reported, not deleted.
- `test_gate_integrity.py` covers timeouts/execution failures/return-code propagation, partial PNGs/old PNG
  contamination/normal conversion/optional-query failures. Human visual-approval fields are never automatically promoted.
- Full regression exposed an existing environment-dependent NUL attachment-path failure: some environments
  classified it as missing file rather than path-resolution failure. Reject NUL explicitly at the input boundary
  rather than depend on filesystem calls, preserving consistent error classification.

## Validation scope and limitations

Existing `test_skill_schema.py` checks document links/routing/install copies/distribution ZIP linkage.
Run root tests and diff whitespace checks per repository instructions and record actual results in completion reports.
This document does not assume passing results before execution.

This change strengthens instructions/documentation and execution reliability in existing check processes.
It implements no automatic orchestrator or new audit schema and proves no improvement in actual customer
proposal visual quality/win rates, independent-evaluation execution, or final PowerPoint inspection.

### Execution results (2026-10-24)

| Check | Result |
|---|---|
| 10 new error paths + 19 existing skill-schema cases | 29 passed, exit 0 |
| NUL path regression + new error paths | 11 passed, exit 0 |
| Root unittest discovery | 501 run, 500 passed/1 skipped, exit 0 (110.118 seconds) |
| Flagship quick_validate | `Skill is valid!`, exit 0 |
| git diff whitespace check | exit 0 |
| Existing hygiene patterns on new documents | 0 findings |

Initial default-temp permission failure was resolved with a separate writable temporary path.
The skill validator's default cp949 read was resolved using `PYTHONUTF8=1`, without global-setting changes.
Reproduced the NUL path failure on the unchanged original before fixing input validation.
Quiet full-test output did not show the skip reason. LibreOffice was separately absent from the environment,
so actual LibreOffice→PDF→PNG rendering and PowerPoint visual inspection were not performed.
New render-error tests use mock tools to check error propagation.
Remote push/PR and updates to existing skill installations were outside this local validation.

### Update re-review (2026-10-24)

Re-reviewed 12 commits from `189c75a` to `45664d3`. The comparison target replaced its output-only runner
with a checker featuring actual test commands, exit-code records, evidence-hash chains, code-change detection,
CI reruns, and environment diagnostics. The earlier skeleton-runner assessment applies only to that earlier version.
Claude-only hooks/read tracing/stage JSON ledgers duplicate existing unified gates/CI and are not imported.
Apply only the principle of binding inputs/artifacts to actual check results through existing tools.

The same review of ProposalSkills reproduced synthetic cases where changing document/audit during child checks
still returned `SUBMISSION-READY`. Compare start/end document/audit hashes; changes/deletion/read failures
become `INVALID`. Move attachment comparison after audit evaluation. Preserve normal controls, existing
unchanged-input quality-failure decisions, human approvals, existing audit schema, and actual-file hash binding.

Validate with `test_gate_integrity.py` change/deletion + quality-failure combinations, audit-only, and attachment
changes. Record final actual results in completion reports. This provides neither file locks/OS isolation nor
immutability throughout execution, and is not evidence of improved proposal persuasiveness.

### Test-strength and Windows update re-review (2026-10-25)

Compared 18 changed files across 3 commits from `45664d3` to `6bc8e25`.
Main changes: Windows read-path normalization/actual Bash diagnostics, improved hook path/command patterns,
real CLI/hook E2E, and retry/error-path tests. Latest documented coverage belongs to upstream; do not transfer
it as ProposalSkills coverage.

| Candidate | Selection |
|---|---|
| Windows path conversion/Bash diagnostics/Claude read hooks | Exclude. ProposalSkills uses Python Path/argument arrays without host hooks |
| Validation beyond one OS | Retain existing Ubuntu 24.04/26.04/Windows × Python 3.10/3.12 matrix |
| Actual installed/archive execution linkage | Existing `PortableExecutionTests` covers Korean/space paths, separate working folders, isolated Python; no duplicate |
| Failure → fix → revalidation E2E | Adopt. Actual unified-gate CLI sequentially verifies block/recovery for numerical errors, revoked approval, changed attachments |
| Symbolic-link boundaries | Adopt. Tests allow valid in-bundle targets and block external/broken links |
| Targeted mutation validation | Privately remove check functions to confirm existing tests fail; no new runner/dependency distributed |

New lifecycle tests verify incorrect amounts remain blocked even with updated document hashes.
Then rerun numerical fixes, approval restoration, and attachment-hash updates individually to ensure old PASS/FAIL
is not reused. Approval fields are synthetic fixtures, not evidence of actual human visual review.
Where Windows cannot create symlinks, skip only those tests and verify in Linux CI.
No product-code/audit-schema/submission-contract changes. UI is outside scope.
