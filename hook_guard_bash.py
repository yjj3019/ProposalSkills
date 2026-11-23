#!/usr/bin/env python3
"""Claude Code PreToolUse(Bash) hook: deny a short list of destructive commands.

This is a lexical guardrail, NOT a security boundary and not a sandbox. It tokenizes the command with shell quoting, splits
it on control operators (`;`, `&`, `&&`, `||`, `|`, parentheses, newlines), skips shell keywords (`if`, `then`, `do`, `!`...),
checks `$(...)`, backtick and `<(...)` substitutions (also inside double quotes), and denies:
  - `rm` with a recursive/force flag aimed at a broad target (/, ~, $HOME, ., ./, .., *, .*, a drive root, a top-level folder)
  - `git push --force` / `--force-with-lease` / `-f` / `+refspec` / `--delete` / `-d` / `:branch`, `git reset --hard`,
    `git clean -f`, `git checkout .|:/|-f`, `git switch -f`, `git restore .|:/`, `git stash drop|clear`, `git branch -D`,
    including abbreviated long options that Git accepts (`--forc`, `--har`)
  - a download piped or substituted into a shell (`curl ... | sh`, `bash <(curl ...)`, `eval $(curl ...)`)
  - the same commands wrapped in `bash -c '...'`, `sh -c "..."` or `eval ...` (the inner text is checked again)
  - `find` with `-delete` and no filter, `dd of=/dev/...`, `mkfs`, `shred`, `xargs rm -r`, `chmod/chown -R` or `mv` on a
    broad target, a redirect into /etc and similar system folders, a fork bomb, `format C:`, and PowerShell
    `Remove-Item -Recurse` on a broad target
  - a download piped into `python`/`node`/`perl`/`ruby`/`php` with no script, PowerShell `iwr ... | iex`, `-EncodedCommand`,
    `git filter-branch`, `git reflog expire`, `git gc --prune=now`, `find -exec rm|shred` without a filter, `tee` into a
    system folder, `rm -rf $PWD`
Aliases, functions, variables and encoded payloads can still evade it, and a `Bash` matcher does not cover a separate
PowerShell tool; real approval and host permissions are required for external or destructive effects. Unparsable input is
denied (fail closed).
`--force-with-lease` is denied on purpose: it is still a history rewrite on a shared branch, so the user decides.

Hook protocol: reads the hook JSON on stdin (`tool_input.command`). Exit 0 allows, exit 2 denies with the reason on stderr.

Opt-in setup (nothing is installed automatically), in .claude/settings.json:
  {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "python hook_guard_bash.py"}]}]}}
"""
from __future__ import annotations

import json
import posixpath
import re
import shlex
import sys

OPERATOR_CHARS = "();<>|&\n"
REDIRECTS = {">", ">>", "<", "<<", "<<<", ">&", "<&", "&>", "&>>", ">|", "<>"}
SHELL_KEYWORDS = {"if", "then", "elif", "else", "while", "until", "do", "!"}
PIPE_TO_SHELL = re.compile(
    r"\b(?:curl|wget)\b[^\n|]*\|\s*(?:sudo\s+)?(?:ba|z|da|k)?sh\b"
    r"|\b(?:(?:ba|z|da|k)?sh|source|eval)\b[^\n]*(?:<\(|\$\(|`)\s*(?:curl|wget)\b", re.I)
PIPE_TO_INTERPRETER = re.compile(r"\b(?:curl|wget)\b[^\n|]*\|\s*(?:sudo\s+)?(?:python[0-9.]*|node|perl|ruby|php)(?:\s+-)?\s*(?:$|[;&])", re.I | re.M)
PS_DOWNLOAD_EXEC = re.compile(r"\b(?:iwr|irm|invoke-webrequest|invoke-restmethod)\b[^\n|]*\|\s*(?:iex|invoke-expression)\b"
                              r"|\b(?:iex|invoke-expression)\b[^\n]*\b(?:iwr|irm|invoke-webrequest|invoke-restmethod|downloadstring)\b", re.I)
SYSTEM_REDIRECT = re.compile(r"(?:^|\s)\d?>>?\s*/(?:etc|boot|bin|sbin|usr|lib|dev/(?!null\b|stderr\b|stdout\b|tty\b))", re.I)
BROAD = re.compile(r"^(?:/|/\*|~|~/.*|\$HOME(?:/.*)?|\$\{HOME\}(?:/.*)?|\$\{?PWD\}?/?|\.|\./?|\.\.|\*|\.\*|\./\.\*|\./\*|\.\./\*|[A-Za-z]:[\\/]?|/[A-Za-z0-9._-]+/?)$")
WRAPPERS = {"sudo", "command", "env", "nohup", "time", "nice", "ionice", "timeout", "exec", "busybox", "setsid", "stdbuf"}
# options of a wrapper that take a value: `sudo -u root rm ...`, `env -u X ...`, `nice -n 5 ...`, `timeout -s KILL 5 ...`
WRAPPER_VALUE_OPTIONS = {"-u", "-g", "-n", "-s", "-k", "-c", "-C", "--user", "--group", "--signal", "--kill-after"}
UPLOAD = re.compile(r"\b(?:curl|wget)\b[^\n|;&]*(?:\s-d\s*@|--data(?:-binary|-raw|-urlencode)?[ =]@|\s-F\s*\S*=@|\s-T\s|--upload-file|--post-file)", re.I)
SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
GIT_VALUE_OPTIONS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}
FIND_FILTERS = {"-name", "-iname", "-path", "-ipath", "-regex", "-type", "-newer", "-mtime", "-mmin", "-size", "-empty", "-user"}
PS_REMOVE = {"remove-item", "ri", "rd", "rmdir", "del", "erase"}


def is_broad(target: str) -> bool:
    flat = target.replace("\\", "/")
    if BROAD.match(flat) or BROAD.match(target):
        return True
    if not flat.startswith(("$", "~")) and "*" not in flat and flat:
        return bool(BROAD.match(posixpath.normpath(re.sub(r"/{2,}", "/", flat))))  # `//` and `/tmp/..` are the root
    return False


def strip_wrappers(words: list[str]) -> list[str]:
    """Drop leading wrappers, their options and VAR=value words, so `nice -n 5 rm -rf /` is judged as `rm -rf /`."""
    words = [w for w in words if w not in {"(", ")", "{", "}"}]
    while words:
        head = words[0]
        if head in SHELL_KEYWORDS:
            words = words[1:]
        elif head in WRAPPERS:
            words = words[1:]
            while words and words[0].startswith("-"):
                words = words[2:] if words[0] in WRAPPER_VALUE_OPTIONS else words[1:]
            if head == "timeout" and words and re.fullmatch(r"\d+[smhd]?", words[0]):
                words = words[1:]
        elif re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", head):
            words = words[1:]
        else:
            break
    return words


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


def abbreviates(word: str, option: str, shortest: int) -> bool:
    """Git accepts a unique prefix of a long option, so `--forc` means `--force`."""
    return len(word) >= shortest and option.startswith(word)


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
    short_f = any(re.fullmatch(r"-[a-zA-Z]*f[a-zA-Z]*", w) for w in rest)
    long_force = any(abbreviates(w, "--force", 5) or w.startswith("--force") for w in rest)
    if sub == "push" and (short_f or long_force or any(w.startswith("+") and len(w) > 1 for w in rest)):
        return "git push with force"
    if sub == "push" and any(abbreviates(w, "--mirror", 4) for w in rest):
        return "git push --mirror"
    if sub == "push" and (any(abbreviates(w, "--delete", 4) or re.fullmatch(r"-[a-zA-Z]*d[a-zA-Z]*", w) for w in rest)
                          or any(w.startswith(":") and len(w) > 1 for w in rest)):
        return "git push that deletes a remote branch"
    if sub == "reset" and any(abbreviates(w, "--hard", 4) for w in rest):
        return "git reset --hard"
    if sub == "clean" and (short_f or any(abbreviates(w, "--force", 3) for w in rest)):
        return "git clean with force"
    if sub in {"checkout", "restore"} and any(w in {".", "./", "*", ":/", ":/*"} for w in rest):
        return f"git {sub} that discards all working-tree changes"
    if sub in {"checkout", "switch"} and (short_f or long_force or any(abbreviates(w, "--discard-changes", 4) for w in rest)):
        return f"git {sub} that discards local changes"
    if sub == "stash" and rest[:1] and rest[0] in {"drop", "clear"}:
        return f"git stash {rest[0]} (unrecoverable)"
    if sub == "filter-branch":
        return "git filter-branch rewrites history"
    if sub == "reflog" and "expire" in rest:
        return "git reflog expire (unrecoverable)"
    if sub == "gc" and any(w.startswith("--prune") and "now" in w for w in rest):
        return "git gc --prune=now (unrecoverable)"
    if sub == "branch" and any(abbreviates(w, "--delete", 4) or re.fullmatch(r"-[a-zA-Z]*D[a-zA-Z]*", w) for w in rest):
        return "git branch -D"
    if sub == "branch" and short_f and any(re.fullmatch(r"-[a-zA-Z]*d[a-zA-Z]*", w) for w in rest):
        return "git branch -d with force"
    return None


def other_denied(name: str, words: list[str]) -> str | None:
    args = words[1:]
    flags = "".join(w.lstrip("-") for w in args if w.startswith("-") and not w.startswith("--"))
    targets = [w for w in args if not w.startswith("-")]
    broad = [t for t in targets if is_broad(t)]
    if name in SHELLS:  # `-c` may be clustered: `bash -lc`, `sh -ec`
        script_at = next((k for k, w in enumerate(args[:-1]) if re.fullmatch(r"-[A-Za-z]*c[A-Za-z]*", w)), None)
        if script_at is not None:
            return deny_reason(args[script_at + 1])
    if name == "kill" and any(w in {"-1", "0"} for w in targets + args):
        return "kill of every process"
    if name == "eval":
        return deny_reason(" ".join(args))
    if name == "find" and "-delete" in args and not FIND_FILTERS & set(args):
        return "find -delete without a filter"
    exec_at = next((k for k, w in enumerate(args) if w in {"-exec", "-execdir"}), None)
    if name == "find" and exec_at is not None and args[exec_at + 1:exec_at + 2]:
        runner = args[exec_at + 1].rsplit("/", 1)[-1]
        start = targets[0] if targets else "."
        if runner == "shred" or (runner == "rm" and (not FIND_FILTERS & set(args) or (is_broad(start) and start not in {".", "./"}))):
            return f"find -exec {runner} without a filter or from a broad start"
    if name == "tee" and any(re.match(r"/(?:etc|boot|bin|sbin|usr|lib)(?:/|$)", t) for t in targets):
        return "tee into a system folder"
    if name in {"powershell", "pwsh"} and any(w.lower() in {"-enc", "-ec", "-encodedcommand"} for w in args):
        return "encoded PowerShell command"
    if name == "dd" and any(w.startswith("of=/dev/") for w in args):
        return "dd onto a device"
    if name.startswith("mkfs") or name == "shred":
        return f"{name} destroys data"
    if name in {"chmod", "chown", "chgrp"} and ("R" in flags or "--recursive" in args) and broad:
        return f"recursive {name} of broad target {broad[0]!r}"
    if name == "mv" and targets:
        # Moving a file into the current or parent folder is routine; moving such a folder is not.
        risky = [t for t in targets[:-1] if is_broad(t)]
        if is_broad(targets[-1]) and targets[-1] not in {".", "./", "..", "../"}:
            risky.append(targets[-1])
        if risky:
            return f"mv of broad target {risky[0]!r}"
    if name == "xargs" and "rm" in args and any(re.fullmatch(r"-[a-zA-Z]*[rR][a-zA-Z]*", w) for w in args):
        return "xargs rm -r (targets unknown)"
    if name in PS_REMOVE and any(w.lower() in {"-recurse", "/s"} for w in args) and broad:
        return f"recursive delete of broad target {broad[0]!r}"
    if name == "format" and targets and re.fullmatch(r"[A-Za-z]:", targets[0]):
        return "format of a drive"
    return None


def simple_commands(command: str) -> list[list[str]]:
    """Split on unquoted control operators. A redirect and its target stay out of the command's words."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=OPERATOR_CHARS)
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    lexer.commenters = ""  # a `#` must not hide the next line from the check
    commands: list[list[str]] = [[]]
    skip_next = False
    for token in lexer:
        if token in REDIRECTS:
            skip_next = True
        elif token and all(ch in OPERATOR_CHARS for ch in token):
            skip_next = False
            commands.append([])
        elif skip_next:
            skip_next = False
        else:
            commands[-1].append(token)
    return [words for words in commands if words]


def substitutions(text: str) -> list[str]:
    """Bodies of `$(...)`, `<(...)`, `>(...)` and backticks that the shell would run; single quotes keep them literal."""
    found: list[str] = []
    i, quote = 0, ""
    while i < len(text):
        ch = text[i]
        if quote == "'":
            quote = "" if ch == "'" else quote
        elif ch == "\\":
            i += 1
        elif ch == '"':
            quote = "" if quote else '"'
        elif ch == "'" and not quote:
            quote = "'"
        elif ch == "`":
            end = text.find("`", i + 1)
            end = len(text) if end < 0 else end
            found.append(text[i + 1:end])
            i = end
        elif ch in "$<>" and text[i + 1:i + 2] == "(":
            depth, end = 1, i + 2
            while end < len(text) and depth:
                depth += {"(": 1, ")": -1}.get(text[end], 0)
                end += 1
            found.append(text[i + 2:end - 1 if depth == 0 else end])
            i = end - 1
        i += 1
    return found


def deny_reason(command: str) -> str | None:
    if PIPE_TO_SHELL.search(command):
        return "download piped into a shell"
    if PIPE_TO_INTERPRETER.search(command):
        return "download piped into an interpreter"
    if PS_DOWNLOAD_EXEC.search(command):
        return "PowerShell download executed with iex"
    if SYSTEM_REDIRECT.search(command):
        return "redirect into a system folder"
    if UPLOAD.search(command):
        return "upload of a local file to a remote host"
    if ":(){" in command.replace(" ", ""):
        return "fork bomb"
    for inner in substitutions(command):
        reason = deny_reason(inner)
        if reason:
            return reason
    try:
        commands = simple_commands(command)
    except ValueError:
        return "command could not be parsed (unbalanced quote)"
    for words in commands:
        words = strip_wrappers(words)
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
    try:
        reason = deny_reason(command)
    except RecursionError:
        reason = "command is nested too deeply to check"
    if reason:
        print(f"Blocked by hook_guard_bash.py: {reason}. Have the user run it, or approve it, themselves.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
