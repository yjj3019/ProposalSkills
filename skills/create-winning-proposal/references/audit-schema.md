# Audit JSON schema

Create every top-level field; do not omit empty arrays.

```json
{
  "mode": "submission",
  "bid_decision": "conditional-bid",
  "bid_conditions": [{"id": "B1", "owner": "Legal", "deadline": "2026-08-20T17:00:00+09:00", "accepted": true}],
  "requirements": [{"id": "R1", "mandatory": true, "state": "approved", "rationale": "", "reviewer": "Security lead"}],
  "claims": [{"id": "C1", "kind": "commitment", "status": "supported", "owner_approved": true}],
  "unresolved_tokens": [],
  "attachments": [{"name": "signature.pdf", "required": true, "present": true}],
  "source_conflicts": [],
  "inputs": [{"id": "I1", "class": "non-blocking", "status": "closed"}],
  "defects": [{"id": "D1", "severity": "minor", "status": "closed", "closure_evidence": "reviewed page 12"}],
  "checks": {"consistency": true, "arithmetic": true, "submission": true},
  "artifact_required": true,
  "render": {"verified": true},
  "package": {"required": true, "inspected": true},
  "submission": {"cleared": true, "rehearsal_evidence": ["test upload opened"], "receipt_plan": "save portal confirmation", "receipt_evidence": []}
}
```

- `mode`: submission, draft, review, or analysis.
- Conditional-bid passes only when every condition has an owner, ISO-8601 deadline, and acceptance.
- Intake-incomplete and no-bid never pass submission readiness.
- Not-applicable mandatory items need rationale and reviewer.
- Material claims must be supported, qualified, or removed; commitments also need owner approval.
- Open blocking inputs and open Critical/Major defects block submission. `conditional-go` is an internal review state only.
- Use `artifact_required: false` only when no rendered artifact is requested.
- Set package inspection `required` for editable office files; missing capability is `inspected: false`, not a pass.
- Submission clearance requires rehearsal evidence and a receipt-capture plan. Add the actual receipt evidence after submission; do not fabricate it before submission.
- Record completed or documented-not-applicable consistency, arithmetic, and submission checks as `true`.
