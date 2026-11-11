#!/usr/bin/env python3
"""Append-only, hash-chained log of the checks that were actually run, bound to the files they ran on.

Each record stores the command, its exit code, the SHA-256 of every artifact, and the hash of the previous record.
Editing or removing a record from the middle breaks the chain; changing an artifact afterwards is reported by
`verify --check-artifacts`. Cutting records off the END of the log is not detectable from the file alone: keep the
`head` hash from `verify` in the hand-off note and compare it later.

This is tamper-evidence for honest mistakes and casual edits, not authentication: anyone who can rewrite the whole
file can rebuild the chain.

  python evidence_chain.py append LOG --command "..." --exit-code N [--artifact FILE ...] [--note TEXT]
                                       [--seconds S] [--cost AMOUNT]
  python evidence_chain.py verify LOG [--check-artifacts]
  python evidence_chain.py rerun LOG        list the commands whose artifacts changed or vanished (nothing else to redo)

`--seconds` and `--cost` are optional; `verify` totals them so cost per verified check can be read off. `rerun` reads the
latest record per command, so only the checks that ran on a file that has since changed need to be run again. Exit codes:
0 ok / nothing stale, 1 chain broken, artifact changed, or something stale, 2 usage error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
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
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]


def append(log: Path, command: str, exit_code: int, artifacts: list[Path], note: str = "", now: datetime | None = None,
           seconds: float | None = None, cost: float | None = None) -> dict:
    records = read_log(log)
    problems = verify(records)
    if problems:
        raise ValueError("refusing to append to a broken chain: " + problems[0])
    record = {"seq": len(records) + 1, "time": (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "command": command, "exit_code": exit_code, "note": note,
              "artifacts": [{"path": p.as_posix(), "sha256": digest(p)} for p in artifacts],
              "prev": records[-1]["hash"] if records else GENESIS}
    for key, value in (("seconds", seconds), ("cost", cost)):
        if value is not None:
            if value < 0:
                raise ValueError(f"{key} must not be negative")
            record[key] = value
    record["hash"] = record_hash(record)
    with log.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
    return record


def verify(records: list[dict], check_artifacts: bool = False, base: Path = Path(".")) -> list[str]:
    problems: list[str] = []
    prev = GENESIS
    for index, record in enumerate(records, 1):
        if record.get("seq") != index:
            problems.append(f"record {index}: sequence number is {record.get('seq')}")
        if record.get("prev") != prev:
            problems.append(f"record {index}: previous-hash link is broken (a record was removed or reordered)")
        if record.get("hash") != record_hash(record):
            problems.append(f"record {index}: content does not match its hash (edited)")
        prev = record.get("hash", "")
        if check_artifacts:
            for item in record.get("artifacts", []):
                target = base / item["path"]
                if not target.is_file():
                    problems.append(f"record {index}: artifact {item['path']} is missing")
                elif digest(target) != item["sha256"]:
                    problems.append(f"record {index}: artifact {item['path']} changed after it was checked")
    return problems


def stale_commands(records: list[dict], base: Path = Path(".")) -> list[str]:
    """Commands (latest record each) that ran on an artifact that is now missing or different."""
    latest = {r["command"]: r for r in records}
    stale = []
    for command, record in latest.items():
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
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    for problem in problems:
        print(f"[BROKEN] {problem}")
    head = records[-1]["hash"] if records else GENESIS
    totals = "".join(f", total {k}={sum(r.get(k, 0) for r in records):g}" for k in ("seconds", "cost")
                     if any(k in r for r in records))
    print(f"EVIDENCE-CHAIN: {'BROKEN' if problems else 'OK'} ({len(records)} record(s), head={head}{totals})")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
