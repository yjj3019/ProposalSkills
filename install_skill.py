#!/usr/bin/env python3
"""Install a proposal skill from this repository into an AI skill directory."""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parent / "skills"
DEFAULT_NAME = "create-best-proposal"
# Legacy import target for tests that expect the governance package tree.
SOURCE = SKILLS_ROOT / "create-winning-proposal"
# Flagship needs sibling gates for full unified_gate path (S6).
DEPS: dict[str, list[str]] = {
    "create-best-proposal": [
        "create-proposal-document",
        "create-winning-proposal",
    ],
}


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


def resolve_names(name: str, all_flag: bool, with_deps: bool) -> list[str]:
    if all_flag:
        return available_skills()
    names = [name]
    if with_deps:
        for dep in DEPS.get(name, []):
            if dep not in names:
                names.append(dep)
    return names


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", help="Parent directory that stores AI skills")
    parser.add_argument(
        "--name", default=DEFAULT_NAME,
        help=f"Skill to install (default: {DEFAULT_NAME}). "
             f"Available: {', '.join(available_skills())}")
    parser.add_argument("--all", action="store_true", help="Install every skill")
    parser.add_argument(
        "--with-deps", action="store_true",
        help="Also install sibling skills required by the named skill "
             "(create-best-proposal → document + winning gates)")
    args = parser.parse_args()
    root = destination_root(args.dest)
    names = resolve_names(args.name, args.all, args.with_deps)
    for name in names:
        try:
            print(f"Installed: {install(root, name)}")
        except SystemExit as exc:
            msg = str(exc)
            if msg.startswith("Already exists:"):
                print(f"Skip (exists): {root.resolve() / name}")
            else:
                raise


if __name__ == "__main__":
    main()
