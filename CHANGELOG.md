# Changelog

Versions describe the local candidate in `plugin.json`; a version here does not imply a GitHub release or an
official-directory publication (see `references/marketplace-management.md`).

## Unreleased

Added
- `references/editorial-deck-design.md` (nine-step type scale, one content grid, decluttering, seven at-a-glance patterns, render
  loop and the DRM caveat) and `scripts/tidy_audit.py` (font sizes, near-miss alignments, thin rules, characters per slide).
- `references/ai-vendor-comparison-playbook.md`: how to compare AI vendors from their own documentation, a Korea data-location
  checklist and a dated 2026-11-12 snapshot; `assets/examples/ai-model-comparison/make_deck.py` builds the 17-slide example.
- `mapping_check.py` (requirements matrix vs REQ-IDs in the document, both directions) and `package_inspect.py` (PPTX/DOCX
  package hints: author metadata, notes, comments, hidden slides, external links, embeddings, macros); a DRM-wrapped file is
  NOT INSPECTED (exit 2).
- Optional `Dockerfile` and `runtime_check.py` (python-pptx, Pillow, LibreOffice, Poppler) that follow `requirements.txt`.
- `writing-style.md` section 7 (translationese and mechanical phrasing) and a matching review-checklist item.

Added (self-review without user feedback)
- `references/deck-intake-and-self-review.md`: up to five questions with defaults before building, one direction checkpoint, a four-rung
  self-review (plain, busy, not at a glance, unfinished) with a report format, and the rule to write assumptions down when nobody can answer.
- `scripts/tidy_audit.py` also measures body fill per slide and the share of text-only content slides; `scripts/contact_sheet.py` tiles
  rendered pages into one view (exit 2 for an unreadable or DRM-wrapped image).
- `AGENTS.md`: "Look before you deliver, ask before you guess".

Fixed (third simulation round, closed later)
- `hook_guard_bash.py`: also denies a download piped into `python`/`node`/`perl`/`ruby`/`php` with no script (`curl ... | python -m json.tool`
  stays allowed), PowerShell `iwr ... | iex` and `-EncodedCommand`, `git filter-branch`, `git reflog expire`, `git gc --prune=now`,
  `find -exec rm` without a filter or from a broad start, `find -exec shred`, `tee` into a system folder and `rm -rf $PWD`.

Added (simulation catalog)
- `references/harness-simulation-catalog.md` (how to run a round, what three rounds found, documented limits) and a testing-pitfalls
  section in `AGENTS.md` (hygiene tests read tracked files only, Windows 8.3 temp paths, exit codes behind pipes, patch-script discipline).

Added (slide types)
- `build_deck.py`: three at-a-glance slide types inside the standard frame: `scoreboard` (head-to-head with a winner track and a
  required verdict rule), `triage` (which option first, per situation) and `weights` (one stacked bar that must add to 100).

Fixed (found while building the AI model comparison deck)
- `sensitive_scan.py`: an Office package embedded one level deep (a native chart's value workbook) is now read, so a deck with
  charts is no longer INCOMPLETE for that reason; nested parts are named `outer.xlsx!inner/part.xml`. Images, OLE objects, an
  embedded file that is not a ZIP and nesting deeper than one level are still reported UNSCANNED.
- `build_deck.py`: the generated file no longer carries python-pptx's template author or its "generated using python-pptx"
  comment; the author is empty unless `meta.author` is set and the title comes from `meta.title`.
- `package_inspect.py`: hidden slides are read from the slide part (PowerPoint stores `show="0"` there, not in
  `presentation.xml`); chart value workbooks are reported as information, not as an attachment; tracked changes in a DOCX
  block.
- `mapping_check.py`: REQ-IDs that PowerPoint or Word split across text runs (`REQ-` and `001`) are found, five- and six-digit
  IDs are no longer dropped, and DOCX headers, footers and footnotes are read.

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
