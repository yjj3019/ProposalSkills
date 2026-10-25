# AGENTS.md — Instructions for AI agents working in this repository

This repository contains **3 skills for Korean IT/public-sector proposals**. When a user
points to this repository and asks to install it (Korean example: "설치해줘"), run the line below.
Do not ask which directory to use: the script detects installed AI CLIs and installs into their skill directories.

```bash
python install_skill.py --auto
```

Use this command in a local environment with file and command execution tools. If Python is unavailable,
check `python3`; if there is no execution environment, report installation as not performed and continue
writing/reviewing the supplied material. Local installation does not install into a ChatGPT web account.
No external packages are required for installation.

## Documentation and display language

Write shared instructions, operational documentation, and code explanations in English.
Generated proposals follow the user and RFP language requirements.
Keep Korean README prose natural Korean; separate English guidance into language-specific files such as
`README.en.md`. Clearly label Korean examples and preserve their original content. Preserve product names,
commands, paths, configuration keys, code field names, status values, Korean test inputs, and raw validation evidence verbatim.

## Skill routing (all models)

| Role | Skill | Invocation |
|---|---|---|
| **Entry point (flagship)** | `create-best-proposal` | Implicit or explicit. Proposal-writing requests always start here |
| **Internal layers (siblings)** | `create-proposal-document`, `create-winning-proposal` | **Explicit invocation only** (`$skill-name`; original Korean placeholder: `$스킬명` / user requests only that layer). Never select implicitly |

Sibling skills provide the content and governance layers loaded by the flagship. Do not open them directly
unless the user names them. Claude prevents implicit sibling invocation with `disable-model-invocation: true`;
Codex/ChatGPT use `policy.allow_implicit_invocation: false` in `agents/openai.yaml`.
Do not apply this restriction to the flagship.

## Installation locations

`--auto` detects each tool's marker in the home directory and installs into its skill path.

| Detected marker | Installation path |
|---|---|
| `~/.claude/` exists | `~/.claude/skills/` |
| `~/.codex/` exists | `~/.agents/skills/` (**recommended for Codex**, shared AGENTS.md convention) |
| `~/.grok/` exists | `~/.grok/skills/` |
| `~/.agents/` exists | `~/.agents/skills/` |
| None | `~/.agents/skills/` |

If `AI_SKILLS_DIR` is set, include that path too. If `CODEX_HOME` is set, also install into
`$CODEX_HOME/skills` with a **legacy compatibility warning**: Codex still reads that deprecated compatibility
path, but `~/.agents/skills` is recommended. Do not use `CODEX_HOME` as the default `--dest`.
To inspect targets before installation, run `python install_skill.py --list-targets`.
For a specific path, use the original command example `python install_skill.py --dest <경로> --all`.

Install **all three** skills by default. Installing only the flagship (`create-best-proposal`) leaves
the unified gate unable to locate sibling gates and breaks the submission-decision path.

Existing installations are skipped (`Skip (exists)`). Add `--force` to update skill files.
Separately added user files are preserved.

## Post-installation checks

The script validates each skill's `SKILL.md`, `scripts/`, `references/`, and routing metadata
(openai.yaml / `disable-model-invocation`) and prints results.
If `Installed with problems` appears, report the missing files listed on that line.

If a functional check is needed, use this command (Korean path placeholders preserved):

```bash
python <설치경로>/create-best-proposal/scripts/unified_gate.py \
       <설치경로>/create-best-proposal/fixtures/audit_ready_financial.json --audit-only --no-explain
```

`STATUS: AUDIT-VALID` indicates success.

## Usage after installation

Use **only `create-best-proposal`** as the entry point for proposal requests.
Open the other two internal layers only when the user explicitly requests them or the flagship workflow directs you there.

## Plugins and environments without execution tools

For marketplace registration, installation, updates, or releases, first read the
[management guide](references/marketplace-management.md). Distinguish catalog IDs from plugin IDs,
and local direct installation from marketplace installation. Generate distribution ZIPs with
`package_plugin.py`; never ignore manifest/catalog linkage failures.

Distinguish ordinary ChatGPT/Claude chats from local Codex/Claude Code execution.
Do not infer file, Python, or rendering tools from the host name; check the current session.
Follow [host-portability.md](skills/create-best-proposal/references/host-portability.md) for shared execution
and natural-language starting requests. Supported ChatGPT `@` skill selection, Codex `$` invocation, and
Claude Code `/` invocation are host entry methods; uploading files does not automatically install/register a skill.

`plugin.json` uses the shared Agent Plugins format; `.codex-plugin/plugin.json` and
`.claude-plugin/plugin.json` are compatibility manifests. Distribute all three skills together using
`python package_plugin.py -o <ZIP경로>` (original Korean path placeholder). Both marketplace catalogs point to the repository root.

Invoke direct local installations with Codex `$create-best-proposal` or Claude Code/Grok Build
`/create-best-proposal`. Claude/Grok plugin invocation is `/proposal-skills:create-best-proposal`.
Web accounts require separate registration through that service. Uploading a folder to a project does not register a skill.

Without file/execution tools, write/review the supplied text and leave file generation and checks as not performed.
With execution tools, use the shared scripts. Never report an unexecuted check as passed or declare
`SUBMISSION-READY`. See the README for installation and invocation details.

## Public repository — never commit these

This repository is **public**. Proposal work involves sensitive information; committing material seen during
that work makes it permanently public. Never put the following in examples, fixtures, documentation, or commit messages:

- **Real customer, buyer, or competitor names**, business names, project numbers, or contract information.
- **Actual amounts, quotations, or unit prices**, performance figures, or personnel names/contact details/affiliations.
- **Original excerpts** from real RFPs/proposals, page images, or filenames.
- Workers' **local absolute paths** (Windows user folders or Unix home directories), email addresses, or internal workspace links.
- Credentials (API keys, tokens, passwords).

Use fictitious buyers (Korean example: `○○공사`) and synthetic figures for fixtures.
Transfer only **structural generalizations** from real documents (Korean example:
"요구가 100건을 넘으면 조견표가 9장이 된다"); do not transfer anything that identifies the source document.

`test_repo_hygiene.py` mechanically checks local paths, email addresses, credential patterns, and fixture buyers.
It cannot decide whether a name belongs to a real customer; that judgment relies on these rules and human review.

## When modifying this repository

- After changes, `python -m unittest discover -s . -p "test_*.py" -q` must pass.
- If gate behavior changes, add a reproduction test to `test_gate_integrity.py`.
- Follow the public-repository rules above. Retain only structural generalizations from real proposal material.
- The gate contract (submission-decision rules) is documented in `README.md` and
  `skills/create-winning-proposal/references/audit-schema.md`. Update code and documentation together.
- When changing routing metadata (implicit/explicit), maintain `test_skill_schema.py` and sibling/flagship symmetry.
  Never weaken gates, fixtures, or workflows.
