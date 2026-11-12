#!/usr/bin/env python3
"""Render a deck and report which slides changed since the last render, so only those need to be looked at again.

Looking at rendered pages is the expensive part of reviewing a deck (every image viewed costs the reviewer's time or tokens).
Rebuilding and rendering is cheap. This script renders every page every time (so the images are always current and the review
ledger's "image not older than the deck" rule holds), but it compares each slide's content hash with the previous run and builds
a contact sheet of only the slides that changed. Look at that sheet, open single pages only for the slides you doubt, and skip
the rest.

Usage:
    python render_delta.py deck.pptx -o out/render [--dpi 80] [--full-sheet] [--force]

Writes under -o:
    pages/page-NN.png        every page, current
    changed_sheet.png        contact sheet of the changed slides only, tiles numbered with the real slide number
    sheet.png                contact sheet of all pages (first run, --full-sheet, or --force)
    delta.json               {"changed": [...], "unchanged": [...], "removed": n, "engine": "...", "dpi": 80}
    render_state.json        hashes of the last run

The first run, a different --dpi, or --force treats every slide as changed. A changed layout or master changes every slide hash.
This never judges the pages: viewing the changed pages (and recording that in `review_ledger.py`) is still required.

Exit codes: 0 = rendered, 2 = no LibreOffice (soffice), no PDF-to-PNG converter (PyMuPDF or Poppler pdftoppm), or conversion failed:
NOT INSPECTED, nothing is reported as unchanged.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

WINDOWS_SOFFICE = r"C:\Program Files\LibreOffice\program\soffice.exe"


def find_soffice() -> str | None:
    return shutil.which("soffice") or shutil.which("libreoffice") or (WINDOWS_SOFFICE if os.path.isfile(WINDOWS_SOFFICE) else None)


def delta(old: list[str], new: list[str]) -> tuple[list[int], list[int], int]:
    """Greedy match of identical hashes. Returns (changed slide numbers, unchanged slide numbers, net removed count), 1-based."""
    pool: dict[str, int] = {}
    for digest in old:
        pool[digest] = pool.get(digest, 0) + 1
    changed, unchanged = [], []
    for number, digest in enumerate(new, 1):
        if pool.get(digest, 0) > 0:
            pool[digest] -= 1
            unchanged.append(number)
        else:
            changed.append(number)
    return changed, unchanged, max(0, sum(pool.values()) - len(changed))   # old slides with no match, net of the ones replaced


def to_pdf(deck: Path, pdf_dir: Path, soffice: str) -> Path:
    pdf_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as profile:     # a throwaway profile: no lock file, no first-run dialog
        cmd = [soffice, f"-env:UserInstallation={Path(profile).as_uri()}", "--headless", "--convert-to", "pdf",
               "--outdir", str(pdf_dir), str(deck)]
        run = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    pdf = pdf_dir / (deck.stem + ".pdf")
    if run.returncode != 0 or not pdf.is_file():
        raise RuntimeError((run.stderr or run.stdout or "soffice produced no PDF").strip()[:200])
    return pdf


def to_pngs(pdf: Path, pages_dir: Path, dpi: int) -> list[Path]:
    """PyMuPDF when installed, else Poppler's pdftoppm."""
    shutil.rmtree(pages_dir, ignore_errors=True)
    pages_dir.mkdir(parents=True)
    try:
        import pymupdf
        with pymupdf.open(str(pdf)) as doc:
            for number, page in enumerate(doc, 1):
                page.get_pixmap(dpi=dpi).save(str(pages_dir / f"page-{number:02d}.png"))
    except ImportError:
        tool = shutil.which("pdftoppm")
        if not tool:
            raise RuntimeError("no PDF-to-PNG converter: install PyMuPDF (pip install pymupdf) or Poppler (pdftoppm)")
        run = subprocess.run([tool, "-r", str(dpi), "-png", str(pdf), str(pages_dir / "p")], capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=300)
        if run.returncode != 0:
            raise RuntimeError(run.stderr.strip()[:200])
        for number, produced in enumerate(sorted(pages_dir.glob("p-*.png"), key=lambda p: int(p.stem.split("-")[-1])), 1):
            produced.rename(pages_dir / f"page-{number:02d}.png")
    return sorted(pages_dir.glob("page-*.png"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deck", type=Path)
    ap.add_argument("-o", "--output", type=Path, required=True)
    ap.add_argument("--dpi", type=int, default=80)
    ap.add_argument("--full-sheet", action="store_true", help="also write the contact sheet of all pages")
    ap.add_argument("--force", action="store_true", help="treat every slide as changed")
    a = ap.parse_args(argv)
    if not a.deck.is_file():
        print(f"deck not found: {a.deck}", file=sys.stderr)
        return 2
    soffice = find_soffice()
    if not soffice:
        print("NOT INSPECTED: LibreOffice (soffice) not found; nothing was rendered", file=sys.stderr)
        return 2
    import contact_sheet
    import review_ledger
    out = a.output
    out.mkdir(parents=True, exist_ok=True)
    try:
        hashes = review_ledger.slide_hashes(a.deck)
        pdf = to_pdf(a.deck.resolve(), out / "_pdf", soffice)
        pages = to_pngs(pdf, out / "pages", max(40, a.dpi))
    except Exception as exc:  # noqa: BLE001 - any engine failure means NOT INSPECTED
        print(f"NOT INSPECTED: rendering failed ({type(exc).__name__}: {str(exc)[:160]})", file=sys.stderr)
        return 2
    if len(pages) != len(hashes):
        print(f"NOT INSPECTED: {len(hashes)} slides but {len(pages)} rendered pages", file=sys.stderr)
        return 2
    state_file = out / "render_state.json"
    try:
        state = json.loads(state_file.read_text(encoding="utf-8")) if state_file.is_file() else {}
    except ValueError:
        state = {}
    previous = state.get("hashes", []) if (state.get("dpi") == a.dpi and not a.force) else []
    changed, unchanged, removed = delta(previous, hashes)
    first = not previous
    sheet_changed = sheet_all = None
    if changed:
        sheet_changed = out / "changed_sheet.png"
        contact_sheet.build_sheets([pages[n - 1] for n in changed], sheet_changed, cols=4, thumb=480, per_sheet=12,
                                   labels=[str(n) for n in changed])
    if first or a.full_sheet:
        sheet_all = out / "sheet.png"
        contact_sheet.build_sheets(pages, sheet_all, cols=4, thumb=480, per_sheet=12)
    elif (out / "changed_sheet.png").exists() and not changed:
        (out / "changed_sheet.png").unlink()
    state_file.write_text(json.dumps({"hashes": hashes, "dpi": a.dpi}), encoding="utf-8")
    result = {"changed": changed, "unchanged": unchanged, "removed": removed, "engine": "LibreOffice", "dpi": a.dpi,
              "pages": str(out / "pages"), "changed_sheet": str(sheet_changed) if sheet_changed else None,
              "sheet": str(sheet_all) if sheet_all else None}
    (out / "delta.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(pages)} page(s) rendered; changed: {changed or 'none'}; unchanged: {len(unchanged)}; removed: {removed}")
    if sheet_changed:
        print(f"look at {sheet_changed} (changed slides only, numbered); open single pages in {out / 'pages'} for detail")
    else:
        print("no slide changed since the last render: nothing to look at again")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
