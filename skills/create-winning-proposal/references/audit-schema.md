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
  "checks": {"consistency": true, "arithmetic": true, "submission": true},
  "artifact_required": true,
  "render": {"verified": true}
}
```

- `mode`: submission, draft, review, or analysis.
- Conditional-bid passes only when every condition has an owner, ISO-8601 deadline, and acceptance.
- Intake-incomplete and no-bid never pass submission readiness.
- Not-applicable mandatory items need rationale and reviewer.
- Material claims must be supported, qualified, or removed; commitments also need owner approval.
- Use `artifact_required: false` only when no rendered artifact is requested.
- Record completed or documented-not-applicable consistency, arithmetic, and submission checks as `true`.
