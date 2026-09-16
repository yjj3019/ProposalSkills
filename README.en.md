# ProposalSkills

English · [한국어](README.md)

ProposalSkills is a Korean Proposal Production & Governance Engine. It turns the requirements and
evaluation criteria of Korean IT RFPs into evaluator-centered technical proposals, and keeps the
real PPTX and the submission bundle in a verifiable state.

The repository holds model-neutral proposal skills and supporting research. The core `SKILL.md`
files, references, and verification scripts work the same way in ChatGPT, Claude, Gemini, Grok,
and other agents. Proposal content and templates target Korean-language public and enterprise
bids.

```
RFP / amendments → requirement & evaluation ledgers → win themes & lead-sentence map
  → slides.json → PPTX → number / render / audit checks → SHA-256 artifact binding
  → submission bundle check → SUBMISSION-READY
```

## Skills

| Skill | Role | Invocation | Use it for |
|---|---|---|---|
| **[`create-best-proposal`](skills/create-best-proposal/SKILL.md)** ★ **entry point** | **Unified flagship** — orchestrates content and governance, meta → audit, unified gate, bulk compliance matrix | Implicit and explicit ("write a proposal" always routes here) | Running a real proposal end to end, from bid decision to the submission gate |
| [`create-proposal-document`](skills/create-proposal-document/SKILL.md) | Internal content, style, and visual layer | **Explicit only** (`disable-model-invocation` / `allow_implicit_invocation: false`) | Deep work on writing style, structure, or slide layout (or when the flagship is unavailable) |
| [`create-winning-proposal`](skills/create-winning-proposal/SKILL.md) | Internal governance, audit, and gate layer | **Explicit only** | Bid / audit / gate work only (or when the flagship is unavailable) |

The three skills do not conflict. **The entry point is always `create-best-proposal`.** The other
two are internal layers that the flagship loads; open them directly only when the user names them.
Detailed style and schema sources live in the sibling skills' `references/`.

Writing quality and submission readiness are separate axes. A document skill alone produces a
well-written proposal that misses submission requirements; a governance skill alone produces a
document that passes but says nothing. The flagship enforces both.

> Scores shown in this repository are **structural check metrics** (file, keyword, and schema
> coverage). They do not measure win probability or visual quality, and they have not been
> validated by external blind evaluation.

## Installation

Give this repository to an AI CLI (Claude Code, Codex, Grok) and say **"install it"**. The AI reads
[AGENTS.md](AGENTS.md) and [CLAUDE.md](CLAUDE.md) in the repository root and runs:

```bash
git clone https://github.com/yjj3019/ProposalSkills.git
cd ProposalSkills
python install_skill.py --auto
```

`--auto` detects the AI CLIs installed on this machine and installs all three skills into each
skills directory without asking for paths.

| Detected | Install path |
|---|---|
| `~/.claude/` | `~/.claude/skills/` |
| `~/.codex/` | `~/.agents/skills/` (**recommended for Codex**, shared AGENTS.md convention) |
| `~/.grok/` | `~/.grok/skills/` |
| `~/.agents/` | `~/.agents/skills/` |
| none | `~/.agents/skills/` |

Use `--list-targets` to preview targets, `--dest <path> --all` to install to a specific path, and
`--force` to replace an existing install (by default existing installs are left untouched and
reported as `Skip`). If `AI_SKILLS_DIR` is set, that path is also a target. If `CODEX_HOME` is set,
the installer also writes to `$CODEX_HOME/skills` with a **legacy-compatibility warning** — Codex
still reads that path as deprecated compat, but the recommended location is `~/.agents/skills`, and
`CODEX_HOME` is never the `--dest` default. After installing, the installer verifies `SKILL.md`,
`scripts/`, `references/`, and routing metadata for each skill.

Installing all three skills is the default. With the flagship alone, the unified gate cannot find
the sibling gates and the submission path breaks. Install a single skill with
`--name create-proposal-document`.

**Updating:** the installer does not overwrite existing installs. After pulling the repository,
reinstall with `--force` so new references and scripts take effect.

```bash
git pull
python install_skill.py --auto --force
```

When uploading skills to a web environment, upload all three. Flagship documents reference files
in the sibling skills.

### ChatGPT / Codex plugin (Web / Work / Mobile)

**Uploading `skills/` to a project is reference material only; it does not register a skill.**
In ChatGPT and Codex Web, Work, and Mobile, register the package as a plugin.

1. [`.codex-plugin/plugin.json`](.codex-plugin/plugin.json) in the repository root points to
   `skills/` (flagship plus explicit-only siblings).
2. Register the package through a local or repository marketplace, or the plugin install flow.
   (Official docs: [Build plugins](https://developers.openai.com/codex/plugins/build),
   [Agent Skills](https://developers.openai.com/codex/skills))
3. After registration, "write a proposal" routes to `create-best-proposal`; siblings accept only
   explicit `$skill-name` calls.
4. Run gate scripts (`unified_gate.py` and others) from a local CLI.

TODO: marketplace submission, icon, and screenshot assets will be added under `.codex-plugin/` and
`assets/` once the distribution channel is decided. The package currently ships a minimal manifest
and the `skills/` layout.

Keeping `skills/create-best-proposal/` as project knowledge files is possible for reference use,
but it does not replace plugin or skill registration.

Selection and adoption records: [critical-selection-2026-08.md](references/critical-selection-2026-08.md) ·
three rounds of gate reliability audits and fixes (2026-09):
[gate-hardening-2026-09.md](references/gate-hardening-2026-09.md) — false-pass hardening → deck
production layer → artifact hash binding and a single verdict source.

## Writing method (before building slides)

Settle requirements, evaluation criteria, win themes, and the lead-sentence structure before
building slides. Do not open PowerPoint and look for the argument while filling slides
(requirement ledger → evaluation ledger → win themes → lead-sentence map → `slides.json` → PPTX).

| Stage | Document | Role |
|---|---|---|
| Pre-RFP positioning | [capture-and-positioning.md](skills/create-best-proposal/references/capture-and-positioning.md) | Record decision drivers, comparison axes, and capability gaps as FACT / HYPOTHESIS / UNKNOWN at the RFI or pre-notice stage. Feeds Pink only; never replaces the bid decision or any gate |
| Skeleton review (Pink) | [evaluator-journey.md](skills/create-best-proposal/references/evaluator-journey.md) | Link evaluator question → conclusion → evidence → buyer impact → commitment boundary to REQ-IDs and criteria. Check that the outline and lead sentences alone carry the argument |
| Technical writing | [technical-depth-six-questions.md](skills/create-best-proposal/references/technical-depth-six-questions.md) | Before writing a key technical slide, answer six questions (what, why, how it works, how it is built and run, how it is verified, what happens on failure), then compress to conclusion, mechanism, verification, and boundary |
| Style | [writing-style.md](skills/create-proposal-document/references/writing-style.md) | Banned overclaims and rules for ambiguous commitments ("support available", "under review") |
| Evaluator simulation (Red) | [master-playbook.md](skills/create-best-proposal/references/master-playbook.md) | For each criterion, report where the evidence is and the weaknesses (Critical / Major). No score or win-probability prediction |
| Public regulatory basis | [korean-public-proposal-regulatory-basis.md](skills/create-winning-proposal/references/korean-public-proposal-regulatory-basis.md) | Mapping of current Korean public procurement rules to the repository schema, authority order, and values that must never be constants |
| External method boundaries | [external-method-boundaries.md](skills/create-best-proposal/references/external-method-boundaries.md) | Concepts borrowed from foreign methodologies and public repositories, and rules that are not imported |

Authority order: amendment notice > the RFP > official Q&A > evaluation table > prescribed
submission forms > approved internal material > current official external sources > general
methodology. External methodology is a quality heuristic, not a source of facts. Technical-to-price
ratios, pass thresholds, and page, paper, and font limits differ per notice, so none of them is a
default anywhere.

## Deck production pipeline (PPTX)

```bash
# slides.json → PPTX. The script fixes coordinates, colors, and fonts; the model supplies content
python skills/create-proposal-document/scripts/build_deck.py slides.json -o proposal.pptx --strict
# Layout lint (lead sentence, REQ-IDs, page count, minimum font) + LibreOffice render + render block for audit
python skills/create-proposal-document/scripts/deck_check.py proposal.pptx --max-pages 40 \
  --exclude-cover-toc --require-req-ids --render --png-dir out/png --emit-render render.json
# A presentation version uses the same content with a different profile (font, density, and splitting change together)
python skills/create-proposal-document/scripts/build_deck.py slides.json -o presentation.pptx --profile presentation
```

Output type sets the standard. Choose it with `--profile presentation|executive-summary|detailed-submission`
(or `meta.output_profile`); font size, density, table rows, and matrix splitting change together.

| Profile | Use | Body | Tables / shape notes | Text per slide | Matrix rows |
|---|---|---|---|---|---|
| `detailed-submission` (default) | Detailed version for print / PDF scoring | 11pt | 10pt | 600 chars | 12 |
| `presentation` | On-screen presentation in a meeting room | 18pt | 14pt | 250 chars | 6 |
| `executive-summary` | Executive decision summary | 14pt | 12pt | 400 chars | 9 |

The font floor measures **body text and small text (table cells, legends, Gantt labels)
separately** — a single floor would let a slide pass with body text shrunk to table size. Text
whose size is set only at paragraph level is checked too.

Profiles live only in `deck_profiles.py`, which both the generator and the checker read, so the two
tools cannot drift. Generated PPTX files carry a stamp of the profile used, and `deck_check.py`
applies the same standard without arguments. **A missing or unknown stamp blocks at submission** —
externally built decks must pass `--profile` explicitly (they never silently fall back to the
loosest default).

**Buyer-specified output standards go into `meta.output_spec` as the notice states them**
(`source` required; `canvas`, `page_limit`, `font_min_pt`, `file_size_limit_mb` optional). The
generator and the checker share one resolver, the spec is stamped into the PPTX, and checker
arguments cannot lower the stamped font floor. A non-16:9 canvas (A4, A3, 4:3) is not generated;
those go through the prescribed form or the DOCX path. There are no numeric defaults —
see [deck-production.md §1-2](skills/create-proposal-document/references/deck-production.md).
Bundle-level properties (`anonymous_copy`, `price_separation`, `file_format`) are rejected here
and belong in `attachments[]`.

Builder safeguards: templates that still contain slides are **rejected** (old customer names and
amounts would remain and page counts would be off — use an empty template with masters and layouts
only). `rows_per_slide` accepts positive integers only, and the matrix compares input and output
row counts to block data loss. Page limits are checked against the actual slide count, not an
internal counter. `deck_check.py` blocks text shapes that leave the slide or are clipped by more
than 25%.

Twelve layouts (cover, TOC, section divider, matrix with auto-split, table, process, architecture
zones, Gantt, staffing, cards, bullets, closing), the schema, and the page-allocation formula are in
[deck-production.md](skills/create-proposal-document/references/deck-production.md).
End-to-end golden example: [fixtures/e2e-mini-rfp](skills/create-proposal-document/fixtures/e2e-mini-rfp/).
Without LibreOffice (`soffice`), rendering stays `NOT INSPECTED` and only the lint runs.
Dependency: `python-pptx`.

## create-best-proposal quick commands

```bash
# Authoring meta → audit JSON
python skills/create-best-proposal/scripts/build_audit_from_meta.py meta.json -o audit.json

# Type C bulk compliance matrix
python skills/create-best-proposal/scripts/bulk_matrix.py requirements.json -o matrix.md

# Unified gate (audit + hash check against the real document)
python skills/create-best-proposal/scripts/unified_gate.py audit.json --doc proposal.pptx --stage submission
python skills/create-best-proposal/scripts/unified_gate.py audit.json --audit-only   # audit only, no document → AUDIT-VALID

# Ledger numbers ↔ document (recognizes Korean notation variants such as 37억 / 3,700,000,000)
# — runs automatically inside unified_gate --doc; standalone form below
python skills/create-proposal-document/scripts/check_numbers.py proposal.pptx --audit audit.json

# Whole submission bundle (named, anonymous, and price volumes match the audit hashes)
python skills/create-best-proposal/scripts/unified_gate.py audit.json --doc proposal.pptx --bundle submission/

# Two-axis completeness
python skills/create-best-proposal/scripts/score_completeness.py audit.json   # root score_completeness.py is equivalent
```

## Submission verdicts are bound to real files

The audit JSON is **a record of human review**. If nobody checks which file that record applies
to, a past verdict gets reused on a document whose price or schedule changed after review. So the
submission verdict is bound to file hashes.

```bash
# 1) build the deck → 2) check it and emit a render block with the real hash
python .../build_deck.py slides.json -o proposal.pptx --strict
python .../deck_check.py proposal.pptx --render --emit-render render.json   # includes artifact_hash
# 3) put render.json into meta → build audit → 4) judge together with that file
python .../unified_gate.py audit.json --doc proposal.pptx --stage submission
```

| State | Meaning |
|---|---|
| `SUBMISSION-READY` | Only when the audit is `mode=submission` **and** the sha256 of the supplied file matches `render/package.artifact_hash` |
| `AUDIT-VALID` | `--audit-only` — the audit itself is valid but no file was inspected. Not a submission verdict |
| `DRAFT-READY` etc. | Passed the gate for that mode. Internal progress only |
| `CONDITIONAL-GO` | Internal work may continue. Not cleared for external submission |
| `BLOCKED` / `DECISION_MEMO_ONLY` / `INVALID` | Blocked / no-bid decision / schema or usage error |

Rules the gates enforce:

- `mode=submission` without `--doc` is **blocked**. `artifact_required: false` does not cancel the
  render and hash obligation of submission mode — one input value cannot switch checks off.
- A supplied file whose hash differs from the audit is blocked (change after review).
- In submission mode, `artifact_hash` must be a real `sha256:<64 hex>`, and render and package must
  point to the same file. String labels such as `sha256:proposal` are rejected.
- The supplied file must be **an OOXML package that actually opens**. Missing
  `[Content_Types].xml`, `_rels/.rels`, or body parts, or broken XML, is a usage error (exit 2) — a
  ZIP renamed to `.pptx` does not pass. Relationship parts and slide / document parts are **all
  parsed**, and `deck_check.py` opens the file once with python-pptx (structure checks only if the
  library is missing).
- **A missing check record is not a pass.** Without `render.layout_checked` the gate treats the
  layout as unchecked and blocks (deleting the field does not remove the requirement).
  Contradictions such as `verified: true` with `render_succeeded: false` are blocked. The
  meta → audit conversion carries check and approval records through unchanged.
- **Ledger entries must be human-readable.** In submission mode, requirement and claim entries need
  `text` (or `label` / `title` / `summary` / `description`). An ID-only ledger cannot show what
  "R1 approved" approved. Claims marked `kind: informational`, which skip evidence checks, need a
  `rationale`, so unsupported claims cannot escape by reclassification.
- **Classification changes the requirements.** When `context` records institution attributes,
  engagement type, procurement stage, and reading conditions as axes (axes, not names — a public
  hospital is `["public","healthcare"]`), the gate reads them. Public + submission requires the
  **evaluation ledger (`evaluation_criteria`)**, with point-total checks and blocking of scored
  items that no requirement answers. A mismatch between reading conditions and the actual deck
  profile, or **a missing profile record**, is blocked (missing = uninspected). Submission mode
  requires classification, because without it these checks would silently switch off.
- **Evaluation structure comes from the notice, not from the institution type.** The same
  "100 points" can mean technical 90 + price volume 10, a technical stage with 20 quantitative and
  80 qualitative points, or per-part pass thresholds. The evaluation ledger represents hierarchy
  (`parent`), ledger total (`evaluation_total`), pass threshold (`minimum_ratio`), and undisclosed
  weights (`disclosed`). The gate checks top-level and child sums and **never predicts scores or
  invents weights.** Values such as an 85% negotiation threshold or a 90:10 technical-to-price
  split vary per notice and are not constants.
- **Requirement strength is explicit.** `requirements[].strength` records
  required / recommended / optional / conditional / informational. Exceeding a recommended page
  count is not the same as violating a requirement, but submitting without following a
  recommendation needs a `rationale`.
- **An RFI is not a bid.** With `context.rfx_type: rfi`, the evaluation ledger is not required, and
  commitments (`kind: commitment`) are blocked — estimates must not become contractual promises.
  Eligibility, attachment, and format checks still apply.
- **The gate recomputes numbers.** Amounts, durations, and quantities in the `numbers[]` ledger have
  their sums (`components`) and ratios (`percent_of`) recomputed. In submission mode a bare
  `checks.arithmetic: true` does not pass. `check_numbers.py` confirms ledger values appear in the
  deck, including Korean notation variants, **only in body text the evaluator sees** (values only in
  notes, layouts, or masters are blocked), and distinguishes decimals, units, and signs. Amount
  totals are checked to an absolute error of one won, not a relative tolerance.
- **Vendor-dependent promises need confirmation.** A claim with `claims[].depends_on_vendor` needs
  a matching `vendor_confirmations` entry in submission mode — citing a vendor's public SLA is not
  the same as confirming that SLA applies to this contract.
- **Time-bound claims need a reference date.** Lifecycle, EOL, and version claims carry
  `time_sensitive: true` and `as_of` (YYYY-MM), so reused slides do not silently go stale.
- **Relations between numbers are checked.** `numbers[].at_most` / `at_least` express orderings
  such as "initial response ≤ sustained response". Durations are normalized to hours, so swapped
  values across units (`4 hours` vs `2 days`) are caught.
- **Engagement type shapes the outline.** `context.engagement` selects the outline skeleton
  (`build` / `migrate` → build, `operate` / `service-improvement` → maintenance,
  `product-selection` → technical response), and the audit's `proposal_archetype` records the one
  used. A mismatch is blocked. With `sections[]`, required sections for the skeleton are checked.
  **Education, consulting, and policy work have no outline basis in this repository and are not
  forced into a type.**
- **A submission is more than one file.** `attachments[]` entries carry a `role` with its own rules
  — anonymous copies need `anonymity_checked` and a reviewer, outputs that must not contain prices
  need `price_screened`, and every submitted attachment needs a `sha256`. `unified_gate.py --bundle
  <dir>` compares each attachment with the real file.
- **Ledger number checks run inside the unified gate.** With `--doc`, `check_numbers` runs
  automatically. A matching hash with an old amount still in the deck is blocked. `--skip-numbers`
  is not a pass for the submission verdict.
- **A successful render is not visual approval.** Submission mode requires
  `render.visual_review_approved` and `visual_reviewer`. `deck_check.py` always writes `false`; the
  person who reviewed the thumbnails changes it.
- Downgrading a `mode=submission` audit with `--stage draft` is a usage error (exit 2).
- Labels come from one place, `proposal_gate.readiness()` — the CLI, the **action table**, and the
  score report share the same verdict. `score_completeness.py` never inspects files and reports at
  most `AUDIT-VALID`.

Review state and compliance state are separate. A requirement with `support: X` (unsupported) or
`fit: GAP` cannot be `state: approved`; only buyer-granted exceptions count, via
`exception: {granted_by, evidence}`. Response locations go in `response_refs`, supporting sources in
`evidence_refs`. Details: [audit-schema.md](skills/create-winning-proposal/references/audit-schema.md).

## Tests

Run `pip install -r requirements.txt` before local runs (CI installs automatically). Without it,
`test_deck_pipeline.py` fails with `ModuleNotFoundError: No module named 'pptx'` — a missing
dependency, not a code defect. If every PPTX-building test fails with
`PackageNotFoundError: ...pptx\templates\default.pptx`, the python-pptx install is damaged; repair
it with `pip install --force-reinstall --no-cache-dir python-pptx`.

```bash
cd ProposalSkills
python -m unittest discover -s . -p "test_*.py" -q
python skills/create-winning-proposal/scripts/test_proposal_gate.py -q
python skills/create-best-proposal/scripts/test_best_proposal.py -q
```

The root run currently executes 466 tests. GitHub Actions (`.github/workflows/ci.yml`) runs the same
suite on Ubuntu and Windows × Python 3.10 and 3.12 (Ubuntu installs LibreOffice to cover the render
path). The golden stage tests the hash-binding contract itself — that submission without a document,
hash mismatch, and stage downgrade are each blocked, and that `SUBMISSION-READY` appears only when
file and hash match.

A single root `python -m unittest discover -s . -p "test_*.py" -t .` also runs **the tests inside the
skills** (`test_skill_scripts.py` pulls in `skills/*/scripts/test_*.py`). `discover` does not recurse
into non-package directories, so those files previously ran only in CI.

Tests call skill scripts **in-process** (`test_support.run_script`). Every script exposes
`main(argv) -> int`, so no interpreter starts per call. Child processes are used only when they are
the subject of the test — console encoding (cp949), exit codes reaching the shell, running an
installed copy. `SpeedContractTests` enforces this.

Scope of each regression test file:

- `test_gate_hardening.py` — false passes and fail-open paths (unchecked notes, masters, headers;
  overclaims split across runs; string booleans; SUBMISSION-READY on a draft audit; cp949 console
  crashes).
- `test_deck_pipeline.py` — the mini-RFP golden run through slides.json → PPTX → deck_check →
  quality_gate → audit → unified_gate.
- `test_gate_integrity.py` — artifact hash binding, single verdict source, schema loss, evidence vs.
  compliance separation, chart category extraction, with positive controls against over-blocking.
- `test_context_classification.py` — classification axes, public evaluation ledger requirement,
  point totals, unanswered scored items, reading conditions vs. deck profile, conversion
  preservation.
- `test_output_profiles.py` — per-profile font and density differences, stamp round trip, generator
  and checker reading the same definition.
- `test_output_spec.py` — buyer-specified output standard precedence, profile fallback, rejection of
  unknown canvases and keys, font floor that arguments cannot lower, spec stamp round trip and
  tampering.
- `test_ambiguous_commitment.py` — ambiguous-commitment detection with false-positive controls
  (named-party conditions, capability descriptions, buyer as subject, quantified sentences) and the
  non-blocking warning contract.
- `test_skill_schema.py` — skill routing metadata, broken relative paths, references not linked from
  any document.
- `test_numbers_ledger.py` — sum and ratio recomputation, blocking of self-declared arithmetic
  without a ledger, document matching (Korean notation variants, number boundaries).
- `test_gate_integrity2.py` — bypassing verification (`artifact_required:false`), packages that do
  not open, contradictory explanations (including `--explain`), unaccepted aliases, leftover template
  slides, matrix row loss, off-slide placement, enum type errors.
- `test_gate_hardening_d.py` — approval records surviving conversion, missing or contradictory check
  records, uncomputable ledgers, decimal / unit / sign / body-only matching, broken package parts,
  inherited paragraph fonts and group coordinates, installer protection of user files, readable
  ledger entries, plus a **normal-path e2e** so hardening does not block valid output.
- `test_repo_hygiene.py` — no local absolute paths, emails, internal links, or credential-shaped
  strings committed, and fixture buyers use fictional names.
- `test_rfx_rules.py` — evaluation structures seen in public RFx documents (price volume, hierarchy,
  pass thresholds, undisclosed weights) reproduced with synthetic data, requirement strength, RFI
  rules. No source text is stored.
- `test_submission_bundle.py` — per-role attachment rules, `--bundle` hash checks, ledger ↔ document
  number checks in the unified gate.
- `test_real_proposal_findings.py` — gaps found by running one real public proposal through the
  gates (vendor-dependent commitments, reference dates, SLA relations, superlatives), reproduced as
  rules on synthetic data only.
- `test_outline_archetypes.py` — engagement type ↔ outline skeleton, required sections, no forced
  type for unsupported sectors, reading environment vs. document role.
- `test_skill_scripts.py` — merges in-skill tests into the root run and checks that no test file is
  left out of every execution path.

OOXML fixtures are built in one place, `ooxml_fixtures.py`, and tests confirm they open with the real
loader.

Common gate script contract: exit 0 = pass, 1 = blocked, 2 = usage error, damaged file, or schema
error. Audit JSON booleans accept only `true` / `false`; strings such as `"yes"` are INVALID. A plain
ZIP renamed to `.pptx` is rejected as a usage error, not passed as "no text".

## What the gates do not check

A pass does not mean "safe to submit". The automated gates check **structural completeness** only.

- **Truth of claims** — the gate checks that evidence is attached, not that it is true.
- **Numbers outside the ledger** — only values in `numbers[]` are computed and matched.
- **Table cell overflow and occlusion** — `deck_check.py` catches off-slide placement and large
  clipping, but text overflowing inside cells or shapes hiding each other must be checked in the PNG
  thumbnails.
- **Content of ledger entries** — the gate checks that entries are readable, not that they match the
  RFP text.
- **Rendering differences** — LibreOffice and PowerPoint differ in line breaks and font
  substitution. Open the final deck once in PowerPoint.
- **Sector judgment** — only the **public sector** profile is provided
  ([sectors/](skills/create-winning-proposal/references/sectors/)). Enterprise, education, and
  healthcare have classification axes and gate rules but no content, rather than unverifiable
  guidance.
- **Meaning of ambiguous commitments** — `[모호확약]` in `quality_gate.py` is a sentence-level
  heuristic warning. It never affects the submission verdict; people judge whether a promise is
  appropriate.
- **Scores and win probability** — Red review reports evidence locations and weaknesses per
  criterion. It does not predict scores.
- **Comparative proposal quality** — the repository does not measure win rate or persuasiveness.
  That requires independent blind scoring of outputs produced under identical conditions, which is
  human work and has not been done.

## Materials

Most research notes below are written in Korean.

- [Skill comparison and cross-improvements](references/skill-comparison-and-improvements.md)
- [Skill material research notes](references/proposal-skill-materials-research.md)
- [Related public Git repositories](references/proposal-related-git-repositories.md) (includes the 2026-09 proposal-skill repository benchmark)
- [Deep audit of 39 repositories and Gists](references/repository-deep-audit.md)
- [Ten simulation runs and improvement results](references/simulation-report-10-runs.md)
- Per-type simulation reports: local `simulation/output/SIMULATION_REPORT.md` (not in the repository, `.gitignore`)
