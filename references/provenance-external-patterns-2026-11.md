# Provenance record: patterns reviewed in public skill repositories (2026-11-24)

This record states what was reviewed, which ideas were adopted, and which were deliberately not adopted, so the licensing
position of every addition is auditable. It is a development record, not legal advice.

## How the review was done

Twenty-eight public repositories were read through the GitHub API (file lists, licenses, and the documents named below). No
repository was cloned or executed. Performance figures in their READMEs (for example token savings) were read but not verified.
The three that carry skills for the same job as this repository (a quality loop, an evaluation harness, a maintenance
discipline) were read closely; the rest were screened for relevance and recorded under "Not adopted".

## Licensing position

- Everything adopted is an **idea implemented independently** in Python for this repository's standard-library toolchain. No
  source file, test, document text, or data was copied or translated line by line, so no third-party notice is carried here.
- This repository is MIT. If any text or code from the sources below were later copied, the source license's notice
  requirements would apply (Apache-2.0: license copy, change notices, retained attributions) and this record must be updated first.
- `anthropics/skills` reports no repository-level license; each skill folder carries its own Apache-2.0 `LICENSE.txt`, which is what
  the one idea below is attributed to.

## Adopted (idea, then independent implementation here)

| Source (license) | Idea | Implementation here |
|---|---|---|
| `kajisho5/ffmpeg-skill` (MIT), `GoogleChrome/modern-web-guidance-src` (Apache-2.0) | A register of behaviours that look like defects but are decisions, each with rationale, location and pinning test | `references/design-decisions.md`, `repo_records.py` |
| `kajisho5/ffmpeg-skill` (MIT) | A change's own test must fail without the change | `revert_proof.py`, `test_revert_proof.py` |
| `GoogleChrome/modern-web-guidance-src` (Apache-2.0) | Replay saved inputs through the old and new grader and triage the differences | `gate_replay.py`, `test_gate_replay.py` |
| `kajisho5/ffmpeg-skill` (MIT) | A defect ledger with the class, why checks missed it, and the mechanism that now prevents it; a guard test once a class repeats | `references/defect-ledger.jsonl`, `references/defect-guards.json`, `repo_records.py` |
| `anthropics/skills` skill-creator (Apache-2.0), `kajisho5/ffmpeg-skill` (MIT) | Measure skill triggering by running prompts through the headless CLI and reading the tool calls | `trigger_eval_run.py`, `test_trigger_eval_run.py`; the Codex and Grok event shapes were observed from real runs, not from these sources |

## Not adopted, and why

- **Text and context compression** (`JuliusBrussee/caveman`, `headroomlabs-ai/headroom`): shortening proposal text or evidence loses
  detail this repository must keep, and `caveman-compress` sends file text to a model provider.
- **Animation, graphics and video** (`airbnb/lottie-web`, `motion-canvas/motion-canvas`, `tsparticles/tsparticles`,
  `rough-stuff/rough`, `metafizzy/zdog`, `theatre-js/theatre`, `hydra-synth/hydra`, `remotion-dev/remotion`, the Blender and
  Muse skills, `ComfyUI-ReaVideoBreakdown`): unrelated to generating a proposal deck with python-pptx. `remotion` and `serena` report
  a license without a standard identifier, `zdog` reports none, and `hydra` is AGPL-3.0; none was a candidate for reuse.
- **Social research and web design** (`ScrapeCreators/social-media-research-skills`, `mvanhorn/last30days-skill`, `MengTo/Skills`):
  different domain; the first two are built around third-party data services.
- **Developer tooling** (`dream-num/univer`, `oraios/serena`, `colbymchenry/codegraph`, `ag-ui-protocol/ag-ui`, `meta/astryx`,
  `DietrichGebert/ponytail`): a JavaScript office SDK, code-navigation servers, a protocol and a design system do not fit a
  stdlib-and-python-pptx repository of about sixty tests.
- **`elementalsouls/Claude-BugHunter`**: offensive-security content; only its use of an on/off skill ablation was noted. A blind
  comparative evaluation of proposals stays out of scope for the reason recorded in `gate-hardening-2026-09.md` (no independent evaluators).
