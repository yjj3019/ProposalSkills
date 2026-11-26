#!/usr/bin/env python3
"""Compare two or more slide plans (Markdown/text) against the requirement matrix and report what each one covers.

Use it after asking several models (or people) for a slide-by-slide plan from the same RFP. Picking "the best parts" by taste
drifts; this picks by requirement coverage. For each plan it reports which REQ-IDs are answered, which are only listed without a
message, and which REQ-IDs it cites that the matrix does not have (invented or stale). Across plans it reports the union, what
only one plan covers, and what no plan covers.

A REQ-ID counts as answered when a line that cites it also carries at least 12 other characters (a message), after the ID and
table or list markup are removed. A bare mention such as `| REQ-004 | |` is reported as listed only. This measures that a plan
addresses a requirement, not that the answer is good or true; a person still reads the chosen plan.

Weights (optional): a JSON object {"REQ-001": 25, ...} of evaluation points per requirement. Every matrix REQ-ID must then
have a weight. Without it every requirement weighs 1.

Exit codes: 0 report produced and no plan cites an unknown REQ-ID (and the union meets --min-coverage, when given),
1 otherwise, 2 usage error or unreadable input.

Usage: python plan_coverage.py matrix.md PLAN_A.md PLAN_B.md [--weights weights.json] [--min-coverage 90] [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import mapping_check

MIN_MESSAGE_CHARS = 12
MARKUP = re.compile(r"[|*_`#>\-:\[\]()~]+")


def line_message_length(line: str) -> int:
    """Characters of a message left on a line after REQ-IDs and table/list markup are removed."""
    stripped = mapping_check.REQ_RE.sub(" ", line)
    stripped = MARKUP.sub(" ", stripped)
    return len(" ".join(stripped.split()))


def analyse_plan(text: str, matrix_ids: set[str]) -> dict:
    answered: set[str] = set()
    listed: set[str] = set()
    unknown: set[str] = set()
    for line in text.splitlines():
        ids = {mapping_check.normalize_id(m.group(0)) for m in mapping_check.REQ_RE.finditer(line)}
        if not ids:
            continue
        substantive = line_message_length(line) >= MIN_MESSAGE_CHARS
        for rid in ids:
            if rid not in matrix_ids:
                unknown.add(rid)
            elif substantive:
                answered.add(rid)
            else:
                listed.add(rid)
    return {"answered": answered, "listed_only": listed - answered, "unknown": unknown}


def weighted_share(ids: set[str], weights: dict[str, float]) -> float:
    total = sum(weights.values())
    return 100.0 * sum(weights[i] for i in ids) / total if total else 0.0


def compare(matrix_ids: set[str], plans: dict[str, str], weights: dict[str, float]) -> dict:
    per_plan = {}
    for name, text in plans.items():
        info = analyse_plan(text, matrix_ids)
        per_plan[name] = {
            "answered": sorted(info["answered"]),
            "listed_only": sorted(info["listed_only"]),
            "unknown": sorted(info["unknown"]),
            "answered_count": len(info["answered"]),
            "coverage_percent": round(weighted_share(info["answered"], weights), 1),
        }
    union = set().union(*(set(p["answered"]) for p in per_plan.values())) if per_plan else set()
    only = {name: sorted(set(p["answered"]) - set().union(*(set(q["answered"]) for n, q in per_plan.items() if n != name)))
            for name, p in per_plan.items()}
    best = max(per_plan, key=lambda n: (per_plan[n]["coverage_percent"], per_plan[n]["answered_count"])) if per_plan else None
    take_from_others = sorted(union - set(per_plan[best]["answered"])) if best else []
    return {
        "requirements": len(matrix_ids),
        "plans": per_plan,
        "union_coverage_percent": round(weighted_share(union, weights), 1),
        "covered_by_no_plan": sorted(matrix_ids - union),
        "only_in": only,
        "base_plan": best,
        "take_from_other_plans": take_from_others,
    }


def load_weights(path: Path | None, matrix_ids: set[str]) -> dict[str, float]:
    if path is None:
        return {rid: 1.0 for rid in matrix_ids}
    data = json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=mapping_check._unique_json_members)
    if not isinstance(data, dict):
        raise ValueError("weights must be a JSON object {REQ-ID: points}")
    weights: dict[str, float] = {}
    for key, value in data.items():
        rid = mapping_check.normalize_id(str(key))
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise ValueError(f"weight for {key} must be a non-negative number")
        if rid in weights:
            raise ValueError(f"duplicate weight for {rid}")
        weights[rid] = float(value)
    extra, missing = set(weights) - matrix_ids, matrix_ids - set(weights)
    if extra or missing:
        raise ValueError(f"weights and matrix disagree (not in matrix: {sorted(extra)}; no weight: {sorted(missing)})")
    return weights


def render(report: dict) -> str:
    lines = [f"Requirements: {report['requirements']} | plans: {len(report['plans'])} | "
             f"union coverage: {report['union_coverage_percent']}%"]
    for name, plan in report["plans"].items():
        lines.append(f"- {name}: answers {plan['answered_count']} ({plan['coverage_percent']}%), "
                     f"listed only {len(plan['listed_only'])}, unknown IDs {len(plan['unknown'])}")
        if plan["unknown"]:
            lines.append(f"    unknown (not in the matrix): {', '.join(plan['unknown'])}")
        if plan["listed_only"]:
            lines.append(f"    listed without a message: {', '.join(plan['listed_only'])}")
        if report["only_in"][name]:
            lines.append(f"    only this plan answers: {', '.join(report['only_in'][name])}")
    if report["base_plan"]:
        lines.append(f"Base plan (highest coverage): {report['base_plan']}")
        if report["take_from_other_plans"]:
            lines.append(f"Take from the other plans: {', '.join(report['take_from_other_plans'])}")
    if report["covered_by_no_plan"]:
        lines.append(f"Answered by no plan: {', '.join(report['covered_by_no_plan'])}")
    lines.append("Coverage means a requirement is addressed, not that the answer is good; read the chosen plan.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("matrix", type=Path)
    parser.add_argument("plans", type=Path, nargs="+")
    parser.add_argument("--weights", type=Path)
    parser.add_argument("--min-coverage", type=float)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if len(args.plans) < 2:
        print("Give at least two plans to compare", file=sys.stderr)
        return 2
    try:
        matrix_ids = set(mapping_check.parse_matrix(args.matrix))
        if not matrix_ids:
            print("No REQ-ID found in the matrix", file=sys.stderr)
            return 2
        weights = load_weights(args.weights, matrix_ids)
        plans: dict[str, str] = {}
        for index, path in enumerate(args.plans, 1):
            name = path.stem if path.stem not in plans else f"{path.stem}#{index}"
            plans[name] = path.read_text(encoding="utf-8-sig")
    except (OSError, ValueError, UnicodeDecodeError, KeyError) as exc:
        print(f"Cannot read input: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    report = compare(matrix_ids, plans, weights)
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else render(report))
    unknown = any(plan["unknown"] for plan in report["plans"].values())
    below = args.min_coverage is not None and report["union_coverage_percent"] < args.min_coverage
    return 1 if unknown or below else 0


if __name__ == "__main__":
    sys.exit(main())
