#!/usr/bin/env python3
"""Compare two ways of producing proposals (baseline vs candidate) on the same tasks, from recorded runs.

A change to a skill, prompt or workflow is only an improvement if the same tasks, run under the same conditions, end
up verified more often at no worse cost. This aggregates run records; it never runs anything and never invents a result.

runs.json: a list of {"task": "...", "arm": "baseline|candidate", "conditions": "model, budget, input version",
                      "claimed_complete": true|false, "verified": true|false|null,
                      "seconds": 0, "cost": 0, "prior_pass": true|false, "regressed": true|false}
  verified null means "not independently verified": it counts as NOT VERIFIED, never as success. Missing/null cost or
  seconds makes that aggregate unavailable, not zero. Conditions can also be an object with model, input, rubric,
  scorer and environment fields. Add budget, tools and prompt to record an extended context. Legacy contexts are
  reported as INCOMPLETE. Matching labels are declarations, not evidence that conditions actually matched.
  Alternatively supply {"planned": ["task ID", ...], "runs": [...]} to detect tasks omitted from both arms.
  Optional attempts are {"id": "...", "status": "started|completed|invalid|skipped"} with an explicit boolean
  retry_allowed. Attempt histories are declarations; validation does not establish their authenticity or reconciliation.
  prior_pass/regressed are optional: regression rate = regressed / prior_pass tasks.

Refused (exit 2) unless the arms are paired: each arm covers exactly the same tasks, once each, with identical
`conditions` per task. Metrics per arm:
  verified success rate     verified true / tasks (unverified and failed both count against it)
  false completion rate     claimed complete but verified false / claimed complete; unavailable if any claim is unverified
  not-verified count        runs with verified null
  cost per verified task    total cost / verified true (n/a when none)
  regression rate           regressed / prior_pass
  paired counts             pass/pass, fail/pass, pass/fail, fail/fail, or either side unverified

No significance test is performed and no target is assumed: with few tasks a difference is an observation, not a result.
Exit codes: 0 ok, 2 invalid or unpaired input.

Usage: python eval_metrics.py runs.json
"""
from __future__ import annotations

import json
import math
import os
import stat
import sys
from collections import Counter
from pathlib import Path

ARMS = ("baseline", "candidate")
CONTEXT_REQUIRED = {"model", "input", "rubric", "scorer", "environment"}
CONTEXT_EXTENDED = CONTEXT_REQUIRED | {"budget", "tools", "prompt"}
MAX_INPUT_BYTES = 4 * 1024 * 1024


def _finite_nonnegative(value: object) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _unique_members(pairs):
    data = {}
    for key, value in pairs:
        if key in data:
            raise ValueError("duplicate JSON member")
        data[key] = value
    return data


def read_input(path: str):
    """Read bounded regular-file JSON; no claim about source authenticity or concurrent writes."""
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(path, flags)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("input must be a regular file")
        with os.fdopen(fd, "rb") as stream:
            fd = -1
            data = stream.read(MAX_INPUT_BYTES + 1)
        if len(data) > MAX_INPUT_BYTES:
            raise ValueError("input too large")
        return json.loads(data.decode("utf-8-sig"), object_pairs_hook=_unique_members,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError("invalid numeric constant")))
    finally:
        if fd != -1:
            os.close(fd)


def load(runs: list[dict]) -> dict[str, dict[str, dict]]:
    """Return {arm: {task: run}} or raise ValueError describing why the input is unusable or unpaired."""
    by_arm: dict[str, dict[str, dict]] = {arm: {} for arm in ARMS}
    for index, run in enumerate(runs, 1):
        if not isinstance(run, dict) or run.get("arm") not in ARMS or not isinstance(run.get("task"), str) or not run["task"].strip():
            raise ValueError(f"run {index}: needs a task and arm 'baseline' or 'candidate'")
        conditions = run.get("conditions")
        if not isinstance(conditions, (str, dict)) or not conditions or (isinstance(conditions, str) and not conditions.strip()):
            raise ValueError(f"run {index}: conditions must be recorded so the comparison can be checked")
        if isinstance(conditions, str) and conditions.strip().upper() in {"UNKNOWN", "N/A", "TBD", "NONE"}:
            raise ValueError(f"run {index}: conditions are unknown")
        if isinstance(conditions, dict) and (set(conditions) not in (CONTEXT_REQUIRED, CONTEXT_EXTENDED) or any(not isinstance(v, str) or not v.strip() or v.strip().upper() in {"UNKNOWN", "N/A", "TBD", "NONE"} for v in conditions.values())):
            raise ValueError(f"run {index}: invalid structured conditions")
        if not isinstance(run.get("claimed_complete"), bool) or "verified" not in run or not (run["verified"] is True or run["verified"] is False or run["verified"] is None):
            raise ValueError(f"run {index}: claimed_complete must be true/false and verified true/false/null")
        for key in ("seconds", "cost"):
            value = run.get(key)
            if value is not None and not _finite_nonnegative(value):
                raise ValueError(f"run {index}: {key} must be a finite non-negative number or null")
        for key in ("prior_pass", "regressed"):
            if key in run and run[key] is not None and not isinstance(run[key], bool):
                raise ValueError(f"run {index}: {key} must be true, false or null")
        if run.get("regressed") is True and run.get("prior_pass") is not True:
            raise ValueError(f"run {index}: regression requires a prior pass")
        if "attempts" in run:
            attempts = run["attempts"]
            if not isinstance(attempts, list) or any(not isinstance(a, dict) or set(a) != {"id", "status"} or not isinstance(a["id"], str) or not a["id"].strip() or a["status"] not in ("started", "completed", "invalid", "skipped") for a in attempts):
                raise ValueError(f"run {index}: invalid attempts")
            if len({a["id"] for a in attempts}) != len(attempts):
                raise ValueError(f"run {index}: duplicate attempt ID")
            if not isinstance(run.get("retry_allowed"), bool):
                raise ValueError(f"run {index}: retry_allowed must be declared")
            if len(attempts) > 1 and not run["retry_allowed"]:
                raise ValueError(f"run {index}: retry was not allowed")
            if run["verified"] is not None and (not attempts or attempts[-1]["status"] != "completed" or any(a["status"] == "started" for a in attempts)):
                raise ValueError(f"run {index}: verified result needs a completed, reconciled attempt")
        if run["task"] in by_arm[run["arm"]]:
            raise ValueError(f"run {index}: task '{run['task']}' appears twice in {run['arm']}")
        by_arm[run["arm"]][run["task"]] = run
    if not by_arm["baseline"] or set(by_arm["baseline"]) != set(by_arm["candidate"]):
        raise ValueError("arms are not paired: baseline and candidate must cover exactly the same tasks")
    for task in by_arm["baseline"]:
        if by_arm["baseline"][task]["conditions"] != by_arm["candidate"][task]["conditions"]:
            raise ValueError(f"task '{task}': conditions differ between arms")
    return by_arm


def metrics(runs: list[dict]) -> dict:
    total = len(runs)
    verified = [r for r in runs if r["verified"] is True]
    claimed = [r for r in runs if r["claimed_complete"]]
    false_complete = [r for r in claimed if r["verified"] is False]
    prior = [r for r in runs if r.get("prior_pass") is True]
    return {
        "tasks": total,
        "verified_success_rate": len(verified) / total,
        "false_completion_rate": (len(false_complete) / len(claimed)) if claimed and all(r["verified"] is not None for r in claimed) else None,
        "claimed_complete": len(claimed),
        "false_completions": len(false_complete),
        "claimed_unverified": sum(r["verified"] is None for r in claimed),
        "attempts_recorded": sum(len(r.get("attempts", [])) for r in runs) if all("attempts" in r for r in runs) else None,
        "not_verified": sum(1 for r in runs if r["verified"] is None),
        "cost_per_verified": (sum(r["cost"] for r in runs) / len(verified)) if verified and all(r.get("cost") is not None for r in runs) else None,
        "seconds_total": sum(r["seconds"] for r in runs) if all(r.get("seconds") is not None for r in runs) else None,
        "regression_rate": (sum(1 for r in prior if r.get("regressed") is True) / len(prior)) if prior and all(r.get("regressed") is not None for r in prior) else None,
    }


def paired_counts(by_arm: dict) -> dict[str, int]:
    counts = {key: 0 for key in ("pass_pass", "fail_pass", "pass_fail", "fail_fail", "unverified")}
    for task, old in by_arm["baseline"].items():
        a, b = old["verified"], by_arm["candidate"][task]["verified"]
        key = "unverified" if a is None or b is None else f"{'pass' if a else 'fail'}_{'pass' if b else 'fail'}"
        counts[key] += 1
    return counts


def render(table: dict[str, dict]) -> str:
    def cell(value):
        return "n/a" if value is None else (f"{value:.2f}" if isinstance(value, float) else str(value))
    keys = list(next(iter(table.values())))
    lines = [f"{'metric':24}" + "".join(f"{arm:>12}" for arm in table)]
    lines += [f"{key:24}" + "".join(f"{cell(table[arm][key]):>12}" for arm in table) for key in keys]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        runs = read_input(args[0])
        planned = None
        if isinstance(runs, dict):
            if set(runs) != {"planned", "runs"} or not isinstance(runs["planned"], list) or not runs["planned"] or not all(isinstance(x, str) and x.strip() for x in runs["planned"]) or len(set(runs["planned"])) != len(runs["planned"]):
                raise ValueError("planned must be a nonempty list of unique task IDs")
            planned, runs = set(runs["planned"]), runs["runs"]
        if not isinstance(runs, list):
            raise ValueError("runs.json must be a list")
        by_arm = load(runs)
        if planned is not None and set(by_arm["baseline"]) != planned:
            raise ValueError("planned tasks and recorded tasks differ")
        table = {arm: metrics(list(by_arm[arm].values())) for arm in ARMS}
        if any(value is not None and not _finite_nonnegative(value)
               for row in table.values() for key, value in row.items()
               if key in {"cost_per_verified", "seconds_total"}):
            raise ValueError("aggregate exceeds supported finite range")
    except (OSError, ValueError, UnicodeError, RecursionError, OverflowError):
        print("Invalid or unreadable evaluation input", file=sys.stderr)
        return 2
    print(render(table))
    complete_context = all(isinstance(r["conditions"], dict) and set(r["conditions"]) == CONTEXT_EXTENDED for arm in ARMS for r in by_arm[arm].values())
    print("CONTEXT: " + ("DECLARED-MATCH" if complete_context else "INCOMPLETE") + "; matching labels do not authenticate comparability")
    print("PAIRS: " + ", ".join(f"{key}={value}" for key, value in paired_counts(by_arm).items()))
    counts = Counter(r["verified"] for arm in ARMS for r in by_arm[arm].values())
    print(f"EVAL-METRICS: paired on {len(by_arm['baseline'])} task(s); verified true={counts[True]}, false={counts[False]}, "
          f"not verified={counts[None]}. Observation only: no significance test, no target assumed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
