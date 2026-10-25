# ProposalSkills marketplace management

One repository supplies catalogs for two hosts and distributes the same three skills as one plugin.
Do not duplicate the plugin into another folder. Both catalogs' source points to the repository root `./`.
Store the display name, description, and starting prompts in `extensions.com.openai.interface` in root `plugin.json`.
OpenAI extensions are not merged into compatibility manifests, so keep `interface` in
`.codex-plugin/plugin.json` identical. The three skills are discovered under root `skills/`.

| Item | Value |
|---|---|
| Repository | `yjj3019/ProposalSkills` |
| Marketplace ID | `proposal-skills-marketplace` |
| Plugin ID | `proposal-skills` |
| Installation identifier | `proposal-skills@proposal-skills-marketplace` |
| Claude catalog | `.claude-plugin/marketplace.json` |
| Codex catalog | `.agents/plugins/marketplace.json` |
| Shared manifest / host compatibility manifests | `plugin.json` / `.codex-plugin/plugin.json` / `.claude-plugin/plugin.json` |

The name after `@` is the catalog's `name`, not the GitHub owner.
This marketplace differs from existing `yjj3019` and `fef-marketplace` marketplaces.
Changing an existing ID also changes the installation identifier; retain names and increment the plugin version.

## Registration and installation

Claude Code session:

```text
/plugin marketplace add yjj3019/ProposalSkills
/plugin install proposal-skills@proposal-skills-marketplace
```

Codex CLI (versions supporting `plugin add`):

```bash
codex plugin marketplace add yjj3019/ProposalSkills --ref main
codex plugin add proposal-skills@proposal-skills-marketplace
```

The Codex installation selector was checked using `codex plugin add --help` in the documentation environment.
If an older version lacks the command, use the supported desktop plugin installation screen.
Editing a local checkout does not change what GitHub installs: the desired version must be available remotely.
Presenting these commands is separate from actually registering/installing the plugin.

After registration, start with Claude `/proposal-skills:create-best-proposal` or Codex `$create-best-proposal`.
Select the installed skill in supported ChatGPT selectors.
Manual skill installation and plugin installation are alternatives; duplicate installations can expose duplicate skill names.

## Direct local installation

Install the three skills directly on file-based hosts without marketplace support.
Choose one installation method to avoid duplicate skills.

```bash
git clone https://github.com/yjj3019/ProposalSkills.git
cd ProposalSkills
python install_skill.py --auto
```

Use `--list-targets` to inspect targets. To update a direct installation, run `git pull`, then
`python install_skill.py --auto --force`. Direct-install Claude invocation is `/create-best-proposal`.
Uploading files alone does not install into ChatGPT.

## Updates

Claude catalog refresh and installed-plugin update (CLI):

```bash
claude plugin marketplace update proposal-skills-marketplace
claude plugin update proposal-skills@proposal-skills-marketplace
```

Codex catalog refresh and available-plugin listing:

```bash
codex plugin marketplace upgrade proposal-skills-marketplace
codex plugin list
```

Do not assume refreshing a catalog completed an installed-plugin update.
Check the host's installation/update result and actual installed version; use a new chat or restart if needed.
Do not update by overwriting files in the installation cache. Keep user material in a separate working folder.

## Release preparation and validation

The current local candidate version is `1.2.5`. This does not imply a GitHub release, tag, or official-directory publication.

1. Match names, versions, descriptions, and authors across all three manifests. Update all three when changing versions.
2. Check both catalogs contain exactly one `proposal-skills` entry pointing to the same root.
3. Run and inspect the checks below. Verify actual host installation/invocation separately in the deployment environment.

```bash
python -m unittest test_skill_schema -q
python -m unittest discover -s . -p "test_*.py" -q
claude plugin validate .
python package_plugin.py -o dist/proposal-skills-1.2.5.zip
```

Historical validation on 2026-10-25: in a temporary home with Codex CLI 0.164.0, local catalog registration,
1.2.3 installation, and installed/enabled listing state were confirmed. All three cached SKILL.md hashes matched
the originals. The installed audit-only check returned AUDIT-VALID; submission without an actual document
returned BLOCKED. These checks are distinct from UI discovery/invocation validation.

Packaging checks JSON parsing, identity across the three manifests, Codex skill paths, catalog names,
and missing/duplicate/source entries for this plugin. These are this repository's linkage checks,
not a general schema validator for all external catalogs or remote plugins.
On errors, packaging fails without creating a ZIP. Existing ZIPs are not overwritten.
A valid ZIP includes both catalogs, shared/compatibility manifests, three skills, and the Python dependency list.

## Repository marketplace versus official directory

Repository registration downloads a user-specified catalog. Publication in an official public directory is a
separate process. Passing local Claude validation does not rule out additional directory-publication findings.
The repository currently specifies no license and has no directory icon, resulting in related findings.
Do not choose a rights holder's license or publish publicly on their behalf in this task.

Root CLAUDE.md guides repository maintainers/agents. Do not assume it is automatically loaded as project
context on installation. Plugin execution instructions are in the three distributed SKILL.md files and references.

Format and registration sources (checked 2026-10-24):
[Claude marketplace guide](https://code.claude.com/docs/en/plugin-marketplaces),
[OpenAI plugin packaging guide](https://developers.openai.com/plugins/build/plugins).
