#!/usr/bin/env python3
"""Optional PDF visual regression. A matching image is never submission approval."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def write_json(path: Path, value: dict) -> None:
    serialized = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(serialized)


def snapshot(pdf: Path, source: Path, environment: dict, destination: Path,
             reviewer: str | None = None) -> dict:
    """Capture an immutable PDF copy and declared render environment, not an audit."""
    for field in ("renderer", "renderer_version", "font_profile"):
        if not isinstance(environment.get(field), str) or not environment[field].strip():
            raise ValueError(f"Render environment requires {field}")
    if not pdf.is_file() or not source.is_file():
        raise ValueError("PDF and source must be local files")
    with pdf.open("rb") as stream:
        if stream.read(5) != b"%PDF-":
            raise ValueError("Input is not a PDF")
    if reviewer is not None and not reviewer.strip():
        raise ValueError("Reviewer must not be blank")
    source_hash = sha256(source)
    pdf_hash = sha256(pdf)
    destination.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(pdf, destination / "document.pdf")
    if sha256(destination / "document.pdf") != pdf_hash or sha256(source) != source_hash:
        raise ValueError("Input changed while creating snapshot")
    data = {
        "schema_version": 1, "kind": "proposal-visual-snapshot",
        "source_sha256": source_hash, "pdf_sha256": pdf_hash,
        "environment": {**environment, "snapshot_os": platform.platform()},
        "environment_observation": "declared by caller; verify renderer and actual fonts",
        "baseline_reviewer": reviewer, "submission_approval": False,
    }
    write_json(destination / "manifest.json", data)
    return data


def load_snapshot(folder: Path) -> tuple[dict, Path]:
    data = read_object(folder / "manifest.json")
    if data.get("kind") != "proposal-visual-snapshot" or data.get("schema_version") != 1:
        raise ValueError("Unsupported snapshot")
    for key in ("pdf_sha256", "source_sha256"):
        value = data.get(key)
        if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError(f"Invalid {key}")
    env = data.get("environment")
    if not isinstance(env, dict) or any(not isinstance(env.get(k), str) or not env[k].strip()
                                      for k in ("renderer", "renderer_version", "font_profile", "snapshot_os")):
        raise ValueError("Invalid environment")
    pdf = folder / "document.pdf"
    if sha256(pdf) != data["pdf_sha256"]:
        raise ValueError("Snapshot PDF hash mismatch")
    return data, pdf


def render(pdf: Path, folder: Path, dpi: int) -> list[Path]:
    folder.mkdir()
    info = subprocess.run(["pdfinfo", str(pdf.resolve())], check=True, capture_output=True, timeout=15,
                          env={**os.environ, "LC_ALL": "C"})
    counts = [line.split(":", 1)[1].strip() for line in info.stdout.decode("utf-8", "replace").splitlines()
              if line.startswith("Pages:")]
    if len(counts) != 1 or not counts[0].isdigit() or int(counts[0]) < 1:
        raise ValueError("PDF page count unavailable")
    subprocess.run(["pdftoppm", "-png", "-r", str(dpi), str(pdf.resolve()), str(folder / "page")],
                   check=True, capture_output=True, timeout=180)
    pages = sorted(folder.glob("page-*.png"), key=lambda p: int(p.stem.split("-")[-1]))
    if len(pages) != int(counts[0]) or [int(p.stem.split("-")[-1]) for p in pages] != list(range(1, len(pages) + 1)):
        raise ValueError("Missing or incomplete rendered pages")
    return pages


def compare(baseline: Path, candidate: Path, destination: Path, *,
            max_changed_ratio: float, dpi: int = 150, channel_delta: int = 8) -> dict:
    if not math.isfinite(max_changed_ratio) or not 0 <= max_changed_ratio < 1:
        raise ValueError("max_changed_ratio must be finite and in [0, 1)")
    if not 72 <= dpi <= 300 or not 0 <= channel_delta <= 254:
        raise ValueError("dpi must be 72..300 and channel_delta 0..254")
    before, before_pdf = load_snapshot(baseline)
    after, after_pdf = load_snapshot(candidate)
    destination.mkdir(parents=True, exist_ok=False)
    result = {
        "schema_version": 1, "kind": "proposal-visual-comparison", "status": "NOT-RUN",
        "baseline": before, "candidate": after,
        "settings": {"dpi": dpi, "channel_delta": channel_delta,
                     "max_changed_ratio": max_changed_ratio},
        "pages": [], "visual_review_approved": False,
    }
    try:
        if not isinstance(before.get("baseline_reviewer"), str) or not before["baseline_reviewer"].strip():
            raise ValueError("Baseline requires explicit reviewer approval")
        if before["environment"] != after["environment"]:
            result.update(status="INCOMPARABLE", reason="Declared render environments differ")
        else:
            from PIL import Image, ImageChops, __version__ as pillow_version
            version = subprocess.run(["pdftoppm", "-v"], capture_output=True, timeout=15, check=True)
            result["tools"] = {"pillow": pillow_version,
                               "pdftoppm": (version.stdout + version.stderr).decode("utf-8", "replace").strip()}
            a = render(before_pdf, destination / "before", dpi)
            b = render(after_pdf, destination / "after", dpi)
            result["page_counts"] = {"baseline": len(a), "candidate": len(b)}
            different = len(a) != len(b)
            for number, (left, right) in enumerate(zip(a, b), 1):
                with Image.open(left) as image_a, Image.open(right) as image_b:
                    if image_a.size != image_b.size:
                        result["pages"].append({"page": number, "different": True, "reason": "page size changed"})
                        different = True
                        continue
                    diff = ImageChops.difference(image_a.convert("RGB"), image_b.convert("RGB"))
                    red, green, blue = diff.split()
                    maximum = ImageChops.lighter(ImageChops.lighter(red, green), blue)
                    mask = maximum.point(lambda value: 255 if value > channel_delta else 0)
                    ratio = (image_a.width * image_a.height - mask.histogram()[0]) / (image_a.width * image_a.height)
                    changed = ratio > max_changed_ratio
                    different |= changed
                    diff_name = f"diff-{number}.png"
                    diff.save(destination / diff_name)
                    result["pages"].append({"page": number, "changed_ratio": ratio,
                                             "changed_bbox": mask.getbbox(), "different": changed,
                                             "diff": diff_name})
            # Files may be modified by another process during rendering.
            if sha256(before_pdf) != before["pdf_sha256"] or sha256(after_pdf) != after["pdf_sha256"]:
                raise ValueError("Snapshot changed during comparison")
            result["status"] = "DIFFERENT" if different else "SAME"
    except Exception as exc:
        # This is an external image/render adapter. Backend-specific failures
        # (including Pillow's decompression limit) become explicit ERROR evidence.
        # KeyboardInterrupt/SystemExit still propagate and cannot produce SAME.
        # Never echo backend exception details, which can contain document paths.
        result.update(status="ERROR", reason=type(exc).__name__)
    write_json(destination / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    capture = sub.add_parser("snapshot")
    capture.add_argument("pdf", type=Path)
    capture.add_argument("--source", type=Path, required=True)
    capture.add_argument("--environment", type=Path, required=True)
    capture.add_argument("--output", type=Path, required=True)
    capture.add_argument("--reviewer", help="Only set after a human approves the baseline PDF")
    check = sub.add_parser("compare")
    check.add_argument("baseline", type=Path)
    check.add_argument("candidate", type=Path)
    check.add_argument("--output", type=Path, required=True)
    check.add_argument("--max-changed-ratio", required=True, type=float)
    check.add_argument("--dpi", default=150, type=int)
    check.add_argument("--channel-delta", default=8, type=int)
    args = parser.parse_args()
    try:
        if args.command == "snapshot":
            snapshot(args.pdf, args.source, read_object(args.environment), args.output, args.reviewer)
            print("SNAPSHOT-CREATED (not submission approval)")
            return 0
        result = compare(args.baseline, args.candidate, args.output,
                         max_changed_ratio=args.max_changed_ratio, dpi=args.dpi, channel_delta=args.channel_delta)
        print(result["status"])
        return {"SAME": 0, "DIFFERENT": 1, "ERROR": 2, "NOT-RUN": 2, "INCOMPARABLE": 3}[result["status"]]
    except (OSError, ValueError) as exc:
        print(f"Comparison failed: {type(exc).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
