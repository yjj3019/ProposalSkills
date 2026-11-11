"""Licensing guardrails: no unrecorded bundled assets, dependencies are listed in the notices, notices ship."""
from __future__ import annotations

import re
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

import package_plugin

REPO = Path(__file__).resolve().parent
TEXT_SUFFIXES = {".py", ".md", ".json", ".yml", ".yaml", ".txt"}
# Extensionless repository metadata. Anything else that is not text must be recorded in THIRD-PARTY-NOTICES.md first.
ALLOWED_OTHER = {".gitignore", ".gitattributes", ".mailmap", "LICENSE", "skills/create-proposal-document/assets/brand-assets/.gitkeep"}
NOTICES = (REPO / "THIRD-PARTY-NOTICES.md").read_text(encoding="utf-8")


def tracked() -> list[str]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=str(REPO), capture_output=True)
    if out.returncode != 0:
        raise unittest.SkipTest("not a git checkout")
    return [n for n in out.stdout.decode("utf-8").split("\0") if n]


class AssetTests(unittest.TestCase):
    def test_no_unrecorded_binary_or_asset_files(self):
        stray = [n for n in tracked() if Path(n).suffix.lower() not in TEXT_SUFFIXES and n not in ALLOWED_OTHER]
        self.assertEqual(stray, [], "record the license in THIRD-PARTY-NOTICES.md, then allow-list: " + ", ".join(stray))

    def test_text_files_contain_no_nul_bytes(self):
        for name in tracked():
            if Path(name).suffix.lower() in TEXT_SUFFIXES and (REPO / name).is_file():
                self.assertNotIn(b"\0", (REPO / name).read_bytes()[:4096], name)


class NoticesTests(unittest.TestCase):
    def test_every_requirement_is_listed(self):
        names = [re.split(r"[<>=!~\s\[]", line.strip(), maxsplit=1)[0]
                 for line in (REPO / "requirements.txt").read_text(encoding="utf-8").splitlines()
                 if line.strip() and not line.lstrip().startswith("#")]
        self.assertTrue(names)
        for name in names:
            self.assertIn(name.lower(), NOTICES.lower(), f"{name} is not listed in THIRD-PARTY-NOTICES.md")

    def test_notices_state_the_repository_license_and_ship_in_the_archive(self):
        self.assertIn("MIT License", NOTICES)
        with tempfile.TemporaryDirectory() as tmp:
            archive = package_plugin.build_archive(Path(tmp) / "pkg.zip")
            with zipfile.ZipFile(archive) as z:
                self.assertIn("THIRD-PARTY-NOTICES.md", z.namelist())

    def test_credited_upstream_projects_match_the_provenance_record(self):
        provenance = (REPO / "references" / "provenance-harness-review-2026-11.md").read_text(encoding="utf-8")
        for repo in re.findall(r"github\.com/([\w.-]+/[\w.-]+)", NOTICES):
            self.assertIn(repo, provenance, f"{repo} credited in the notices but absent from the provenance record")


if __name__ == "__main__":
    unittest.main()
