#!/usr/bin/env python3
"""Install a proposal skill from this repository into an AI skill directory."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
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
    raise SystemExit("Set --dest, AI_SKILLS_DIR, or CODEX_HOME (or use --auto).")


# 호스트별 개인 스킬 디렉터리. 경로 규약은 각 도구의 공식 문서 기준이며,
# 홈 아래 상위 디렉터리(~/.claude 등)가 이미 있을 때만 "설치된 호스트"로 본다.
# ~/.agents/skills는 AGENTS.md 호환 규약이라 Codex·Grok이 함께 읽는다.
HOSTS: list[tuple[str, str, str]] = [
    # (표시명, 존재 여부를 판단할 홈 하위 디렉터리, 스킬 디렉터리)
    ("Claude Code", ".claude", ".claude/skills"),
    ("Codex CLI", ".codex", ".agents/skills"),
    ("Grok", ".grok", ".grok/skills"),
    ("AGENTS.md 호환(공용)", ".agents", ".agents/skills"),
]
# 아무 호스트도 없을 때의 기본 설치 위치 — 여러 CLI가 공통으로 읽는 경로.
FALLBACK_SKILLS_DIR = ".agents/skills"


def detect_targets(home: Path | None = None) -> list[tuple[str, Path]]:
    """이 컴퓨터에 설치된 AI CLI의 스킬 디렉터리를 찾는다. (표시명, 경로) 목록."""
    home = home or Path.home()
    found: list[tuple[str, Path]] = []
    seen: set[Path] = set()
    for label, marker, skills_dir in HOSTS:
        if not (home / marker).is_dir():
            continue
        target = home / skills_dir
        if target not in seen:
            seen.add(target)
            found.append((label, target))
    for env in ("AI_SKILLS_DIR", "CODEX_HOME"):
        raw = os.environ.get(env)
        if not raw:
            continue
        target = Path(raw).expanduser()
        if env == "CODEX_HOME":
            target = target / "skills"
        if target not in seen:
            seen.add(target)
            found.append((f"${env}", target))
    return found


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
        if not force and any(target.iterdir()):
            # SKILL.md가 없다고 사용자 자료를 지우지 않는다. 설치 중단으로 남은
            # 디렉터리인지 사용자가 만든 폴더인지 설치기는 구분할 수 없다.
            raise SystemExit(
                f"Not empty and not a skill install: {target} — "
                "내용을 확인한 뒤 옮기거나 --force로 교체한다(교체는 이 폴더를 지운다)")
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


def verify(target: Path) -> list[str]:
    """설치본이 실제로 동작 가능한 상태인지 확인한다. 문제 목록을 반환(빈 목록=정상)."""
    problems: list[str] = []
    if not (target / "SKILL.md").is_file():
        problems.append(f"{target.name}: SKILL.md 없음")
        return problems
    source = SKILLS_ROOT / target.name
    for script in sorted(source.glob("scripts/*.py")):
        if script.name.startswith("test_"):
            continue
        if not (target / "scripts" / script.name).is_file():
            problems.append(f"{target.name}: scripts/{script.name} 누락")
    for ref in sorted(source.glob("references/*.md")):
        if not (target / "references" / ref.name).is_file():
            problems.append(f"{target.name}: references/{ref.name} 누락")
    return problems


def _utf8_console() -> None:
    """콘솔을 UTF-8로 고정한다. cp949 같은 기본 코드페이지에서 한글·em dash 출력이
    UnicodeEncodeError로 죽던 문제를 막는다(재설정 불가 환경은 조용히 통과)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def install_all(root: Path, names: list[str], force: bool) -> list[str]:
    """한 대상 디렉터리에 여러 스킬을 설치하고 사람이 읽을 결과 줄을 만든다."""
    lines: list[str] = []
    for name in names:
        try:
            target = install(root, name, force=force)
        except SystemExit as exc:
            if str(exc).startswith("Already exists:"):
                lines.append(f"  Skip (exists): {root.resolve() / name}")
                continue
            raise
        problems = verify(target)
        lines.append(f"  Installed: {target}" if not problems
                     else f"  Installed with problems: {target} — {'; '.join(problems)}")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", help="Parent directory that stores AI skills")
    parser.add_argument(
        "--auto", action="store_true",
        help="이 컴퓨터에 설치된 AI CLI를 찾아 각각의 스킬 디렉터리에 설치한다 "
             "(찾지 못하면 ~/.agents/skills 사용)")
    parser.add_argument(
        "--list-targets", action="store_true",
        help="설치하지 않고 감지된 대상 디렉터리만 출력한다")
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
    _utf8_console()

    if args.list_targets:
        targets = detect_targets()
        if targets:
            for label, path in targets:
                print(f"{label}: {path}")
        else:
            print(f"감지된 AI CLI 없음 — 기본 위치: {Path.home() / FALLBACK_SKILLS_DIR}")
        return

    # --auto: 감지된 모든 호스트에 설치한다. 기본은 세 스킬 전부(플래그십이 형제 게이트를
    # 필요로 하므로, 부분 설치는 unified_gate 경로가 끊긴다).
    if args.auto:
        # --name을 따로 주지 않았으면 세 스킬 전부. 플래그십만 깔면 unified_gate가
        # 형제 게이트를 찾지 못해 경로가 끊긴다.
        explicit = args.name != DEFAULT_NAME
        names = resolve_names(args.name, not explicit or args.all, args.with_deps)
        targets = detect_targets()
        if not targets:
            fallback = Path.home() / FALLBACK_SKILLS_DIR
            print(f"감지된 AI CLI 없음 — 공용 위치에 설치한다: {fallback}")
            targets = [("AGENTS.md 호환(공용)", fallback)]
        for label, root in targets:
            print(f"{label} → {root}")
            for line in install_all(root, names, args.force):
                print(line)
        print(f"\n다음 단계: AI 세션을 새로 시작하고 "
              f"'{names[0]} 스킬로 제안서 작성 시작'이라고 요청한다.")
        return

    root = destination_root(args.dest)
    for line in install_all(root, resolve_names(args.name, args.all, args.with_deps), args.force):
        print(line.strip())


if __name__ == "__main__":
    main()
