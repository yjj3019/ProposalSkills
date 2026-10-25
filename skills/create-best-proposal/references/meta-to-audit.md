# Meta → Audit builder (SI-B1)

Transfers draft slide/requirement metadata into governance audit JSON.
The goal is to reduce duplicate manual entry and the readiness gap (simulation average ~64).

## Minimum input meta schema

Korean example values and filenames are preserved verbatim.

```json
{
  "mode": "submission",
  "bid_decision": "bid",
  "bid_conditions": [],
  "title": "사업명",
  "buyer": "발주처",
  "proposal_type": "A",
  "deadline": "2026-12-31T17:00:00+09:00",
  "flags": {"financial": false},
  "eligibility": [
    {"id": "E1", "criterion": "최근 3년 3억 실적", "mandatory": true, "met": true, "curable": false}
  ],
  "requirements": [
    {
      "id": "R1",
      "text": "이중화 구성",
      "mandatory": true,
      "state": "approved",
      "evidence_refs": ["slide:12", "조견표#R1"],
      "slide": 12
    }
  ],
  "claims": [
    {"id": "C1", "kind": "commitment", "text": "RTO 4h", "status": "supported", "owner_approved": true}
  ],
  "attachments": [
    {"name": "사업자등록증.pdf", "required": true, "present": true}
  ],
  "slides": [
    {"no": 1, "title": "표지", "lead": "...", "req_ids": []},
    {"no": 12, "title": "HA 구성", "lead": "...", "req_ids": ["R1"]}
  ],
  "unresolved_tokens": [],
  "defects": [],
  "inputs": [],
  "regulatory_checks": [],
  "vendor_confirmations": [],
  "render": {"verified": false},
  "package": {"required": true, "inspected": false},
  "submission": {
    "cleared": false,
    "rehearsal_evidence": [],
    "receipt_plan": ""
  }
}
```

## Builder behavior

Do not confuse authoring `proposal_type` A/B/C with audit `proposal_archetype`:
its values are `build`/`maintenance`/`technical-response`. `mode: draft` and
`context.stage: internal-review` are also separate classifications; record reading conditions in
`context.reading_mode`, e.g. `screen-presentation`. Record synthetic status as
`artifact_mode: simulation-only`; do not invent context constraint values.
Evaluation labels use `evaluation_criteria[].label`; missing mandatory inputs use
`inputs[].class: blocking`/`status: open`. See
[audit-schema.md](../../create-winning-proposal/references/audit-schema.md) for all allowed values.
Successful conversion does not establish audit validity or approval. Run the unified gate afterward.
Never mark actually open inputs or human approvals complete merely to fix metadata errors.

```bash
python scripts/build_audit_from_meta.py meta.json -o audit.json
python scripts/build_audit_from_meta.py meta.json --strict
```

- Populate required top-level fields in audit-schema form.
- requirement.state=approved with empty evidence_refs fails under `--strict`; otherwise produces a warning field.
- Record bidirectional slides[].req_ids ↔ requirements mismatches in `source_conflicts`.
- Leave unverified render/package state intact so the gate returns NO-GO (prevent false READY).
- `artifact_required`/`package.required` **default true only for mode=submission**. Draft/review default false,
  allowing lead-map audits to reach `DRAFT-READY` (explicit values take precedence).

## When to use

1. Immediately after lead-map/matrix draft → draft audit (mode=draft). **Pink checkpoint recipe**:
   requirements are not `state: drafted`; only reviewed items become `approved`, so "not approved" appears.
   For Pink, use `mode: "draft"`; fill `bid_decision`/`eligibility`/`checks` without requiring all mandatory
   requirements to be `state: "approved"`. Read the gate's "requirement … is not approved" list as a **work list**.
   DRAFT-READY normally follows first body completion (step 2) once evidence_refs are populated.
2. After first body completion → strengthen evidence_refs.
3. After render/package inspection → update verified/inspected → unified_gate.

Example: `fixtures/meta_sample.json`.
