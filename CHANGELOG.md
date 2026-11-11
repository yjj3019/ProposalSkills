# Changelog

Versions describe the local candidate in `plugin.json`; a version here does not imply a GitHub release or an
official-directory publication (see `references/marketplace-management.md`).

## 1.3.0

Added
- Repository tools: `gate_mutation_probe.py` (weaken a gate, require a test to fail), `skill_audit.py` (injection patterns and
  license declarations), `merge_guard.py` (advisory PR readiness), `hook_guard_bash.py` (opt-in destructive-command hook).
- `sensitive_scan.py`: credentials and personal data (including resident-registration numbers with date and checksum notes)
  in PPTX/DOCX/XLSX/HWPX and text; unreadable files are reported as UNSCANNED, and an incomplete scan exits 2.
- HWPX (Hancom, ZIP of XML) reading in `sensitive_scan.py`, `quality_gate.py`, `check_numbers.py` and
  `plain_language_check.py`: paragraphs, table cells, headers/footers and metadata; embedded `BinData/` is reported as not
  inspected. The older binary `.hwp` is still reported as UNSCANNED (save it as HWPX first).
- Proposal checks: `edit_preservation.py`, `deck_story_check.py`, `plain_language_check.py`, `deck_stage_gate.py`,
  `verification_report.py`, `retry_guard.py`, `evidence_chain.py`, `handoff_lint.py`.
- References: AI-tell review, visual critique, plain-writing guide; operating principles in `AGENTS.md`.
- `THIRD-PARTY-NOTICES.md` and license-hygiene tests; `.gitattributes` pins line endings to LF.

Changed
- `skill_audit.py`: a negation word exempts a match only when it precedes it in the same clause.
- `sensitive_scan.py`: UTF-16/32 XML and DOCTYPE/ENTITY anywhere in a part are refused.

## 1.2.5

Previous local candidate. See git history.
