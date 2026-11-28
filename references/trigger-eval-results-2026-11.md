# Skill trigger measurement, 2026-11-24 (baseline)

First measurement made with `trigger_eval_run.py` on Claude Code 2.1.331, Codex CLI 0.171.0 and Grok Build 1.0.92. Each prompt in
[trigger-eval-cases.json](trigger-eval-cases.json) ran three times per CLI. The skills under test were the working tree at the time
(`proposal-skills` 1.3.0). It is a baseline to compare later description edits against, not a pass mark: the model is not
deterministic, and three runs per prompt only separate clear cases from borderline ones.

How to read it: a should-trigger prompt passes when its skill or the entry skill (`create-best-proposal`) was used in at least two of
three runs; a near-miss prompt passes when a repository skill was used in at most one of three. Claude counts only a Skill tool call.
Codex and Grok have no such tool, so a read of `<skill>/SKILL.md` counts, which a model can also do while browsing the workspace.

| CLI | should-trigger passed | near-miss passed | errored runs |
|---|---|---|---|
| Claude Code | 8 of 10 | 8 of 8 | 0 |
| Codex | 8 of 10 | 8 of 8 | 0 |
| Grok Build | 10 of 10 | 7 of 8 | 0 (3 near-miss runs timed out while it waited for an answer to its own question) |

## Prompts that did not pass

| CLI | Prompt | Result |
|---|---|---|
| Claude Code | Review my proposal before submission | no skill in 3 runs; it listed files, read `rfp.md`, and answered |
| Claude Code | I only need the outline and slide layout for the proposal | no skill in 3 runs |
| Codex | Use create-winning-proposal to build the evidence ledger | a skill file was read in 1 of 3 runs |
| Codex | I only need the approval chain and the audit JSON | a skill file was read in 1 of 3 runs |
| Grok Build | Plan a team offsite (near miss) | the proposal skill was read in 2 of 3 runs in the first measurement. Repeated 8 times per prompt later: see "Follow-up" |

Every other prompt passed. Most passed in all three runs, including the six that should reach the entry skill on Grok and Codex.
Two were not unanimous: Claude used the entry skill in two of three runs for "Is this bid a go or no-bid?", and Codex used a skill
in two of three runs for "Use create-proposal-document to lay out only the slides".

## What this does and does not show

- Both Claude misses are plain requests with no proposal attached. A model may reasonably look for the material first, so these are
  candidates for a wording change, not proof of a defect. Test a candidate description with the same tool before editing one.
- The two explicit-only skills (`disable-model-invocation`) are not meant to start on their own. Their prompts are judged by whether the
  entry skill or the named skill was used, which is how the Codex rows above were counted.
- Codex and Grok read skill files while browsing, so a read is weaker evidence than Claude's Skill tool call. The follow-up below
  separates the part the description earns from the part browsing and the skill name explain. Claude's skills were loaded as a
  session plugin, so they were not files to browse.
- Early versions of the tool measured something else (skills copied into the workspace for Claude, a proposal file in every
  workspace). Those runs are not reported here.

## Follow-up: is it the description? (2026-11-25)

Control: the same should-trigger prompts, three runs each, with every skill description replaced by "Reference material." (names and
paths kept; `--control neutral-descriptions`). Compared with the real-description run above:

| CLI | mean use rate, real descriptions | mean use rate, neutral descriptions |
|---|---|---|
| Codex | 0.83 | 0.57 |
| Grok Build | 1.00 | 1.00 |

- **Codex**: the description earns part of it. Generic requests that name no skill fell from 1.0 to 0.0 or 0.33 ("Write a technical
  proposal for this RFP", "Is this bid a go or no-bid?", "Build the compliance matrix for the tender", "Review my proposal before
  submission"). Requests that contain the skill's own name or the words "gate" and "technical-response" kept their rate, so there the
  name and workspace browsing explain the read. Rows that named a skill outright were not helped by the description.
- **Grok Build**: no difference. Its first tool call was `read_file` in every control run, with or without a description. Grok's
  should-trigger result therefore does not show that the description works; it shows that Grok opens skill files. Do not use Grok's
  10 of 10 as evidence for a wording change.
- **Grok near misses, repeated**: 8 runs for each of the 8 near-miss prompts (64 runs). A repository skill was read in 1 run (the "Plan
  a team offsite" prompt, 1 of 8). The earlier 2 of 3 on that prompt was variance; the false-trigger rate observed here is 1 in 64.
  13 of the 64 runs, all on "Plan a team offsite", timed out while Grok waited for an answer to its own question; they are counted
  as no skill used, as in the first measurement.

Not established: why Grok reads skill files in an untouched workspace (it may be its listing of `.agents/skills`), and any
comparison for Claude, which a neutral description cannot fake because only a Skill tool call counts. Three runs per prompt.

## Manual runs in the real CLIs (2026-11-25)

Six prompts, each run by hand in a new session of Codex and Grok Build, in a workspace holding only the three skills and the synthetic
`rfp.md`. The prompts name no file and no skill; each asks the CLI to write a record of what it opened, ran and decided. The records
were checked against each CLI's own session log. T1 to T3 should use the skill; T4 to T6 should not.

| Prompt | Codex | Grok Build |
|---|---|---|
| T1 technical proposal outline and strategy chapter | skill used, 2 of 2 runs; read `SKILL.md` only | skill used; read the playbook and reference files of all three skills |
| T2 bid or no-bid | skill used; read `SKILL.md` only; **decision differs from the skill's rule** | skill used; read the playbook and reference files; followed the rule |
| T3 compliance matrix skeleton | skill used; read `SKILL.md` only | skill used; ran `scripts/bulk_matrix.py` |
| T4 Python `AttributeError` question | no skill file opened | no skill file opened |
| T5 team workshop schedule | no skill file opened | no skill file opened |
| T6 one-sentence translation | no skill file opened | no skill file opened |

- Both CLIs picked the skill on their own for all three proposal prompts and none of the three unrelated ones. Codex receives a list of
  skill names and descriptions at the start of a session, so opening `SKILL.md` is its normal way of using one.
- They differ in how far they follow it. Codex stopped at `SKILL.md` in all four proposal runs. In T2 it recommended a conditional bid
  with no owner or deadline, which the skill's own rule does not allow without them; Grok, which read the playbook, answered
  `intake-incomplete`. The rule was in the playbook but not in `SKILL.md`; the entry file now states it.
  After the entry file stated it, one more Codex T2 run (opening `SKILL.md` only, as before) answered `intake-incomplete`.
- The answer carried no `DECISION_MEMO_ONLY` label. Phase A now names it. Three more Codex T2 runs in clean sessions (each opened `SKILL.md`
  only; session logs checked) all answered `intake-incomplete` with the `DECISION_MEMO_ONLY` label and wrote no proposal body.
  Before the change: 1 run, no label. Three runs show the direction, not a rate.
- Claude Code (2.1.331, headless `claude -p`, 2026-11-25) ran the same T2 prompt three times in a separate workspace that held `rfp.md` and the
  three skills under `.claude/skills`, with `--setting-sources project` so the globally installed plugin copy was not loaded (the session's
  skill list showed only the workspace skills) and `--allowedTools Read,Glob,Grep,Skill`. All three answered `intake-incomplete` with the
  `DECISION_MEMO_ONLY` label and no proposal body. Each opened `SKILL.md` with Read, not the Skill tool; run 1 also opened
  `create-proposal-document/references/bid-and-submission.md`. Runs 2 and 3 also ran one read-only `Bash` listing (`find`/`ls`/`git log`).
  Run 1 noted that the RFP looked like test input.
- Claude Code baseline, same setup but with the entry `SKILL.md` as it was before the label sentence (it already had the `intake-incomplete`
  rule from the first fix): 5 runs. Conclusion `intake-incomplete` 2/5, `DECISION_MEMO_ONLY` label 1/5, conditional bid 3/5. With the label
  sentence, 5 runs: `intake-incomplete` 5/5, label 5/5, conditional bid 0/5. Five against five is not significant for the conclusion
  (one-sided Fisher p about 0.08); the label difference is clearer but the sample is small. The sentence may also have made the
  `intake-incomplete` path easier to find, so it is not shown to affect only the label.
- Grok Build, three T2 runs after the change in clean sessions: `intake-incomplete` with `DECISION_MEMO_ONLY` each time. This is **not**
  evidence that the new sentence caused it. Grok keeps a persistent memory under its own home directory, and that memory held notes from
  the earlier T2 runs, including a note that the earlier decision was `intake-incomplete (DECISION_MEMO_ONLY)`. The third run read those
  notes and searched `results/` for earlier outputs. Grok also ran `unified_gate.py` in runs 2 and 3 and left a `decision-audit.json` in the
  workspace; a third run that read the file left by run 2 was discarded and rerun after the file was removed. Grok results after the first
  session cannot be treated as independent runs. A clean comparison needs Grok's memory cleared first, which was not done here.
- The records matched the logs on what mattered (which skill files were opened), but a CLI's record can leave out steps: one Codex record
  omitted a failed first read and two listing commands, and one Grok session answered a prompt meant for the other CLI before the rerun.
  Read the log, not only the record.
- One run per cell, except Codex T1. It shows direction, not a rate. Not covered: an empty workspace, other wordings, Claude Code.
- Two runs were discarded and redone: a Grok session that had run the other CLI's prompt first, and a Codex T3 run in a workspace that still
  held Grok's output.

## Answer contract and checker (2026-11-26)

Sampling cannot make a model's output certain, so the entry `SKILL.md` now carries a bid-decision answer contract (first line
`BID_DECISION: ...`, the `DECISION_MEMO_ONLY` label for no-bid and intake-incomplete, `REQUIRED_INPUTS`, and per-condition
owner / ISO deadline / acceptance), and `scripts/check_decision_answer.py` fails any answer that breaks it. The checker is
deterministic and pinned by `test_decision_answer.py`; it checks form and consistency, not the judgment.

Acceptance rule, fixed before the run: five Claude Code T2 runs on the new `SKILL.md`, graded by the checker with
`--bidder-material absent`; accept at 4 of 5; one check, no repeats.

Result: 3 of 5 passed (runs 3, 4 and 5). Runs 1 and 2 answered "conditional bid" and did not follow the contract because they never
opened the entry `SKILL.md`: they listed the skill folder and read one reference file (`capture-and-positioning.md`) and answered
without the skill's rules. The three runs that loaded the skill all passed, and runs 4 and 5 ran the checker on their own answer
before replying. So the rule works when the skill is loaded, and the remaining failure is the skill not being loaded at all,
which text inside `SKILL.md` cannot fix. The acceptance rule was not met and is recorded as not met.

What this leaves open: how often a host skips the entry file. The earlier 10 Claude Code runs all opened it; these 5 did in 3.
The skill's `description` is the only text a host shows before the file is opened, so it now ends its routing sentence with
"For any bid decision or RFP judgment, open this SKILL.md first and follow its answer contract; never answer from a reference file
alone." (pinned by a test). Same rule as above, fixed beforehand, one check: five more Claude Code T2 runs, graded by the checker with
`--bidder-material absent`, accept at 4 of 5. Result: 5 of 5 passed, and all five called the Skill tool for `create-best-proposal`
before reading the RFP. Counted per check: 3 of 5 before the description line and 5 of 5 after. Five against five is small and not a rate; this is the evidence, not proof. Codex and
Grok were not run on the contract or the description line.

## Not re-measured after the acceptance bullet (2026-11-26; see the 2026-11-27 section below for a later check)

`create-best-proposal/SKILL.md` gained one bullet in the answer contract: `accepted: yes` must record an acceptance seen in the supplied
material, otherwise the decision is `intake-incomplete`. The five-run Claude Code check above was **not** repeated. The prompt text of
that manual run is not kept in this repository, so a new run would use a different prompt and could not be compared with 5 of 5. The
bullet only changes the conditional-bid path; the measured path (no bidder material, `intake-incomplete`) is unchanged. The sentence is
pinned by `test_skill_schema.py::EntrySkillBidDecisionTests`. A future check should save its prompt next to its result.

## Holdout baseline and the acceptance bullet re-checked (2026-11-27)

Claude Code 2.1.332, Codex CLI 0.172.0, Grok Build 1.0.92; the skills at `main` after PR #78 (`proposal-skills` as then released).

**Holdout baseline.** `trigger_eval_run.py --set holdout --runs 3` (5 prompts, 45 model calls, `--timeout 150`). These prompts were written
after the description was last edited and were not used to tune it. Pass rules as in the first measurement.

| CLI | should-trigger passed | near-miss passed | notes |
|---|---|---|---|
| Claude Code | 2 of 3 | 2 of 2 | "Check that our response answers every requirement in the RFP": skill in 0 of 3 runs |
| Codex | 2 of 3 | 2 of 2 | "We received this tender notice. Should we respond to it?": 0 of 3, all three runs timed out; the RFP-check prompt 2 of 3 |
| Grok Build | 3 of 3 | 2 of 2 | 5 of the 6 near-miss runs timed out; counted as no skill. Grok opens skill files in a neutral-description control too, so this is not evidence for the wording |

The two misses are plain requests that name no skill and no file, like the two Claude misses in the first measurement. They are a candidate
for a wording change and are **not acted on here**: editing the description until these pass would turn the holdout into tuning data.
If the description is changed, write new holdout prompts first. Three runs per prompt; this is a baseline, not a rate.

**T2 on the current entry file, Claude Code.** Rule fixed before the run: five headless runs, graded by `check_decision_answer.py
--bidder-material absent`, accept at 4 of 5. Prompt: T2 in [manual-eval-prompts.md](manual-eval-prompts.md) without its record tail (the answer is read
from stdout). Setup as before: workspace with `.claude/skills`, `rfp.md`, `--setting-sources project`, `--allowedTools Read,Glob,Grep,Skill`.
A first set of five was discarded: the script's copy of `rfp.md` used a wrong path, so the file may not have been in the workspace (not
verified; all five answered `intake-incomplete`). Second set, with `rfp.md` confirmed present: **5 of 5 passed** (one answer was wrapped in a code fence, which the checker tolerates).
This covers the path the acceptance bullet leaves unchanged (no bidder material); it does not exercise the bullet itself, which only applies to a conditional bid.

**T2, Codex** (`codex exec`, read-only sandbox, `.agents/skills`, 240 s limit, 3 runs): one run answered and passed the checker; two ended at the limit
with no final answer, so there is nothing to grade. Inconclusive. **Grok** was not run: its persistent memory holds notes from earlier T2 runs, so a run would not be independent, and clearing it was not done.

**T2, Codex, rerun** (`--timeout 600`, 3 runs): runs 1 and 2 passed the checker; run 3 had no answer because Codex's sandbox helper failed ("Failed to create unified exec process"), an infrastructure error, not a contract result. Across both sets: 3 graded runs, all passed; 3 runs produced no answer (2 timeouts, 1 sandbox failure). That is 3 of 3 where graded, not 3 of 6.

## Second holdout, and a description edit that was tried and reverted (2026-11-27)

The five holdout prompts above had been read and discussed, so they were moved into the dev lists in `trigger-eval-cases.json` (except "We received this tender notice. Should we respond to it?", which the dev lint rejects because the description has no matching route term; it is listed under `known_misses` in the cases file, which the lint and the runner skip, so the gap stays visible), and five new
holdout prompts were written before any further edit. Same CLIs and versions, 3 runs per prompt, `--timeout 300`.

| Description | Claude Code | Codex |
|---|---|---|
| Unchanged | 4 of 5 prompts pass; "Verify that every mandatory requirement in this RFP is covered by our submission": 0 of 3 | 5 of 5 pass (one prompt at 2 of 3) |
| Edited: added "tender" and "requirement-coverage check" to the route list | 4 of 5; the same prompt still 0 of 3 | 4 of 5; "Get our bid package ready to submit next week" 1 of 3, 2 runs timed out |

The edit did not fix the targeted miss and did not improve either CLI; the Codex drop comes with two timeouts, so it is mostly noise, but there is
no gain to weigh against it. **The edit was reverted; the description is unchanged.** The miss (a plain request, no skill named, phrased as
verifying coverage of an RFP) remains open, along with the first one. Grok was not run on the new set. Three runs per prompt is evidence, not a rate.
The holdout used here is spent in the same way as the first: its prompts are now in the dev lists, and a third holdout (3 should-trigger, 2 near-miss, written without running them) replaces it. That third set has not been measured, so there is no baseline for it yet. The RFP-coverage prompt still misses and is now a dev prompt, so a future edit can be tuned on it.

## Third and fourth holdout, and a description edit that helped (2026-11-28)

**Third holdout** (written without running, baseline on the unchanged description): Claude Code 4 of 5 prompts, Codex 5 of 5. The Claude miss was
"Make sure nothing in the buyer's requirements list is left unanswered in our response" (0 of 3). It is the third holdout in a row in which Claude
missed a plain request to check that a response covers every requirement (0 of 3 each time, in different wording), so it is a gap in the description,
not noise. That set was then spent: its prompts moved to the dev lists under `semantic_should_trigger` (dev prompts that carry no route term, so the
routing lint skips them and the runner runs them). The two tender prompts that were `known_misses` moved there too, so they are now measured.

**Fourth holdout** (new, written before any edit): baseline on the unchanged description, Claude Code 4 of 5 ("Before we submit, double-check that
our answer covers each item the client asked for": 0 of 3), Codex 5 of 5.

**The edit.** Added to the route sentence of `create-best-proposal`: "including checking that a response answers every requirement the buyer or client
set". An earlier edit that only added the terms "tender" and "requirement-coverage check" had not helped; this one describes the user's action in plain words.

| | Before | After |
|---|---|---|
| Fourth holdout, Claude Code | 4 of 5 (the coverage prompt 0 of 3) | **5 of 5** (the coverage prompt 3 of 3) |
| Fourth holdout, Codex | 5 of 5 | 5 of 5 |
| Dev set, Claude Code (31 prompts, 3 runs each) | not run on the full set | 30 of 31 prompts pass; all 14 near-miss prompts used no skill |

The one dev miss is "Verify that every mandatory requirement in this RFP is covered by our submission": 1 of 3 after the edit, 0 of 3 before it (from the
second holdout, with the unedited description and with the first edit). It improved and still fails. Two of the prompts it was judged on are close in
meaning to the dev prompts the wording was written against, so the holdout result shows the fix for this kind of request, not a general guarantee.

Not done: Codex and Grok were not run on the full dev set, and no full dev run exists for the description before this edit, so "no regression" is
measured only for Claude Code and only on the near-miss prompts. Three runs per prompt. The fourth holdout is now spent as well.

## Reproduce

    python trigger_eval_run.py --yes --host all --runs 3 --max-invocations 200 --timeout 150 --report trigger-report.json

About 160 model calls and 30 to 40 minutes. See [design-decisions.md](design-decisions.md) D08 for why it is not part of CI.
