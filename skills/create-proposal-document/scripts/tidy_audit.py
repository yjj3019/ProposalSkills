#!/usr/bin/env python3
"""Measure how orderly a PPTX deck is: type scale, near-miss alignment, thin-rule clutter and text density.

`deck_check.py` lints readability (minimum font, density, page count). This script measures what makes a deck look
untidy even when every slide passes that lint: too many font sizes, boxes that almost line up, a thicket of
hairlines and a few slides that carry far more text than the rest. It prints numbers and advisory warnings; it never
judges whether a slide makes its point, so a person still looks at the rendered pages
(see `references/editorial-deck-design.md`).

Measured per deck
  - distinct font sizes used by text runs (body text, table cells), and how many runs have no explicit size
  - font families
  - near-miss alignments: text boxes whose left edges (or top edges) differ by 0.012-0.12 in, i.e. almost but not
    exactly aligned (identical edges and clearly different edges are fine)
  - thin rules per slide (shapes under 0.05 in thick) and non-text shapes per slide
  - characters per slide

Usage:
    python tidy_audit.py deck.pptx
    python tidy_audit.py deck.pptx --json --strict --max-sizes 9 --max-near-miss 10

Exit codes: 0 = measured (warnings may exist), 1 = --strict and a threshold was exceeded,
2 = file missing, not a PPTX package (for example wrapped by an enterprise DRM agent) or unreadable: NOT INSPECTED.
Chart text and text that inherits its size from the master are not measured; the output says so.
"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path

EMU = 914400.0
NEAR_LO, NEAR_HI = 0.012, 0.12          # inches: a gap in this band reads as a mistake, not a choice
THIN = 0.05                              # inches: thinner than this counts as a rule
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def _near(values: list[float]) -> int:
    unique = sorted(set(values))
    return sum(1 for a, b in zip(unique, unique[1:]) if NEAR_LO < b - a < NEAR_HI)


def _runs(text_frame):
    for paragraph in text_frame.paragraphs:
        yield from paragraph.runs


def measure(path: Path) -> dict:
    from pptx import Presentation
    prs = Presentation(str(path))
    sizes: Counter = Counter()
    families: Counter = Counter()
    unresolved = 0
    slides = []
    for number, slide in enumerate(prs.slides, 1):
        xs, ys, chars, rules, shapes = [], [], 0, 0, 0
        frames = []
        for shape in slide.shapes:
            has_text = shape.has_text_frame and shape.text_frame.text.strip()
            if has_text:
                frames.append(shape.text_frame)
                if shape.width / EMU > 0.5 and shape.height / EMU > 0.15:
                    xs.append(round(shape.left / EMU, 3))
                    ys.append(round(shape.top / EMU, 3))
            elif getattr(shape, "has_table", False) and shape.has_table:
                frames.extend(cell.text_frame for row in shape.table.rows for cell in row.cells)
            else:
                shapes += 1
                thin, long_ = min(shape.width, shape.height) / EMU, max(shape.width, shape.height) / EMU
                if thin < THIN and long_ > 0.1:
                    rules += 1
        for frame in frames:
            chars += len(frame.text.strip())
            for run in _runs(frame):
                if not run.text.strip():
                    continue
                if run.font.size is None:
                    unresolved += 1
                else:
                    sizes[round(run.font.size.pt, 1)] += len(run.text)
                r_pr = run._r.find(f"{A}rPr")
                latin = r_pr.find(f"{A}latin") if r_pr is not None else None
                if latin is not None and latin.get("typeface"):
                    families[latin.get("typeface")] += 1
        slides.append({"slide": number, "chars": chars, "near_x": _near(xs), "near_y": _near(ys),
                       "rules": rules, "shapes": shapes})
    return {"file": str(path), "slides": slides, "font_sizes": sorted(sizes), "font_families": dict(families),
            "runs_without_size": unresolved,
            "near_miss": sum(s["near_x"] + s["near_y"] for s in slides),
            "rules_total": sum(s["rules"] for s in slides), "shapes_total": sum(s["shapes"] for s in slides),
            "chars_max": max((s["chars"] for s in slides), default=0),
            "chars_avg": round(sum(s["chars"] for s in slides) / max(len(slides), 1))}


def warnings(report: dict, max_sizes: int, max_near: int, max_rules: int, max_chars: int) -> list[str]:
    out = []
    if len(report["font_sizes"]) > max_sizes:
        out.append(f"{len(report['font_sizes'])} font sizes in use (limit {max_sizes}): {report['font_sizes']}")
    if report["near_miss"] > max_near:
        out.append(f"{report['near_miss']} near-miss alignments (limit {max_near}): snap boxes to one grid line")
    for s in report["slides"]:
        if s["rules"] > max_rules:
            out.append(f"slide {s['slide']}: {s['rules']} thin rules (limit {max_rules}); separate with space instead")
        if s["chars"] > max_chars:
            out.append(f"slide {s['slide']}: {s['chars']} characters (limit {max_chars}); split or cut")
    if report["runs_without_size"]:
        out.append(f"NOT INSPECTED: {report['runs_without_size']} text runs inherit their size, so the scale is incomplete")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deck", type=Path)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="exit 1 when a threshold is exceeded")
    ap.add_argument("--max-sizes", type=int, default=9)
    ap.add_argument("--max-near-miss", type=int, default=10)
    ap.add_argument("--max-rules", type=int, default=24, help="thin rules allowed on one slide")
    ap.add_argument("--max-chars", type=int, default=700, help="characters allowed on one slide")
    a = ap.parse_args(argv)
    if not a.deck.is_file():
        print(f"file not found: {a.deck}", file=sys.stderr)
        return 2
    try:
        from pptx.exc import PackageNotFoundError   # python-pptx raises this for a file that is not a ZIP package
        unreadable = (zipfile.BadZipFile, PackageNotFoundError, KeyError, ValueError, OSError)
    except ImportError:
        print("python-pptx is required (pip install -r requirements.txt)", file=sys.stderr)
        return 2
    try:
        report = measure(a.deck)
    except unreadable as exc:
        print(f"NOT INSPECTED: cannot read the PPTX package ({type(exc).__name__}); it may be damaged or "
              "wrapped by an enterprise DRM agent", file=sys.stderr)
        return 2
    warn = warnings(report, a.max_sizes, a.max_near_miss, a.max_rules, a.max_chars)
    report["warnings"] = warn
    if a.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"slides: {len(report['slides'])}")
        print(f"font sizes ({len(report['font_sizes'])}): {report['font_sizes']}")
        print(f"font families ({len(report['font_families'])}): {report['font_families']}")
        print(f"near-miss alignments: {report['near_miss']}")
        print(f"thin rules: {report['rules_total']} total, non-text shapes: {report['shapes_total']}")
        print(f"characters per slide: avg {report['chars_avg']}, max {report['chars_max']}")
        for line in warn:
            print(f"  [WARN] {line}")
        print("TIDY-AUDIT: " + (f"{len(warn)} warning(s)" if warn else "CLEAN") + " (measures order, not whether each slide makes its point)")
    return 1 if (warn and a.strict) else 0


if __name__ == "__main__":
    raise SystemExit(main())
