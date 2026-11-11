# Third-party notices

ProposalSkills is released under the [MIT License](LICENSE). This file records what it depends on and what it was
inspired by, so the licensing position of the repository stays auditable. It is a development record, not legal advice.

## Bundled third-party material

None. The repository contains text, Python source and JSON only. No third-party code, fonts, images, templates, or
other assets are bundled or redistributed. `test_license_hygiene.py` fails if a new binary or asset file is added
without being recorded here first.

## Runtime dependencies (installed by the user from `requirements.txt`; not redistributed here)

| Package | License | Used by |
|---|---|---|
| python-pptx | MIT | `build_deck.py`, `deck_check.py` and related deck tools |
| Pillow | MIT-CMU (HPND family) | `visual_compare.py` (also a dependency of python-pptx) |

python-pptx in turn installs lxml (BSD-3-Clause), XlsxWriter (BSD-2-Clause) and typing_extensions (PSF-2.0). Their
licenses apply to those packages when a user installs them; none of their code is included in this repository.
Optional tools (LibreOffice for rendering) are installed separately by the user under their own licenses.

## Ideas credited, nothing reused

The following projects inspired the design of a few checks. Only general ideas were taken; no code, prompt text,
examples, or assets from them are present in this repository. Details are in
`references/provenance-harness-review-2026-11.md`.

| Project | License | Idea | Where it ended up |
|---|---|---|---|
| [blader/humanizer](https://github.com/blader/humanizer) | MIT | Edit prose for clarity while preserving facts and uncertainty | `edit_preservation.py` |
| [hugohe3/ppt-master](https://github.com/hugohe3/ppt-master) | MIT | Staged, gated deck workflow with a locked design spec | `deck_stage_gate.py` |
| [alchaincyf/huashu-design](https://github.com/alchaincyf/huashu-design) | MIT | Verify the saved artifact and report which checks really ran | `verification_report.py` |

The repository owner's separate private agent-harness repository (Apache-2.0, same author) was also reviewed for ideas.
Its content is not included; the overlap check and rewording are recorded in the provenance file.

## Format knowledge and planning notes

- HWPX (Hancom) is read through its published package layout (a ZIP of XML parts such as `Contents/section*.xml`). No
  Hancom or third-party library, specification text or sample file is included; the committed HWPX tests build synthetic files.
- The owner's own planning notes (a growth and execution guide) were a source of ideas. The third-party repositories that
  guide lists as candidates were not consulted, copied from or depended on, and nothing from them was adopted.

## Obligations going forward

- Adding third-party code, text, fonts, images, or templates requires recording the exact license and notice here
  first and preserving the notice in the file itself.
- Keep every `SKILL.md` declaring `license:` and `python skill_audit.py` green.
