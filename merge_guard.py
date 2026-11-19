#!/usr/bin/env python3
"""Advisory pull-request readiness check: every CI check passed (not skipped) and the PR is mergeable.

Reads `gh pr checks` and `gh pr view` for the pull request. It is NOT server-side enforcement: a later push can race a
manual merge, and passing check names do not prove test quality or owner review. GitHub branch protection is the only
enforcing boundary. A skipped check is deliberately not accepted, because a skipped suite is not evidence that it passed.

Rules
  - at least one check exists (an empty list is "unknown", not "passing")
  - every check has bucket `pass`; `skipping`, `pending`, `fail` and `cancel` all block
  - the CI matrix jobs and each --require NAME are present among the checks
  - the PR state is OPEN and mergeable is MERGEABLE
  - head/base identities and draft state are checked before and after the check query; this is not an atomic server-side check

Exit codes: 0 ready, 1 not ready, 2 error (gh missing, bad output).

Usage: python merge_guard.py PR_NUMBER [--require "ubuntu-24.04 / py3.12" ...]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

REQUIRED = tuple(f"{os_name} / py{version}" for os_name in ("ubuntu-24.04", "ubuntu-26.04", "windows-latest") for version in ("3.10", "3.12"))


def run_gh(args: list[str]) -> str:
    done = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", timeout=60)
    if done.returncode != 0 and not done.stdout.strip():
        raise RuntimeError(f"gh {args[0]} {args[1]} failed: {done.stderr.strip()[:200]}")
    return done.stdout


def evaluate(checks: list[dict], view: dict, required: list[str]) -> list[str]:
    problems: list[str] = []
    if not checks:
        problems.append("no checks reported: readiness is unknown")
    for check in checks:
        if check.get("bucket") != "pass":
            problems.append(f"check '{check.get('name')}' is {check.get('bucket')!r}, not 'pass'")
    names = {c.get("name") for c in checks}
    if len(names) != len(checks):
        problems.append("duplicate check names: cannot identify an unambiguous result")
    for name in required:
        if name not in names:
            problems.append(f"required check '{name}' is missing")
    if view.get("state") != "OPEN":
        problems.append(f"pull request state is {view.get('state')!r}")
    if view.get("mergeable") != "MERGEABLE":
        problems.append(f"mergeable is {view.get('mergeable')!r}")
    return problems


def main(argv: list[str] | None = None, runner=run_gh) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pr")
    parser.add_argument("--require", action="append", default=[], metavar="NAME")
    args = parser.parse_args(argv)
    try:
        fields = "state,mergeable,headRefOid,baseRefOid,isDraft"
        view = json.loads(runner(["pr", "view", args.pr, "--json", fields]))
        checks = json.loads(runner(["pr", "checks", args.pr, "--json", "name,bucket"]) or "[]")
        after = json.loads(runner(["pr", "view", args.pr, "--json", fields]))
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    problems = evaluate(checks, view, list(REQUIRED) + args.require)
    for key in ("headRefOid", "baseRefOid"):
        value = view.get(key)
        if not isinstance(value, str) or len(value) != 40 or any(c not in "0123456789abcdefABCDEF" for c in value) or after.get(key) != value:
            problems.append(f"{key} missing, invalid or changed during checks")
    if view.get("isDraft") is not False or after.get("isDraft") is not False:
        problems.append("draft state is true or unknown")
    if after.get("state") != view.get("state") or after.get("mergeable") != view.get("mergeable"):
        problems.append("PR state changed during checks")
    for problem in problems:
        print(f"[NOT READY] {problem}")
    print(f"MERGE-GUARD: {'NOT READY' if problems else 'READY'} ({len(checks)} check(s)); advisory only, not branch protection")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
