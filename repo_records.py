#!/usr/bin/env python3
"""Check the repository's own records: deliberate decisions and the defect ledger.

    python repo_records.py            # prints REPO-RECORDS: CLEAN, or each finding and exit 1

references/design-decisions.md  Each `### Dnn` entry needs Decision, Why, Revisit only if, Lives in and Pinned by. Every path
                                in `Lives in` must exist and every `file.py::Class.test` in `Pinned by` must resolve to a real
                                test, so a decision cannot outlive the test that holds it.
references/defect-ledger.jsonl  One JSON object per fixed defect: date, change (#number), class, what, escaped, mechanism.
                                `escaped` says why the existing checks let it through and `mechanism` what now prevents the class.
references/defect-guards.json   A class with `threshold` (3) or more ledger entries needs a guard test; the file maps the class to
                                that test. A guard whose class is not in the ledger is stale.
The test suite runs this check, so a record that drifts from the code fails CI like any other test.
"""
from __future__ import annotations

import ast
import datetime
import json
import re
import sys
from collections import Counter
from pathlib import Path

DECISIONS = "references/design-decisions.md"
LEDGER = "references/defect-ledger.jsonl"
GUARDS = "references/defect-guards.json"
DECISION_FIELDS = ("Decision", "Why", "Revisit only if", "Lives in", "Pinned by")
LEDGER_FIELDS = ("date", "change", "class", "what", "escaped", "mechanism")
PLACEHOLDER = re.compile(r"^(?:todo|tbd|n/?a|none|-+|\.{3})$", re.I)
ENTRY = re.compile(r"^### (D\d{2}) (.+)$")
FIELD = re.compile(r"^- \*\*(.+?):\*\* (.+)$")


def unique_members(pairs):
    seen: dict = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError(f"duplicate key {key!r}")
        seen[key] = value
    return seen


def resolve_test_ref(repo: Path, ref: str) -> str | None:
    """None when `file.py::Class.test` (or `file.py::test`) names a test that exists, otherwise the reason it does not."""
    file_part, _, member = ref.partition("::")
    path = repo / file_part
    if not file_part.endswith(".py") or not path.is_file():
        return f"{ref}: no such test file {file_part!r}"
    if not member:
        return f"{ref}: name the test as file.py::Class.test_name"
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, ValueError) as exc:
        return f"{ref}: {file_part} cannot be read ({type(exc).__name__})"
    scope = tree.body
    *classes, name = member.split(".")
    for class_name in classes:
        found = next((n for n in scope if isinstance(n, ast.ClassDef) and n.name == class_name), None)
        if found is None:
            return f"{ref}: no class {class_name!r} in {file_part}"
        scope = found.body
    if not any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name for n in scope):
        return f"{ref}: no test {name!r} in {file_part}"
    return None


def backticked(value: str) -> list[str]:
    return re.findall(r"`([^`]+)`", value)


def check_decisions(repo: Path, relative: str = DECISIONS) -> list[str]:
    path = repo / relative
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return [f"{relative}: cannot be read"]
    entries: dict[str, dict[str, str]] = {}
    problems: list[str] = []
    current = None
    for line in lines:
        head = ENTRY.match(line)
        if head:
            if head.group(1) in entries:
                problems.append(f"{relative}: {head.group(1)} appears twice")
            current = entries.setdefault(head.group(1), {})
            continue
        field = FIELD.match(line)
        if field and current is not None:
            current[field.group(1)] = field.group(2).strip()
    if not entries:
        problems.append(f"{relative}: no `### Dnn` entries found")
    for ident, fields in entries.items():
        for name in DECISION_FIELDS:
            value = fields.get(name, "")
            if not value or PLACEHOLDER.match(value):
                problems.append(f"{relative}: {ident} lacks a real '{name}'")
        for where in backticked(fields.get("Lives in", "")):
            if not (repo / where).exists():
                problems.append(f"{relative}: {ident} lives in {where!r}, which does not exist")
        refs = backticked(fields.get("Pinned by", ""))
        if not refs:
            problems.append(f"{relative}: {ident} names no pinning test in backticks")
        problems += [f"{relative}: {ident} pinned by {reason}" for reason in filter(None, (resolve_test_ref(repo, r) for r in refs))]
    return problems


def check_ledger(repo: Path, ledger: str = LEDGER, guards: str = GUARDS) -> list[str]:
    problems: list[str] = []
    try:
        raw_lines = (repo / ledger).read_text(encoding="utf-8").splitlines()
    except OSError:
        return [f"{ledger}: cannot be read"]
    rows: list[dict] = []
    for number, line in enumerate(raw_lines, 1):
        if not line.strip():
            problems.append(f"{ledger}:{number}: blank line")
            continue
        try:
            row = json.loads(line, object_pairs_hook=unique_members)
        except ValueError as exc:
            problems.append(f"{ledger}:{number}: not a JSON object ({exc})")
            continue
        if not isinstance(row, dict):
            problems.append(f"{ledger}:{number}: not a JSON object")
            continue
        rows.append(row)
        for name in LEDGER_FIELDS:
            value = row.get(name)
            if not isinstance(value, str) or not value.strip() or PLACEHOLDER.match(value.strip()):
                problems.append(f"{ledger}:{number}: '{name}' must be real text")
        for name in set(row) - set(LEDGER_FIELDS):
            problems.append(f"{ledger}:{number}: unknown field {name!r}")
        try:
            datetime.date.fromisoformat(str(row.get("date", "")))
        except ValueError:
            problems.append(f"{ledger}:{number}: date must be YYYY-MM-DD")
        if not re.fullmatch(r"#\d+", str(row.get("change", ""))):
            problems.append(f"{ledger}:{number}: change must be a pull request or issue number like #66")
        if not re.fullmatch(r"[a-z][a-z0-9-]*", str(row.get("class", ""))):
            problems.append(f"{ledger}:{number}: class must be lower-case words joined by hyphens")
    try:
        config = json.loads((repo / guards).read_text(encoding="utf-8"), object_pairs_hook=unique_members)
    except (OSError, ValueError) as exc:
        return problems + [f"{guards}: cannot be read ({exc})"]
    threshold = config.get("threshold") if isinstance(config, dict) else None
    classes = config.get("classes") if isinstance(config, dict) else None
    if not isinstance(threshold, int) or isinstance(threshold, bool) or threshold < 2 or not isinstance(classes, dict):
        return problems + [f"{guards}: needs an integer `threshold` of at least 2 and a `classes` object"]
    counts = Counter(str(row.get("class")) for row in rows)
    for name, count in sorted(counts.items()):
        if count >= threshold and name not in classes:
            problems.append(f"{ledger}: class {name!r} has {count} entries, so it needs a guard test in {guards}")
    for name, guard in classes.items():
        if name not in counts:
            problems.append(f"{guards}: guard for class {name!r}, which is not in the ledger")
        if not isinstance(guard, dict) or not str(guard.get("how", "")).strip():
            problems.append(f"{guards}: guard {name!r} must say `how` the test catches the class")
            continue
        reason = resolve_test_ref(repo, str(guard.get("test", "")))
        if reason:
            problems.append(f"{guards}: guard {name!r}: {reason}")
    return problems


def main(argv: list[str] | None = None) -> int:
    repo = Path(argv[0]) if argv else Path(__file__).resolve().parent
    problems = check_decisions(repo) + check_ledger(repo)
    for problem in problems:
        print(f"[finding] {problem}")
    if problems:
        print(f"REPO-RECORDS: FINDINGS ({len(problems)})")
        return 1
    print("REPO-RECORDS: CLEAN")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
