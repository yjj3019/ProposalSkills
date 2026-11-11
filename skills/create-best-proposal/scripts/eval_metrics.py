#!/usr/bin/env python3
"""Compare two ways of producing proposals (baseline vs candidate) on the same tasks, from recorded runs.

A change to a skill, prompt or workflow is only an improvement if the same tasks, run under the same conditions, end
up verified more often at no worse cost. This aggregates run records; it never runs anything and never invents a result.

runs.json: a list of {"task": "...", "arm": "baseline|candidate", "conditions": "model, budget, input version",
                      "claimed_complete": true|false, "verified": true|false|null,
                      "seconds": 0, "cost": 0, "prior_pass": true|false, "regressed": true|false}
  verified null means "not independently verified": it counts as NOT VERIFIED, never as success.
  prior_pass/regressed are optional: regression rate = regressed / prior_pass tasks.

Refused (exit 2) unless the arms are paired: each arm covers exactly the same tasks, once each, with identical
`conditions` per task. Metrics per arm:
  verified success rate     verified true / tasks (unverified and failed both count against it)
  false completion rate     claimed complete but verified false / claimed complete
  not-verified count        runs with verified null
  cost per verified task    total cost / verified true (n/a when none)
  regression rate           regressed / prior_pass

No significance test is performed and no target is assumed: with few tasks a difference is an observation, not a result.
Exit codes: 0 ok, 2 invalid or unpaired input.

Usage: python eval_metrics.py runs.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ARMS = ("baseline", "candidate")


def load(runs: list[dict]) -> dict[str, dict[str, dict]]:
    """Return {arm: {task: run}} or raise ValueError describing why the input is unusable or unpaired."""
    by_arm: dict[str, dict[str, dict]] = {arm: {} for arm in ARMS}
    for index, run in enumerate(runs, 1):
        if not isinstance(run, dict) or run.get("arm") not in ARMS or not str(run.get("task", "")).strip():
            raise ValueError(f"run {index}: needs a task and arm 'baseline' or 'candidate'")
        if not str(run.get("conditions", "")).strip():
            raise ValueError(f"run {index}: conditions must be recorded so the comparison can be checked")
        if not isinstance(run.get("claimed_complete"), bool) or run.get("verified") not in (True, False, None):
            raise ValueError(f"run {index}: claimed_complete must be true/false and verified true/false/null")
        for key in ("seconds", "cost"):
            if not isinstance(run.get(key, 0), (int, float)) or isinstance(run.get(key), bool) or run.get(key, 0) < 0:
                raise ValueError(f"run {index}: {key} must be a non-negative number")
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
        "false_completion_rate": (len(false_complete) / len(claimed)) if claimed else None,
        "not_verified": sum(1 for r in runs if r["verified"] is None),
        "cost_per_verified": (sum(r.get("cost", 0) for r in runs) / len(verified)) if verified else None,
        "seconds_total": sum(r.get("seconds", 0) for r in runs),
        "regression_rate": (sum(1 for r in prior if r.get("regressed")) / len(prior)) if prior else None,
    }


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
        runs = json.loads(Path(args[0]).read_text(encoding="utf-8-sig"))
        if not isinstance(runs, list):
            raise ValueError("runs.json must be a list")
        by_arm = load(runs)
    except (OSError, ValueError) as exc:
        print(f"Invalid input: {exc}", file=sys.stderr)
        return 2
    table = {arm: metrics(list(by_arm[arm].values())) for arm in ARMS}
    print(render(table))
    counts = Counter(r["verified"] for arm in ARMS for r in by_arm[arm].values())
    print(f"EVAL-METRICS: paired on {len(by_arm['baseline'])} task(s); verified true={counts[True]}, false={counts[False]}, "
          f"not verified={counts[None]}. Observation only: no significance test, no target assumed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
