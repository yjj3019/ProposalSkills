#!/usr/bin/env python3
"""Install a proposal skill from this repository into an AI skill directory."""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parent / "skills"
DEFAULT_NAME = "create-winning-proposal"
# Backward compatibility for existing tests/tools that import SOURCE.
SOURCE = SKILLS_ROOT / DEFAULT_NAME


def destination_root(value: str | None) -> Path:
    if value:
        return Path(value).expanduser()
    if value := os.environ.get("AI_SKILLS_DIR"):
        return Path(value).expanduser()
    if value := os.environ.get("CODEX_HOME"):
        return Path(value).expanduser() / "skills"
    raise SystemExit("Set --dest, AI_SKILLS_DIR, or CODEX_HOME.")


def available_skills() -> list[str]:
    return sorted(p.parent.name for p in SKILLS_ROOT.glob("*/SKILL.md"))


def install(root: Path, name: str = DEFAULT_NAME) -> Path:
    source = SKILLS_ROOT / name
    if not (source / "SKILL.md").is_file():
        raise SystemExit(
            f"Unknown skill '{name}'. Available: {', '.join(available_skills())}")
    target = root.resolve() / name
    if target.exists():
        raise SystemExit(f"Already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)
    if not (target / "SKILL.md").is_file():
        shutil.rmtree(target, ignore_errors=True)
        raise SystemExit("Installation verification failed.")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", help="Parent directory that stores AI skills")
    parser.add_argument(
        "--name", default=DEFAULT_NAME,
        help=f"Skill to install (default: {DEFAULT_NAME}). "
             f"Available: {', '.join(available_skills())}")
    parser.add_argument("--all", action="store_true", help="Install every skill")
    args = parser.parse_args()
    root = destination_root(args.dest)
    names = available_skills() if args.all else [args.name]
    for name in names:
        print(f"Installed: {install(root, name)}")


if __name__ == "__main__":
    main()
