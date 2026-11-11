#!/usr/bin/env python3
"""Audit skill packages for instruction-level risks and undeclared licensing.

A skill is text that an agent obeys. Two failures matter before a skill is distributed:

1. Injected or unsafe instructions: a line telling the agent to ignore its prior instructions, pipe a
   download into a shell, decode an obfuscated payload, or send secrets somewhere. Every Markdown file
   under a skill is scanned (SKILL.md and references/, because references are loaded on demand).
2. Unclear provenance: each SKILL.md must declare `license:`. If it differs from the repository's root
   license, the skill must ship its own LICENSE/LICENSE.txt so reused third-party content cannot sit in
   the tree with undeclared terms.

Heuristics only: a clean audit means these patterns were absent, not that a skill is safe or that its
content is original. Review remains a human decision.

Exit codes: 0 clean, 1 findings, 2 usage error.

Usage: python skill_audit.py [SKILLS_DIR] [--root-license MIT]
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from install_skill import parse_frontmatter

REPO = Path(__file__).resolve().parent

REJECT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions", re.I), "prompt injection"),
    (re.compile(r"disregard\s+(?:all\s+)?(?:previous|prior|above|your)\s+(?:instructions|rules)", re.I), "prompt injection"),
    (re.compile(r"(?:curl|wget)\b[^\n|]*\|\s*(?:sudo\s+)?(?:ba|z|da)?sh\b", re.I), "download piped to a shell"),
    (re.compile(r"base64\s+(?:-d|--decode)\b", re.I), "obfuscated decode"),
    (re.compile(r"(?:send|upload|post|forward|email)\s+(?:the\s+|your\s+|all\s+)?(?:api[_ -]?keys?|tokens?|secrets?|credentials?|\.env)\b", re.I),
     "secret exfiltration"),
    (re.compile(r"unrestricted\s+(?:shell|network|file)\s+access", re.I), "over-broad permission claim"),
    (re.compile(r"exfiltrat\w+|steal\s+credentials", re.I), "exfiltration intent"),
)

# Lines that quote a pattern in order to forbid or detect it are documentation, not instructions.
NEGATION_CONTEXT = re.compile(
    r"(?:never|do not|don't|must not|forbid|forbidden|reject|block|detect|flag|scan|avoid|금지|하지 않|않는다|차단|탐지|거부)", re.I)


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    rule: str
    text: str


def skill_dirs(skills_root: Path) -> list[Path]:
    return sorted(p for p in skills_root.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()) if skills_root.is_dir() else []


def license_findings(skill: Path, root_license: str) -> list[Finding]:
    skill_md = skill / "SKILL.md"
    try:
        declared = parse_frontmatter(skill_md.read_text(encoding="utf-8")).get("license")
    except ValueError as exc:
        return [Finding(f"{skill.name}/SKILL.md", 1, "frontmatter", str(exc))]
    if not isinstance(declared, str) or not declared.strip():
        return [Finding(f"{skill.name}/SKILL.md", 1, "license-missing",
                        "declare `license:` in the frontmatter (use the repository license or ship a LICENSE file)")]
    if declared.strip() != root_license and not any((skill / n).is_file() for n in ("LICENSE", "LICENSE.txt", "LICENSE.md")):
        return [Finding(f"{skill.name}/SKILL.md", 1, "license-mismatch",
                        f"declares {declared.strip()!r} but the repository is {root_license!r}; add a LICENSE file to the skill")]
    return []


def content_findings(skill: Path, base: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in sorted(skill.rglob("*.md")):
        if path.is_symlink() or "__pycache__" in path.parts:
            continue  # never follow links out of the skill
        rel = path.relative_to(base).as_posix()
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            findings.append(Finding(rel, 0, "unreadable", type(exc).__name__))
            continue
        in_fence = False
        for number, line in enumerate(lines, 1):
            if line.lstrip().startswith(("```", "~~~")):
                in_fence = not in_fence
            for pattern, rule in REJECT_PATTERNS:
                if pattern.search(line) and not NEGATION_CONTEXT.search(line):
                    findings.append(Finding(rel, number, rule, line.strip()[:120] + (" [in code block]" if in_fence else "")))
    return findings


def audit(skills_root: Path, root_license: str) -> list[Finding]:
    findings: list[Finding] = []
    for skill in skill_dirs(skills_root):
        findings += license_findings(skill, root_license)
        findings += content_findings(skill, skills_root)
    return findings


def root_license_id(repo: Path) -> str:
    """SPDX id taken from plugin.json, so it is declared in one place."""
    import json
    try:
        value = json.loads((repo / "plugin.json").read_text(encoding="utf-8-sig")).get("license")
    except (OSError, ValueError):
        value = None
    return value.strip() if isinstance(value, str) and value.strip() else ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("skills_dir", nargs="?", type=Path, default=REPO / "skills")
    parser.add_argument("--root-license", default=None, help="SPDX id of the repository (default: plugin.json license)")
    args = parser.parse_args(argv)
    if not args.skills_dir.is_dir():
        print(f"Not a directory: {args.skills_dir}", file=sys.stderr)
        return 2
    root_license = args.root_license or root_license_id(REPO)
    if not root_license:
        print("Repository license is unknown: set `license` in plugin.json or pass --root-license", file=sys.stderr)
        return 2
    findings = audit(args.skills_dir, root_license)
    for f in findings:
        print(f"{f.path}:{f.line} [{f.rule}] {f.text}")
    print(f"SKILL-AUDIT: {'FINDINGS' if findings else 'CLEAN'} ({len(skill_dirs(args.skills_dir))} skill(s), {len(findings)} finding(s))")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
