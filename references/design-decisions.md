# Deliberate decisions (read before filing a defect or an issue)

This file lists behaviours and omissions that look like defects or gaps on a first read but are decisions, each with the
reason, where it lives in the code, and the test that pins it. A reviewer, an audit, or a contributor who finds one of these
should report it only if the stated rationale no longer holds, and the report should say which sentence is wrong.

When a decision changes, edit its entry in the same pull request. `python repo_records.py` (also run by the test suite)
checks that every entry names all five fields, that each path exists, and that each pinning test exists.
Gate-hardening rounds and their longer reasoning stay in [gate-hardening-2026-09.md](gate-hardening-2026-09.md).

### D01 Only the public-sector profile ships

- **Decision:** `sectors/` holds the public-sector profile and the classification axes. There are no education, healthcare, enterprise or finance profiles.
- **Why:** Sector guidance cannot be verified inside this repository, and an unverified profile lends false authority to what it says. Classification in the audit `context` changes gate requirements instead, which is checkable. Issues #8 and #10 asked for four packs and were closed as not planned on 2026-11-24.
- **Revisit only if:** a practitioner supplies de-identified material for a sector and reviews the profile, and the pinning test is updated in the same change.
- **Lives in:** `skills/create-winning-proposal/references/sectors/README.md`, `references/gate-hardening-2026-09.md`
- **Pinned by:** `test_context_classification.py::SectorDocumentationTests.test_only_the_public_profile_ships`

### D02 A simulation artifact never clears a submission

- **Decision:** `artifact_mode: simulation-only` blocks `mode: submission` even when every other check passes.
- **Why:** Simulation artifacts exist for internal inspection; promoting one to submission readiness would present a rehearsal as the real file.
- **Revisit only if:** a real artifact class is introduced that a simulation can honestly stand in for.
- **Lives in:** `skills/create-winning-proposal/scripts/proposal_gate.py`
- **Pinned by:** `test_gate_integrity.py::StageAndLabelTests.test_simulation_only_cannot_clear_submission`

### D03 A replaced gate never clears an audit

- **Decision:** When `PROPOSAL_GATE_PATH` or `QUALITY_GATE_PATH` points at a file that differs from the packaged gate, `unified_gate.py` warns, refuses a `mode: submission` audit, and never reports `AUDIT-VALID` or `SUBMISSION-READY`. A byte-identical copy is allowed.
- **Why:** An environment variable would otherwise let any script replace the decision maker, and an exit code would then look like a verdict.
- **Revisit only if:** overrides gain a signature or a recorded hash that identifies a reviewed gate.
- **Lives in:** `skills/create-best-proposal/scripts/unified_gate.py`
- **Pinned by:** `test_audit_remediation.py::GateOverrideTests.test_replaced_gate_cannot_clear_a_submission_audit`, `test_audit_remediation.py::GateOverrideTests.test_byte_identical_copy_is_allowed`

### D04 The hook guard is a lexical, opt-in guardrail that does not guess

- **Decision:** `hook_guard_bash.py` judges the command text, resolves variables assigned in the same command, and nothing more. A variable it cannot see (`$PY script.py`, `rm -rf "$BUILD_DIR"`) is allowed, and the script is never installed automatically.
- **Why:** The environment and earlier tool calls are invisible to it. Guessing would deny routine commands, and a guard that cries wolf gets switched off. Real approval and host permissions remain the boundary.
- **Revisit only if:** the host passes the environment or the shell state to the hook.
- **Lives in:** `hook_guard_bash.py`
- **Scope of protected folders:** system folders are protected at any depth; a user profile is protected itself and one level below it. A build or temp folder deeper inside a profile, or anywhere on a data drive, is allowed, because agents clean those up constantly.
- **Pinned by:** `test_audit_residual_risks.py::HookEvasionTests.test_unknown_variables_are_not_guessed`, `test_hook_guard_targets.py::ProtectedTargetTests.test_build_and_temp_folders_inside_a_profile_stay_allowed`

### D05 The strict JSON reader is copied into each script on purpose

- **Decision:** `_unique_json_members` (reject duplicate keys, including nested and identical-value ones) exists as a copy in eight scripts instead of one shared module.
- **Why:** Each skill script must run alone after installation, and the mutation catalog anchors on the text of each copy. Drift is caught by a test that runs every copy against the same cases.
- **Revisit only if:** scripts stop being installed and run as standalone files.
- **Lives in:** `skills/create-best-proposal/scripts/unified_gate.py`, `skills/create-winning-proposal/scripts/proposal_gate.py`
- **Pinned by:** `test_audit_maintenance.py::MaintenanceContractTests.test_copies_of_the_json_guard_all_reject_duplicates`

### D06 Dependency minimums are tested floors and are not raised automatically

- **Decision:** `requirements.txt` states the lowest versions the deck tests pass on, a `dependency floor` CI job installs exactly those, and Dependabot raises a minimum only when the declared range no longer allows the new version.
- **Why:** Pillow 13 requires Python 3.11 while this project supports 3.10, so an automatic minimum bump (PR #63) would have dropped a supported version.
- **Revisit only if:** the supported Python range changes; update the floor job and `requirements.txt` together.
- **Lives in:** `requirements.txt`, `.github/dependabot.yml`, `.github/workflows/ci.yml`
- **Pinned by:** `test_audit_maintenance.py::MaintenanceContractTests.test_dependency_updates_cover_packages_and_actions`, `test_audit_remediation.py::TestRunHonestyTests.test_ci_sets_a_skip_limit_and_the_requirement_floor_matches_its_job`

### D07 `merge_guard.py` is advisory; branch protection enforces

- **Decision:** `merge_guard.py` reports whether the seven required checks passed, and the same seven checks are required by the `main` branch protection, which applies to administrators too.
- **Why:** A script can be skipped or edited by whoever runs it; a repository setting cannot be bypassed from a pull request.
- **Revisit only if:** the CI matrix changes; the test requires the list in the script to match the workflow.
- **Lives in:** `merge_guard.py`, `.github/workflows/ci.yml`
- **Pinned by:** `test_session_guardrails.py::MergeGuardTests.test_required_checks_match_ci_matrix`

### D08 The review tools run locally, not in CI

- **Decision:** `revert_proof.py`, `gate_replay.py` and `trigger_eval_run.py` are run by the person preparing a change. CI does not call them, and `trigger_eval_run.py` does nothing without an explicit `--yes`.
- **Why:** Every extra CI job multiplies across the six-platform matrix. The trigger run spends a model account and is not deterministic, so it is a measurement for a person to read, not a gate.
- **Revisit only if:** a deterministic, cheap subset can be run on one platform.
- **Lives in:** `revert_proof.py`, `gate_replay.py`, `trigger_eval_run.py`
- **Pinned by:** `test_trigger_eval_run.py::LocalOnlyTests.test_ci_does_not_run_the_local_review_tools`, `test_trigger_eval_run.py::PlanTests.test_nothing_runs_without_explicit_consent`
