#!/usr/bin/env python3
"""Return 0 only when a proposal audit JSON passes deterministic gates."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path


REQUIRED_FIELDS = {
    "mode", "bid_decision", "bid_conditions", "requirements", "claims",
    "unresolved_tokens", "attachments", "source_conflicts", "checks",
    "inputs", "defects", "artifact_required", "render", "package", "submission",
}
ARRAY_FIELDS = {
    "bid_conditions", "requirements", "claims", "unresolved_tokens",
    "attachments", "source_conflicts", "inputs", "defects",
}
OBJECT_FIELDS = {"checks", "render", "package", "submission"}
MODES = {"submission", "draft", "review", "analysis"}
BID_DECISIONS = {"bid", "conditional-bid", "intake-incomplete", "no-bid"}
INPUT_CLASSES = {"blocking", "non-blocking", "assumption"}
DEFECT_SEVERITIES = {"critical", "major", "minor", "note"}
ITEM_STATUSES = {"open", "closed"}


def is_iso_datetime(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def validate_schema(data: object) -> list[str]:
    if not isinstance(data, dict):
        return ["audit root must be an object"]
    failures = [f"missing field: {name}" for name in sorted(REQUIRED_FIELDS - data.keys())]
    failures += [f"{name} must be an array" for name in sorted(ARRAY_FIELDS)
                 if name in data and not isinstance(data[name], list)]
    failures += [f"{name} must be an object" for name in sorted(OBJECT_FIELDS)
                 if name in data and not isinstance(data[name], dict)]
    if "artifact_required" in data and not isinstance(data["artifact_required"], bool):
        failures.append("artifact_required must be a boolean")
    for name in ("bid_conditions", "requirements", "claims", "attachments", "inputs", "defects"):
        if isinstance(data.get(name), list) and any(not isinstance(item, dict) for item in data[name]):
            failures.append(f"{name} entries must be objects")
    if "mode" in data and data["mode"] not in MODES:
        failures.append(f"unsupported mode: {data['mode']}")
    if "bid_decision" in data and data["bid_decision"] not in BID_DECISIONS:
        failures.append(f"unsupported bid_decision: {data['bid_decision']}")
    for item in data.get("inputs", []) if isinstance(data.get("inputs"), list) else []:
        if not isinstance(item, dict):
            continue
        if item.get("class") not in INPUT_CLASSES:
            failures.append(f"input {item.get('id', '?')} has unsupported class: {item.get('class')}")
        if item.get("status") not in ITEM_STATUSES:
            failures.append(f"input {item.get('id', '?')} has unsupported status: {item.get('status')}")
    for defect in data.get("defects", []) if isinstance(data.get("defects"), list) else []:
        if not isinstance(defect, dict):
            continue
        if defect.get("severity") not in DEFECT_SEVERITIES:
            failures.append(
                f"defect {defect.get('id', '?')} has unsupported severity: {defect.get('severity')}")
        if defect.get("status") not in ITEM_STATUSES:
            failures.append(f"defect {defect.get('id', '?')} has unsupported status: {defect.get('status')}")
        if defect.get("severity") in {"critical", "major"} and defect.get("status") == "closed":
            if not isinstance(defect.get("closure_evidence"), list) or not defect["closure_evidence"]:
                failures.append(f"defect {defect.get('id', '?')} lacks closure evidence")
            if not defect.get("reviewer"):
                failures.append(f"defect {defect.get('id', '?')} lacks closure reviewer")
            if not is_iso_datetime(defect.get("closed_at")):
                failures.append(f"defect {defect.get('id', '?')} lacks ISO closed_at")
            if not isinstance(defect.get("reverified_scope"), list) or not defect["reverified_scope"]:
                failures.append(f"defect {defect.get('id', '?')} lacks reverified scope")
    package = data.get("package")
    if isinstance(package, dict) and "checks" in package and not isinstance(package["checks"], dict):
        failures.append("package checks must be an object")
    render = data.get("render")
    if isinstance(render, dict) and "evidence" in render and not isinstance(render["evidence"], list):
        failures.append("render evidence must be an array")
    return failures


def evaluate(data: dict) -> list[str]:
    failures = validate_schema(data)
    if failures:
        return failures

    decision = data["bid_decision"]
    if decision == "conditional-bid":
        if not data["bid_conditions"]:
            failures.append("conditional-bid requires conditions")
        for condition in data["bid_conditions"]:
            if not all((condition.get("owner"), condition.get("deadline"), condition.get("accepted"))):
                failures.append(f"bid condition {condition.get('id', '?')} is not accepted")
    elif decision != "bid":
        failures.append("bid_decision must be 'bid' or accepted 'conditional-bid'")

    for item in data["requirements"]:
        if not item.get("mandatory"):
            continue
        if item.get("state") == "approved":
            continue
        if item.get("state") == "not-applicable" and item.get("rationale") and item.get("reviewer"):
            continue
        failures.append(f"requirement {item.get('id', '?')} is not approved")

    for claim in data["claims"]:
        if claim.get("kind") not in {"material", "commitment"}:
            continue
        if claim.get("status") not in {"supported", "qualified", "removed"}:
            failures.append(f"claim {claim.get('id', '?')} is unsupported")
        if claim.get("kind") == "commitment" and not claim.get("owner_approved"):
            failures.append(f"commitment {claim.get('id', '?')} lacks owner approval")

    failures.extend(f"unresolved token: {token}" for token in data["unresolved_tokens"])
    failures.extend(f"source conflict: {item}" for item in data["source_conflicts"])

    for item in data["inputs"]:
        if item.get("class") == "blocking" and item.get("status") != "closed":
            failures.append(f"blocking input {item.get('id', '?')} is open")

    for defect in data["defects"]:
        if defect.get("severity") in {"critical", "major"} and defect.get("status") != "closed":
            failures.append(f"{defect.get('severity')} defect {defect.get('id', '?')} is open")

    for attachment in data["attachments"]:
        if attachment.get("required") and not attachment.get("present"):
            failures.append(f"missing attachment: {attachment.get('name', '?')}")

    for name in ("consistency", "arithmetic", "submission"):
        if data["checks"].get(name) is not True:
            failures.append(f"check failed or missing: {name}")

    if data["artifact_required"] and not data["render"].get("verified"):
        failures.append("render verification is missing or failed")
    if data["artifact_required"] and data["render"].get("verified"):
        for field in ("artifact_hash", "tool", "evidence"):
            if not data["render"].get(field):
                failures.append(f"render verification lacks {field}")
    if data["package"].get("required") and not data["package"].get("inspected"):
        failures.append("package inspection is missing or failed")
    if data["package"].get("required") and data["package"].get("inspected"):
        for field in ("artifact_hash", "tool", "checks", "reviewer"):
            if not data["package"].get(field):
                failures.append(f"package inspection lacks {field}")
        for name, status in data["package"].get("checks", {}).items():
            if status not in {"pass", "fail", "not-inspected", "not-applicable"}:
                failures.append(f"package check {name} has unsupported status: {status}")
            elif status == "fail" or (data["mode"] == "submission" and status == "not-inspected"):
                failures.append(f"package check {name} is {status}")
    if data["mode"] == "submission":
        if not data["submission"].get("cleared"):
            failures.append("submission is not cleared")
        if not data["submission"].get("rehearsal_evidence"):
            failures.append("submission rehearsal evidence is missing")
        if not data["submission"].get("receipt_plan"):
            failures.append("submission receipt plan is missing")
    return failures


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: proposal_gate.py AUDIT.json", file=sys.stderr)
        return 2
    try:
        data = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"invalid audit file: {exc}", file=sys.stderr)
        return 2
    schema_failures = validate_schema(data)
    if schema_failures:
        print("INVALID AUDIT")
        for failure in schema_failures:
            print(f"- {failure}")
        return 2
    failures = evaluate(data)
    if failures:
        print("BLOCKED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
