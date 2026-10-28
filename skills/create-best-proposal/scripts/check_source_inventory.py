#!/usr/bin/env python3
"""Propose open audit inputs for a caller-declared source inventory; never approve sources."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import sys
from pathlib import Path


ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def check_inventory(manifest: dict, base: Path) -> dict:
    sources = manifest.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("sources must be a nonempty array")
    base = base.resolve()
    items, inputs, seen = [], [], set()
    for item in sources:
        if not isinstance(item, dict):
            raise ValueError("each source must be an object")
        ident = item.get("id")
        if "required" not in item:
            raise ValueError("required must be explicitly declared; null means unknown")
        required = item["required"]
        if (not isinstance(ident, str) or not ID.fullmatch(ident) or ident in seen
                or ident == "inventory-completeness"):
            raise ValueError("source IDs must be unique and use letters, digits, dot, dash, or underscore")
        if required is not None and not isinstance(required, bool):
            raise ValueError("required must be true, false, or null")
        seen.add(ident)
        for field in ("source_path", "extraction_path"):
            value = item.get(field)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{field} must be a nonempty path or null")
            if value is not None:
                path = Path(value)
                if path.is_absolute() or not (base / path).resolve().is_relative_to(base):
                    raise ValueError(f"{field} must remain within the manifest directory")
        source = base / item["source_path"] if item.get("source_path") else None
        extraction = base / item["extraction_path"] if item.get("extraction_path") else None
        status = "source_not_supplied"
        before = sidecar_hash = None
        if source is not None:
            try:
                info = source.lstat()
                if not stat.S_ISREG(info.st_mode):
                    status = "source_unavailable"
                else:
                    before = digest(source)
                    status = "extraction_not_supplied"
                    if extraction is not None:
                        try:
                            extraction_info = extraction.lstat()
                        except FileNotFoundError:
                            extraction_info = None
                        if extraction_info is None or not stat.S_ISREG(extraction_info.st_mode):
                            status = "extraction_unavailable"
                        else:
                            sidecar_hash = digest(extraction)
                            sidecar = json.loads(extraction.read_text(encoding="utf-8-sig"))
                            source_info = sidecar.get("source") if isinstance(sidecar, dict) else None
                            if (not isinstance(source_info, dict)
                                    or type(sidecar.get("schema_version")) is not int
                                    or sidecar.get("schema_version") != 1
                                    or sidecar.get("kind") != "proposal-rfp-extraction"
                                    or sidecar.get("review_status") != "UNREVIEWED"
                                    or sidecar.get("submission_approval") is not False
                                    or not isinstance(sidecar.get("document"), dict)):
                                status = "invalid_extraction"
                            elif (source_info.get("sha256") != before
                                  or source_info.get("format") != source.suffix.lower()):
                                status = "source_mismatch"
                            else:
                                status = "extracted_unreviewed"
                            if digest(extraction) != sidecar_hash:
                                status = "extraction_changed"
                    if digest(source) != before:
                        status = "source_changed"
            except FileNotFoundError:
                status = "source_missing" if before is None else "source_changed"
            except (OSError, ValueError, TypeError, UnicodeError):
                status = "inspection_failed"
        obligation = "unknown" if required is None else ("required" if required else "optional")
        items.append({"id": ident, "required": obligation, "status": status,
                      "source_sha256": before, "extraction_sha256": sidecar_hash})
        if required is not False:
            inputs.append({"id": f"source-{ident}", "class": "blocking", "status": "open"})
        elif status not in {"source_not_supplied", "source_missing"}:
            inputs.append({"id": f"source-{ident}", "class": "non-blocking", "status": "open"})
    inputs.append({"id": "source-inventory-completeness", "class": "blocking", "status": "open"})
    existing = manifest.get("existing_inputs")
    if existing is not None and (not isinstance(existing, list)
                                 or any(not isinstance(i, dict) or not isinstance(i.get("id"), str)
                                        for i in existing)):
        raise ValueError("existing_inputs must be an array of objects with IDs")
    existing_ids = [i["id"] for i in existing or []]
    if len(existing_ids) != len(set(existing_ids)):
        raise ValueError("existing input IDs must be unique")
    conflicts = [i["id"] for i in inputs if i["id"] in existing_ids]
    return {"inventory_completeness": "UNVERIFIED", "sources": items, "inputs": inputs,
            "conflict_check": "CHECKED" if existing is not None else "NOT_CHECKED",
            "conflicting_input_ids": conflicts}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Private JSON source inventory")
    parser.add_argument("--output", type=Path, required=True, help="New private report; never overwritten")
    args = parser.parse_args(argv)
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
        if not isinstance(manifest, dict):
            raise ValueError("manifest must be an object")
        report = check_inventory(manifest, args.manifest.resolve().parent)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        return 0
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        print(f"Source inventory failed ({type(exc).__name__}); no report was approved", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
