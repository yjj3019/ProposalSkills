"""Package the shared skills and host manifests without repository or local output files."""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
PACKAGE_FILES = (
    "plugin.json", ".codex-plugin/plugin.json", ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json", ".agents/plugins/marketplace.json", "requirements.txt",
)
CACHE_PARTS = {"__pycache__", ".pytest_cache", ".git"}


def validate_distribution(root: Path) -> None:
    """Validate this plugin's identity and root entry in both marketplace formats."""
    def read(relative: str) -> dict:
        data = json.loads((root / relative).read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            raise ValueError(f"Manifest must be an object: {relative}")
        return data

    shared = read("plugin.json")
    identity = ("name", "version", "description", "author")
    for key in ("name", "version", "description"):
        if not isinstance(shared.get(key), str) or not shared[key].strip():
            raise ValueError(f"Missing string plugin identity: {key}")
    author = shared.get("author")
    if not isinstance(author, dict) or not isinstance(author.get("name"), str) or not author["name"].strip():
        raise ValueError("Missing plugin author name")
    for relative in (".codex-plugin/plugin.json", ".claude-plugin/plugin.json"):
        overlay = read(relative)
        for key in identity:
            if overlay.get(key) != shared[key]:
                raise ValueError(f"Plugin identity mismatch: {relative} ({key})")
        if relative.startswith(".codex") and overlay.get("skills") != "./skills/":
            raise ValueError("Codex plugin must include ./skills/")

    marketplace_name = None
    for relative in (".claude-plugin/marketplace.json", ".agents/plugins/marketplace.json"):
        catalog = read(relative)
        name = catalog.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Missing marketplace name: {relative}")
        if marketplace_name is not None and name != marketplace_name:
            raise ValueError("Marketplace names differ between hosts")
        marketplace_name = name
        entries = catalog.get("plugins")
        if not isinstance(entries, list):
            raise ValueError(f"Marketplace plugins must be a list: {relative}")
        matches = [entry for entry in entries
                   if isinstance(entry, dict) and entry.get("name") == shared["name"]]
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one {shared['name']} entry: {relative}")
        source = matches[0].get("source")
        if relative.startswith(".agents"):
            if not isinstance(source, dict) or source.get("source") != "local":
                raise ValueError(f"Expected a local marketplace source: {relative}")
            source = source.get("path")
        if (not isinstance(source, str) or not source.startswith("./")
                or (root / source).resolve() != root.resolve()):
            raise ValueError(f"Marketplace source must resolve to this plugin root: {relative}")


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
    validate_distribution(root)
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
