# Manual eval prompts (kept so a result can be reproduced)

The 2026-11-25 manual runs in [trigger-eval-results-2026-11.md](trigger-eval-results-2026-11.md) did not save their prompt text, so
they cannot be replayed. These are the prompts for the **next** manual check. They are new wording, not a recovery of the old
ones, and a result written with them is comparable only to other results with them. Save the prompt id and this file's commit next to
every result.

Setup for every run: a new session, a workspace holding only the three skills and a synthetic `rfp.md`, no skill named in the
prompt. Add this tail to each prompt so the record can be checked against the CLI's own session log:

> Before answering, write `record.md` listing every file you opened, every command you ran, and the decision you reached.

| Id | Should use a skill | Prompt body |
|---|---|---|
| T1 | yes | Draft the outline and the strategy chapter of the technical proposal for this RFP. |
| T2 | yes | Is this bid a go or a no-bid for us? |
| T3 | yes | Build a compliance matrix skeleton for this RFP. |
| T4 | no | Why does my Python code raise `AttributeError: 'NoneType' object has no attribute 'get'`? |
| T5 | no | Make a schedule for a one-day team workshop. |
| T6 | no | Translate this sentence into English: 오늘 회의는 오후 세 시에 시작합니다. |

Grading: T2 is graded with `check_decision_answer.py --bidder-material absent` (see the results file). T4 to T6 pass when no skill
file was opened. Clear Grok's persistent memory before a run, or the run is not independent (see the results file).
