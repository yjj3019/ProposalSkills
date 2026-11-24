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

## Reproduce

    python trigger_eval_run.py --yes --host all --runs 3 --max-invocations 200 --timeout 150 --report trigger-report.json

About 160 model calls and 30 to 40 minutes. See [design-decisions.md](design-decisions.md) D08 for why it is not part of CI.
