# Verdict vocabulary: one meaning for every tool's result

The tools print their own words (PASS, 통과, CLEAN, VALID, READY). When results are reported together, translate them
into four verdicts so a reader never mistakes "not checked" for "passed".

| Verdict | Meaning | Never means |
|---|---|---|
| PASS | The check ran on the delivered file and found nothing blocking | The content is true, persuasive or approved |
| FAIL | The check ran and found a defect | (only the check's own scope) |
| BLOCKED | The check ran, or could not proceed, and submission must not continue until a named cause is resolved | A permanent failure |
| NOT VERIFIED | The check did not run, was unavailable, was skipped, or could only partly run | PASS (a missing tool, an unread file and a skipped suite are all NOT VERIFIED) |

Rules: report the verdict and the exact scope ("layout lint and LibreOffice render, slides 1-17"); never combine
NOT VERIFIED into PASS; a PASS recorded for an older version of a file is NOT VERIFIED for the current one
(`evidence_chain.py rerun` lists those); style and heuristic checks (`plain_language_check.py`, `deck_story_check.py`)
produce leads for a person, not PASS or FAIL on quality.

## Mapping of tool output

| Tool | Prints | Verdict |
|---|---|---|
| `proposal_gate.py` | `READY` / `BLOCKED` | PASS / BLOCKED |
| `unified_gate.py` | exit 0 / `BLOCKED` lines | PASS / BLOCKED |
| `deck_check.py`, `quality_gate.py`, `check_numbers.py` | `통과` / `차단` / `[NOT INSPECTED]` | PASS / BLOCKED / NOT VERIFIED |
| `sensitive_scan.py` | `CLEAN` / `FINDINGS` / `INCOMPLETE` | PASS / FAIL / NOT VERIFIED |
| `skill_audit.py` | `CLEAN` / `FINDINGS` | PASS / FAIL |
| `verification_report.py` | `VALID` / `INVALID` | PASS / FAIL (of the report, not the deliverable) |
| `deck_story_check.py`, `deck_stage_gate.py` | `PASS` / `BLOCKED` | PASS / BLOCKED |
| `edit_preservation.py` | `PASS` / `REVIEW` / `BLOCKED` | PASS / NOT VERIFIED (a person must read it) / BLOCKED |
| `xlsx_check.py` | `PASS` / `BLOCKED`, warning "never calculated" | PASS / BLOCKED / NOT VERIFIED for never-calculated formulas |
| `cross_format_numbers.py` | `PASS` / `BLOCKED`, `[DIVERGENT]` | PASS / BLOCKED |
| `retry_guard.py` | `DONE` / `CONTINUE` / `STOP-*` | (loop control, not a verdict on the deliverable) |
| `evidence_chain.py` | `OK` / `BROKEN`, `RERUN:` | PASS / FAIL for the log; stale records are NOT VERIFIED |
| `handoff_lint.py` | `OK` / `PROBLEMS` | PASS / FAIL (`STALE` rows are NOT VERIFIED) |
| `task_contract.py` | states `Verified` / `Failed` / `Blocked` / `Not Verified` | the same four verdicts |
| `merge_guard.py` | `READY` / `NOT READY` | PASS / BLOCKED (advisory only) |
| `gate_mutation_probe.py` | `KILLED` / `SURVIVED` | PASS / FAIL (a survived mutation is a test gap) |

An exit code of 2 from any of these means the tool could not do its job (usage error, unreadable or protected file):
that is NOT VERIFIED, never a pass.
