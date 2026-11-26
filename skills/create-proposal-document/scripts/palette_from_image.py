#!/usr/bin/env python3
"""Derive deck palette tokens from a reference image, and check any palette against the contrast the generator relies on.

Why: a mood image (a screenshot, a brand photo) is a fast way to pick a color direction, but raw picked colors fail the
generator's text/background pairs (white text on a pale primary, muted gray on a tint). This tool takes the image's dominant
colors, then adjusts them until every pair the generator uses passes WCAG contrast, and prints a `meta.palette` object.

  palette_from_image.py IMAGE [--out palette.json]     derive tokens (primary, tint1-3, text, muted, side_b)
  palette_from_image.py --check FILE                   check a palette JSON, or a slides.json (its meta.palette)

Only colors are taken, never the image itself. The image is untrusted data: it is decoded with Pillow, size-limited, and no
metadata is read or printed. A buyer-prescribed palette or template always wins over a derived one (deck-production.md §3);
semantic colors (warn, ok, white, bg) are never taken from an image.

Checked pairs (text on background, minimum 4.5:1): text/bg, muted/bg, primary/bg, warn/bg, white/primary, white/side_b,
text/tint2, text/tint3. Values must be 6-digit hex.

Exit codes: 0 ok, 1 a palette fails the check, 2 usage error or unreadable image/file.

Usage: python palette_from_image.py IMAGE [--out palette.json] | --check FILE
"""
from __future__ import annotations

import argparse
import colorsys
import json
import re
import sys
from pathlib import Path

from color_contrast import contrast_ratio

HEX6 = re.compile(r"^[0-9A-Fa-f]{6}$")
MIN_RATIO = 4.5
PAIRS = (("text", "bg"), ("muted", "bg"), ("primary", "bg"), ("warn", "bg"),
         ("white", "primary"), ("white", "side_b"), ("text", "tint2"), ("text", "tint3"))
DERIVED = ("primary", "tint1", "tint2", "tint3", "text", "muted", "side_b")
MAX_IMAGE_BYTES = 25 * 1024 * 1024
MIN_HUE_GAP = 40  # degrees between the two accent seeds


def to_hex(rgb: tuple[float, float, float]) -> str:
    return "".join(f"{max(0, min(255, round(c))):02X}" for c in rgb)


def to_rgb(hex6: str) -> tuple[int, int, int]:
    return tuple(int(hex6[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def mix(a: str, b: str, amount: float) -> str:
    """`amount` of b mixed into a."""
    return to_hex(tuple(x + (y - x) * amount for x, y in zip(to_rgb(a), to_rgb(b))))


def adjust(color: str, against: str, minimum: float, toward: str) -> str:
    """Move `color` toward black or white in small steps until it reaches `minimum` contrast against `against`."""
    target = "000000" if toward == "dark" else "FFFFFF"
    for step in range(0, 41):
        candidate = mix(color, target, step / 40)
        if contrast_ratio(candidate, against) >= minimum:
            return candidate
    return target


def check_palette(palette: dict) -> list[str]:
    """Problems with a full palette (every role present, as the generator sees it)."""
    problems = []
    for role, value in palette.items():
        if not isinstance(value, str) or not HEX6.match(value.lstrip("#")):
            problems.append(f"{role}: `{value}` is not a 6-digit hex color")
    if problems:
        return problems
    clean = {role: value.lstrip("#").upper() for role, value in palette.items()}
    for foreground, background in PAIRS:
        if foreground in clean and background in clean:
            ratio = contrast_ratio(clean[foreground], clean[background])
            if ratio < MIN_RATIO:
                problems.append(f"{foreground} {clean[foreground]} on {background} {clean[background]}: "
                                f"{ratio:.2f}:1 < {MIN_RATIO}:1")
    return problems


def dominant_colors(image_path: Path) -> list[tuple[str, int]]:
    from PIL import Image  # Pillow is a declared requirement; imported late so --check works without decoding anything

    if image_path.stat().st_size > MAX_IMAGE_BYTES:
        raise ValueError("image larger than 25 MB")
    try:
        with Image.open(image_path) as source:
            rgb = source.convert("RGB")
    except Image.DecompressionBombError as exc:
        raise ValueError("image has too many pixels") from exc
    rgb.thumbnail((96, 96))
    quantized = rgb.quantize(colors=8, method=Image.MEDIANCUT)
    palette = quantized.getpalette() or []
    colors = []
    for count, index in quantized.getcolors() or []:
        colors.append((to_hex(tuple(palette[index * 3:index * 3 + 3])), count))
    return sorted(colors, key=lambda item: (-item[1], item[0]))


def hue_of(hex6: str) -> float:
    return colorsys.rgb_to_hsv(*(c / 255 for c in to_rgb(hex6)))[0] * 360


def saturation_value(hex6: str) -> tuple[float, float]:
    _, s, v = colorsys.rgb_to_hsv(*(c / 255 for c in to_rgb(hex6)))
    return s, v


def rotate_hue(hex6: str, degrees: float) -> str:
    h, s, v = colorsys.rgb_to_hsv(*(c / 255 for c in to_rgb(hex6)))
    return to_hex(tuple(c * 255 for c in colorsys.hsv_to_rgb(((h * 360 + degrees) % 360) / 360, max(s, 0.45), max(v, 0.6))))


def derive(colors: list[tuple[str, int]], defaults: dict) -> tuple[dict, list[str]]:
    notes: list[str] = []
    chromatic = [(c, n) for c, n in colors if saturation_value(c)[0] >= 0.2 and saturation_value(c)[1] >= 0.15]
    if chromatic:
        seed1 = chromatic[0][0]
    else:
        seed1 = defaults["primary"]
        notes.append("no usable color in the image (all near-white or gray): kept the default primary hue")
    seed2 = next((c for c, _ in chromatic[1:]
                  if min(abs(hue_of(c) - hue_of(seed1)), 360 - abs(hue_of(c) - hue_of(seed1))) >= MIN_HUE_GAP), None)
    if seed2 is None:
        seed2 = rotate_hue(seed1, 150)
        notes.append("no second distinct hue in the image: side_b is a hue-rotated variant of primary")
    bg = defaults["bg"]
    primary = adjust(seed1, bg, MIN_RATIO, "dark")
    side_b = adjust(seed2, "FFFFFF", MIN_RATIO, "dark")
    text = adjust(mix(primary, "000000", 0.8), bg, 7.0, "dark")
    tint1, tint2, tint3 = mix(primary, "FFFFFF", 0.5), mix(primary, "FFFFFF", 0.82), mix(primary, "FFFFFF", 0.93)
    muted = adjust(mix(text, "FFFFFF", 0.35), tint2, MIN_RATIO, "dark")
    palette = {"primary": primary, "tint1": tint1, "tint2": tint2, "tint3": tint3, "text": text, "muted": muted,
               "side_b": side_b}
    if primary != seed1:
        notes.append(f"primary {seed1} darkened to {primary} for white-text contrast")
    return palette, notes


def default_palette(theme: str | None = None) -> dict:
    from build_deck import DEFAULT_PALETTE, THEMES  # one definition of the defaults

    return {**DEFAULT_PALETTE, **THEMES.get(theme or "standard", {}).get("palette", {})}


def palette_from_file(path: Path) -> tuple[dict, str | None]:
    """The palette in a file, and the theme when the file is a slides.json."""
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    theme = None
    if isinstance(data, dict) and isinstance(data.get("meta"), dict):
        theme = data["meta"].get("theme")
        data = data["meta"].get("palette") or {}
    if isinstance(data, dict) and isinstance(data.get("palette"), dict):
        data = data["palette"]
    if not isinstance(data, dict):
        raise ValueError("expected a palette object, or a slides.json with meta.palette")
    return data, theme


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("image", type=Path, nargs="?")
    parser.add_argument("--check", type=Path, metavar="FILE")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    if bool(args.image) == bool(args.check):
        parser.print_usage(sys.stderr)
        return 2
    try:
        defaults = default_palette()
        if args.check:
            given, theme = palette_from_file(args.check)
            merged = {**default_palette(theme), **{k: v.lstrip("#") if isinstance(v, str) else v
                                                    for k, v in given.items()}}
            problems = check_palette(merged)
            for problem in problems:
                print(f"[PROBLEM] {problem}")
            print(f"PALETTE: {'PROBLEMS' if problems else 'OK'} ({len(problems)})")
            return 1 if problems else 0
        palette, notes = derive(dominant_colors(args.image), defaults)
    except (OSError, ValueError, UnicodeDecodeError, ImportError) as exc:
        print(f"Cannot read input: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    problems = check_palette({**defaults, **palette})
    if problems:  # derivation must never hand out a failing palette
        print("[BUG] derived palette fails its own check: " + "; ".join(problems), file=sys.stderr)
        return 1
    payload = {"palette": palette, "notes": notes,
               "use": "Paste `palette` into slides.json meta.palette. Buyer templates and palettes take precedence."}
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
