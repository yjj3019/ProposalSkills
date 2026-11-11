#!/usr/bin/env python3
"""Gate mutation probe: checks that the tests notice when a submission gate is weakened.

A passing test suite proves little about a gate unless a deliberately weakened gate makes it fail.
For each catalogued mutation this tool copies the repository into a disposable directory, applies one
exact-once text replacement to a gate source file, and runs the focused unittest modules that are
supposed to guard that rule.

Outcomes (fail-closed; only an assertion failure counts as a kill):
  killed    at least one test FAILED on an assertion: the suite noticed the weakened gate.
  crashed   the suite only hit errors/exceptions: detected, but not by an assertion about the rule.
  survived  every focused test still passed: a test gap; the weakened gate would ship unnoticed.
  invalid   the mutated file no longer compiles, or the replacement did not match exactly once.
  error     the run itself failed (timeout, no tests executed, unreadable output).

Exit code: 0 all killed, 1 any survived/crashed, 2 error/invalid/baseline failure.

This is a manual, local quality tool, not a sandbox and not a CI substitute for review. Mutations run
on copies; the working tree is never modified. Stdlib only.

Usage:
  python gate_mutation_probe.py                 # whole catalog
  python gate_mutation_probe.py --list          # print catalog
  python gate_mutation_probe.py --only unified-binding-hash --jobs 2
  python gate_mutation_probe.py --json report.json
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent

# Test modules (repository root) that guard the gates. Kept small so a probe run stays fast.
GATE_TESTS = (
    # Fast, rule-focused modules first: with failfast a killed mutation stops at the first failing test.
    "test_proposal_gate_discovery",  # re-exports the proposal_gate unit tests that live under skills/
    "test_gate_mutation_gaps", "test_numbers_ledger", "test_ambiguous_commitment", "test_rfx_rules",
    "test_real_proposal_findings", "test_gate_hardening", "test_gate_hardening_d",
    "test_gate_integrity2", "test_gate_integrity", "test_submission_bundle",
)
PROPOSAL = "skills/create-winning-proposal/scripts/proposal_gate.py"
UNIFIED = "skills/create-best-proposal/scripts/unified_gate.py"

# Variables that would make the copied gates call the original checkout instead of the copy.
SCRUBBED_ENV = ("PROPOSAL_GATE_PATH", "QUALITY_GATE_PATH", "CHECK_NUMBERS_PATH",
                "AI_SKILLS_DIR", "CODEX_HOME", "PROPOSAL_GATE_NOW")


@dataclass(frozen=True)
class Mutation:
    name: str
    path: str            # file to weaken, relative to the repository root
    old: str             # must occur exactly once
    new: str
    why: str             # the rule this protects (shown in reports)
    tests: tuple[str, ...] = GATE_TESTS


MUTATIONS: tuple[Mutation, ...] = (
    Mutation("placeholder-detection", PROPOSAL,
             "    return _PLACEHOLDER_RE.search(value) is not None\n\n\ndef _evidence_ok",
             "    return False\n\n\ndef _evidence_ok",
             "TBD / needs-input strings must never count as evidence"),
    Mutation("evidence-needs-real-string", PROPOSAL,
             "    return any(isinstance(v, str) and not _is_placeholder(v) for v in values)",
             "    return len(values) > 0",
             "evidence lists need at least one non-placeholder string"),
    Mutation("exception-needs-evidence", PROPOSAL,
             '    return not _is_placeholder(item.get("granted_by")) and _evidence_ok(item.get("evidence"))',
             '    return not _is_placeholder(item.get("granted_by"))',
             "buyer-authorized exceptions need both an approver and evidence"),
    Mutation("currency-absolute-tolerance", PROPOSAL,
             "CURRENCY_ABS_TOLERANCE = 1.0", "CURRENCY_ABS_TOLERANCE = 1e9",
             "currency sums must not hide a large discrepancy behind relative tolerance"),
    Mutation("bool-is-not-a-number", PROPOSAL,
             "    return isinstance(value, (int, float)) and not isinstance(value, bool)",
             "    return isinstance(value, (int, float))",
             "true/false must not be accepted as ledger numbers"),
    Mutation("digest-format", PROPOSAL,
             "    return isinstance(value, str) and _DIGEST_RE.match(value.strip()) is not None",
             "    return isinstance(value, str)",
             "artifact hashes must be sha256:<64 hex> to be comparable"),
    Mutation("naive-datetime-rejected", PROPOSAL,
             '        return "T" in value and parsed.tzinfo is not None',
             '        return "T" in value',
             "deadlines without a time zone are ambiguous and must be rejected"),
    Mutation("deadline-must-be-future", PROPOSAL,
             "    return dt > reference_now()", "    return True",
             "an expired submission deadline must block"),
    Mutation("unsupported-symbol-alias", PROPOSAL,
             '    text = value.strip().upper().replace("✗", "X").replace("Ｘ", "X")',
             '    text = value.strip().upper().replace("Ｘ", "X")',
             "the ✗ notation must not bypass approval consistency checks"),
    Mutation("not-applicable-is-supported", PROPOSAL,
             '    if not text or text in {"N/A", "NA", "해당없음", "해당 없음"}:',
             "    if not text:",
             "N/A (not applicable) is not an unsupported requirement"),
    Mutation("readiness-blocks-on-failures", PROPOSAL,
             '    if failures:\n        return "BLOCKED", 1\n    if decision == "conditional-bid":',
             '    if False:\n        return "BLOCKED", 1\n    if decision == "conditional-bid":',
             "any failure must produce BLOCKED with exit code 1"),
    Mutation("unified-binding-hash", UNIFIED,
             "        if declared and declared != actual:", "        if False:",
             "the audit hash must match the actual submitted file"),
    Mutation("unified-digest-case-insensitive", UNIFIED,
             '    v = value.strip().lower().removeprefix("sha256:")',
             '    v = value.strip().removeprefix("sha256:")',
             "an upper-case hash must still be compared, not silently dropped"),
    Mutation("unified-timeout-fails-closed", UNIFIED,
             'return 2, f"{Path(cmd[1]).name}: check timed out',
             'return 0, f"{Path(cmd[1]).name}: check timed out',
             "a timed-out check is an execution error, never a pass"),
    Mutation("unified-quality-failure-blocks", UNIFIED,
             '            print("BLOCKED: document quality_gate failed")\n            return 1',
             '            print("BLOCKED: document quality_gate failed")\n            return 0',
             "a failed document quality gate must block submission"),
)


@dataclass
class Result:
    name: str
    outcome: str
    why: str
    detail: str = ""
    seconds: float = 0.0
    failing: list[str] = field(default_factory=list)


def replace_once(text: str, old: str, new: str) -> str:
    """Replace `old` with `new`, requiring exactly one occurrence so a mutation cannot drift."""
    if not old or old == new:
        raise ValueError("invalid replacement")
    first = text.find(old)
    if first < 0:
        raise ValueError("mutation text not found")
    if text.find(old, first + 1) != -1:
        raise ValueError("mutation text must match exactly once")
    return text[:first] + new + text[first + len(old):]


def apply_mutation(text: str, mutation: Mutation) -> str:
    """replace_once, written for the file's own line endings (the catalog is written with LF)."""
    eol = "\r\n" if "\r\n" in text else "\n"
    return replace_once(text, mutation.old.replace("\n", eol), mutation.new.replace("\n", eol))


def tracked_files(root: Path) -> list[Path]:
    """Files to copy: tracked plus untracked-but-not-ignored files (a new test must be probed before it is
    committed), else every file outside caches when this is not a git checkout."""
    if (root / ".git").exists():
        out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                             cwd=str(root), capture_output=True)
        if out.returncode == 0:
            names = [n for n in out.stdout.decode("utf-8", "replace").split("\0") if n]
            return [root / n for n in names if (root / n).is_file()]
    skip = {".git", "__pycache__", ".pytest_cache", "dist"}
    return [p for p in root.rglob("*") if p.is_file() and not skip.intersection(p.relative_to(root).parts)]


def copy_tree(root: Path, destination: Path) -> None:
    for source in tracked_files(root):
        target = destination / source.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def classify(returncode: int, output: str) -> tuple[str, list[str]]:
    """Map unittest output to an outcome. Only assertion failures (FAIL:) count as a kill."""
    ran = re.search(r"^Ran (\d+) tests? in ", output, re.MULTILINE)
    if not ran or int(ran.group(1)) <= 0:
        return "error", []
    fails = re.findall(r"^FAIL: (\S+)", output, re.MULTILINE)
    errors = re.findall(r"^ERROR: (\S+)", output, re.MULTILINE)
    if returncode == 0 and not fails and not errors:
        return "survived", []
    if fails:
        return "killed", fails
    if errors:
        return "crashed", errors
    return "error", []


def run_tests(directory: Path, tests: tuple[str, ...], timeout: int) -> tuple[int, str]:
    env = {k: v for k, v in os.environ.items() if k not in SCRUBBED_ENV}
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    cmd = [sys.executable, "-m", "unittest", "-f", *tests]
    try:
        proc = subprocess.run(cmd, cwd=str(directory), capture_output=True, text=True,
                              encoding="utf-8", errors="replace", env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        return -1, "timeout"
    except OSError as exc:
        return -1, f"cannot start: {type(exc).__name__}"
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def run_one(root: Path, scratch: Path, mutation: Mutation, timeout: int) -> Result:
    started = time.monotonic()
    work = Path(tempfile.mkdtemp(prefix=mutation.name + "-", dir=str(scratch)))
    try:
        copy_tree(root, work)
        target = work / mutation.path
        try:
            # Bytes in, bytes out: the mutated copy keeps the file's own line endings (CRLF stays CRLF).
            mutated = apply_mutation(target.read_bytes().decode("utf-8"), mutation)
        except (OSError, ValueError) as exc:
            return Result(mutation.name, "invalid", mutation.why, str(exc), time.monotonic() - started)
        target.write_bytes(mutated.encode("utf-8"))
        try:
            py_compile.compile(str(target), doraise=True, cfile=str(work / "_probe.pyc"))
        except py_compile.PyCompileError as exc:
            return Result(mutation.name, "invalid", mutation.why, f"does not compile: {exc.msg}",
                          time.monotonic() - started)
        code, output = run_tests(work, mutation.tests, timeout)
        if output == "timeout":
            return Result(mutation.name, "error", mutation.why, f"timed out after {timeout}s",
                          time.monotonic() - started)
        outcome, failing = classify(code, output)
        detail = "" if outcome != "error" else output[-300:].strip()
        return Result(mutation.name, outcome, mutation.why, detail, time.monotonic() - started, failing)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def baseline(root: Path, scratch: Path, tests: tuple[str, ...], timeout: int) -> tuple[bool, str]:
    """The unmutated copy must pass; otherwise 'killed' would only mean 'already broken'."""
    work = Path(tempfile.mkdtemp(prefix="baseline-", dir=str(scratch)))
    try:
        copy_tree(root, work)
        code, output = run_tests(work, tests, timeout)
        if output == "timeout":
            return False, f"baseline timed out after {timeout}s"
        outcome, _ = classify(code, output)
        if outcome != "survived":  # "survived" == every test passed
            return False, "baseline is not green:\n" + output[-1200:]
        return True, ""
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run_probe(root: Path, mutations: tuple[Mutation, ...], *, jobs: int = 2, timeout: int = 600,
              check_baseline: bool = True) -> tuple[list[Result], str]:
    """Return (results, baseline_error). results are empty when the baseline fails."""
    with tempfile.TemporaryDirectory(prefix="gate-probe-") as scratch_name:
        scratch = Path(scratch_name)
        if check_baseline:
            tests = tuple(sorted({t for m in mutations for t in m.tests}))
            ok, message = baseline(root, scratch, tests, timeout)
            if not ok:
                return [], message
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
            futures = [pool.submit(run_one, root, scratch, m, timeout) for m in mutations]
            results = [f.result() for f in futures]
    return results, ""


def exit_code(results: list[Result]) -> int:
    if any(r.outcome in {"invalid", "error"} for r in results):
        return 2
    if any(r.outcome in {"survived", "crashed"} for r in results):
        return 1
    return 0


def render(results: list[Result]) -> str:
    lines = [f"{'MUTATION':36} {'OUTCOME':9} {'SEC':>5}  RULE"]
    for r in results:
        lines.append(f"{r.name:36} {r.outcome.upper():9} {r.seconds:5.1f}  {r.why}")
        if r.outcome == "survived":
            lines.append("    ^ test gap: no focused test fails when this rule is weakened")
        elif r.outcome == "crashed":
            lines.append("    ^ only errors, no assertion failure: " + ", ".join(r.failing[:3]))
        elif r.outcome in {"invalid", "error"} and r.detail:
            lines.append(f"    ^ {r.detail[:300]}")
    counts = {k: sum(1 for r in results if r.outcome == k)
              for k in ("killed", "crashed", "survived", "invalid", "error")}
    lines.append("SUMMARY: " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list", action="store_true", help="print the mutation catalog and exit")
    parser.add_argument("--only", action="append", default=[], metavar="NAME", help="run only these mutations")
    parser.add_argument("--jobs", type=int, default=2, help="parallel runs (default 2)")
    parser.add_argument("--timeout", type=int, default=600, help="seconds per run (default 600)")
    parser.add_argument("--json", type=Path, metavar="FILE", help="also write a machine-readable report")
    parser.add_argument("--skip-baseline", action="store_true", help="do not verify the unmutated copy first")
    args = parser.parse_args(argv)

    selected = MUTATIONS
    if args.only:
        unknown = sorted(set(args.only) - {m.name for m in MUTATIONS})
        if unknown:
            print("Unknown mutation(s): " + ", ".join(unknown), file=sys.stderr)
            return 2
        selected = tuple(m for m in MUTATIONS if m.name in args.only)
    if args.list:
        for m in MUTATIONS:
            print(f"{m.name:36} {m.path}\n    {m.why}")
        return 0

    results, problem = run_probe(REPO, selected, jobs=args.jobs, timeout=args.timeout,
                                 check_baseline=not args.skip_baseline)
    if problem:
        print(problem, file=sys.stderr)
        return 2
    print(render(results))
    if args.json:
        args.json.write_text(json.dumps([r.__dict__ for r in results], ensure_ascii=False, indent=2),
                             encoding="utf-8")
    return exit_code(results)


if __name__ == "__main__":
    raise SystemExit(main())
