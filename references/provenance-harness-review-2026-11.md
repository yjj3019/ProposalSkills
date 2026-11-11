# Provenance record: harness review and adoption (2026-11-11)

This record states what was reviewed, what was adopted, and what was deliberately not adopted, so the
licensing position of every addition is auditable. It is a development record, not legal advice.

## Source reviewed

The repository owner's private agent-harness repository (Apache-2.0, owner-authored; 213 tracked files:
shell/Node tooling, host hook templates, 26 general-purpose skills, and design/evaluation notes). It is not
linked here because it is private. The review read its tooling, skills, and documents end to end.

## Licensing position

- Everything adopted is **independently implemented in Python** for this repository's standard-library
  toolchain. No source file, prompt text, test, fixture, or asset was copied or translated line by line.
  Only well-known public formats were reused as data (for example credential prefixes such as `AKIA` or
  `ghp_`, and the public resident-registration and Luhn checksum algorithms).
- This repository is MIT. The source repository is Apache-2.0 and owned by the same author, so adopting its
  ideas creates no third-party obligation. Had any code been copied, the Apache-2.0 notice requirements
  (license copy, change notices, retained attributions) would have applied; none was.
- Items in the source that carry **third-party** terms were excluded entirely (table below).

## Adopted (idea → independent implementation here)

| Idea in the reviewed repository | Implementation here | Why it fits this project |
|---|---|---|
| Mutation probe: weaken a gate, require a test to fail | `gate_mutation_probe.py`, `test_gate_mutation_probe.py` | The project's central claim is gate integrity. The probe found four unguarded rules on its first run (now closed by `test_gate_mutation_gaps.py`). Follows the earlier "targeted mutation validation" item in `harness-adoption-review-2026-10.md`. |
| Secret scan and evidence redaction before recording content | `skills/create-best-proposal/scripts/sensitive_scan.py`, `test_sensitive_scan.py`, hygiene check in `test_repo_hygiene.py` | Proposal material carries customer data. Extended beyond the source with Korean resident-registration numbers (date and checksum validated), payment cards (Luhn), internal IP ranges, Office-file text and metadata, and an explicit UNSCANNED result so unreadable content is never reported as clean. |
| Skill audit: reject injection patterns, require a `license:` declaration consistent with the repository | `skill_audit.py`, `test_skill_audit.py`, `license: MIT` in the three `SKILL.md` files | Skills are agent instructions that get distributed through marketplaces. |
| Doc-versus-CI drift lint (stale claims in handoff notes) | `test_release_consistency.py` | Keeps the quoted version and license aligned with manifests and the packaged archive. |

## Considered and not adopted

| Item | Reason |
|---|---|
| Design-evidence skill (carries its own MIT license from a third-party author) | Third-party license; unrelated to Korean proposals. |
| PPT staged-workflow skill (adapted from a third-party MIT project) | Third-party derivative; this project already has its own deck pipeline (`build_deck.py`, `deck_check.py`). |
| Evidence-preserving editor skill | Its license grant is not documented by a local license file (the source's own provenance note flags this). Not reused until the owner clarifies. |
| Generic writing, document, coding, design, security, and observability skills | Duplicate or weaker than this project's proposal-specific guidance (`writing-style.md`, `review-checklist.md`, `quality_gate.py`). |
| Phase-gate workflow, hook templates, tool broker, dashboard, task-graph and accounting tools | Solve long-running coding-agent supervision, not proposal authoring; they would add a Node runtime dependency and attack surface to a stdlib-only Python project. |
| Paired-evaluation and usage-accounting experiments | Need real model runs to mean anything; the source itself labels them proposals, not measured results. |

## Obligations going forward

- Keep `skill_audit.py` green: every skill declares `license:`; a skill that differs from the root license
  must ship its own LICENSE file.
- If third-party text or code is ever added, record its exact license and notice here first, and preserve
  the notice in the file. A concept reference is not a license determination.
- `.mailmap` only unifies displayed author identities. Original author e-mail addresses remain in commit
  history; removing them requires a history rewrite, which has not been done.
