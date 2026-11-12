# Changelog

Versions describe the local candidate in `plugin.json`; a version here does not imply a GitHub release or an
official-directory publication (see `references/marketplace-management.md`).

## Unreleased

Added
- `mapping_check.py` (requirements matrix vs REQ-IDs in the document, both directions) and `package_inspect.py` (PPTX/DOCX
  package hints: author metadata, notes, comments, hidden slides, external links, embeddings, macros); a DRM-wrapped file is
  NOT INSPECTED (exit 2).
- Optional `Dockerfile` and `runtime_check.py` (python-pptx, Pillow, LibreOffice, Poppler) that follow `requirements.txt`.

Fixed (found by a 10-scenario simulation of the skills and harness)
- `hook_guard_bash.py`: also denies commands wrapped in `bash -c`/`sh -c`/`eval`, `bash <(curl ...)` and `eval $(curl ...)`,
  `git checkout .`, `git stash drop|clear`, `git branch -D`, `git push --delete`/`:branch`, unfiltered `find -delete`,
  `rm -rf ./` and `.*`, `dd of=/dev/...`, `mkfs`, `shred`, `xargs rm -r`, recursive `chmod`/`chown`/`mv` on a broad target,
  redirects into system folders, a fork bomb, `format C:` and PowerShell `Remove-Item -Recurse` on a broad target.
- `task_contract.py`: `write_boundary` must name one specific folder (not `.`, `..`, a drive or filesystem root, `~`, `*`).
- `plain_language_check.py`: a DRM-wrapped or non-ZIP Office file is reported as NOT INSPECTED (exit 2), not a traceback.
- `build_deck.py`: a `slides.json` whose top level is not an object, or a damaged python-pptx install, exits 2 with a message.
- `install_skill.py`: test files are no longer copied into the installed skill folder.
- `evidence_chain.py verify`: `--expect-head` / `--expect-count` compare the log with a value written down elsewhere, so a
  truncated or rebuilt log is caught.

Fixed (second simulation round)
- `hook_guard_bash.py`: judges the command inside wrappers (`nice`, `timeout`, `exec`, `busybox`, `sudo -u`, `env -i`) and
  groupings `( )`/`{ }`; treats `//` and `/tmp/..` as the root; also denies `git push --mirror`, `kill -9 -1`, and uploading a
  local file with `curl`/`wget` (`-d @file`, `-F x=@file`, `-T`).
- `skill_audit.py`: folds fullwidth letters and invisible format characters before matching, and recognises Korean
  "ignore the previous instructions" and "print the system prompt" phrasings.
- `unified_gate.py --bundle`: a file in the submission folder that `attachments[]` does not list (and that is not the checked
  document or audit) is reported as a warning, and an unlisted executable or script (.exe, .bat, .ps1, .js ...) blocks.
- `build_deck.py`: when python-pptx's default template has been encrypted by an enterprise DRM agent (header `<##`), the error says
  so and suggests a virtual environment outside the DRM-managed paths.

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
- `cross_format_numbers.py` (one numbers ledger over every delivered format), `xlsx_check.py` (error cells, `#REF!`,
  never-calculated formulas, `--recalc` through a throwaway LibreOffice profile that forces recalculation),
  `task_contract.py` (limits and states for a long job; `Verified` needs evidence), `eval_metrics.py` (paired
  baseline/candidate metrics from recorded runs), `skill_audit.py --inventory/--deny` (what each skill's scripts can do).
- `evidence_chain.py`: `rerun` lists the checks whose artifacts changed; optional `--seconds` and `--cost` are totaled.
- References: AI-tell review, visual critique (mandatory defects, non-numeric trend), plain-writing guide (question
  coverage, strongest objection), verdict vocabulary (PASS / FAIL / BLOCKED / NOT VERIFIED); operating principles in `AGENTS.md`.
- `THIRD-PARTY-NOTICES.md` and license-hygiene tests; `.gitattributes` pins line endings to LF.

Changed
- `skill_audit.py`: a negation word exempts a match only when it precedes it in the same clause.
- `sensitive_scan.py`: UTF-16/32 XML and DOCTYPE/ENTITY anywhere in a part are refused; an Office-named file that is not
  a ZIP (for example one wrapped by an enterprise DRM agent) is reported as encrypted or DRM-protected, not silently skipped.

## 1.2.5

Previous local candidate. See git history.
