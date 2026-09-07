#!/usr/bin/env python3
"""Install a proposal skill from this repository into an AI skill directory."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import warnings
from pathlib import Path
from typing import Any

SKILLS_ROOT = Path(__file__).resolve().parent / "skills"
DEFAULT_NAME = "create-best-proposal"
FLAGSHIP = "create-best-proposal"
SIBLINGS = frozenset({"create-proposal-document", "create-winning-proposal"})
# Legacy import target for tests that expect the governance package tree.
SOURCE = SKILLS_ROOT / "create-winning-proposal"
# Flagship needs sibling gates for full unified_gate path (S6).
DEPS: dict[str, list[str]] = {
    "create-best-proposal": [
        "create-proposal-document",
        "create-winning-proposal",
    ],
}

# Codex recommended personal skills path (AGENTS.md / multi-host convention).
# $CODEX_HOME/skills is still loaded by Codex as deprecated compat — prefer this.
CODEX_RECOMMENDED_SKILLS = ".agents/skills"
CODEX_HOME_LEGACY_MSG = (
    "CODEX_HOME/skills is a legacy Codex compat path; preferred install location "
    f"is ~/{CODEX_RECOMMENDED_SKILLS} (or set AI_SKILLS_DIR / --dest)."
)


def _warn_codex_home_legacy() -> None:
    warnings.warn(CODEX_HOME_LEGACY_MSG, UserWarning, stacklevel=3)
    print(f"WARNING: {CODEX_HOME_LEGACY_MSG}", file=sys.stderr)


def destination_root(value: str | None) -> Path:
    """Resolve a single install root.

    Priority: explicit --dest → AI_SKILLS_DIR → (legacy) CODEX_HOME/skills.
    Do not treat CODEX_HOME as the recommended default; warn when it is used.
    """
    if value:
        return Path(value).expanduser()
    if env := os.environ.get("AI_SKILLS_DIR"):
        return Path(env).expanduser()
    if env := os.environ.get("CODEX_HOME"):
        _warn_codex_home_legacy()
        return Path(env).expanduser() / "skills"
    raise SystemExit(
        "Set --dest or AI_SKILLS_DIR (recommended), or use --auto. "
        "CODEX_HOME/skills remains a legacy fallback only."
    )


# 호스트별 개인 스킬 디렉터리. 경로 규약은 각 도구의 공식 문서 기준이며,
# 홈 아래 상위 디렉터리(~/.claude 등)가 이미 있을 때만 "설치된 호스트"로 본다.
# ~/.agents/skills는 AGENTS.md 호환 규약이라 Codex·Grok이 함께 읽는다.
HOSTS: list[tuple[str, str, str]] = [
    # (표시명, 존재 여부를 판단할 홈 하위 디렉터리, 스킬 디렉터리)
    ("Claude Code", ".claude", ".claude/skills"),
    ("Codex CLI", ".codex", CODEX_RECOMMENDED_SKILLS),
    ("Grok", ".grok", ".grok/skills"),
    ("AGENTS.md 호환(공용)", ".agents", CODEX_RECOMMENDED_SKILLS),
]
# 아무 호스트도 없을 때의 기본 설치 위치 — 여러 CLI가 공통으로 읽는 경로.
FALLBACK_SKILLS_DIR = CODEX_RECOMMENDED_SKILLS


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
    if raw := os.environ.get("AI_SKILLS_DIR"):
        target = Path(raw).expanduser()
        if target not in seen:
            seen.add(target)
            found.append(("$AI_SKILLS_DIR", target))
    if raw := os.environ.get("CODEX_HOME"):
        # Legacy compat: Codex still loads $CODEX_HOME/skills, but recommend ~/.agents/skills.
        _warn_codex_home_legacy()
        target = Path(raw).expanduser() / "skills"
        if target not in seen:
            seen.add(target)
            found.append(("$CODEX_HOME/skills (legacy)", target))
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


_FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)


def parse_frontmatter(text: str) -> dict[str, Any]:
    """Parse SKILL.md YAML frontmatter (flat keys + booleans/strings)."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}
    return _parse_simple_yaml(match.group(1))


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    """Minimal indented YAML subset for skill metadata (no PyYAML dependency)."""
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if ":" not in raw:
            continue
        key, _, rest = raw.lstrip(" ").partition(":")
        key = key.strip()
        value = rest.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if value == "":
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
            continue
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            parent[key] = value[1:-1]
        elif value in {"true", "false"}:
            parent[key] = value == "true"
        elif re.fullmatch(r"-?\d+", value):
            parent[key] = int(value)
        else:
            parent[key] = value
    return root


def load_openai_yaml(skill_dir: Path) -> dict[str, Any] | None:
    path = skill_dir / "agents" / "openai.yaml"
    if not path.is_file():
        return None
    return _parse_simple_yaml(path.read_text(encoding="utf-8"))


def allow_implicit_invocation(meta: dict[str, Any] | None) -> bool:
    """Codex default is true when policy is omitted."""
    if not meta:
        return True
    policy = meta.get("policy")
    if not isinstance(policy, dict):
        return True
    if "allow_implicit_invocation" not in policy:
        return True
    return bool(policy["allow_implicit_invocation"])


def skill_schema_problems(skill_dir: Path) -> list[str]:
    """Validate skill package schema (source tree or install). Model-neutral routing rules."""
    problems: list[str] = []
    name = skill_dir.name
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        problems.append(f"{name}: SKILL.md 없음")
        return problems

    body = skill_md.read_text(encoding="utf-8")
    fm = parse_frontmatter(body)
    if not fm.get("name"):
        problems.append(f"{name}: frontmatter name 없음")
    elif fm["name"] != name:
        problems.append(f"{name}: frontmatter name={fm['name']!r} != dir")
    if not fm.get("description"):
        problems.append(f"{name}: frontmatter description 없음")

    disable = bool(fm.get("disable-model-invocation", False))
    openai = load_openai_yaml(skill_dir)
    if openai is None:
        problems.append(f"{name}: agents/openai.yaml 없음")
    elif "interface" not in openai:
        problems.append(f"{name}: openai.yaml interface 없음")
    else:
        implicit = allow_implicit_invocation(openai)
        if name in SIBLINGS:
            if implicit:
                problems.append(
                    f"{name}: sibling must set policy.allow_implicit_invocation: false")
            if not disable:
                problems.append(
                    f"{name}: sibling must set disable-model-invocation: true")
        elif name == FLAGSHIP:
            if not implicit:
                problems.append(
                    f"{name}: flagship must allow implicit invocation "
                    "(omit policy or allow_implicit_invocation: true)")
            if disable:
                problems.append(
                    f"{name}: flagship must NOT set disable-model-invocation")
            if "policy" in openai and openai["policy"].get(
                    "allow_implicit_invocation") is False:
                problems.append(
                    f"{name}: flagship must not disable implicit invocation")

    # Packaged dependencies must exist in the repository skills/ tree.
    for dep in DEPS.get(name, []):
        if not (SKILLS_ROOT / dep / "SKILL.md").is_file():
            problems.append(f"{name}: packaged dependency missing: {dep}")

    return problems


def coinstall_problems(target: Path) -> list[str]:
    """Flagship installs need sibling skills beside them for unified_gate."""
    problems: list[str] = []
    for dep in DEPS.get(target.name, []):
        if not (target.parent / dep / "SKILL.md").is_file():
            problems.append(
                f"{target.name}: co-install missing: {dep} "
                "(install with --all or --with-deps)")
    return problems


def verify(target: Path, *, require_coinstall: bool = False) -> list[str]:
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
    problems.extend(skill_schema_problems(target))
    if require_coinstall:
        problems.extend(coinstall_problems(target))
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
             "(찾지 못하면 ~/.agents/skills 사용). Codex 권장 경로는 ~/.agents/skills")
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
