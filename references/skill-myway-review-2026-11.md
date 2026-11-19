# Selective review of skill-myway (2026-11-19)

Reviewed the public repository at commit `b6c6bc725192d5c359d5508e053b32db75236331`:
<https://github.com/yjj3019/skill-myway/tree/b6c6bc725192d5c359d5508e053b32db75236331>.
The root and plugin declare Apache-2.0; the source also contains separately licensed skill material and an
explicitly documented unresolved provenance question. The repository-level license alone does not resolve the
rights of every file or dependency. See its `docs/LICENSES.md` at that revision.

## Comparison and decisions

| Area | Existing ProposalSkills baseline | This change |
|---|---|---|
| Protected wording | Regex inventories in `edit_preservation.py` cannot detect every change of meaning. | Add an optional caller-supplied exact-phrase inventory and an output mode that suppresses source text. Both remain mechanical checks. |
| Paired evaluation | The existing tool aggregates paired records and cannot authenticate them. | Label older comparison context as incomplete, allow extra declared fields, and reject ambiguous JSON. Matching labels do not prove comparability. |
| Review evidence | `verification_report.py` already checks the artifact hash and review declarations. | Optionally compare evidence file hashes within a specified local root; this proves neither reviewer identity nor review quality. |
| Visual review | `review_ledger.py` already binds page reviews to slide and image hashes. | Keep the current proposal-specific review loop; do not duplicate a general design gate. |
| Runtime and approvals | Existing task contracts and host controls have separate roles. | Do not install another runtime or treat self-declared approvals as authority. |

The selected methods were written for this repository without copying source code, tests, example data, assets or
prose. The reviewer had seen the source; this is not a clean-room claim or a legal opinion. No conclusion is made
about historical material, third-party rights, semantic equivalence, model behavior, or unseen dependencies. Any
future reuse of protected expression requires a separate file-level license and notice review before adoption.
