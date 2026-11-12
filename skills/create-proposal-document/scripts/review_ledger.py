#!/usr/bin/env python3
"""A page-by-page review ledger: makes "I looked at every slide" a recorded, checkable claim instead of an assumption.

No script can judge whether a slide makes its point; `tidy_audit.py` only measures proxies. What can be enforced is that the
review happened: every slide was seen at the right size, judged on the four rungs (plain, busy, not at a glance, unfinished),
every serious finding was closed or knowingly accepted, the deck was revised at least once, and the ledger still matches the
file that is being delivered. This checks the process and its honesty, never the quality: a ledger can still be filled in
carelessly, but it can no longer be skipped silently, and `verification_report.py` can cite it as the evidence of a
rendered-level check.

ledger.json (created by `init`):
  {"deck": "deck.pptx", "deck_sha256": "...", "engine": "LibreOffice 24.8", "revisions": 1,
   "slides": [{"slide": 3, "title": "...", "kind": "content", "visual": true, "viewed": "full|sheet|none",
               "image": "png/page-03.png", "image_sha256": "...",
               "rungs": {"plain": "pass|fail|waived", "busy": "...", "glance": "...", "unfinished": "..."},
               "waived_reason": "", "findings": [{"severity": "Critical|Major|Minor", "text": "...",
                                                   "status": "open|fixed|accepted", "reason": ""}]}],
   "not_inspected": ["what could not be checked"]}

A verdict is tied to the image that was looked at, for `full` and for `sheet` alike: `set --viewed ...` records the image's SHA-256,
`check` refuses a slide whose image now differs (a changed font or render engine makes the same slide look different), and `sync` carries
a verdict onto a rebuilt slide only when it can PROVE the picture is the same (the old and the new hash are both recorded and equal);
a missing hash (an older ledger) or a different picture resets the slide. Giving `set --image` a different image, or viewing again after
the image changed, clears the viewing and the four rungs: they must be given again. Open Critical or Major findings of a slide that no
longer exists are kept in `orphaned_findings` and block `check` until they are resolved in the ledger.

Each slide also carries a content hash (its XML plus the parts it uses: layout, master, charts, images). After the deck is rebuilt,
`sync` keeps the verdicts of slides whose hash is unchanged and resets only the changed or new ones, so only those need to be looked at
again. A verdict is never carried onto a slide whose hash differs, and `check` refuses a ledger whose hashes no longer match the deck.

Usage:
    python review_ledger.py init deck.pptx -o ledger.json [--png-dir out/png] [--engine "LibreOffice"]
    python review_ledger.py sync ledger.json [--png-dir out/png]     # after a rebuild: keep unchanged slides, reset the rest
    python review_ledger.py set ledger.json --slide 3 --viewed full --plain pass --busy pass --glance pass --unfinished pass
    python review_ledger.py check ledger.json

Rules enforced by `check`
  - the ledger matches the deck's SHA-256 and every slide's hash (a changed deck needs `sync` and a look at the changed slides) and
    names the engine that produced the images
  - every slide is viewed; a content slide with a chart or diagram is viewed at full size (`full`), the cover and closing
    slide may be seen on a contact sheet; `full` needs an image that exists, is not older than the deck and still has the SHA-256 it
    had when it was viewed
  - every content slide has all four rungs pass or waived (a waiver needs a reason); none is fail
  - no Critical or Major finding is open; an accepted finding needs a reason
  - at least one revision is recorded, `not_inspected` is present, and no score fields exist

Exit codes: 0 = complete, 1 = incomplete or invalid, 2 = usage error or unreadable file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

RUNGS = ("plain", "busy", "glance", "unfinished")
SCORE_KEYS = {"score", "rating", "quality_score", "grade"}
MTIME_SLACK = 2.0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def natural(path: Path) -> list:
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", path.name)]


def slide_hashes(deck: Path) -> list[str]:
    """One content hash per slide: the slide part plus the parts it uses, three levels deep (layout, master and theme; charts and
    their workbooks; images), the slide size and the table styles. Changing the layout, master, theme, slide size or table styles
    therefore changes every slide, which is correct: a theme colour or font change alters how a slide looks. Part names are left
    out so inserting or deleting a slide does not change the hash of the slides after it."""
    from pptx import Presentation
    prs = Presentation(str(deck))
    common = hashlib.sha256(f"{prs.slide_width}x{prs.slide_height}".encode())
    for rel_ in prs.part.rels.values():
        if str(rel_.reltype).endswith("/tableStyles") and not rel_.is_external:
            common.update(rel_.target_part.blob)

    def feed(part, digest, depth, seen):
        if id(part) in seen:
            return
        seen.add(id(part))
        digest.update(part.blob)   # content only: part names shift when slides are inserted or removed
        if depth <= 0:
            return
        for rel_ in sorted(part.rels.values(), key=lambda r: r.rId):
            digest.update(rel_.reltype.encode())
            if rel_.is_external:
                digest.update(str(rel_.target_ref).encode())
            elif not str(rel_.reltype).endswith("/slide"):
                feed(rel_.target_part, digest, depth - 1, seen)

    out = []
    for slide in prs.slides:
        digest = hashlib.sha256(common.digest())
        feed(slide.part, digest, 3, set())
        out.append(digest.hexdigest())
    return out


def rel(path: Path, base: Path) -> str:
    """Path relative to the ledger's folder; absolute when the two are on different drives."""
    try:
        return os.path.relpath(Path(path).resolve(), base.resolve())
    except ValueError:
        return str(Path(path).resolve())


def slide_title(slide) -> str:
    for shape in slide.shapes:
        if shape.name == "TITLE" and shape.has_text_frame and shape.text_frame.text.strip():
            return shape.text_frame.text.strip()
    texts = [sh.text_frame.text.strip() for sh in slide.shapes if sh.has_text_frame and sh.text_frame.text.strip()]
    return texts[0] if texts else ""


def init(deck: Path, out: Path, png_dir: Path | None, engine: str) -> dict:
    from pptx import Presentation
    import tidy_audit
    report = tidy_audit.measure(deck)
    prs = Presentation(str(deck))
    hashes = slide_hashes(deck)
    images = sorted((p for p in png_dir.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg"}), key=natural) if png_dir else []
    count = len(prs.slides)
    slides = []
    for number, (slide, metrics, digest) in enumerate(zip(prs.slides, report["slides"], hashes), 1):
        kind = "content" if 1 < number < count or count < 3 else ("cover" if number == 1 else "closing")
        image = rel(images[number - 1], out.resolve().parent) if number - 1 < len(images) else ""
        slides.append({"slide": number, "title": slide_title(slide), "kind": kind, "visual": metrics["visual"], "hash": digest,
                       "viewed": "none", "image": image, "rungs": {r: None for r in RUNGS}, "waived_reason": "", "findings": []})
    return {"deck": rel(deck, out.resolve().parent), "deck_sha256": sha256(deck), "engine": engine, "revisions": 0, "slides": slides, "not_inspected": []}


def sync(ledger: dict, base: Path, png_dir: Path | None) -> tuple[dict, dict]:
    """Bring a ledger up to date with the rebuilt deck. Returns (new ledger, {"kept": [...], "reset": [...], "removed": n})."""
    deck = (base / str(ledger["deck"])).resolve()
    new_hashes = slide_hashes(deck)
    fresh = init(deck, base / "_sync.json", png_dir, str(ledger.get("engine", "")))
    old_by_hash: dict[str, list[dict]] = {}
    for old in ledger.get("slides", []):
        old_by_hash.setdefault(old.get("hash", ""), []).append(old)
    kept, reset, rendered = [], [], []
    for slide, digest in zip(fresh["slides"], new_hashes):
        pool = old_by_hash.get(digest) or []
        if digest and pool:
            old = pool.pop(0)
            slide["findings"] = old.get("findings", [])         # findings describe the content, which is unchanged
            image = (base / slide["image"]) if slide["image"] else None
            new_sha = sha256(image) if image is not None and image.is_file() else ""
            old_sha = old.get("image_sha256", "")
            looked = old.get("viewed") in {"full", "sheet"}
            if not looked:
                reset.append(slide["slide"])
            elif not (old_sha and new_sha and old_sha == new_sha):
                # the verdict cannot be shown to be about this picture: no hash was recorded (older ledger), the image is
                # missing, or the picture differs; either way it has to be looked at again
                reset.append(slide["slide"])
                if old_sha and new_sha:
                    rendered.append(slide["slide"])
            else:
                for key in ("viewed", "rungs", "waived_reason"):
                    slide[key] = old.get(key, slide[key])
                slide["image_sha256"] = new_sha
                kept.append(slide["slide"])
        else:
            reset.append(slide["slide"])
    orphans = list(ledger.get("orphaned_findings") or [])
    for leftover in (old for pool in old_by_hash.values() for old in pool):
        for f in leftover.get("findings") or []:
            if f.get("severity") in {"Critical", "Major"} and f.get("status") == "open":
                orphans.append({"was_slide": leftover.get("slide"), "severity": f["severity"], "text": f.get("text", ""),
                                "status": "open", "reason": ""})
    fresh["orphaned_findings"] = orphans
    removed = sum(len(v) for v in old_by_hash.values())
    fresh["deck"] = ledger["deck"]
    fresh["revisions"] = ledger.get("revisions", 0)
    fresh["not_inspected"] = ledger.get("not_inspected", [])
    return fresh, {"kept": kept, "reset": reset, "removed": removed, "render_changed": rendered}


def problems_in(ledger: dict, base: Path) -> list[str]:
    out: list[str] = []
    if SCORE_KEYS & set(ledger) or any(SCORE_KEYS & set(s) for s in ledger.get("slides", [])):
        out.append("score fields are not allowed: report findings and levels, never a number")
    deck = (base / str(ledger.get("deck", ""))).resolve() if ledger.get("deck") else None
    if deck is None or not deck.is_file():
        out.append(f"deck not found: {ledger.get('deck')!r}")
    elif sha256(deck) != ledger.get("deck_sha256"):
        out.append("ledger is stale: the deck changed after the review (run sync, then look at the slides it resets)")
    else:
        current = slide_hashes(deck)
        recorded = [s.get("hash") for s in ledger.get("slides", [])]
        if len(current) != len(recorded):
            out.append(f"the deck has {len(current)} slides but the ledger lists {len(recorded)}: run sync")
        else:
            for number, (now, then) in enumerate(zip(current, recorded), 1):
                if now != then:
                    out.append(f"slide {number}: changed since it was judged (hash differs): run sync and look at it again")
    if not str(ledger.get("engine", "")).strip():
        out.append("engine is empty: name what produced the images (LibreOffice, PowerPoint, ...)")
    if int(ledger.get("revisions") or 0) < 1:
        out.append("no revision recorded: revise at least once against the findings, then render and look again")
    if not isinstance(ledger.get("not_inspected"), list):
        out.append("not_inspected must be a list (empty when everything was inspected)")
    slides = ledger.get("slides") or []
    if not slides:
        out.append("no slides in the ledger")
    for s in slides:
        n = s.get("slide")
        content = s.get("kind") == "content"
        viewed = s.get("viewed")
        if viewed not in {"full", "sheet"}:
            out.append(f"slide {n}: not viewed")
        elif content and s.get("visual") and viewed != "full":
            out.append(f"slide {n}: a chart or diagram must be viewed at full size, not on a contact sheet")
        if viewed in {"full", "sheet"}:
            image = (base / str(s.get("image", ""))) if s.get("image") else None
            if image is None or not image.is_file():
                out.append(f"slide {n}: viewed ({viewed}) but the rendered image is missing")
            elif deck is not None and deck.is_file() and image.stat().st_mtime + MTIME_SLACK < deck.stat().st_mtime:
                out.append(f"slide {n}: the image is older than the deck; render again")
            elif not s.get("image_sha256"):
                out.append(f"slide {n}: the viewed image's hash is not recorded; run set --viewed {viewed} again after looking at it")
            elif sha256(image) != s["image_sha256"]:
                out.append(f"slide {n}: the image changed after it was viewed (it renders differently now); look again")
        if content:
            for rung in RUNGS:
                value = (s.get("rungs") or {}).get(rung)
                if value not in {"pass", "waived"}:
                    out.append(f"slide {n}: rung '{rung}' is {value or 'not judged'} (pass or waive it with a reason)")
                elif value == "waived" and not str(s.get("waived_reason", "")).strip():
                    out.append(f"slide {n}: rung '{rung}' is waived without a reason")
        for f in s.get("findings") or []:
            if f.get("severity") in {"Critical", "Major"} and f.get("status") == "open":
                out.append(f"slide {n}: open {f.get('severity')} finding: {str(f.get('text', ''))[:70]}")
            if f.get("status") == "accepted" and not str(f.get("reason", "")).strip():
                out.append(f"slide {n}: an accepted finding needs a reason")
    for f in ledger.get("orphaned_findings") or []:
        if f.get("severity") in {"Critical", "Major"} and f.get("status") == "open":
            out.append(f"an open {f.get('severity')} finding from old slide {f.get('was_slide')} has no slide any more: set its status "
                       f"to fixed, or to accepted with a reason, in `orphaned_findings`")
        if f.get("status") == "accepted" and not str(f.get("reason", "")).strip():
            out.append(f"an accepted orphaned finding from old slide {f.get('was_slide')} needs a reason")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init")
    i.add_argument("deck", type=Path)
    i.add_argument("-o", "--output", type=Path, required=True)
    i.add_argument("--png-dir", type=Path)
    i.add_argument("--engine", default="")
    sy = sub.add_parser("sync")
    sy.add_argument("ledger", type=Path)
    sy.add_argument("--png-dir", type=Path)
    st = sub.add_parser("set")
    st.add_argument("ledger", type=Path)
    st.add_argument("--slide", type=int, required=True)
    st.add_argument("--viewed", choices=["full", "sheet", "none"])
    st.add_argument("--image")
    for rung in RUNGS:
        st.add_argument(f"--{rung}", choices=["pass", "fail", "waived"])
    st.add_argument("--waived-reason")
    st.add_argument("--finding", help="SEVERITY|status|text|reason, for example 'Major|open|axis unit missing|'")
    st.add_argument("--revisions", type=int)
    c = sub.add_parser("check")
    c.add_argument("ledger", type=Path)
    a = ap.parse_args(argv)
    try:
        if a.cmd == "init":
            if not a.deck.is_file():
                print(f"deck not found: {a.deck}", file=sys.stderr)
                return 2
            ledger = init(a.deck, a.output, a.png_dir, a.engine)
            a.output.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"wrote {a.output} ({len(ledger['slides'])} slides); fill it in as you look, then run check")
            return 0
        ledger = json.loads(a.ledger.read_text(encoding="utf-8-sig"))
        if a.cmd == "sync":
            base = a.ledger.resolve().parent
            fresh, summary = sync(ledger, base, a.png_dir)
            deck = (base / str(ledger["deck"])).resolve()
            fresh["deck_sha256"] = sha256(deck)
            a.ledger.write_text(json.dumps(fresh, ensure_ascii=False, indent=2), encoding="utf-8")
            note = f" ({summary['render_changed']} render differently now)" if summary["render_changed"] else ""
            print(f"kept {len(summary['kept'])} slide(s) {summary['kept']}; look again at {summary['reset']}{note}; "
                  f"{summary['removed']} removed. Set revisions to at least 1 once you have revised.")
            return 0
        if a.cmd == "set":
            slides = {s["slide"]: s for s in ledger["slides"]}
            if a.slide not in slides:
                print(f"no slide {a.slide} in the ledger", file=sys.stderr)
                return 2
            s = slides[a.slide]
            old_image, old_sha = s.get("image", ""), s.get("image_sha256", "")
            if a.image:
                s["image"] = a.image
            if a.viewed:
                s["viewed"] = a.viewed
            if a.viewed or a.image:                                   # only when viewing or the picture is recorded, never on a later edit
                shown = a.ledger.resolve().parent / s["image"] if s.get("image") else None
                now = sha256(shown) if shown is not None and shown.is_file() else ""
                if (a.image and a.image != old_image) or (old_sha and now and now != old_sha):
                    # another picture is another thing to judge: the earlier viewing and the four rungs do not carry over
                    if not a.viewed:
                        s["viewed"] = "none"
                    s["rungs"] = {r: None for r in RUNGS}
                    s["waived_reason"] = ""
                    s["image_sha256"] = ""
                if s.get("viewed") in {"full", "sheet"} and now:
                    s["image_sha256"] = now
            for rung in RUNGS:
                if getattr(a, rung):
                    s["rungs"][rung] = getattr(a, rung)
            if a.waived_reason is not None:
                s["waived_reason"] = a.waived_reason
            if a.finding:
                parts = (a.finding.split("|") + ["", "", "", ""])[:4]
                s.setdefault("findings", []).append({"severity": parts[0], "status": parts[1] or "open", "text": parts[2], "reason": parts[3]})
            if a.revisions is not None:
                ledger["revisions"] = a.revisions
            a.ledger.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"updated slide {a.slide}")
            return 0
        problems = problems_in(ledger, a.ledger.resolve().parent)
        for line in problems:
            print(f"  - {line}")
        print("REVIEW-LEDGER: " + ("COMPLETE" if not problems else f"INCOMPLETE ({len(problems)} problem(s))")
              + " (proves every page was recorded as seen, not that the judgments are right)")
        return 1 if problems else 0
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        print(f"cannot read: {type(exc).__name__}: {str(exc)[:100]}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
