#!/usr/bin/env python3
"""Claude Code PreToolUse(Bash) hook: deny a short list of destructive commands.

This is a lexical guardrail, NOT a security boundary and not a sandbox. It splits the command on `;`, `&&`, `||`,
`|` and newlines, tokenizes each part, and denies:
  - `rm` with a recursive/force flag aimed at a broad target (/, ~, $HOME, ., .., *, a drive root, a top-level folder)
  - `git push --force` / `-f` / `+refspec`, `git reset --hard`, `git clean -f`, `git checkout -- .`, `git restore .`
  - a download piped into a shell (`curl ... | sh`)
Aliases, functions, substitutions, variables and encoded payloads can evade it; real approval and host permissions
are still required for external or destructive effects. Unparsable input is denied (fail closed).

Hook protocol: reads the hook JSON on stdin (`tool_input.command`). Exit 0 allows, exit 2 denies with the reason on stderr.

Opt-in setup (nothing is installed automatically), in .claude/settings.json:
  {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "python hook_guard_bash.py"}]}]}}
"""
from __future__ import annotations

import json
import re
import shlex
import sys

SPLIT = re.compile(r"\|\||&&|;|\||\n")
PIPE_TO_SHELL = re.compile(r"\b(?:curl|wget)\b[^\n|]*\|\s*(?:sudo\s+)?(?:ba|z|da|k)?sh\b", re.I)
BROAD = re.compile(r"^(?:/|/\*|~|~/.*|\$HOME(?:/.*)?|\$\{HOME\}(?:/.*)?|\.|\.\.|\*|\./\*|\.\./\*|[A-Za-z]:[\\/]?|/[A-Za-z0-9._-]+/?)$")
WRAPPERS = {"sudo", "command", "env", "nohup", "time"}
GIT_VALUE_OPTIONS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}


def rm_denied(words: list[str]) -> str | None:
    flags = "".join(w.lstrip("-") for w in words if w.startswith("-") and not w.startswith("--"))
    long_flags = {w for w in words if w.startswith("--")}
    recursive = "r" in flags.lower() or "--recursive" in long_flags
    if not recursive:
        return None
    targets = [w for w in words if not w.startswith("-")]
    for target in targets:
        if BROAD.match(target.replace("\\", "/")) or BROAD.match(target):
            return f"recursive rm of broad target {target!r}"
    return None


def git_denied(words: list[str]) -> str | None:
    i = 1
    while i < len(words):
        word = words[i]
        if word in GIT_VALUE_OPTIONS:
            i += 2
            continue
        if word.startswith("-"):
            i += 1
            continue
        break
    if i >= len(words):
        return None
    sub, rest = words[i], words[i + 1:]
    if sub == "push" and (any(w in {"-f", "--force"} or w.startswith("--force-with-lease") for w in rest)
                          or any(w.startswith("+") and len(w) > 1 for w in rest)
                          or any(re.fullmatch(r"-[a-zA-Z]*f[a-zA-Z]*", w) for w in rest)):
        return "git push with force"
    if sub == "reset" and "--hard" in rest:
        return "git reset --hard"
    if sub == "clean" and any(re.fullmatch(r"-[a-zA-Z]*f[a-zA-Z]*", w) or w == "--force" for w in rest):
        return "git clean with force"
    if sub in {"checkout", "restore"} and any(w in {".", "*"} for w in rest) and (sub == "restore" or "--" in rest):
        return f"git {sub} that discards all working-tree changes"
    return None


def deny_reason(command: str) -> str | None:
    if PIPE_TO_SHELL.search(command):
        return "download piped into a shell"
    for part in SPLIT.split(command):
        if not part.strip():
            continue
        try:
            words = shlex.split(part, posix=True)
        except ValueError:
            return "command could not be parsed (unbalanced quote)"
        while words and (words[0] in WRAPPERS or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", words[0])):
            words = words[1:]
        if not words:
            continue
        name = words[0].replace("\\", "/").rsplit("/", 1)[-1].lower().removesuffix(".exe")
        reason = rm_denied(words[1:]) if name == "rm" else git_denied(words) if name == "git" else None
        if reason:
            return reason
    return None


def main(stdin=None) -> int:
    raw = (stdin or sys.stdin).read()
    try:
        command = json.loads(raw).get("tool_input", {}).get("command", "")
    except (ValueError, AttributeError):
        print("Blocked: hook input is not valid JSON", file=sys.stderr)
        return 2
    if not isinstance(command, str):
        print("Blocked: command is not text", file=sys.stderr)
        return 2
    reason = deny_reason(command)
    if reason:
        print(f"Blocked by hook_guard_bash.py: {reason}. Ask the user to run it or approve it explicitly.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
