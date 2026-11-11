# ProposalSkills

[한국어](README.md)

A Korean IT proposal plugin for RFP analysis, editable PPTX authoring, review, and submission checks.
Shared instructions, operational guides, and code explanations are in English. README.md provides a Korean quick start.

## Install

### Codex · ChatGPT desktop

Register the marketplace and install with the Codex CLI.

```bash
codex plugin marketplace add yjj3019/ProposalSkills --ref main
codex plugin add proposal-skills@proposal-skills-marketplace
```

Restart the app and start a new conversation after installation.

### Claude Code

```text
/plugin marketplace add yjj3019/ProposalSkills
/plugin install proposal-skills@proposal-skills-marketplace
```

All three skills install together. See the [management guide](references/marketplace-management.md) for updates, direct installation, and ZIP packaging.

## Use

Provide the RFP, amendments, evaluation criteria, required templates, and available evidence, then ask:

> Use create-best-proposal to write a proposal for the attached RFP.
> Map requirements and evidence, create the PPTX, and review numbers and slide quality.

Start with `$create-best-proposal` in Codex or `/proposal-skills:create-best-proposal` in the Claude plugin.
In supported ChatGPT environments, select the installed skill.

## Included skills

| Skill | Role |
|---|---|
| [Unified proposal workflow](skills/create-best-proposal/SKILL.md) | Unified entry for authoring, review, and submission checks |
| [Proposal content and slides](skills/create-proposal-document/SKILL.md) | Content, writing style, and PPTX generation |
| [Evidence and submission review](skills/create-winning-proposal/SKILL.md) | Requirements, evidence, and approval validation |

The unified entry uses the two internal skills; name them explicitly for standalone work.

## Runtime and verification

PPTX generation and inspection require Python 3.10+ and `python-pptx`; automated rendering requires LibreOffice and Poppler.
Installing the plugin does not install these tools. Automated checks do not replace factual review, visual review, or submission approval.
Keep customer materials and generated output outside this public repository.

[Authoring and review](skills/create-proposal-document/references/quality-first-authoring.md) ·
[Slide specifications](skills/create-proposal-document/references/deck-production.md) ·
[Submission checks](skills/create-winning-proposal/references/audit-schema.md) ·
[Development and contribution](AGENTS.md)

## Helper checks

Standard-library scripts; each prints what it did not check and never replaces review. See each script's docstring for exit codes.

| Script | Purpose |
|---|---|
| [`sensitive_scan.py`](skills/create-best-proposal/scripts/sensitive_scan.py) | Find credentials and personal data in PPTX/DOCX/XLSX and text before sharing; unreadable files are reported, not skipped |
| [`edit_preservation.py`](skills/create-proposal-document/scripts/edit_preservation.py) | Block a wording edit that lost or invented a figure, date, ID, link, quote or hedge |
| [`deck_story_check.py`](skills/create-proposal-document/scripts/deck_story_check.py) | Print the titles-only "ghost deck"; flag duplicate titles and unsourced figures |
| [`plain_language_check.py`](skills/create-proposal-document/scripts/plain_language_check.py) | Long sentences, unexpanded acronyms, self-narration, filler, passive stacks |
| [`deck_stage_gate.py`](skills/create-proposal-document/scripts/deck_stage_gate.py) | Gate a deck workspace: approved design spec bound to its hash, plan matches `slides.json` |
| [`verification_report.py`](skills/create-best-proposal/scripts/verification_report.py) | Validate that a check report matches the delivered file and does not overstate its depth |
| [`retry_guard.py`](skills/create-best-proposal/scripts/retry_guard.py), [`evidence_chain.py`](skills/create-best-proposal/scripts/evidence_chain.py), [`handoff_lint.py`](skills/create-best-proposal/scripts/handoff_lint.py) | Stop rule for fix-and-recheck loops, tamper-evident check log, hand-off note lint |
| `gate_mutation_probe.py`, `skill_audit.py`, `merge_guard.py`, `hook_guard_bash.py` | Repository tools: weaken-a-gate probe, skill safety and license audit, advisory PR readiness, opt-in destructive-command hook |

Release notes: [CHANGELOG.md](CHANGELOG.md).

## License

[MIT](LICENSE)

[Third-party notices](THIRD-PARTY-NOTICES.md)
