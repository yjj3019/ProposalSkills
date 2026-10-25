# Boundaries for external methods

Overseas proposal methods and public skill repositories offer useful writing habits, but assume different
procurement systems. This document defines what to borrow as heuristics and what to exclude.

## 1. Principles

- External methods are **writing-quality heuristics**, not truth sources.
- Facts, specifications, weights, and eligibility always come from the opportunity's original notice.
- Do not copy external repository sentences, code, or scoring models. Express concepts independently.

Authority order:

Actual amendment > base RFP > official Q&A > evaluation sheet > specified submission template >
approved internal material > current official external material > general methodology.

Official regulatory sources: `../create-winning-proposal/references/korean-public-proposal-regulatory-basis.md`.

## 2. Borrowed concepts

| Concept | Repository implementation |
|---|---|
| Capture (preliminary positioning) | [capture-and-positioning.md](capture-and-positioning.md) — strengthens Pink inputs; does not replace gates |
| Evaluator Journey | [evaluator-journey.md](evaluator-journey.md) — Pink/Red checks |
| Technical narrative depth | [technical-depth-six-questions.md](technical-depth-six-questions.md) |
| Evidence-first | Existing `claims[]`/`evidence_refs` ledgers |
| Review-stage discipline (Pink/Red/Gold) | Path contracts in [master-playbook.md](master-playbook.md) |
| Overcommitment boundaries | Ambiguous-commitment rules in `writing-style.md` + RFI commitment-blocking gate |
| Risk/methodology structure | Type A/B/C outlines |
| Iterative production/stage evidence/session handoff | [iteration-and-handoff.md](iteration-and-handoff.md) — reuse gates; state records only for long work |

## 3. Excluded concepts

| Item | Reason |
|---|---|
| US FAR, Section L/M structure | Different from Korean RFP/evaluation systems |
| US federal past-performance rules (CPARS, etc.) | Different performance-evidence practices |
| International organization/development-bank procurement rules | Different applicable system |
| Chinese military document standards, classified protection, localization rules | Different applicable system |
| Price-to-Win estimates | Unsupported winning-price estimates; use Price Posture only if needed |
| External scoring/win-probability models | Unverifiable; conflict with prohibition on predicting evaluation results |
| External customer names/track records/prices/example wording | Licensing/factuality issues |
| Cultural generalizations (Korean example: "한국형 서사는 기승전결") | Unsupported rule; narrative patterns are optional |

## 4. Checks before adopting a new concept

1. Does it actually improve Korean IT proposal quality?
2. Does it avoid duplicating existing references/gates?
3. Does it respect original-notice priority?
4. Does it avoid unsupported constants/rules?
5. Does it preserve fail-closed submission gates?
6. Can tests or inspection procedures verify it?

If any answer is no, do not adopt it; record why.
