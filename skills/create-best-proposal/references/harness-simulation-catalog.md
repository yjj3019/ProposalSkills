# Harness simulation catalog (attacking the skills and the harness on purpose)

A simulation drives the real tools with odd or hostile input and records exit codes and output. Each defect becomes a
regression test (`test_simulation_fixes.py`, `test_editorial_design.py`). Three rounds so far found about sixty gaps that
unit tests had not, because unit tests are written by the person who wrote the code. Run a round after any change to a
gate, a reader or the hook guard, and before a release.

## 1. How to run a round

1. List ten scenarios across different areas; for each, **decide the expected result first** (denied or allowed, exit
   code, message) so a surprise is visible.
2. Call the real script as a subprocess. Capture its exit code directly; never pipe through `| tail` or `| head`, which
   replaces the exit code with the pipe's.
3. Build fixtures at runtime in a temporary folder. Resolve the temp root (`Path(...).resolve()`): Windows runners give
   8.3 short paths that differ from the resolved path.
4. Record what worked as well as what failed. "Verified working" areas stop the next round from repeating them.
5. For every fix add a regression test **and its look-alike that must stay allowed** (for example deny
   `curl x | python`, allow `curl x | python -m json.tool`), otherwise a fix turns into a false-positive source.
6. Treat environment problems as findings (an enterprise DRM agent encrypting python-pptx's template looked like a
   corrupted install for two rounds).
7. Say what a fix does not cover. A lexical guard is a guardrail, not a sandbox.

## 2. Scenario families and what they found

| Area | Probe | Found | Fixed in |
|---|---|---|---|
| Hook guard | `bash -c`, `eval`, a download piped into a shell, process substitution, wrappers (`nice`, `timeout`, `exec`, `busybox`, `sudo -u`, `env -i`), groupings, `//` and `/tmp/..` as the root, `curl -d @file` uploads | about fifty bypasses | #43, #44 |
| Hook guard, third round | download piped into `python`/`node`, PowerShell `iwr | iex` and `-EncodedCommand`, `git filter-branch`, `reflog expire`, `gc --prune=now`, `find -exec rm`, `tee /etc/...`, `rm -rf $PWD` | eight gaps found in a round that was interrupted, closed later | this change |
| Task contract | `write_boundary` of `.`, `..`, `~`, `*`, a drive root | accepted too-broad boundaries | #43 |
| Every Office reader | a DRM-wrapped or non-ZIP `.pptx` | tracebacks | #43, #47, #48 |
| Installer | test files copied into the installed skill | shipped tests | #43 |
| Evidence chain | truncated or rebuilt log; BOM, garbage, empty file | truncation undetected | #43 (`--expect-head`, `--expect-count`) |
| Skill audit | fullwidth letters, zero-width characters, Korean injection phrasing | evaded the patterns | #44 |
| Submission bundle | unlisted executable or script in the folder, tampered or missing attachment, path escape | strays unnoticed | #44 |
| Readers | hidden slides, ids split across runs, 5-6 digit ids, DOCX headers, chart workbooks, tracked changes | missed or mis-read | #48 |
| Scanner | personal data inside an embedded chart workbook | deck reported INCOMPLETE | #49 |
| Verified working | leak detection (resident number, cloud key, IP, email, phone), hash-bound tamper detection, HWPX and the zip-bomb guard, cross-format number divergence, concurrent chain appends, cp949 and ASCII encodings, Hangul and space paths, the English gate, determinism, profiles | no change needed | n/a |

## 3. Limits that are documented, not fixable by this repository

- **Hook guard** is lexical. It cannot see interpreter one-liners (`node -e`, `python -c`), `pkill`, `history -c`,
  domain commands (`docker system prune`, `kubectl delete`, SQL `DROP`), or what an alias or a variable expands to.
  Approval and host permissions remain the real control.
- **Evidence chain** anchors catch truncation only when the head hash was written down outside the log.
- **`unified_gate.py --audit-only`** ignores a deadline already past, by design.
- **Scanner** reads text and one level of embedded Office packages; images and OLE objects need a person or OCR.
- **Enterprise DRM** that encrypts Office output or the system python-pptx template is an environment fault. Use a
  virtual environment outside the managed paths and render with LibreOffice.

## 4. Adding a scenario

Write it as a test first (`test_simulation_fixes.py` has one class per round), name the area in the class, keep fixtures
inline, and put the allowed look-alikes in the same class. Add a row to the table above.
