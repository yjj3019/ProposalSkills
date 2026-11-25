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

## Reproduce

    python trigger_eval_run.py --yes --host all --runs 3 --max-invocations 200 --timeout 150 --report trigger-report.json

About 160 model calls and 30 to 40 minutes. See [design-decisions.md](design-decisions.md) D08 for why it is not part of CI.
