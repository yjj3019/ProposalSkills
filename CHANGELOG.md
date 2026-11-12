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

Fixed (found by an independent review of the review loop)
- `review_ledger.py`: slide hashes now reach the theme (slide, layout, master, theme) and include the slide size and the table styles, so a
  theme colour or font change or a resize resets every verdict; before, an earlier verdict survived a visible change.
- `render_delta.py`: more than 12 changed slides split the sheet, and the output and `delta.json` (`changed_sheets`, `sheets`) now name every
  file.
- `render_delta.py` deletes only what it created: the output folder must be new, empty or its own (`render_state.json`), otherwise it is
  refused before anything is written; it removes only the sheets and page images it recorded, never a folder and never another file
  that matches a name (before, files named like `sheet*.png` and the whole `pages` folder could be deleted).
- `render_delta.py` records the hash of each page image it writes and refuses (exit 2, nothing changed) to overwrite or delete a recorded page the user has since edited or replaced.
- `review_ledger.py set --viewed sheet` now needs `--sheet <file>` and records that overview's hash (checked by `check`); the page image is no longer passed off as the overview. Viewing again a slide whose old verdict has no image hash clears the four rungs.
- `render_delta.py` also compares each rendered image's own hash and the render environment (LibreOffice build read from the install
  folder, the PDF converter): a slide whose content is unchanged but whose picture differs after a font or engine change is reported in
  `render_changed`, and a changed environment re-checks every slide. An unknown part of the environment is not treated as a change.
- `review_ledger.py` ties a verdict to the image that was looked at (its SHA-256 is recorded when viewing is recorded): `check` refuses an
  image that changed since, and `sync` does not carry a verdict onto a slide whose picture differs.
- `render_delta.py` no longer deletes a page image by its name: it renders in a temporary folder, installs only after checking, removes
  only the page images and sheets recorded as its own, and refuses (exit 2, nothing changed) when a file it is about to write exists and
  is not recorded (a `page-99.png` or `sheet.png` the user added); the PDF is no longer written into the output folder.
- `review_ledger.py sync` carries a verdict onto a rebuilt slide only when it can prove the picture is the same (the old and the new image
  hash are both recorded and equal); a missing hash (an older ledger) resets the slide. `set --image` with another image, or viewing
  again after the image changed, clears the viewing and the four rungs. `sheet` viewing (cover, closing) is held to the same image proof
  as `full`. Open Critical or Major findings of a slide that no longer exists are kept in `orphaned_findings` and block `check`.

Added (cheap review loop)
- `scripts/render_delta.py`: renders every page, compares each slide's content hash with the last run and builds a numbered contact sheet
  of only the changed slides (`changed_sheet.png`, `delta.json`); exit 2 without LibreOffice or a PDF-to-PNG converter.
- `review_ledger.py`: per-slide content hashes and `sync` (keeps the verdicts of unchanged slides, resets the changed or new ones,
  never carries a verdict onto a slide whose hash differs); `check` refuses a ledger whose slide hashes no longer match the deck.
- `contact_sheet.py`: tile labels can carry real slide numbers; the sheet is no wider than its tiles.
- `deck-intake-and-self-review.md`: the cheap iteration loop, and the conditions an HTML preview would have to meet to be allowed
  (one source, identical geometry, a read-back parity check, a text-fit margin, the final PPTX still reviewed).

Added (editorial theme and review ledger)
- `build_deck.py`: `meta.theme: "editorial"` (opt-in; default `standard` unchanged): paper background, serif title, light lead, no title
  rule, hairline tables, flat cards with a top rule; role names kept, so `deck_check.py` and the contrast check still apply.
  `meta.title_font` sets the title face; an unknown theme is rejected.
- `scripts/review_ledger.py` (`init`, `set`, `check`): records per page that it was viewed, judged on the four rungs and closed out;
  refuses completion for an unseen page, a chart seen only on a sheet, an image older than the deck, an open Critical or Major
  finding, no revision, or a deck that changed after the review. It checks the review's honesty, not the quality.

Fixed (found while adding the theme)
- `build_deck.py`: every run now carries the East Asian and complex-script typeface (`a:ea`, `a:cs`) next to the Latin one; before,
  Korean text fell back to the theme font and looked different on each machine.

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
