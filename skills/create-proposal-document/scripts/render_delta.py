#!/usr/bin/env python3
"""Render a deck and report which slides changed since the last render, so only those need to be looked at again.

Looking at rendered pages is the expensive part of reviewing a deck (every image viewed costs the reviewer's time or tokens).
Rebuilding and rendering is cheap. This script renders every page every time (so the images are always current and the review
ledger's "image not older than the deck" rule holds), compares each slide's content hash AND the rendered image's own hash with the
previous run, and builds a contact sheet of only the slides that changed. Look at that sheet, open single pages only for the slides
you doubt, and skip the rest.

Usage:
    python render_delta.py deck.pptx -o out/render [--dpi 80] [--full-sheet] [--force]

Writes under -o:
    pages/page-NN.png        every page, current (recorded in render_state.json)
    changed_sheet.png        contact sheet of the changed slides only, tiles numbered with the real slide number; more than
                             12 changed slides split into changed_sheet_1.png, changed_sheet_2.png, ...
    sheet.png                contact sheet of all pages (first run, --full-sheet, or --force); sheet_1.png, ... when split
    delta.json               {"changed": [...], "unchanged": [...], "render_changed": [...], "removed": n,
                              "environment_changed": bool, "engine": "...", "dpi": 80, "changed_sheets": [...], "sheets": [...]}
    render_state.json        hashes, image hashes, the render environment and the files this tool created (sheets and pages)

A slide counts as changed when its content hash differs, or when its content is the same but the page now renders differently
(a changed font, a different LibreOffice or converter version): those are listed in `render_changed`. A different render
environment, a different --dpi or --force treats every slide as changed. A changed layout, master or theme changes every slide hash.

Safety: -o must be a new or empty folder, or one this tool created before (it holds render_state.json); any other folder is refused
before anything is written. The tool renders in a temporary folder, then installs its files. It deletes only files it recorded as its
own (the sheets and the page images it wrote), never a folder, never another file that happens to match a name, and it refuses
(exit 2, nothing changed) when a file it is about to write already exists and is not recorded as its own.

This never judges the pages: viewing the changed pages (and recording that in `review_ledger.py`) is still required.

Exit codes: 0 = rendered, 2 = no LibreOffice (soffice), no PDF-to-PNG converter (PyMuPDF or Poppler pdftoppm), conversion failed, or
an output folder that is not this tool's: NOT INSPECTED, nothing is reported as unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

WINDOWS_SOFFICE = r"C:\Program Files\LibreOffice\program\soffice.exe"
OWN_SHEET = re.compile(r"^(changed_sheet|sheet)(_\d+)?\.png$")
OWN_PAGE = re.compile(r"^(page-\d+|p-\d+)\.png$")
TOOL = "render_delta"


def find_soffice() -> str | None:
    return shutil.which("soffice") or shutil.which("libreoffice") or (WINDOWS_SOFFICE if os.path.isfile(WINDOWS_SOFFICE) else None)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def libreoffice_version(soffice: str) -> str:
    """The LibreOffice build, read from the install folder first (fast and deterministic; on Windows `soffice --version` prints
    nothing), then from `--version`. "unknown" when neither works."""
    try:
        program = Path(soffice).resolve().parent
        for name in ("version.ini", "versionrc"):
            ini = program / name
            if ini.is_file():
                for line in ini.read_text(encoding="utf-8", errors="replace").splitlines():
                    if line.lower().startswith("buildid="):
                        return "LibreOffice buildid " + line.split("=", 1)[1].strip()[:40]
    except OSError:
        pass
    try:
        run = subprocess.run([soffice, "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
        return (run.stdout or run.stderr).strip()[:120] or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def environment_differs(old: dict, new: dict) -> bool:
    """True when a recorded part of the environment differs. A part that is unknown on either side is not evidence of a change."""
    for key in set(old) | set(new):
        a, b = str(old.get(key, "unknown")), str(new.get(key, "unknown"))
        if a != b and "unknown" not in (a, b):
            return True
    return False


def environment(soffice: str) -> dict:
    """What produced the pictures: the LibreOffice build and the PDF-to-PNG converter. A change here can change every page."""
    version = libreoffice_version(soffice)
    try:
        import pymupdf
        converter = "pymupdf " + str(getattr(pymupdf, "__version__", "?"))
    except ImportError:
        converter = "pdftoppm " + str(shutil.which("pdftoppm") or "missing")
    return {"soffice": version, "converter": converter}


def delta_with_images(old: list[dict], new: list[dict]) -> tuple[list[int], list[int], int, list[int]]:
    """Match slides by content hash. A slide with the same hash whose rendered image hash differs counts as changed and is also
    listed in `render_changed`. Returns (changed, unchanged, net removed, render_changed), slide numbers 1-based."""
    pool: dict[str, list[str]] = {}
    for entry in old:
        pool.setdefault(entry["hash"], []).append(entry.get("image", ""))
    changed, unchanged, render_changed = [], [], []
    for number, entry in enumerate(new, 1):
        candidates = pool.get(entry["hash"]) or []
        if candidates:
            previous_image = candidates.pop(0)
            if previous_image and entry.get("image") and previous_image != entry["image"]:
                changed.append(number)
                render_changed.append(number)
            else:
                unchanged.append(number)
        else:
            changed.append(number)
    unmatched_old = sum(len(v) for v in pool.values())
    return changed, unchanged, max(0, unmatched_old - len(changed)), render_changed


def delta(old: list[str], new: list[str]) -> tuple[list[int], list[int], int]:
    """Hash-only form of `delta_with_images`: (changed, unchanged, net removed), 1-based."""
    changed, unchanged, removed, _ = delta_with_images([{"hash": h} for h in old], [{"hash": h} for h in new])
    return changed, unchanged, removed


def claim_output(out: Path) -> str | None:
    """None when `out` may be used (absent, empty, or created by this tool), else the reason it was refused."""
    if out.is_file():
        return f"{out} is a file"
    if not out.exists() or not any(out.iterdir()):
        return None
    try:
        state = json.loads((out / "render_state.json").read_text(encoding="utf-8"))
        if state.get("tool") == TOOL:
            return None
    except (OSError, ValueError):
        pass
    return f"{out} is not empty and was not created by render_delta: use a new or empty folder (nothing was deleted)"


def to_pdf(deck: Path, pdf_dir: Path, soffice: str) -> Path:
    """Convert into `pdf_dir`, a fresh temporary folder (never the user's output folder)."""
    pdf_dir.mkdir(parents=True, exist_ok=True)
    pdf = pdf_dir / (deck.stem + ".pdf")
    with tempfile.TemporaryDirectory() as profile:     # a throwaway profile: no lock file, no first-run dialog
        cmd = [soffice, f"-env:UserInstallation={Path(profile).as_uri()}", "--headless", "--convert-to", "pdf",
               "--outdir", str(pdf_dir), str(deck)]
        run = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    if run.returncode != 0 or not pdf.is_file():
        raise RuntimeError((run.stderr or run.stdout or "soffice produced no PDF").strip()[:200])
    return pdf


def to_pngs(pdf: Path, pages_dir: Path, dpi: int) -> list[Path]:
    """PyMuPDF when installed, else Poppler's pdftoppm. Writes page-NN.png into `pages_dir`, a fresh temporary staging folder."""
    pages_dir.mkdir(parents=True, exist_ok=True)
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
    return sorted(p for p in pages_dir.glob("page-*.png") if OWN_PAGE.match(p.name))


def sheet_names(base: str, tiles: int, per_sheet: int = 12) -> list[str]:
    """The file names contact_sheet.build_sheets will write for `tiles` tiles."""
    if tiles <= 0:
        return []
    count = (tiles + per_sheet - 1) // per_sheet
    return [f"{base}.png"] if count == 1 else [f"{base}_{i}.png" for i in range(1, count + 1)]


def install_pages(staged: list[Path], pages_dir: Path, recorded: list[str]) -> list[Path]:
    """Copy staged page images into `pages_dir`. Raises FileExistsError, before changing anything, when a target exists and was not
    recorded as this tool's; then removes only the recorded page images it replaces."""
    own = {n for n in recorded if OWN_PAGE.match(n)}
    for path in staged:
        if (pages_dir / path.name).exists() and path.name not in own:
            raise FileExistsError(f"{pages_dir / path.name} exists and was not created by render_delta; move or rename it "
                                  "(nothing was changed)")
    pages_dir.mkdir(parents=True, exist_ok=True)
    for name in own:
        (pages_dir / name).unlink(missing_ok=True)
    installed = []
    for path in staged:
        target = pages_dir / path.name
        shutil.copyfile(path, target)
        installed.append(target)
    return installed


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
    out = a.output
    refusal = claim_output(out)
    if refusal:
        print(f"NOT INSPECTED: {refusal}", file=sys.stderr)
        return 2
    import review_ledger
    out.mkdir(parents=True, exist_ok=True)
    state_file = out / "render_state.json"
    try:
        state = json.loads(state_file.read_text(encoding="utf-8")) if state_file.is_file() else {}
    except ValueError:
        state = {}
    env = environment(soffice)
    work = Path(tempfile.mkdtemp(prefix="render_delta_"))
    try:
        try:
            hashes = review_ledger.slide_hashes(a.deck)
            pdf = to_pdf(a.deck.resolve(), work / "pdf", soffice)
            staged = to_pngs(pdf, work / "pages", max(40, a.dpi))
        except Exception as exc:  # noqa: BLE001 - any engine failure means NOT INSPECTED
            print(f"NOT INSPECTED: rendering failed ({type(exc).__name__}: {str(exc)[:160]})", file=sys.stderr)
            return 2
        if len(staged) != len(hashes):
            print(f"NOT INSPECTED: {len(hashes)} slides but {len(staged)} rendered pages", file=sys.stderr)
            return 2
        new = [{"hash": h, "image": file_sha256(p)} for h, p in zip(hashes, staged)]
        return _finish(a, out, state_file, state, env, staged, new)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _finish(a, out: Path, state_file: Path, state: dict, env: dict, staged: list[Path], new: list[dict]) -> int:
    import contact_sheet
    environment_changed = bool(state) and environment_differs(state.get("environment") or {}, env)
    usable = state.get("dpi") == a.dpi and not a.force and not environment_changed
    previous = state.get("slides", []) if usable else []
    changed, unchanged, removed, render_changed = delta_with_images(previous, new)
    first = not previous
    recorded = [n for n in state.get("created", []) if OWN_SHEET.match(n)]
    rewrite_full = first or a.full_sheet
    to_delete = [n for n in recorded if n.startswith("changed_sheet") or rewrite_full]
    kept = [n for n in recorded if n not in to_delete]
    # refuse, before touching anything, to overwrite a file this tool did not record
    clashes = [name for name in sheet_names("changed_sheet", len(changed)) + (sheet_names("sheet", len(new)) if rewrite_full else [])
               if (out / name).exists() and name not in to_delete]
    if clashes:
        print(f"NOT INSPECTED: {out / clashes[0]} exists and was not created by render_delta; move or rename it (nothing was changed)",
              file=sys.stderr)
        return 2
    try:
        pages = install_pages(staged, out / "pages", state.get("pages", []))
    except FileExistsError as exc:
        print(f"NOT INSPECTED: {exc}", file=sys.stderr)
        return 2
    for name in to_delete:
        (out / name).unlink(missing_ok=True)
    changed_sheets: list[Path] = []
    sheets: list[Path] = []
    if changed:
        changed_sheets = contact_sheet.build_sheets([pages[n - 1] for n in changed], out / "changed_sheet.png", cols=4, thumb=480,
                                                    per_sheet=12, labels=[str(n) for n in changed])
    if rewrite_full:
        sheets = contact_sheet.build_sheets(pages, out / "sheet.png", cols=4, thumb=480, per_sheet=12)
    created = kept + [p.name for p in changed_sheets + sheets]
    state_file.write_text(json.dumps({"tool": TOOL, "slides": new, "dpi": a.dpi, "environment": env, "created": created,
                                      "pages": [p.name for p in pages]}), encoding="utf-8")
    result = {"changed": changed, "unchanged": unchanged, "render_changed": render_changed, "removed": removed,
              "environment_changed": environment_changed, "engine": env["soffice"], "dpi": a.dpi, "pages": str(out / "pages"),
              "changed_sheets": [str(p) for p in changed_sheets], "sheets": [str(p) for p in sheets]}
    (out / "delta.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(pages)} page(s) rendered; changed: {changed or 'none'}; unchanged: {len(unchanged)}; removed: {removed}")
    if environment_changed:
        print("the render environment changed (LibreOffice or converter): every slide is treated as changed")
    elif render_changed:
        print(f"same content but rendered differently (font or engine change?): {render_changed}")
    if changed_sheets:
        print("look at " + ", ".join(str(p) for p in changed_sheets) + f" (changed slides only, numbered); open single pages in {out / 'pages'} for detail")
    else:
        print("no slide changed since the last render: nothing to look at again")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
