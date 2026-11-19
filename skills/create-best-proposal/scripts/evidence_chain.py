#!/usr/bin/env python3
"""Append-only, hash-chained log of the checks that were actually run, bound to the files they ran on.

Each record stores the command, its exit code, the SHA-256 of every artifact, and the hash of the previous record.
Editing or removing a record from the middle breaks the chain; changing an artifact afterwards is reported by
`verify --check-artifacts`. Cutting records off the END of the log is not detectable from the file alone: keep the
`head` hash from `verify` in the hand-off note and pass it back with `--expect-head` (or the record count with
`--expect-count`): a truncated log or one rebuilt from scratch then fails the comparison.

This is tamper-evidence for honest mistakes and casual edits, not authentication: anyone who can rewrite the whole
file can rebuild the chain.

Append uses a sibling .lock directory and replaces the log only after writing a complete temporary file. Concurrent
cooperating writers fail instead of waiting. The lock's owner.json is a diagnostic hint, not proof of identity or liveness.
After an interrupted process, check that it has stopped before manually removing its stale lock. This is not a filesystem
security boundary or a guarantee against power-loss corruption.

  python evidence_chain.py append LOG --command "..." --exit-code N [--artifact FILE ...] [--note TEXT]
                                       [--seconds S] [--cost AMOUNT]
  python evidence_chain.py verify LOG [--check-artifacts] [--expect-head HASH] [--expect-count N]
  python evidence_chain.py rerun LOG        list the commands whose artifacts changed or vanished (nothing else to redo)

`--seconds` and `--cost` are optional; `verify` totals recorded values, not necessarily the complete cost. `rerun` reads the
latest record per command and flags failed, artifact-free, missing or changed checks. It does not run them. Exit codes:
0 ok / nothing stale, 1 chain broken, artifact changed, or something stale, 2 usage error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

GENESIS = "0" * 64


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record_hash(record: dict) -> str:
    body = {k: v for k, v in record.items() if k != "hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def read_log(log: Path) -> list[dict]:
    if not log.exists():
        return []
    records = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]
    if any(not isinstance(record, dict) for record in records):
        raise ValueError("evidence records must be objects")
    return records


def _valid_metric(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value) and value >= 0
    except OverflowError:
        return False


def _metric_totals(records: list[dict]) -> dict[str, float]:
    totals = {}
    for key in ("seconds", "cost"):
        if any(key in record for record in records):
            try:
                totals[key] = math.fsum(record.get(key, 0) for record in records)
            except OverflowError as exc:
                raise ValueError(f"total {key} is out of range") from exc
            if not math.isfinite(totals[key]):
                raise ValueError(f"total {key} is out of range")
    return totals


def append(log: Path, command: str, exit_code: int, artifacts: list[Path], note: str = "", now: datetime | None = None,
           seconds: float | None = None, cost: float | None = None) -> dict:
    lock = log.with_name(log.name + ".lock")
    try:
        lock.mkdir()
    except FileExistsError as exc:
        raise ValueError("evidence log is locked; check the owner before removing a stale lock") from exc
    owner = lock / "owner.json"
    try:
        owner.write_text(json.dumps({"pid": os.getpid(), "started_utc": datetime.now(timezone.utc).isoformat()}), encoding="utf-8")
        return _append_locked(log, command, exit_code, artifacts, note, now, seconds, cost)
    finally:
        owner.unlink(missing_ok=True)
        lock.rmdir()


def _append_locked(log: Path, command: str, exit_code: int, artifacts: list[Path], note: str, now: datetime | None,
                   seconds: float | None, cost: float | None) -> dict:
    records = read_log(log)
    problems = verify(records) if records else []
    if problems:
        raise ValueError("refusing to append to a broken chain: " + problems[0])
    record = {"seq": len(records) + 1, "time": (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "command": command, "exit_code": exit_code, "note": note,
              "artifacts": [{"path": p.as_posix(), "sha256": digest(p)} for p in artifacts],
              "prev": records[-1]["hash"] if records else GENESIS}
    for key, value in (("seconds", seconds), ("cost", cost)):
        if value is not None:
            if not _valid_metric(value):
                raise ValueError(f"{key} must be finite and non-negative")
            record[key] = value
    record["hash"] = record_hash(record)
    _metric_totals([*records, record])
    old = log.read_bytes() if log.exists() else b""
    if old and not old.endswith(b"\n"):
        raise ValueError("refusing to append to an incomplete log line")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=log.parent, prefix=".evidence-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(old)
            handle.write((json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, log)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return record


def verify(records: list[dict], check_artifacts: bool = False, base: Path = Path(".")) -> list[str]:
    problems: list[str] = []
    if not records:
        return ["no evidence records: not verified"]
    prev = GENESIS
    for index, record in enumerate(records, 1):
        if not isinstance(record.get("command"), str) or not isinstance(record.get("exit_code"), int) or isinstance(record.get("exit_code"), bool):
            problems.append(f"record {index}: invalid command or exit code")
        for key in ("seconds", "cost"):
            if key in record and not _valid_metric(record[key]):
                problems.append(f"record {index}: {key} must be finite and non-negative")
        artifacts = record.get("artifacts")
        if not isinstance(artifacts, list):
            problems.append(f"record {index}: artifacts must be an array")
            artifacts = []
        if record.get("seq") != index:
            problems.append(f"record {index}: sequence number is {record.get('seq')}")
        if record.get("prev") != prev:
            problems.append(f"record {index}: previous-hash link is broken (a record was removed or reordered)")
        if record.get("hash") != record_hash(record):
            problems.append(f"record {index}: content does not match its hash (edited)")
        prev = record.get("hash", "")
        for item in artifacts:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not isinstance(item.get("sha256"), str):
                problems.append(f"record {index}: invalid artifact descriptor")
                continue
            if check_artifacts:
                target = base / item["path"]
                if not target.is_file():
                    problems.append(f"record {index}: artifact {item['path']} is missing")
                elif digest(target) != item["sha256"]:
                    problems.append(f"record {index}: artifact {item['path']} changed after it was checked")
    if not problems:
        try:
            _metric_totals(records)
        except ValueError as exc:
            problems.append(str(exc))
    return problems


def anchor_problems(records: list[dict], expect_head: str | None, expect_count: int | None) -> list[str]:
    """Compare the log with a head hash / record count that was written down outside the log."""
    problems = []
    head = records[-1].get("hash", "") if records else GENESIS
    if expect_count is not None and len(records) != expect_count:
        problems.append(f"log has {len(records)} record(s) but {expect_count} were recorded (truncated or extended)")
    if expect_head is not None and head != expect_head.strip().lower():
        problems.append("head hash differs from the recorded one (log truncated, extended or rebuilt)")
    return problems


def stale_commands(records: list[dict], base: Path = Path(".")) -> list[str]:
    """Commands (latest record each) that ran on an artifact that is now missing or different."""
    latest = {r["command"]: r for r in records}
    stale = []
    for command, record in latest.items():
        if record.get("exit_code") != 0 or not record.get("artifacts"):
            stale.append(command)
            continue
        for item in record.get("artifacts", []):
            target = base / item["path"]
            if not target.is_file() or digest(target) != item["sha256"]:
                stale.append(command)
                break
    return stale


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="action", required=True)
    add = sub.add_parser("append")
    add.add_argument("log", type=Path)
    add.add_argument("--command", required=True)
    add.add_argument("--exit-code", type=int, required=True)
    add.add_argument("--artifact", type=Path, action="append", default=[])
    add.add_argument("--note", default="")
    add.add_argument("--seconds", type=float)
    add.add_argument("--cost", type=float)
    again = sub.add_parser("rerun")
    again.add_argument("log", type=Path)
    check = sub.add_parser("verify")
    check.add_argument("log", type=Path)
    check.add_argument("--check-artifacts", action="store_true")
    check.add_argument("--expect-head", help="head hash recorded earlier (hand-off note); detects truncation or a rebuilt log")
    check.add_argument("--expect-count", type=int, help="record count recorded earlier")
    args = parser.parse_args(argv)
    try:
        if args.action == "append":
            record = append(args.log, args.command, args.exit_code, args.artifact, args.note,
                            seconds=args.seconds, cost=args.cost)
            print(f"EVIDENCE-CHAIN: appended #{record['seq']} head={record['hash']}")
            return 0
        records = read_log(args.log)
        if args.action == "rerun":
            broken = verify(records)
            if broken:
                print(f"[BROKEN] {broken[0]}")
                return 1
            stale = stale_commands(records)
            for command in stale:
                print(f"RERUN: {command}")
            print(f"EVIDENCE-CHAIN: {len(stale)} check(s) to rerun")
            return 1 if stale else 0
        problems = verify(records, args.check_artifacts)
        problems += anchor_problems(records, args.expect_head, args.expect_count)
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    for problem in problems:
        print(f"[BROKEN] {problem}")
    head = records[-1].get("hash", "") if records else GENESIS
    totals = "".join(f", total {k}={value:g}" for k, value in (_metric_totals(records) if not problems else {}).items())
    print(f"EVIDENCE-CHAIN: {'BROKEN' if problems else 'OK'} ({len(records)} record(s), head={head}{totals})")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
