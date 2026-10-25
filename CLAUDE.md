# CLAUDE.md

The repository's AI instructions are in [AGENTS.md](AGENTS.md). Follow that file.

Summary: when a user requests local installation and execution tools are available, run
`python install_skill.py --auto`. It detects installed AI CLIs and installs all three skills into
their skill directories (`~/.claude/skills/` for Claude Code).

In chats without execution tools, do not claim installation occurred; write/review the supplied material.
Follow the [shared guide](skills/create-best-proposal/references/host-portability.md) for environment-specific execution.
