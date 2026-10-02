"""Package the shared skills and host manifests without repository or local output files."""
from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
PACKAGE_FILES = (
    "plugin.json", ".codex-plugin/plugin.json", ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json", ".agents/plugins/marketplace.json", "requirements.txt",
)
CACHE_PARTS = {"__pycache__", ".pytest_cache", ".git"}


def build_archive(destination: Path, *, root: Path = REPO) -> Path:
    root = root.resolve()
    files = [root / name for name in PACKAGE_FILES]
    files += sorted(p for p in (root / "skills").rglob("*")
                    if p.is_file() and not CACHE_PARTS.intersection(p.relative_to(root).parts)
                    and p.suffix not in {".pyc", ".pyo"})
    for path in files:
        if not path.is_file():
            raise FileNotFoundError(f"Required package file missing: {path.relative_to(root)}")
        if not path.resolve().is_relative_to(root):
            raise ValueError(f"Package path escapes source root: {path.relative_to(root)}")
    for name in ("create-best-proposal", "create-proposal-document", "create-winning-proposal"):
        if root / "skills" / name / "SKILL.md" not in files:
            raise FileNotFoundError(f"Required skill missing: {name}")
    destination = destination.resolve()
    if destination in files:
        raise ValueError("Output must not replace a package source file")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # An existing archive is never silently overwritten.
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(root).as_posix())
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        path = build_archive(args.output)
    except (OSError, ValueError) as exc:
        print(f"Package failed: {exc}", file=sys.stderr)
        return 1
    print(f"Packaged: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
