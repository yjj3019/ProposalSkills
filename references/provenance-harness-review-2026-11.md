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

### Second pass (owner asked to absorb as much as practical)

Same source, same licensing position: owner-authored Apache-2.0 ideas, written fresh for this repository.

| Idea in the reviewed repository | Implementation here | Why it fits this project |
|---|---|---|
| Constitution principles: data-not-instructions, meaningful verification (tests actually ran), instruction drift, approval boundary | `AGENTS.md` "Operating principles" | RFPs and customer files are untrusted text; the rules were missing from the repository's own agent instructions. |
| Anti-AI pattern review with a four-block report (changed / kept / evidence / uncovered) | `skills/create-proposal-document/references/anti-ai-tells.md`, linked from `review-checklist.md` | Proposals need generic-phrasing removal that preserves facts; the Korean checklist and report format are proposal-specific. |
| Skill trigger evaluation (positive and negative phrases) | `references/trigger-eval-cases.json`, `test_skill_triggers.py` | Guards flagship/sibling routing vocabulary. Offline lint only; it does not measure model behaviour. |
| Package lint: relative-link and frontmatter checks | `test_skill_links.py` | Broken reference links silently remove guidance that the skills load on demand. |

### Third-party-derived items: re-implemented as new logic (ideas only, nothing copied)

The three skills in the reviewed repository that carry third-party terms were not copied. The owner asked
for their ideas to be re-implemented here as new logic. Each upstream project is MIT-licensed; only the
general idea was taken, and no upstream text, prompt, example, script, or asset is present in this repository.
Method for all three: **re-implement (ideas only)**; no notice file is required because no expression was reused,
and the upstream is credited here anyway.

| Upstream idea (source, license) | New implementation here | What is different |
|---|---|---|
| Edit prose for clarity while preserving facts, uncertainty and protected spans ([blader/humanizer](https://github.com/blader/humanizer), MIT) | `skills/create-proposal-document/scripts/edit_preservation.py` | A mechanical before/after inventory (figures with Korean units, dates, requirement IDs, links, quotations, code spans, hedges, negation counts) that blocks on lost or invented facts. Upstream is a prompt; this is a checker. |
| Staged, gated deck workflow with a locked design spec and a source-of-truth intermediate ([hugohe3/ppt-master](https://github.com/hugohe3/ppt-master), MIT) | `skills/create-proposal-document/scripts/deck_stage_gate.py` | A manifest-driven gate: approval is bound to the spec file's SHA-256 so later edits invalidate it, plan titles must be claims, and `slides.json` content titles must match the page plan. No SVG or PPTX tooling is involved. |
| Verify the saved artifact itself and report which checks really ran, with their depth ([alchaincyf/huashu-design](https://github.com/alchaincyf/huashu-design), MIT) | `skills/create-best-proposal/scripts/verification_report.py` | A validator that ties a report to the delivered file by hash, requires a tool and evidence for rendered or live passes, requires not-inspected checks to be listed, and refuses numeric scores. |

Tests: `test_reimplemented_workflows.py`. Pointers: `review-checklist.md` and `deck-production.md`.

## Considered and not adopted

| Item | Reason |
|---|---|
| Design-evidence skill (carries its own MIT license from a third-party author) | The skill text itself is not copied. Its idea is re-implemented as `verification_report.py` (see the re-implementation table above). |
| PPT staged-workflow skill (adapted from a third-party MIT project) | The skill text itself is not copied. Its idea is re-implemented as `deck_stage_gate.py`; the existing deck pipeline (`build_deck.py`, `deck_check.py`) is unchanged. |
| Evidence-preserving editor skill | The skill text itself is not copied (its license grant is undocumented locally). Its idea is re-implemented as `edit_preservation.py`. |
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
