#!/usr/bin/env python3
"""Does a change's own test fail without the change?

A regression test that passes on the code it was written against proves nothing, and "I saw it fail first" is a sentence in
a pull request. This runs the tests a change added or edited against the shipped code the change started from, and reports
which of them fail there but pass on the change.

    python revert_proof.py [--base origin/main] [--head HEAD] [--title "fix: ..."]

How it decides (both trees come from `git archive`, so uncommitted edits are not judged; commit first):
  1. The base is the merge-base of --base and --head, so unrelated work that landed on the base is not blamed on the change.
  2. If no shipped code (a tracked .py file that is not a test, fixture or document) changed, nothing is judged.
  3. The base tree gets the change's tests, fixtures and documents laid over it, but keeps the base's shipped code.
  4. Each changed test file runs on that tree and on the head. A test that fails there and passes on the head is proof.
     A test that fails on both is not proof and blocks, because the change itself is broken or the host cannot run it.

Exit 0: no shipped code changed, the title says no behaviour changes, or at least one test is proven.
Exit 1: shipped code changed and no test is proven (none added, all pass on the old code, or the head fails).
Exit 2: the refs could not be read or a test run crashed without output.
A change that is meant to alter no behaviour says so in its title (refactor:, chore:, docs:, ci:, test:, build:) and is not
judged; behaviour-preserving refactors are checked with gate_replay.py instead. Tests that pass on the old code are listed as
pinning behaviour that was already there; that is allowed beside a proven one. This is a local tool and is not run in CI.
"""
from __future__ import annotations

import argparse
import io
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

TEST_FILE = re.compile(r"(?:^|/)test_[^/]+\.py$")
EXEMPT_TITLE = re.compile(r"^(refactor|chore|docs|ci|test|build)\b", re.I)
HEADER = re.compile(r"^(?:FAIL|ERROR): (\S+) \((\S+?)\)")
RAN = re.compile(r"^Ran (\d+) tests? in ")
NOT_SHIPPED_DIRS = ("references/", "docs/", ".github/", "fixtures/", "examples/")


class ToolError(Exception):
    """The refs or the trees could not be read."""


def git(repo: Path, *args: str) -> bytes:
    try:
        done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ToolError(f"git could not run: {exc}") from exc
    if done.returncode != 0:
        raise ToolError(f"git {args[0]} failed: {done.stderr.decode('utf-8', 'replace').strip()[:200]}")
    return done.stdout


def is_shipped(path: str) -> bool:
    return (path.endswith(".py") and not TEST_FILE.search(path)
            and not path.startswith(NOT_SHIPPED_DIRS) and not any(f"/{d}" in path for d in NOT_SHIPPED_DIRS))


def changed_files(repo: Path, base: str, head: str) -> dict[str, str]:
    """Path -> status letter for the change from the merge-base to head, without rename detection."""
    raw = git(repo, "diff", "--name-status", "--no-renames", "-z", f"{base}...{head}").decode("utf-8", "replace")
    parts = raw.split("\0")
    return {path: status for status, path in zip(parts[0::2], parts[1::2]) if status and path}


def safe_extract(data: bytes, dest: Path) -> None:
    root = dest.resolve()
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        for member in tar.getmembers():
            if member.issym() or member.islnk() or not (root / member.name).resolve().is_relative_to(root):
                raise ToolError(f"refusing archive member {member.name!r}")
        tar.extractall(dest, **({"filter": "data"} if hasattr(tarfile, "data_filter") else {}))


def extract(repo: Path, ref: str, dest: Path) -> None:
    safe_extract(git(repo, "archive", "--format=tar", ref), dest)


def parse_failures(output: str) -> tuple[int | None, set[str]]:
    """Tests that failed or errored and how many ran. The header names differ between Python versions
    (`test_x (mod.Class.test_x)` or `test_x (mod.Class)`), so both are reduced to `mod.Class.test_x`."""
    ran, failed = None, set()
    for line in output.splitlines():
        count = RAN.match(line)
        if count:
            ran = int(count.group(1))
        header = HEADER.match(line)
        if header:
            name, where = header.groups()
            failed.add(where if where.endswith("." + name) else f"{where}.{name}")
    return ran, failed


def run_test_file(tree: Path, relative: str, timeout: int) -> tuple[int | None, set[str], bool]:
    """(tests run, failing tests, crashed). A run that printed nothing usable counts as the whole file failing."""
    path = PurePosixPath(relative)
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"}
    command = [sys.executable, "-m", "unittest", "discover", "-s", str(tree / path.parent), "-p", path.name]
    try:
        done = subprocess.run(command, cwd=tree, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, {f"{relative} (timed out after {timeout}s)"}, True
    output = done.stderr + "\n" + done.stdout
    ran, failed = parse_failures(output)
    if ran is None:
        return None, {f"{relative} (no test result: {output.strip()[-160:]})"}, True
    return ran, failed, False


def judge(repo: Path, base: str, head: str, title: str, timeout: int) -> tuple[int, list[str]]:
    lines: list[str] = []
    merge_base = git(repo, "merge-base", base, head).decode().strip()
    changes = changed_files(repo, base, head)
    shipped = sorted(p for p in changes if is_shipped(p))
    tests = sorted(p for p, s in changes.items() if TEST_FILE.search(p) and s in {"A", "M"})
    if not shipped:
        return 0, ["REVERT-PROOF: NOT NEEDED (no shipped code changed)"]
    lines.append(f"shipped code changed: {', '.join(shipped[:6])}{' ...' if len(shipped) > 6 else ''}")
    if EXEMPT_TITLE.match(title.strip()):
        return 0, lines + [f"REVERT-PROOF: NOT JUDGED (title says no behaviour change: {title.strip()[:60]!r}); "
                           "check a behaviour-preserving refactor with gate_replay.py"]
    if not tests:
        return 1, lines + ["REVERT-PROOF: UNPROVEN (shipped code changed and no test was added or edited)"]
    with tempfile.TemporaryDirectory() as tmp:
        base_tree, head_tree = Path(tmp, "base"), Path(tmp, "head")
        base_tree.mkdir()
        head_tree.mkdir()
        extract(repo, merge_base, base_tree)
        extract(repo, head, head_tree)
        for path, status in changes.items():  # the change's tests and data, on the old code
            if status in {"A", "M"} and not is_shipped(path):
                target = base_tree / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((head_tree / path).read_bytes())
        proven: list[str] = []
        broken = 0
        crashed = False
        for test in tests:
            _, head_failed, head_crash = run_test_file(head_tree, test, timeout)
            _, base_failed, _ = run_test_file(base_tree, test, timeout)
            crashed = crashed or head_crash
            if head_failed:
                broken += len(head_failed)
                lines.append(f"fails on the change itself ({test}): {sorted(head_failed)[:3]}")
            proven += sorted(base_failed - head_failed)
    pinned_note = "tests that pass on the old code only pin behaviour that was already there"
    if crashed:
        return 2, lines + ["REVERT-PROOF: ERROR (a test file crashed on the change; nothing is proven)"]
    if broken:
        return 1, lines + [f"REVERT-PROOF: BLOCKED ({broken} test(s) fail on the change itself)"]
    if proven:
        shown = "; ".join(proven[:8]) + (f"; +{len(proven) - 8} more" if len(proven) > 8 else "")
        return 0, lines + [f"REVERT-PROOF: PROVEN ({len(proven)} test(s) fail on the old code and pass on the change: {shown})"]
    return 1, lines + [f"REVERT-PROOF: UNPROVEN (every changed test also passes on the old code; {pinned_note})"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--title", default="", help="pull request title; a refactor:/chore:/docs:/ci:/test:/build: prefix is not judged")
    parser.add_argument("--timeout", type=int, default=900, help="seconds allowed per test file (default 900)")
    args = parser.parse_args(argv)
    try:
        code, lines = judge(args.repo, args.base, args.head, args.title, args.timeout)
    except ToolError as exc:
        print(f"REVERT-PROOF: ERROR ({exc})")
        return 2
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
