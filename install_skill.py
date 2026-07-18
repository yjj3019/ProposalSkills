#!/usr/bin/env python3
"""Install this repository's proposal skill into an AI skill directory."""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

NAME = "create-winning-proposal"
SOURCE = Path(__file__).resolve().parent / "skills" / NAME


def destination_root(value: str | None) -> Path:
    if value:
        return Path(value).expanduser()
    if value := os.environ.get("AI_SKILLS_DIR"):
        return Path(value).expanduser()
    if value := os.environ.get("CODEX_HOME"):
        return Path(value).expanduser() / "skills"
    raise SystemExit("Set --dest, AI_SKILLS_DIR, or CODEX_HOME.")


def install(root: Path) -> Path:
    if not (SOURCE / "SKILL.md").is_file():
        raise SystemExit(f"Invalid repository: missing {SOURCE / 'SKILL.md'}")
    target = root.resolve() / NAME
    if target.exists():
        raise SystemExit(f"Already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE, target)
    if not (target / "SKILL.md").is_file():
        shutil.rmtree(target, ignore_errors=True)
        raise SystemExit("Installation verification failed.")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", help="Parent directory that stores AI skills")
    args = parser.parse_args()
    print(f"Installed: {install(destination_root(args.dest))}")


if __name__ == "__main__":
    main()
