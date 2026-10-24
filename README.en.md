# ProposalSkills

English · [한국어](README.md)

Skills for Korean IT proposals, from requirements analysis to PPTX production, review, and submission preparation.
ChatGPT/Codex, Claude, and Grok share the same guidance and verification scripts.

## Installation

Choose marketplace installation or direct local installation. All three skills are installed together.

### Codex

```bash
codex plugin marketplace add yjj3019/ProposalSkills --ref main
codex plugin add proposal-skills@proposal-skills-marketplace
```

### Claude Code

```text
/plugin marketplace add yjj3019/ProposalSkills
/plugin install proposal-skills@proposal-skills-marketplace
```

### Direct local installation

```bash
git clone https://github.com/yjj3019/ProposalSkills.git
cd ProposalSkills
python install_skill.py --auto
```

Use `--list-targets` to preview installation locations. To update an existing installation, run
`git pull`, then `python install_skill.py --auto --force`.
See [marketplace management](references/marketplace-management.md) for updates and ZIP distribution.

## Usage

The entry point is **`create-best-proposal`**.
Use `$create-best-proposal` in Codex, `/create-best-proposal` for a direct Claude Code installation,
or `/proposal-skills:create-best-proposal` for the Claude plugin.
In supported ChatGPT environments, select the registered skill. Attaching files does not install a skill.

Provide the RFP, amendments, evaluation criteria, required templates, and available evidence, then ask:

> Use create-best-proposal to draft a proposal for the attached RFP.
> Organize the requirements and evaluation criteria, and flag unsupported content for confirmation.
> Define the outline and key messages, create the PPTX, and run the available checks.

Workflow: **requirements and evaluation ledgers → outline and key messages → slides → review and submission checks**.

| Skill | Role |
|---|---|
| [create-best-proposal](skills/create-best-proposal/SKILL.md) | Integrated workflow from authoring to submission checks |
| [create-proposal-document](skills/create-proposal-document/SKILL.md) | Content, writing style, and slide production |
| [create-winning-proposal](skills/create-winning-proposal/SKILL.md) | Evidence, approvals, and submission requirements |

The other two skills are internal layers used by the integrated skill. Invoke them directly only when explicitly named.

## Verification scope

Automated checks verify consistency across requirements, evidence, numbers, file hashes, and submission bundles.
If the final hash comparison detects an audit or document change or deletion during checks, the gate returns `INVALID`.
People must compare claims, OCR results, persuasiveness, and final visual quality against the sources and actual output.
`AUDIT-VALID` means the records passed validation; it is not submission approval. `SUBMISSION-READY` applies
when the file matches the required checks and approval records. It does not guarantee a successful bid.

PPTX generation and inspection require `python-pptx`; rendering checks require LibreOffice and Poppler.
Without file or execution tools, proceed with text authoring and review, and mark unrun checks as not performed.
Keep source documents, customer materials, and working output outside this public repository.

## Detailed guides

- [Host-specific installation, invocation, and execution scope](skills/create-best-proposal/references/host-portability.md)
- [Evidence-based authoring and Red review](skills/create-proposal-document/references/quality-first-authoring.md)
- [Slide production and output specifications](skills/create-proposal-document/references/deck-production.md)
- [Source extraction, OCR, amendments, and visual comparison](skills/create-proposal-document/references/source-and-visual-evidence.md)
- [Submission gate and audit schema](skills/create-winning-proposal/references/audit-schema.md)
- [Related project analysis](references/proposal-related-git-repositories.md)

## Development and testing

```bash
pip install -r requirements.txt
python -m unittest discover -s . -p "test_*.py" -q
```

Before contributing, read [AGENTS.md](AGENTS.md) for change, verification, and public-data rules.
