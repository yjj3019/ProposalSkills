# Master playbook — one-page decision tree

Follow this file near the start of each session. Delegate detailed style/schema guidance to sibling references.

## 1. 30-second triage

```text
User request
 ├─ RFI/preliminary specification/competitive positioning? → Capture memo (+ Pink inputs)
 ├─ Bid decision only?                                  → Decision
 ├─ Document review only?                               → Review-only
 ├─ Skeleton/themes/matrix only or early draft?          → Pink (~30%; no full body)
 ├─ Exhaustive evaluator critique or ~70% draft?         → Red (no full rewrite)
 ├─ Pre-submission approval?                            → Gold (5 items + unified_gate)
 ├─ XLSX/security questionnaire/bulk matrix?            → Matrix (+ bulk_matrix.py)
 ├─ Presentation/PT?                                    → PT (body synchronization required)
 ├─ Joint opportunity/idea without RFP?                  → Discovery (no submission framing)
 └─ Other proposal writing                              → Full
```

### Pink / Red / Gold contracts (S1)

| Path | Timing | Required output | Prohibited |
|---|---|---|---|
| **Pink** | Before body | Type/outline/lead map/matrix skeleton/win_themes(req_ids)/bid decision/key slides and evidence locations per criterion | Full-deck writing, filling unverified track records |
| **Red** | After draft | Coverage evidence locations and weaknesses (Critical/Major) per criterion/unlinked themes/unfilled matrix rows | Full original rewrite (use minimum edits), evaluation scores/win probabilities |
| **Gold** | Before submission | Five pre-submission items + `unified_gate` SUBMISSION-READY for actual file/bundle | Treating uninspected packages/AUDIT-VALID/CONDITIONAL-GO as submission approval |

Pink/Red checks (skeleton logic, 10-second discovery): [evaluator-journey.md](evaluator-journey.md).
Capture strengthens Pink inputs only; it replaces neither bid decisions nor gates:
[capture-and-positioning.md](capture-and-positioning.md).

**Finalize requirements, evaluation criteria, and lead structure before producing slides.**
Do not open PowerPoint and discover the logic while filling content. Order:
requirement ledger → evaluation ledger → Win Theme → lead map → `slides.json` → PPTX.

## 2. Full blocking conditions (before drafting)

Do not write the Full body under any of these conditions:

| Condition | Decision | Output |
|---|---|---|
| No material for eligibility judgment | intake-incomplete | Required-input list |
| Incurable eligibility/capability gap | no-bid | No-bid reason memo |
| Deadline passed + submission purpose | no-bid | Memo (simulation-only for benchmarking) |
| Curable disqualification + unapproved conditions | conditional-bid pending | Condition cards only |

## 3. Full checklist (abridged)

- [ ] A. Confirm bid + source order + stale sweep.
- [ ] B. Atomic requirements + matrix + Win Theme≤3 + lead map.
- [ ] C. Body (one message/page, evidence alongside, 0 overclaims, bounded commitments, six-question review for key technical slides).
- [ ] D. Separate visual/render/package checks.
- [ ] E. meta→audit → unified_gate → five pre-submission items.

## 4. Shared status vocabulary

| Status | Meaning | External submission |
|---|---|---|
| DECISION_MEMO_ONLY | no-bid / intake-incomplete | No |
| DRAFT / DISCOVERY | Draft/exploration/Pink | No |
| NO-GO / BLOCKED | Remaining BLOCKING items or gate failure | No |
| CONDITIONAL-GO | All conditions have owner/deadline/accepted | **Internal only** |
| SUBMISSION-READY | Submission audit + actual file/bundle comparison passed + rehearsal/receipt plan | Yes (retain actual submission evidence afterward) |
| AUDIT-VALID / DRAFT-READY / REVIEW-READY | Audit-only or corresponding internal-stage pass | No |

Do not confuse quality scores with status. **Gates decide status.**

## 5. Type signals

Korean signal keywords are examples preserved verbatim.

| Type | Signal keywords (Korean examples) |
|---|---|
| A: implementation | 구축, 도입, 마이그레이션, 데이터센터, 플랫폼 |
| B: maintenance | 유지보수, SLA, 예방점검, 기술지원, 구독 갱신 |
| C: technical response | 조견표, BMT, 표준제품, 항목별 답변, RFI |

Variants: DCO/resident operations→B, U2L/DR→A, standardization recommendation→C.

## 6. Language and output

| Condition | Default output | Gate lang |
|---|---|---|
| Korean RFP/domestic public or financial sector | PPTX slides | ko |
| English RFP/overseas | DOCX or specified form | en |
| Dual submission | Separate body per language | both |

## 7. Repeated simulation failures

1. High writing quality but empty audit/eligibility → NO-GO.
2. approved without evidence_refs → anti-optimism block.
3. Trying draft markers through submission gate → blocked (separate stages).
4. Mistaking no-bid for a gate bug → explicitly DECISION_MEMO_ONLY.
5. Only five sample rows for type C → bulk_matrix + full appendix.

## 8. Evidence and boundary references

| Need | Document |
|---|---|
| Public procurement/schema mapping; values never to hardcode | `../create-winning-proposal/references/korean-public-proposal-regulatory-basis.md` |
| Key technical slide depth | [technical-depth-six-questions.md](technical-depth-six-questions.md) |
| Adopting overseas methods/external repository concepts | [external-method-boundaries.md](external-method-boundaries.md) |
| Buyer-specified output | `../create-proposal-document/references/deck-production.md` §1-2 buyer-specified output (output_spec) |
| New design pilot/rechecks/long-work handoff | [iteration-and-handoff.md](iteration-and-handoff.md) |
