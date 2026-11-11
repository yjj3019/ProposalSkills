# Plain writing for evaluators (reader and job, tagged claims, fresh-reader check)

Use with `writing-style.md` (sentence rules), `evidence-and-claims.md` (what may be claimed) and
`anti-ai-tells.md` (generic phrasing). This file covers structure and reader fit; `plain_language_check.py` lints
the mechanical part.

## 1. Reader and job first

State, before drafting a section: who reads it (an evaluator scoring against a rubric, a technical reviewer, an
executive), and the one job it must do (earn points on evaluation item X, prove requirement Y, commit to Z). A
section with no job is padding; a section with two jobs is split.

## 2. Answer the item, then prove it

Lead with the answer to the evaluation item in the first sentence, then evidence, then the commitment. Do not open
with background the evaluator already has. Keep the buyer's own terms for the buyer's own concepts.

## 3. Tag every claim

Each non-obvious claim is one of: supported (source and as-of date given), inferred (reasoning shown), or
unverified (marked `[unverified]`, never written as fact). Facts never bend for rhythm: a sentence that hurts the
flow stays if it carries a fact; a rhythm that hides a fact is rewritten. Tags map onto the evidence ledger in
`create-winning-proposal`.

## 4. Plain sentences

- One idea per sentence; split sentences past about 90 Korean characters or 25 English words.
- Name the actor and the deadline ("PM이 매주 금요일까지 보고한다"), not passive stacks ("보고가 이루어지게 됩니다").
- Expand an acronym at first use; keep one term per concept throughout the document.
- Do not narrate the document ("본 장에서는 ~을 살펴보겠습니다"); start with the content.
- Exact terms stay exact: do not simplify a requirement ID, a figure, or a defined term into a vague phrase.

## 5. Fresh-reader check (required before calling a section done)

Read the section as someone who never saw the drafting: can they find the answer, the evidence and the commitment
without asking a question? List what they would have to ask; each item is either fixed or marked open.

## 6. Hand-off block

End a writing review with: verdict, kept claims with sources, fixed items, unresolved items. An empty unresolved
block means the reviewer did not look, not that nothing is wrong. Style review is not fact checking, and fact
checking is not gate approval.
