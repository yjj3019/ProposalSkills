#!/usr/bin/env python3
"""Install a proposal skill from this repository into an AI skill directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import warnings
from pathlib import Path, PurePosixPath
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


# Per-host personal skill directories follow official tool path conventions.
# A host is installed only if its parent directory (such as ~/.claude) exists under home.
# ~/.agents/skills follows the AGENTS.md convention and is shared by Codex and Grok.
HOSTS: list[tuple[str, str, str]] = [
    # (display name, home subdirectory used for detection, skill directory)
    ("Claude Code", ".claude", ".claude/skills"),
    ("Codex CLI", ".codex", CODEX_RECOMMENDED_SKILLS),
    ("Grok", ".grok", ".grok/skills"),
    ("AGENTS.md 호환(공용)", ".agents", CODEX_RECOMMENDED_SKILLS),
]
# Default shared installation path when no host is detected.
FALLBACK_SKILLS_DIR = CODEX_RECOMMENDED_SKILLS


def detect_targets(home: Path | None = None) -> list[tuple[str, Path]]:
    """Find skill directories for AI CLIs installed on this computer; return (display name, path) pairs."""
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


# Caches and the skills' own test_*.py files are never installed.
COPY_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", "test_*.py")
CACHE_PARTS = frozenset({"__pycache__", ".pytest_cache", ".git"})
# A source tree without Git metadata (an extracted release) can only be filtered by file type.
RELEASE_SUFFIXES = frozenset({".py", ".md", ".json", ".yaml", ".yml", ".txt"})
RELEASE_NAMES = frozenset({".gitkeep"})
# Records what an install wrote, so an update removes only files it owns and never a user's file.
MANIFEST_NAME = ".install-manifest.json"


def _is_cache(relative: Path) -> bool:
    return bool(CACHE_PARTS.intersection(relative.parts)) or relative.suffix in {".pyc", ".pyo"}


def _git_paths(root: Path, *options: str) -> list[str]:
    done = subprocess.run(["git", "-C", str(root), "ls-files", "-z", *options, "--", "skills"],
                          capture_output=True, timeout=60)
    if done.returncode != 0:
        raise RuntimeError("git ls-files failed")
    return [os.fsdecode(item).replace("\\", "/") for item in done.stdout.split(b"\0") if item]


def release_files(root: Path, *, require_git: bool = False) -> tuple[list[Path], list[str]]:
    """Return (files that may ship, local files that must not) under root/skills.

    Proposal work leaves customer material near the skills, so a checkout ships only what Git tracks.
    Without Git metadata only known source file types ship. require_git refuses to guess for a checkout.
    """
    skills = root / "skills"
    if not skills.is_dir():
        return [], []
    if (root / ".git").exists():
        try:
            tracked = _git_paths(root, "--cached")
            local = _git_paths(root, "--others", "--exclude-standard")
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            if require_git:
                raise ValueError("Cannot list tracked files with git; refusing to package this checkout") from exc
        else:
            return ([root / item for item in sorted(tracked) if not _is_cache(Path(item))],
                    sorted(item for item in local if not _is_cache(Path(item))))
    ship: list[Path] = []
    refused: list[str] = []
    for path in sorted(p for p in skills.rglob("*") if p.is_file()):
        relative = path.relative_to(root)
        if _is_cache(relative):
            continue
        if path.suffix.lower() in RELEASE_SUFFIXES or path.name in RELEASE_NAMES:
            ship.append(path)
        else:
            refused.append(relative.as_posix())
    return ship, refused


def skill_release(name: str) -> tuple[list[Path], list[str]]:
    """Paths relative to one skill that are installed from it, and that skill's refused local files."""
    root = SKILLS_ROOT.parent
    prefix = f"skills/{name}/"
    files, refused = release_files(root)
    source = SKILLS_ROOT / name
    relative = [path.relative_to(source) for path in files
                if path.is_relative_to(source) and path.is_file() and not path.name.startswith("test_")]
    return relative, [item[len(prefix):] for item in refused if item.startswith(prefix)]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _release_version() -> str | None:
    try:
        version = json.loads((SKILLS_ROOT.parent / "plugin.json").read_text(encoding="utf-8-sig")).get("version")
    except (OSError, ValueError, AttributeError):
        return None
    return version if isinstance(version, str) else None


def read_manifest(target: Path) -> dict[str, str]:
    """Files a previous install recorded as its own. An unreadable manifest owns nothing."""
    path = target / MANIFEST_NAME
    if path.is_symlink() or not path.is_file():
        return {}
    try:
        files = json.loads(path.read_text(encoding="utf-8")).get("files")
    except (OSError, ValueError, AttributeError):
        return {}
    if not isinstance(files, dict):
        return {}
    return {k: v for k, v in files.items() if isinstance(k, str) and isinstance(v, str)}


def _owned_path(target: Path, relative: str) -> Path | None:
    """Resolve a manifest entry only when it stays inside the install without passing through a link."""
    parts = PurePosixPath(relative).parts
    if not parts or PurePosixPath(relative).is_absolute() or ".." in parts or any(":" in p or "\\" in p for p in parts):
        return None
    path = target
    for part in parts:
        path = path / part
        if path.is_symlink():
            return None
    return path


def _prune_removed(target: Path, previous: dict[str, str], current: dict[str, str]) -> list[str]:
    """Delete files an earlier release installed and this one dropped, unless the user changed them."""
    kept: list[str] = []
    for relative, digest in sorted(previous.items()):
        if relative in current:
            continue
        path = _owned_path(target, relative)
        if path is None or not path.is_file():
            continue
        if _sha256(path) != digest:
            kept.append(relative)
            continue
        path.unlink()
        parent = path.parent
        while parent != target and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent
    return kept


def outdated_files(target: Path) -> list[str]:
    """Released files that are missing from an install or differ from this source."""
    released, _ = skill_release(target.name)
    source = SKILLS_ROOT / target.name
    return [relative.as_posix() for relative in released
            if not (target / relative).is_file() or _sha256(target / relative) != _sha256(source / relative)]


def install(root: Path, name: str = DEFAULT_NAME, force: bool = False) -> Path:
    # Allow one path component to prevent names such as '../..' from escaping dest.
    if name not in available_skills() or Path(name).name != name:
        raise SystemExit(
            f"Unknown skill '{name}'. Available: {', '.join(available_skills())}")
    source = SKILLS_ROOT / name
    root = root.resolve()
    if root.exists() and not root.is_dir():
        raise SystemExit(f"--dest is not a directory: {root}")
    target = root / name
    if target.is_symlink() or (target.exists() and not target.is_dir()):
        raise SystemExit(f"Skill target is not a regular directory: {target}")
    if target.exists():
        if (target / "SKILL.md").is_file() and not force:
            raise SystemExit(f"Already exists: {target}")
        if not force and any(target.iterdir()):
            # Do not delete user data because SKILL.md is missing; the installer cannot distinguish
            # an interrupted installation directory from a user-created folder.
            raise SystemExit(
                f"Not empty and not a skill install: {target} — "
                "내용을 확인한 뒤 옮기거나 --force로 스킬 파일을 갱신한다")
    # Stop on links in update paths rather than overwriting external files.
    for path in source.rglob("*"):
        if (target / path.relative_to(source)).is_symlink():
            raise SystemExit(f"Skill update path is a symlink: {path.relative_to(source)}")
    if (target / MANIFEST_NAME).is_symlink():
        raise SystemExit(f"Install manifest is a symlink: {target / MANIFEST_NAME}")
    previous = read_manifest(target)
    # Update only released source files; do not delete separate user files or copy local ones.
    released, refused = skill_release(name)
    for relative in released:
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, destination)
    if refused:
        shown = ", ".join(refused[:5]) + (" ..." if len(refused) > 5 else "")
        print(f"NOTE: {name}: {len(refused)} local file(s) not installed: {shown}", file=sys.stderr)
    if not (target / "SKILL.md").is_file():
        raise SystemExit("Installation verification failed.")
    current = {relative.as_posix(): _sha256(target / relative) for relative in released}
    kept = _prune_removed(target, previous, current)
    if kept:
        shown = ", ".join(kept[:5]) + (" ..." if len(kept) > 5 else "")
        print(f"NOTE: {name}: kept {len(kept)} file(s) removed upstream but edited locally: {shown}", file=sys.stderr)
    manifest = {"schema": 1, "version": _release_version(), "files": current}
    (target / MANIFEST_NAME).write_text(json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                                        encoding="utf-8")
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
        elif value.lower() in {"true", "false"}:
            parent[key] = value.lower() == "true"
        elif value.lower() == "null" or value == "~":
            parent[key] = None
        elif value.lower() in {".nan", ".inf", "+.inf", "-.inf"}:
            parent[key] = float(value.lower().replace(".inf", "inf").replace(".nan", "nan"))
        elif value.startswith(("!", "&", "*", "|", ">")):
            raise ValueError(f"Unsupported YAML syntax for {key}; quote a single-line string")
        elif re.fullmatch(r"-?\d+", value):
            parent[key] = int(value)
        elif re.fullmatch(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?", value):
            parent[key] = float(value)
        elif value.startswith(("[", "{")):
            # JSON flow values are unambiguous. Other YAML flow syntax is outside
            # this dependency-free subset; never silently turn it into a string.
            try:
                parent[key] = json.loads(value)
            except ValueError as exc:
                raise ValueError(f"Unsupported YAML flow value for {key}; use block syntax or quote a string") from exc
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
    if policy is None and "policy" not in meta:
        return True
    if not isinstance(policy, dict):
        raise ValueError("policy must be an object")
    if "allow_implicit_invocation" not in policy:
        return True
    value = policy["allow_implicit_invocation"]
    if not isinstance(value, bool):
        raise ValueError("policy.allow_implicit_invocation must be a boolean")
    return value


def skill_schema_problems(skill_dir: Path, *, skills_root: Path | None = None,
                          strict_common: bool = False) -> list[str]:
    """Validate skill package schema (source tree or install). Model-neutral routing rules."""
    problems: list[str] = []
    name = skill_dir.name
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        problems.append(f"{name}: SKILL.md 없음")
        return problems

    body = skill_md.read_text(encoding="utf-8")
    try:
        fm = parse_frontmatter(body)
    except ValueError as exc:
        return [f"{name}: {exc}"]
    if not isinstance(fm.get("name"), str) or not fm["name"].strip():
        problems.append(f"{name}: frontmatter name 없음")
    elif fm["name"] != name:
        problems.append(f"{name}: frontmatter name={fm['name']!r} != dir")
    if not isinstance(fm.get("description"), str) or not fm["description"].strip():
        problems.append(f"{name}: frontmatter description 없음")

    # Host extensions remain valid. Strict common checks are an explicit profile,
    # not a reason to remove Claude's explicit-only invocation protection.
    if strict_common:
        fields = {"name", "description", "license", "compatibility", "metadata", "allowed-tools",
                  "disable-model-invocation"}
        for key in sorted(fm.keys() - fields):
            problems.append(f"{name}: unsupported frontmatter field: {key}")
    disable = fm.get("disable-model-invocation", False)
    if not isinstance(disable, bool):
        problems.append(f"{name}: disable-model-invocation must be a boolean")
    try:
        openai = load_openai_yaml(skill_dir)
    except ValueError as exc:
        return problems + [f"{name}: {exc}"]
    if openai is None:
        problems.append(f"{name}: agents/openai.yaml 없음")
    elif "interface" not in openai:
        problems.append(f"{name}: openai.yaml interface 없음")
    elif not isinstance(openai["interface"], dict):
        problems.append(f"{name}: openai.yaml interface must be an object")
    else:
        try:
            implicit = allow_implicit_invocation(openai)
        except ValueError as exc:
            problems.append(f"{name}: {exc}")
            implicit = None
        if name in SIBLINGS:
            if implicit is True:
                problems.append(
                    f"{name}: sibling must set policy.allow_implicit_invocation: false")
            if disable is not True:
                problems.append(
                    f"{name}: sibling must set disable-model-invocation: true")
        elif name == FLAGSHIP:
            if implicit is False:
                problems.append(
                    f"{name}: flagship must allow implicit invocation "
                    "(omit policy or allow_implicit_invocation: true)")
            if disable is True:
                problems.append(
                    f"{name}: flagship must NOT set disable-model-invocation")

    # Packaged dependencies must exist in the repository skills/ tree.
    for dep in DEPS.get(name, []):
        if not ((skills_root or SKILLS_ROOT) / dep / "SKILL.md").is_file():
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


def verify(target: Path, *, require_coinstall: bool = True) -> list[str]:
    """Check that the installation is usable; return problems (an empty list means healthy)."""
    problems: list[str] = []
    if not (target / "SKILL.md").is_file():
        problems.append(f"{target.name}: SKILL.md 없음")
        return problems
    released, _ = skill_release(target.name)
    for relative in released:
        if relative.parent.as_posix() == "scripts" and relative.suffix == ".py" \
                and not (target / relative).is_file():
            problems.append(f"{target.name}: scripts/{relative.name} 누락")
    for relative in released:
        if relative.parent.as_posix() == "references" and relative.suffix == ".md" \
                and not (target / relative).is_file():
            problems.append(f"{target.name}: references/{relative.name} 누락")
    problems.extend(skill_schema_problems(target))
    if require_coinstall:
        problems.extend(coinstall_problems(target))
    return problems


def _utf8_console() -> None:
    """Force UTF-8 console output to prevent UnicodeEncodeError for Korean and em dashes on code pages such as cp949. Silently continue if reconfiguration is unavailable."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def install_all(root: Path, names: list[str], force: bool) -> list[str]:
    """Install multiple skills in one target directory and produce readable result lines."""
    lines: list[str] = []
    # Reject invalid source metadata before touching an installation.
    for name in names:
        problems = skill_schema_problems(SKILLS_ROOT / name)
        if problems:
            raise SystemExit("Invalid source metadata: " + "; ".join(problems))
    installed: list[tuple[Path, bool]] = []
    for name in names:
        try:
            target = install(root, name, force=force)
        except SystemExit as exc:
            if str(exc).startswith("Already exists:"):
                installed.append((root.resolve() / name, True))
                continue
            raise
        installed.append((target, False))
    # Validate after copying all siblings, including dependencies of existing installations.
    for target, skipped in installed:
        problems = verify(target)
        if problems:
            lines.append(f"  Installed with problems: {target} — {'; '.join(problems)}")
            continue
        stale = outdated_files(target) if skipped else []
        if stale:
            lines.append(f"  Skip (outdated): {target} — {len(stale)} file(s) differ from this release; "
                         "rerun with --force to update")
        else:
            lines.append(f"  {'Skip (exists)' if skipped else 'Installed'}: {target}")
    if any("Installed with problems:" in line for line in lines):
        raise SystemExit("\n".join(lines))
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", help="Parent directory that stores AI skills")
    parser.add_argument(
        "--auto", action="store_true",
        help="Find installed AI CLIs and install into each skill directory (fall back to ~/.agents/skills). The recommended Codex path is ~/.agents/skills")
    parser.add_argument(
        "--list-targets", action="store_true",
        help="Print detected target directories without installing")
    parser.add_argument(
        "--name", default=DEFAULT_NAME,
        help=f"Skill to install (default: {DEFAULT_NAME}). "
             f"Available: {', '.join(available_skills())}")
    parser.add_argument("--all", action="store_true", help="Install every skill")
    parser.add_argument(
        "--force", action="store_true",
        help="Update packaged files in an existing installation; preserve extra files (default: skip)")
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

    # --auto installs to every detected host. All three skills are the default because the flagship
    # needs sibling gates; partial installation breaks the unified_gate path.
    if args.auto:
        # Without --name, install all three skills. Installing only the flagship prevents unified_gate
        # from locating sibling gates.
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
    for line in install_all(root, resolve_names(args.name, args.all,
                                               args.with_deps or args.name == FLAGSHIP), args.force):
        print(line.strip())


if __name__ == "__main__":
    main()
