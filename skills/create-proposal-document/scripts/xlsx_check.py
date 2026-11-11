#!/usr/bin/env python3
"""Spreadsheet integrity check for a delivered XLSX: error cells, broken references, never-calculated formulas.

Reads the file as a ZIP of XML (standard library only) and reports, per sheet:
  BLOCKED  an error value in a cell (#REF!, #DIV/0!, #NAME?, #VALUE!, #N/A, #NUM!, #NULL!), or a formula or defined name
           that contains #REF!
  WARN     formulas whose cached value is missing (the file was never calculated: open it in Excel or LibreOffice,
           save, and check again; until then the result is NOT VERIFIED), hidden sheets, external links (the file reads
           another workbook that the evaluator may not have)
With --recalc, a copy is converted through LibreOffice using a throwaway profile that forces recalculation of every
formula on load (by default LibreOffice keeps the stored values of Excel files). The check is then repeated and any
stored value that differs from the recalculated one is BLOCKED. LibreOffice and Excel can disagree on rare functions,
so a difference is a lead to review, and a match is not proof that the formula is the right one.

Exit codes: 0 pass (warnings possible), 1 blocked, 2 usage error or unreadable file. It does not judge whether a formula
is the right formula.

Usage: python xlsx_check.py FILE.xlsx [--recalc]
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree

# OOXMLRecalcMode 0 = always recalculate on load (1 = never, 2 = ask), set in a throwaway LibreOffice profile.
RECALC_PROFILE = (
    '<?xml version="1.0" encoding="UTF-8"?><oor:items xmlns:oor="http://openoffice.org/2001/registry" '
    'xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
    '<item oor:path="/org.openoffice.Office.Calc/Formula/Load"><prop oor:name="OOXMLRecalcMode" oor:op="fuse">'
    '<value>0</value></prop></item></oor:items>')
ERRORS = ("#REF!", "#DIV/0!", "#NAME?", "#VALUE!", "#N/A", "#NUM!", "#NULL!")


def local(element: ElementTree.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def parse(data: bytes) -> ElementTree.Element:
    if b"\0" in data or b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ValueError("XML with DTD/entity declarations or UTF-16/32 is not read")
    return ElementTree.fromstring(data)


def inspect(path: Path) -> dict:
    """Return {"sheets": [{name, hidden, formulas, missing_cache, errors, ref_formulas, values}], "external": n, "ref_names": [..]}."""
    report: dict = {"sheets": [], "external": 0, "ref_names": []}
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        if "xl/workbook.xml" not in names:
            raise ValueError("not an XLSX package (xl/workbook.xml missing)")
        report["external"] = sum(1 for n in names if re.match(r"xl/externalLinks/externalLink\d+\.xml$", n))
        workbook = parse(z.read("xl/workbook.xml"))
        for element in workbook.iter():
            if local(element) == "definedName" and element.text and "#REF!" in element.text:
                report["ref_names"].append(element.get("name", "?"))
        rel_targets: dict[str, str] = {}
        if "xl/_rels/workbook.xml.rels" in names:
            for rel in parse(z.read("xl/_rels/workbook.xml.rels")):
                rel_targets[rel.get("Id", "")] = "xl/" + rel.get("Target", "").lstrip("/").removeprefix("xl/")
        listed = []
        for sheet in workbook.iter():
            if local(sheet) == "sheet":
                rid = next((v for k, v in sheet.attrib.items() if k.endswith("}id")), "")
                listed.append((sheet.get("name", "?"), sheet.get("state") in {"hidden", "veryHidden"}, rel_targets.get(rid)))
        if not any(target in names for _, _, target in listed):  # minimal packages without relationships
            listed = [(Path(n).stem, False, n) for n in sorted(names) if re.match(r"xl/worksheets/sheet\d+\.xml$", n)]
        for name, hidden, target in listed:
            if target not in names:
                continue
            sheet = {"name": name, "hidden": hidden, "formulas": 0, "missing_cache": 0, "errors": [], "ref_formulas": [], "values": {}}
            for cell in parse(z.read(target)).iter():
                if local(cell) != "c":
                    continue
                ref = cell.get("r", "?")
                formula = next((c for c in cell if local(c) == "f"), None)
                value = next((c for c in cell if local(c) == "v"), None)
                text = value.text if value is not None and value.text is not None else None
                if cell.get("t") == "e" or (text or "") in ERRORS:
                    sheet["errors"].append(f"{ref}={text}")
                if formula is not None:
                    sheet["formulas"] += 1
                    if "#REF!" in (formula.text or ""):
                        sheet["ref_formulas"].append(ref)
                    if text is None:
                        sheet["missing_cache"] += 1
                if text is not None:
                    sheet["values"][ref] = text
            report["sheets"].append(sheet)
    return report


def verdict(report: dict) -> tuple[list[str], list[str]]:
    blocked, warnings = [], []
    for sheet in report["sheets"]:
        where = f"sheet '{sheet['name']}'"
        if sheet["errors"]:
            blocked.append(f"{where}: error values {', '.join(sheet['errors'][:5])}")
        if sheet["ref_formulas"]:
            blocked.append(f"{where}: formula with #REF! at {', '.join(sheet['ref_formulas'][:5])}")
        if sheet["missing_cache"]:
            warnings.append(f"{where}: {sheet['missing_cache']} formula(s) have no cached value (never calculated; NOT VERIFIED until saved from Excel or LibreOffice)")
        if sheet["hidden"]:
            warnings.append(f"{where}: hidden sheet")
    if report["ref_names"]:
        blocked.append("defined names with #REF!: " + ", ".join(report["ref_names"]))
    if report["external"]:
        warnings.append(f"{report['external']} external workbook link(s): values may depend on a file the reader lacks")
    return blocked, warnings


def same(a: str, b: str) -> bool:
    try:
        x, y = float(a), float(b)
    except ValueError:
        return a == b
    return abs(x - y) <= 1e-9 * max(1.0, abs(x), abs(y))


def recalc(path: Path) -> dict | None:
    """Inspect a LibreOffice-converted copy; None when LibreOffice is not on PATH."""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return None
    with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
        copy = Path(src) / "in.xlsx"
        shutil.copy2(path, copy)
        profile = Path(src) / "profile" / "user"
        profile.mkdir(parents=True)
        (profile / "registrymodifications.xcu").write_text(RECALC_PROFILE, encoding="utf-8")
        subprocess.run([soffice, f"-env:UserInstallation={(Path(src) / 'profile').as_uri()}", "--headless",
                        "--convert-to", "xlsx", "--outdir", out, str(copy)], capture_output=True, timeout=180)
        converted = Path(out) / "in.xlsx"
        return inspect(converted) if converted.is_file() else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("file", type=Path)
    parser.add_argument("--recalc", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = inspect(args.file)
    except (OSError, ValueError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        print(f"Cannot read the workbook: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    blocked, warnings = verdict(report)
    if args.recalc:
        fresh = recalc(args.file)
        if fresh is None:
            warnings.append("--recalc: LibreOffice unavailable or conversion failed; NOT INSPECTED")
        else:
            blocked_fresh, _ = verdict(fresh)
            blocked += [f"after recalculation: {line}" for line in blocked_fresh]
            old = {s["name"]: s["values"] for s in report["sheets"]}
            for sheet in fresh["sheets"]:
                for ref, value in sheet["values"].items():
                    before = old.get(sheet["name"], {}).get(ref)
                    if before is not None and not same(before, value):
                        blocked.append(f"sheet '{sheet['name']}' {ref}: stored value {before} differs from recalculated {value}")
    for line in blocked:
        print(f"[BLOCKED] {line}")
    for line in warnings:
        print(f"[WARN] {line}")
    formulas = sum(s["formulas"] for s in report["sheets"])
    print(f"XLSX-CHECK: {'BLOCKED' if blocked else 'PASS'} ({len(report['sheets'])} sheet(s), {formulas} formula(s))")
    return 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
