#!/usr/bin/env python3
"""Return 0 only when a proposal audit JSON passes deterministic gates."""

from __future__ import annotations

import json
import sys
from pathlib import Path


REQUIRED_FIELDS = {
    "mode", "bid_decision", "bid_conditions", "requirements", "claims",
    "unresolved_tokens", "attachments", "source_conflicts", "checks",
    "artifact_required", "render",
}
ARRAY_FIELDS = {
    "bid_conditions", "requirements", "claims", "unresolved_tokens",
    "attachments", "source_conflicts",
}
OBJECT_FIELDS = {"checks", "render"}


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
    for name in ("bid_conditions", "requirements", "claims", "attachments"):
        if isinstance(data.get(name), list) and any(not isinstance(item, dict) for item in data[name]):
            failures.append(f"{name} entries must be objects")
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

    for attachment in data["attachments"]:
        if attachment.get("required") and not attachment.get("present"):
            failures.append(f"missing attachment: {attachment.get('name', '?')}")

    for name in ("consistency", "arithmetic", "submission"):
        if data["checks"].get(name) is not True:
            failures.append(f"check failed or missing: {name}")

    if data["artifact_required"] and not data["render"].get("verified"):
        failures.append("render verification is missing or failed")
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
