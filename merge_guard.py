#!/usr/bin/env python3
"""Advisory pull-request readiness check: every CI check passed (not skipped) and the PR is mergeable.

Reads `gh pr checks` and `gh pr view` for the pull request. It is NOT server-side enforcement: a later push can race a
manual merge, and passing check names do not prove test quality or owner review. GitHub branch protection is the only
enforcing boundary. A skipped check is deliberately not accepted, because a skipped suite is not evidence that it passed.

Rules
  - at least one check exists (an empty list is "unknown", not "passing")
  - every check has bucket `pass`; `skipping`, `pending`, `fail` and `cancel` all block
  - each --require NAME is present among the checks (so a removed job cannot silently lower the bar)
  - the PR state is OPEN and mergeable is MERGEABLE

Exit codes: 0 ready, 1 not ready, 2 error (gh missing, bad output).

Usage: python merge_guard.py PR_NUMBER [--require "ubuntu-24.04 / py3.12" ...]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys


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
        checks = json.loads(runner(["pr", "checks", args.pr, "--json", "name,bucket"]) or "[]")
        view = json.loads(runner(["pr", "view", args.pr, "--json", "state,mergeable"]))
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    problems = evaluate(checks, view, args.require)
    for problem in problems:
        print(f"[NOT READY] {problem}")
    print(f"MERGE-GUARD: {'NOT READY' if problems else 'READY'} ({len(checks)} check(s)); advisory only, not branch protection")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
