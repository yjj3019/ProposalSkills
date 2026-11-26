#!/usr/bin/env python3
"""Read the `colors` of a user-supplied DESIGN.md and print `meta.palette` tokens, checked for contrast.

DESIGN.md (the Google Labs `design.md` spec, status alpha) holds optional YAML front matter with token groups such as `colors`,
`typography`, `spacing`. Only `colors` maps onto what the deck generator uses; every other group is reported as ignored, never
silently dropped. Nothing is fetched or bundled: the file is one the user supplies, and a buyer-prescribed template or palette
always wins over it (deck-production.md section 3).

Role names are matched by this tool's own convention, not by the spec: `primary`, `secondary` (becomes `side_b`), `text`, `muted`,
`background` (becomes `bg`), `warn`, `ok`, and the generator's own names (`tint1`..`tint3`, `side_b`, `bg`). Any other color name is
listed as unmapped. A color is used only when it is `#RGB` or `#RRGGBB`, or a `{colors.other}` reference that resolves to one;
`rgb()`, `hsl()`, named colors and 8-digit hex are rejected and listed, not converted. Roles the file does not give keep the
generator's defaults.

Usage: python palette_from_design_md.py DESIGN.md [--out palette.json]
Exit codes: 0 ok, 1 the resulting palette fails the contrast check, 2 usage error or unreadable file.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from palette_from_image import check_palette, default_palette

MAX_BYTES = 1024 * 1024
ROLES = {"primary": "primary", "secondary": "side_b", "side_b": "side_b", "text": "text", "muted": "muted",
         "background": "bg", "bg": "bg", "warn": "warn", "ok": "ok", "tint1": "tint1", "tint2": "tint2", "tint3": "tint3"}
HEX = re.compile(r"^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$")
REF = re.compile(r"^\{colors\.([A-Za-z0-9_-]+)\}$")


def front_matter(text: str) -> str:
    text = text.lstrip("﻿")
    if not text.startswith("---"):
        raise ValueError("no YAML front matter (the file must start with ---)")
    end = re.search(r"^---\s*$", text[3:], re.M)
    if not end:
        raise ValueError("the front matter is not closed with ---")
    return text[3:3 + end.start()]


def groups(block: str) -> dict[str, list[str]]:
    """Top-level keys of the front matter and the indented lines under each (a minimal reader, not a YAML parser)."""
    found: dict[str, list[str]] = {}
    current = None
    for raw in block.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if not raw[0].isspace():
            key = raw.split(":", 1)[0].strip().strip("'\"")
            current = key
            found[current] = []
        elif current is not None:
            found[current].append(raw)
    return found


def color_entries(lines: list[str]) -> tuple[dict[str, str], list[str]]:
    """`name: value` pairs one level deep; anything nested deeper is returned as unsupported."""
    entries, unsupported = {}, []
    indent = None
    for raw in lines:
        width = len(raw) - len(raw.lstrip())
        indent = width if indent is None else indent
        if width > indent:
            unsupported.append(raw.strip())
            continue
        name, _, value = raw.strip().partition(":")
        value = re.sub(r"\s+#.*$", "", value.strip()).strip("'\"")
        if value:
            entries[name.strip().strip("'\"")] = value
        else:
            unsupported.append(name.strip())
    return entries, unsupported


def resolve(name: str, entries: dict[str, str], seen: tuple[str, ...] = ()) -> str | None:
    value = entries.get(name)
    if value is None or name in seen or len(seen) > 5:
        return None
    ref = REF.match(value)
    return resolve(ref.group(1), entries, seen + (name,)) if ref else value


def to_hex6(value: str) -> str | None:
    match = HEX.match(value)
    if not match:
        return None
    digits = match.group(1).upper()
    return "".join(ch * 2 for ch in digits) if len(digits) == 3 else digits


def convert(text: str) -> tuple[dict, list[str]]:
    """(palette tokens read from the file, notes on everything that was not used)."""
    parts = groups(front_matter(text))
    notes = [f"ignored group `{name}` (not used by the deck generator)" for name in parts if name != "colors"]
    entries, unsupported = color_entries(parts.get("colors", []))
    notes += [f"colors.{item}: nested or empty value is not supported, ignored" for item in unsupported]
    if "colors" not in parts:
        notes.append("no `colors` group: nothing to read")
    palette: dict[str, str] = {}
    for name in entries:
        value = resolve(name, entries)
        role = ROLES.get(name.lower().replace("-", "_"))
        if value is None:
            notes.append(f"colors.{name}: reference or value could not be resolved, ignored")
        elif to_hex6(value) is None:
            notes.append(f"colors.{name}: `{value}` is not #RGB or #RRGGBB (rgb(), hsl(), names and alpha are not converted), ignored")
        elif role is None:
            notes.append(f"colors.{name}: no matching deck role, unmapped")
        else:
            palette[role] = to_hex6(value)
    return palette, notes


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("design", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.design.stat().st_size > MAX_BYTES:
            raise ValueError(f"file is larger than {MAX_BYTES} bytes")
        palette, notes = convert(args.design.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        print(f"Cannot read input: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    problems = check_palette({**default_palette(), **palette})
    payload = {"palette": palette, "notes": notes, "problems": problems,
               "use": "Paste `palette` into slides.json meta.palette. Buyer templates and palettes take precedence."}
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
