#!/usr/bin/env python3
"""Tile rendered slide images into contact sheets so a whole deck can be looked at in one or two views.

Use it right after rendering (`deck_check.py --render --png-dir out/png`, or LibreOffice to PDF to PNG). A person or an
AI that can view images looks at the sheet first for balance across the deck (empty slides, repeated layouts, a slide
that breaks the pattern), then opens single pages for detail. It never judges the slides and never replaces looking at
each page: a contact sheet hides small defects (clipped text, overlaps) that a full-size page shows.

Usage:
    python contact_sheet.py out/png -o out/sheet.png
    python contact_sheet.py out/png -o out/sheet.png --cols 4 --thumb 480 --per-sheet 12

`render_delta.py` calls this with the real slide numbers as labels for the slides that changed. Pages are taken in natural order (page-2 before page-10) from *.png, *.jpg, *.jpeg. With more pages than --per-sheet the
output becomes sheet_1.png, sheet_2.png, and so on. Each tile carries its page number.

Exit codes: 0 = sheets written, 2 = folder missing, no images, or an image cannot be read (damaged, or wrapped by an
enterprise DRM agent): NOT INSPECTED, nothing is written.
Needs Pillow (requirements.txt).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SUFFIXES = {".png", ".jpg", ".jpeg"}


def natural_key(path: Path) -> list:
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", path.name)]


def page_images(folder: Path) -> list[Path]:
    return sorted((p for p in folder.iterdir() if p.suffix.lower() in SUFFIXES), key=natural_key)


def build_sheets(images: list[Path], out: Path, cols: int, thumb: int, per_sheet: int, labels: list[str] | None = None) -> list[Path]:
    from PIL import Image, ImageDraw
    pad, label_h = 12, 20
    written: list[Path] = []
    chunks = [images[i:i + per_sheet] for i in range(0, len(images), per_sheet)]
    for n, chunk in enumerate(chunks, 1):
        tiles = []
        for path in chunk:
            with Image.open(path) as im:
                im = im.convert("RGB")
                height = max(1, round(im.height * thumb / im.width))
                tiles.append(im.resize((thumb, height), Image.LANCZOS))
        cols_used = min(cols, len(tiles))
        rows = (len(tiles) + cols - 1) // cols
        row_h = max(t.height for t in tiles) + label_h
        sheet = Image.new("RGB", (cols_used * (thumb + pad) + pad, rows * (row_h + pad) + pad), (236, 233, 226))
        draw = ImageDraw.Draw(sheet)
        for i, tile in enumerate(tiles):
            r, c = divmod(i, cols)
            x, y = pad + c * (thumb + pad), pad + r * (row_h + pad)
            index = (n - 1) * per_sheet + i
            draw.text((x, y + 3), labels[index] if labels else str(index + 1), fill=(60, 60, 60))
            sheet.paste(tile, (x, y + label_h))
            draw.rectangle((x - 1, y + label_h - 1, x + tile.width, y + label_h + tile.height), outline=(190, 186, 176))
        target = out if len(chunks) == 1 else out.with_name(f"{out.stem}_{n}{out.suffix}")
        target.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(target)
        written.append(target)
    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", type=Path, help="folder of rendered page images")
    ap.add_argument("-o", "--output", type=Path, default=Path("sheet.png"))
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--thumb", type=int, default=480, help="tile width in pixels")
    ap.add_argument("--per-sheet", type=int, default=12)
    a = ap.parse_args(argv)
    if not a.folder.is_dir():
        print(f"folder not found: {a.folder}", file=sys.stderr)
        return 2
    images = page_images(a.folder)
    if not images:
        print(f"no .png/.jpg pages in {a.folder}", file=sys.stderr)
        return 2
    try:
        written = build_sheets(images, a.output, max(1, a.cols), max(120, a.thumb), max(1, a.per_sheet))
    except ImportError:
        print("Pillow is required (pip install -r requirements.txt)", file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(f"NOT INSPECTED: cannot read a page image ({type(exc).__name__}); it may be damaged or wrapped by an "
              "enterprise DRM agent, nothing was written", file=sys.stderr)
        return 2
    for path in written:
        print(f"wrote {path}")
    print(f"CONTACT-SHEET: {len(images)} page(s) in {len(written)} sheet(s); look at single pages for detail")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
