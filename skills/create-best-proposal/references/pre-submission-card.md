# Five-item pre-submission card (SI-C3)

A human (or agent) checks this **single-screen** card immediately before/after gate READY.
If any item is unconfirmed, external submission is prohibited.

| # | Item | Check question | Example evidence |
|---:|---|---|---|
| 1 | **Mandatory coverage** | Is every mandatory requirement approved+evidence_refs or N/A (reason/reviewer)? | Final matrix, audit requirements |
| 2 | **Commitments/prices** | Are personnel/schedule/SLA/amounts consistent across summary/body/appendices and recalculated? | checks.arithmetic=true, comparison table |
| 3 | **Package cleanliness** | Is the technical package free of metadata/notes/hidden content/prior customer names/price leaks? | All package.checks pass/n-a |
| 4 | **Format/deadline** | Do filename/size/format/page semantics/deadline (timezone) match the RFP? | submission.deadline, rehearsal log |
| 5 | **Receipt plan** | Was upload/print rehearsed, with a receipt-number/screen/email evidence plan? | rehearsal_evidence, receipt_plan |

## Record template

```text
Pre-submission card — Opportunity: ________  Date/time: ________  Checker: ________
1 Mandatory coverage: [ ]  Notes:
2 Commitments/prices: [ ]  Notes:
3 Package cleanliness: [ ]  Notes:
4 Format/deadline: [ ]  Notes:
5 Receipt plan: [ ]  Notes:
Unified gate: READY / CONDITIONAL-GO / BLOCKED / DECISION_MEMO_ONLY
External submission authorized: YES / NO
```

CONDITIONAL-GO **does not authorize external submission**, even if all five items are complete.
Every condition owner must accept, and an internal authorized approver must sign separately before buyer submission.
