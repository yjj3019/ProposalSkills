# Critical selection — external and internal improvements (2026-08)

## Selection criteria

1. **Preserve anti-optimism**: never issue GO from a model's self-score or winrate percentage.
2. **Thin additions**: do not import a 108-skill engine, RAG, or GraphRAG.
3. **Evidence-based**: address simulation readiness bottlenecks, architecture coupling, and Shipley intermediate stages directly.
4. **Licensing**: adopt concepts and schemas only; do not copy external sentences/code.

## Final selections (implemented)

| ID | Item | Implementation location | Critical note |
|---|---|---|---|
| S1 | Pink/Red/Gold path contracts | `create-best-proposal` SKILL + master-playbook | All 7 Shipley colors would be excessive; use 3 stages |
| S2 | Extended matrix columns (fit/eval/theme/risk) | bulk_matrix + audit requirements fields | Optional columns rather than a mandatory new schema |
| S3 | Win theme → req_ids link validation | build_audit_from_meta | Unlinked themes warn; strict mode fails |
| S4 | unified_gate → explain wiring | unified_gate.py `--explain` | On by default to print remediation tables |
| S5 | Default no-bid CLI = DECISION_MEMO | proposal_gate.py main | Distinguish intentional stops even without explain |
| S6 | Installation default = flagship + --with-deps | install_skill.py | Install dependencies together instead of heavy vendor copies |
| S7 | Minimal AI-slop patterns | quality_gate.py | Extend banned terms; not a style model |
| S8 | Status alias documentation | unified-gates.md | Document the contract rather than split code enums |
| S9 | sibling-map environment-variable consistency | sibling-map.md | Remove nonexistent CLI flags |

## Rejected (intentionally not implemented)

| Candidate | Reason |
|---|---|
| Winrate predictor / Pwin % | Anti-optimism risk; no simulation/organization data |
| Full RFP shred engine | Large language/format variation; retain human + matrix first pass |
| RAG/AutoRFP import | Approved library and hallucination benchmark unavailable |
| Full Vale stack | No Korean corpus |
| Full 508 automation | Some mechanical checks possible, but low value for the scope |
| Gate copies in vendor/ | Duplicate maintenance; use --with-deps instead |

## Validation

- `python -m unittest discover -s . -p "test_*.py" -q`
- `python skills/create-winning-proposal/scripts/test_proposal_gate.py -q`
- `python skills/create-best-proposal/scripts/test_best_proposal.py -q`
