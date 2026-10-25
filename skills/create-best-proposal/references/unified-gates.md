# Operating unified gates

## 1. Layers

```text
quality_gate.py     Document text/colors (overclaims/placeholders/residual names/palette)
       ↓
proposal_gate.py    Audit JSON structure/anti-optimism/submission readiness
       ↓
score_completeness  readiness / quality scores (gates determine status)
       ↓
unified_gate.py     Combination + DECISION_MEMO_ONLY UX + standardized exit codes
```

## 2. quality_gate stage decision tree (SI-B2)

```text
Can this be submitted to the customer unchanged?
  ├─ No (internal draft/fact gathering) → --stage draft
  │     [NEEDS INPUT] / ［입력요망］ → warnings (nonblocking; Korean marker preserved)
  └─ Yes (submission candidate) → --stage submission (default)
        Even one unresolved marker → blocked
If unclear, run submission first, then reclassify warnings against draft rules.
```

Examples:
```bash
# Draft circulation
python ../create-proposal-document/scripts/quality_gate.py draft.pptx --stage draft --lang ko

# Submission candidate
python ../create-proposal-document/scripts/quality_gate.py final.pptx --stage submission \
  --names prior_customers.txt --palette "1F3864,8FAADC,D6E0F0,EDF1F8,C00000,1F7A3D,202020,595959"
```

## 3. proposal_gate / unified_gate result prefixes (SI-B3)

| Output | exit | Meaning |
|---|---:|---|
| READY | 0 | Gate passed. Unified display depends on audit `mode`: `SUBMISSION-READY` (mode=submission) or `DRAFT-READY`/`REVIEW-READY` (otherwise) |
| CONDITIONAL-GO | 0* | accepted conditional-bid + all other checks passed (*unified returns 0 with internal-only notice). **BLOCKED in mode=submission**; conditional is not submission clearance |
| DECISION_MEMO_ONLY | 1 | no-bid / intake-incomplete; no body drafting |
| BLOCKED | 1 | Submission blocked (evidence/defects/package, etc.) |
| INVALID | 2 | Audit schema error |

Do not mix no-bid with a generic "must be bid" error. Message form:
`DECISION_MEMO_ONLY: bid_decision=no-bid; ...`.

## 4. Three mandatory anti-optimism guards

1. **evidence_refs**: mandatory+approved requires nonempty evidence.
   The builder never turns a `slide` number into evidence (location ≠ proof); authors must specify it.
2. **deadline**: submission requires ISO format + timezone and a future time.
   Conditional-bid `bid_conditions[].deadline` must also be in the future.
3. **eligibility**: submission requires a ledger; unmet+incurable prohibits bid.

**Strict booleans**: `accepted`/`present`/`cleared`/`verified`/`inspected`/`owner_approved`/
`met`/`curable`/`mandatory`/`required` accept only JSON `true`/`false`.
Strings such as `"yes"`, `"pending"`, `"no"` are schema errors (INVALID), preventing false passes
from truthy nonempty strings. Omitted `mandatory`/`required`/claim `kind` are treated as
mandatory/required/material respectively (omission cannot bypass checks).
Submission requires at least one mandatory requirement in the ledger.

## 5. Financial submission (SI-B4)

`flags.financial: true` requires `regulatory_checks`.
Each status=`met` requires evidence; gap/in-progress blocks.
Golden fixture: `fixtures/audit_ready_financial.json`.

## 6. Using unified_gate

Executable commands and Korean example filenames are preserved.

```bash
python scripts/unified_gate.py audit.json
python scripts/unified_gate.py audit.json --doc 제안서.pptx --stage submission
python scripts/unified_gate.py audit.json --doc 제안서.pptx --stage draft --lang ko
python scripts/unified_gate.py audit.json --no-explain   # Omit remediation table
```

- **--explain on** by default: also prints proposal_gate remediation Markdown (S4).
- `STATUS: SUBMISSION-READY` ≡ `READY` (S8 alias), **only for audit.mode=submission**.
  Passing draft/review/analysis audits display `DRAFT-READY`, etc.; with `--stage submission`, a NOTE says
  this is not a submission decision.
- With a document path, run quality_gate first; failure produces BLOCKED before audit evaluation.
  quality_gate exit 2 (corrupt/unsupported file) is INVALID (exit 2).
- Immediately before the final decision, compare audit bytes with those parsed and document SHA-256 with its
  value before the first child check. Modification/deletion/read failure yields INVALID (exit 2); recheck.
  Input changes also yield INVALID when quality_gate fails. After audit evaluation, compare actual attachment
  files/hashes. This is not file locking: it cannot guarantee against changes reverted between checks or after
  the final comparison. Preserve the validated submission candidate separately.
- Child processes use UTF-8 (no crash on Korean Windows cp949 consoles).
- If sibling scripts are missing, explain `PROPOSAL_GATE_PATH`/`QUALITY_GATE_PATH` or
  `install_skill.py --with-deps`, then exit 2.
