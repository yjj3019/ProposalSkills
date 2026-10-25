# Sibling skill reference map

This skill focuses on orchestration/integration tools. Specialist banks live in sibling skills.
Paths are relative to `skills/create-best-proposal/`.

## create-proposal-document (content)

| Topic | File |
|---|---|
| Bid/submission/pricing/XLSX | `../create-proposal-document/references/bid-and-submission.md` |
| Intake/requirement extraction | `../create-proposal-document/references/intake-and-requirements.md` |
| Type-specific outlines/leads | `../create-proposal-document/references/proposal-structure.md` |
| Style/overclaims | `../create-proposal-document/references/writing-style.md` |
| Phrase patterns | `../create-proposal-document/references/phrase-library.md` |
| Project management/inspection/test skeletons | `../create-proposal-document/references/content-patterns.md` |
| Evidence/claims | `../create-proposal-document/references/evidence-and-claims.md` |
| Visual tokens | `../create-proposal-document/references/visual-style.md` |
| 8 review areas | `../create-proposal-document/references/review-checklist.md` |
| Mechanical review | `../create-proposal-document/scripts/quality_gate.py` |

## create-winning-proposal (governance)

| Topic | File |
|---|---|
| Audit JSON schema/anti-optimism | `../create-winning-proposal/references/audit-schema.md` |
| Requirement/evidence ledgers | `../create-winning-proposal/references/requirements-and-evidence.md` |
| Review states/outputs | `../create-winning-proposal/references/review-and-output.md` |
| Structural archetypes | `../create-winning-proposal/references/structure-and-design.md` |
| English phrases | `../create-winning-proposal/references/writing-and-phrases.md` |
| Security/restraint in automation | `../create-winning-proposal/references/automation-and-security.md` |
| Licensing | `../create-winning-proposal/references/source-patterns.md` |
| Anonymous patterns | `../create-winning-proposal/references/anonymized-proposal-patterns.md` |
| Korean public procurement sources/values never to hardcode | `../create-winning-proposal/references/korean-public-proposal-regulatory-basis.md` |
| Deterministic gate | `../create-winning-proposal/scripts/proposal_gate.py` |

## Repository root

| Topic | File |
|---|---|
| Two-axis completeness score | `scripts/score_completeness.py` |
| Installer | `../../install_skill.py` |

## Standalone installation

When sibling files are absent:
1. Use only this skill's writing guidance and meta→audit conversion; the unified gate cannot run standalone.
2. Explain that audit uses `build_audit_from_meta.py` and sibling installation is required.
3. Gate-script environment variables (matching code):
   - `PROPOSAL_GATE_PATH` — absolute path to `proposal_gate.py`.
   - `QUALITY_GATE_PATH` — absolute path to `quality_gate.py`.
   - `CHECK_NUMBERS_PATH` — absolute path to `check_numbers.py`.
   - PPTX submission also needs `deck_check.py`; install the content sibling together.
4. Recommended: `python install_skill.py --dest <dir> --name create-best-proposal --with-deps`.
