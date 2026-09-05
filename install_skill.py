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


# 배포본에서 제외할 캐시(스킬 내 test_*.py는 설치 후 자가검증용으로 유지한다).
COPY_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")


def install(root: Path, name: str = DEFAULT_NAME, force: bool = False) -> Path:
    # 경로 구성요소 1개만 허용 — '../..' 같은 이름으로 dest 밖에 설치되는 것을 막는다.
    if name not in available_skills() or Path(name).name != name:
        raise SystemExit(
            f"Unknown skill '{name}'. Available: {', '.join(available_skills())}")
    source = SKILLS_ROOT / name
    root = root.resolve()
    if root.exists() and not root.is_dir():
        raise SystemExit(f"--dest is not a directory: {root}")
    target = root / name
    if target.exists():
        if (target / "SKILL.md").is_file() and not force:
            raise SystemExit(f"Already exists: {target}")
        # --force 또는 SKILL.md 없는 빈/불완전 디렉터리 → 교체 설치
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target, ignore=COPY_IGNORE)
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
        "--force", action="store_true",
        help="Replace an existing installation (default: skip if SKILL.md exists)")
    parser.add_argument(
        "--with-deps", action="store_true",
        help="Also install sibling skills required by the named skill "
             "(create-best-proposal → document + winning gates)")
    args = parser.parse_args()
    root = destination_root(args.dest)
    names = resolve_names(args.name, args.all, args.with_deps)
    for name in names:
        try:
            print(f"Installed: {install(root, name, force=args.force)}")
        except SystemExit as exc:
            msg = str(exc)
            if msg.startswith("Already exists:"):
                print(f"Skip (exists): {root.resolve() / name}")
            else:
                raise


if __name__ == "__main__":
    main()
