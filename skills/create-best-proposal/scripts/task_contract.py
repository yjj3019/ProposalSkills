#!/usr/bin/env python3
"""Proposal task contract: what a long proposal job may do, how long it may try, and what counts as done.

A job that runs for days across sessions needs its limits written down before it starts, and a status that cannot jump
to "verified" without evidence. The contract is a JSON file in the working folder (never in this repository).

contract.json fields
  goal, scope[], non_goals[]                       text; scope and non_goals must be non-empty lists
  inputs[]                                         e.g. the RFP file and its version or SHA-256
  outputs[]                                        deliverables
  allowed_actions[]                                subset of: read, write-workspace, run-checks, render, network,
                                                   external-send, publish (the last three also need approvals[])
  approvals[]                                      who approved each outward-facing action: {"action", "by"}
  write_boundary                                   the one folder the job may write to
  test_oracle[]                                    ids of the checks that decide "done" (e.g. "unified_gate")
  max_attempts, time_budget_minutes                positive integers (max_attempts matches retry_guard.py)
  stop_conditions[], recovery                      when to stop; how to roll back or resume
  state, attempts, results{}, evidence_links[]     progress (maintained by `advance`)

States and moves
  Planned -> Running -> Verifying -> Verified (end)
  Running -> Failed | Blocked;  Verifying -> Failed | Not Verified | Running;  Failed -> Running (while attempts < max_attempts)
  Blocked -> Running (needs a resolution note);  Not Verified -> Verifying | Running
  Entering Verified needs evidence_links and every test_oracle id in results{} marked "pass"; Failed needs a cause; Blocked
  needs a blocker. Going back to Running from Failed counts one attempt and is refused once max_attempts is used up.

Not-started, unavailable and skipped checks are "Not Verified", never "Verified". This records and enforces a procedure; it
does not authenticate who ran what. Exit codes: 0 ok, 1 contract invalid or move refused, 2 usage error or unreadable file.

  python task_contract.py validate CONTRACT.json
  python task_contract.py advance CONTRACT.json STATE [--cause T] [--blocker T] [--note T] [--evidence PATH ...] [--result ID=pass|fail ...]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path, PureWindowsPath

STATES = ("Planned", "Running", "Verifying", "Verified", "Failed", "Blocked", "Not Verified")
MOVES = {"Planned": {"Running"}, "Running": {"Verifying", "Failed", "Blocked"},
         "Verifying": {"Verified", "Failed", "Not Verified", "Running"}, "Failed": {"Running"},
         "Blocked": {"Running"}, "Not Verified": {"Verifying", "Running"}, "Verified": set()}
ACTIONS = {"read", "write-workspace", "run-checks", "render", "network", "external-send", "publish"}
OUTWARD = {"network", "external-send", "publish"}


def boundary_problem(value: object) -> str | None:
    """The write boundary must name one specific folder: not the current directory, a drive or filesystem root, the home
    folder, a wildcard, or a path that climbs out with `..`."""
    text = str(value).strip()
    if not text:
        return None  # reported as empty elsewhere
    path = PureWindowsPath(text)  # understands both / and \
    if ".." in path.parts:
        return "write_boundary must not contain '..'"
    if text in {"~", "*"} or text.startswith(("~/", "~\\")) and not path.parts[1:]:
        return "write_boundary must not be the home folder or a wildcard"
    if not path.parts:
        return "write_boundary must name a specific folder, not the current directory"
    if path.anchor and len(path.parts) <= 1:
        return "write_boundary must not be a drive or filesystem root"
    return None


def validate(contract: dict) -> list[str]:
    problems: list[str] = []
    for key in ("goal", "write_boundary", "recovery"):
        if not str(contract.get(key, "")).strip():
            problems.append(f"{key} is empty")
    reason = boundary_problem(contract.get("write_boundary", ""))
    if reason:
        problems.append(reason)
    for key in ("scope", "non_goals", "outputs", "test_oracle", "stop_conditions"):
        value = contract.get(key)
        if not isinstance(value, list) or not value or not all(isinstance(x, str) and x.strip() for x in value):
            problems.append(f"{key} must be a non-empty list of text")
    for key in ("max_attempts", "time_budget_minutes"):
        value = contract.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            problems.append(f"{key} must be a positive integer")
    actions = contract.get("allowed_actions")
    if not isinstance(actions, list) or not actions or set(actions) - ACTIONS:
        problems.append(f"allowed_actions must be a non-empty subset of {sorted(ACTIONS)}")
    else:
        approved = {a.get("action") for a in contract.get("approvals", []) if isinstance(a, dict) and str(a.get("by", "")).strip()}
        for action in sorted(OUTWARD & set(actions)):
            if action not in approved:
                problems.append(f"{action} is allowed but has no approval (approvals[] needs {{action, by}})")
    state = contract.get("state", "Planned")
    if state not in STATES:
        problems.append(f"state must be one of {STATES}")
    attempts = contract.get("attempts", 0)
    if not isinstance(attempts, int) or isinstance(attempts, bool) or attempts < 0:
        problems.append("attempts must be a non-negative integer")
    elif isinstance(contract.get("max_attempts"), int) and attempts > contract["max_attempts"]:
        problems.append("attempts exceed max_attempts")
    if state == "Verified":
        problems += _verified_problems(contract)
    return problems


def _verified_problems(contract: dict) -> list[str]:
    problems = []
    if not contract.get("evidence_links"):
        problems.append("Verified needs evidence_links")
    results = contract.get("results") if isinstance(contract.get("results"), dict) else {}
    for check in contract.get("test_oracle", []):
        if results.get(check) != "pass":
            problems.append(f"Verified needs test_oracle '{check}' to be 'pass' in results (found {results.get(check)!r})")
    return problems


def advance(contract: dict, target: str, *, cause: str = "", blocker: str = "", note: str = "",
            evidence: list[str] | None = None, results: dict[str, str] | None = None) -> dict:
    """Return the contract after one allowed move, or raise ValueError saying why it is refused."""
    problems = validate(contract)
    if problems:
        raise ValueError("contract is invalid: " + problems[0])
    current = contract.get("state", "Planned")
    if target not in STATES or target not in MOVES[current]:
        raise ValueError(f"{current} -> {target} is not an allowed move (allowed: {sorted(MOVES[current]) or 'none'})")
    new = json.loads(json.dumps(contract))
    new["evidence_links"] = list(new.get("evidence_links", [])) + list(evidence or [])
    new["results"] = {**new.get("results", {}), **(results or {})}
    if target == "Failed" and not cause.strip():
        raise ValueError("Failed needs --cause")
    if target == "Blocked" and not blocker.strip():
        raise ValueError("Blocked needs --blocker")
    if current == "Blocked" and target == "Running" and not note.strip():
        raise ValueError("leaving Blocked needs --note describing the resolution")
    if current == "Failed" and target == "Running":
        if new.get("attempts", 0) + 1 > new["max_attempts"]:
            raise ValueError("max_attempts is used up: stop and report instead of retrying")
        new["attempts"] = new.get("attempts", 0) + 1
    new["state"] = target
    if target == "Verified":
        problems = _verified_problems(new)
        if problems:
            raise ValueError(problems[0])
    new["history"] = list(new.get("history", [])) + [{"from": current, "to": target, "cause": cause, "blocker": blocker, "note": note}]
    return new


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="action", required=True)
    check = sub.add_parser("validate")
    check.add_argument("contract", type=Path)
    move = sub.add_parser("advance")
    move.add_argument("contract", type=Path)
    move.add_argument("state")
    move.add_argument("--cause", default="")
    move.add_argument("--blocker", default="")
    move.add_argument("--note", default="")
    move.add_argument("--evidence", action="append", default=[])
    move.add_argument("--result", action="append", default=[], metavar="ID=pass|fail")
    args = parser.parse_args(argv)
    try:
        contract = json.loads(args.contract.read_text(encoding="utf-8-sig"))
        if not isinstance(contract, dict):
            raise ValueError("contract must be an object")
    except (OSError, ValueError) as exc:
        print(f"Cannot read the contract: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    if args.action == "validate":
        problems = validate(contract)
        for problem in problems:
            print(f"[INVALID] {problem}")
        print(f"TASK-CONTRACT: {'INVALID' if problems else 'VALID'} (state {contract.get('state', 'Planned')})")
        return 1 if problems else 0
    if any("=" not in item for item in args.result):
        print("--result must look like ID=pass or ID=fail", file=sys.stderr)
        return 2
    try:
        updated = advance(contract, args.state, cause=args.cause, blocker=args.blocker, note=args.note,
                          evidence=args.evidence, results=dict(item.split("=", 1) for item in args.result))
    except ValueError as exc:
        print(f"[REFUSED] {exc}")
        return 1
    try:
        args.contract.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"Cannot write the contract: {type(exc).__name__}", file=sys.stderr)
        return 2
    print(f"TASK-CONTRACT: {contract.get('state', 'Planned')} -> {updated['state']} (attempts {updated.get('attempts', 0)}/{updated['max_attempts']})")
    return 0

if __name__ == "__main__":
    sys.exit(main())
