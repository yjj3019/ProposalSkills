#!/usr/bin/env python3
"""Claude Code PreToolUse(Bash) hook: deny a short list of destructive commands.

This is a lexical guardrail, NOT a security boundary and not a sandbox. It splits the command on `;`, `&&`, `||`,
`|` and newlines, tokenizes each part, and denies:
  - `rm` with a recursive/force flag aimed at a broad target (/, ~, $HOME, ., ./, .., *, .*, a drive root, a top-level folder)
  - `git push --force` / `--force-with-lease` / `-f` / `+refspec` / `--delete` / `:branch`, `git reset --hard`,
    `git clean -f`, `git checkout .`, `git restore .`, `git stash drop|clear`, `git branch -D`
  - a download piped or substituted into a shell (`curl ... | sh`, `bash <(curl ...)`, `eval $(curl ...)`)
  - the same commands wrapped in `bash -c '...'`, `sh -c "..."` or `eval ...` (the inner text is checked again)
  - `find` with `-delete` and no filter, `dd of=/dev/...`, `mkfs`, `shred`, `xargs rm -r`, `chmod/chown -R` or `mv` on a
    broad target, a redirect into /etc and similar system folders, a fork bomb, `format C:`, and PowerShell
    `Remove-Item -Recurse` on a broad target
Aliases, functions, variables, other substitutions and encoded payloads can still evade it; real approval and host
permissions are required for external or destructive effects. Unparsable input is denied (fail closed).
`--force-with-lease` is denied on purpose: it is still a history rewrite on a shared branch, so the user decides.

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
PIPE_TO_SHELL = re.compile(
    r"\b(?:curl|wget)\b[^\n|]*\|\s*(?:sudo\s+)?(?:ba|z|da|k)?sh\b"
    r"|\b(?:(?:ba|z|da|k)?sh|source|eval)\b[^\n]*(?:<\(|\$\(|`)\s*(?:curl|wget)\b", re.I)
SYSTEM_REDIRECT = re.compile(r"(?:^|\s)\d?>>?\s*/(?:etc|boot|bin|sbin|usr|lib|dev/(?!null\b|stderr\b|stdout\b|tty\b))", re.I)
BROAD = re.compile(r"^(?:/|/\*|~|~/.*|\$HOME(?:/.*)?|\$\{HOME\}(?:/.*)?|\.|\./?|\.\.|\*|\.\*|\./\.\*|\./\*|\.\./\*|[A-Za-z]:[\\/]?|/[A-Za-z0-9._-]+/?)$")
WRAPPERS = {"sudo", "command", "env", "nohup", "time"}
SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
GIT_VALUE_OPTIONS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}
FIND_FILTERS = {"-name", "-iname", "-path", "-ipath", "-regex", "-type", "-newer", "-mtime", "-mmin", "-size", "-empty", "-user"}
PS_REMOVE = {"remove-item", "ri", "rd", "rmdir", "del", "erase"}


def is_broad(target: str) -> bool:
    return bool(BROAD.match(target.replace("\\", "/")) or BROAD.match(target))


def rm_denied(words: list[str]) -> str | None:
    flags = "".join(w.lstrip("-") for w in words if w.startswith("-") and not w.startswith("--"))
    long_flags = {w for w in words if w.startswith("--")}
    recursive = "r" in flags.lower() or "--recursive" in long_flags
    if not recursive:
        return None
    for target in (w for w in words if not w.startswith("-")):
        if is_broad(target):
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
    if sub == "push" and ("--delete" in rest or any(w.startswith(":") and len(w) > 1 for w in rest)):
        return "git push that deletes a remote branch"
    if sub == "reset" and "--hard" in rest:
        return "git reset --hard"
    if sub == "clean" and any(re.fullmatch(r"-[a-zA-Z]*f[a-zA-Z]*", w) or w == "--force" for w in rest):
        return "git clean with force"
    if sub in {"checkout", "restore"} and any(w in {".", "*"} for w in rest):
        return f"git {sub} that discards all working-tree changes"
    if sub == "stash" and rest[:1] and rest[0] in {"drop", "clear"}:
        return f"git stash {rest[0]} (unrecoverable)"
    if sub == "branch" and any(w == "--delete" or re.fullmatch(r"-[a-zA-Z]*D[a-zA-Z]*", w) for w in rest):
        return "git branch -D"
    return None


def other_denied(name: str, words: list[str]) -> str | None:
    args = words[1:]
    flags = "".join(w.lstrip("-") for w in args if w.startswith("-") and not w.startswith("--"))
    targets = [w for w in args if not w.startswith("-")]
    broad = [t for t in targets if is_broad(t)]
    if name in SHELLS and "-c" in args[:-1]:
        return deny_reason(args[args.index("-c") + 1])
    if name == "eval":
        return deny_reason(" ".join(args))
    if name == "find" and "-delete" in args and not FIND_FILTERS & set(args):
        return "find -delete without a filter"
    if name == "dd" and any(w.startswith("of=/dev/") for w in args):
        return "dd onto a device"
    if name.startswith("mkfs") or name == "shred":
        return f"{name} destroys data"
    if name in {"chmod", "chown", "chgrp"} and ("R" in flags or "--recursive" in args) and broad:
        return f"recursive {name} of broad target {broad[0]!r}"
    if name == "mv" and broad:
        return f"mv of broad target {broad[0]!r}"
    if name == "xargs" and "rm" in args and any(re.fullmatch(r"-[a-zA-Z]*[rR][a-zA-Z]*", w) for w in args):
        return "xargs rm -r (targets unknown)"
    if name in PS_REMOVE and any(w.lower() in {"-recurse", "/s"} for w in args) and broad:
        return f"recursive delete of broad target {broad[0]!r}"
    if name == "format" and targets and re.fullmatch(r"[A-Za-z]:", targets[0]):
        return "format of a drive"
    return None


def deny_reason(command: str) -> str | None:
    if PIPE_TO_SHELL.search(command):
        return "download piped into a shell"
    if SYSTEM_REDIRECT.search(command):
        return "redirect into a system folder"
    if ":(){" in command.replace(" ", ""):
        return "fork bomb"
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
        reason = rm_denied(words[1:]) if name == "rm" else git_denied(words) if name == "git" else other_denied(name, words)
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
        print(f"Blocked by hook_guard_bash.py: {reason}. Have the user run it, or approve it, themselves.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
