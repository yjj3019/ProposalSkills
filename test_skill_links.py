"""Every repository-relative Markdown link inside the skills and references must resolve to a file.

Fenced code is ignored (examples may show paths that do not exist), URLs and anchors are not fetched, and a link
may not escape the repository or be an absolute path.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path
from urllib.parse import unquote

REPO = Path(__file__).resolve().parent
FENCE = re.compile(r"^(`{3,}|~{3,})[^\n]*\n.*?^\1[^\n]*(?:\n|$)", re.M | re.S)
LINK = re.compile(r"\[[^\]\n]*\]\(([^\s()]+)\)")
EXTERNAL = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//|#)", re.I)


def markdown_files() -> list[Path]:
    roots = [REPO / "skills", REPO / "references"]
    top = [REPO / n for n in ("README.md", "README.en.md", "AGENTS.md", "CLAUDE.md")]
    return sorted([p for r in roots for p in r.rglob("*.md") if "__pycache__" not in p.parts] + [p for p in top if p.is_file()])


def broken_links(path: Path) -> list[str]:
    prose = FENCE.sub("", path.read_text(encoding="utf-8").replace("\r\n", "\n"))
    problems = []
    for match in LINK.finditer(prose):
        target = match.group(1)
        if EXTERNAL.match(target):
            continue
        destination = unquote(target.split("#")[0].split("?")[0])
        if not destination:
            continue
        if re.match(r"^[A-Za-z]:[\\/]", destination) or Path(destination).is_absolute():
            problems.append(f"absolute link {target}")
            continue
        resolved = (path.parent / destination).resolve()
        if REPO not in resolved.parents and resolved != REPO:
            problems.append(f"link leaves the repository: {target}")
        elif not resolved.exists():
            problems.append(f"missing target: {target}")
    return problems


class LinkTests(unittest.TestCase):
    def test_relative_links_resolve(self):
        files = markdown_files()
        self.assertGreater(len(files), 10)
        bad = {p.relative_to(REPO).as_posix(): broken_links(p) for p in files}
        bad = {k: v for k, v in bad.items() if v}
        self.assertEqual(bad, {}, "\n".join(f"{k}: {v}" for k, v in bad.items()))

    def test_checker_catches_a_missing_target(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / "a.md"
            doc.write_text("see [x](nope.md)\n```\n[y](also-missing.md)\n```\n", encoding="utf-8")
            global REPO
            saved, REPO = REPO, Path(tmp).resolve()
            try:
                self.assertEqual(broken_links(doc), ["missing target: nope.md"])
            finally:
                REPO = saved


if __name__ == "__main__":
    unittest.main()
