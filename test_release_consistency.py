"""Release facts must agree wherever they are written: manifests, the LICENSE file, the packaged archive,
and the version quoted in the marketplace guide. A stale claim here ships a wrong version or license."""
from __future__ import annotations

import json
import re
import tempfile
import unittest
import zipfile
from pathlib import Path

import package_plugin

REPO = Path(__file__).resolve().parent
MANIFESTS = ("plugin.json", ".claude-plugin/plugin.json", ".codex-plugin/plugin.json")


def load(relative: str) -> dict:
    return json.loads((REPO / relative).read_text(encoding="utf-8-sig"))


class ReleaseConsistencyTests(unittest.TestCase):
    def test_every_manifest_declares_the_same_license_as_the_license_file(self):
        licenses = {relative: load(relative).get("license") for relative in MANIFESTS}
        self.assertEqual(set(licenses.values()), {"MIT"}, licenses)
        self.assertTrue((REPO / "LICENSE").read_text(encoding="utf-8").startswith("MIT License"))

    def test_marketplace_guide_quotes_the_current_version(self):
        version = load("plugin.json")["version"]
        guide = (REPO / "references" / "marketplace-management.md").read_text(encoding="utf-8")
        current = re.search(r"current local candidate version is `([^`]+)`", guide)
        self.assertIsNotNone(current, "the guide must state the current candidate version")
        self.assertEqual(current.group(1), version)
        for quoted in re.findall(r"dist/proposal-skills-([0-9][^ \"'`]*)\.zip", guide):
            self.assertEqual(quoted, version, "package example names a different version")

    def test_archive_ships_the_license(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = package_plugin.build_archive(Path(tmp) / "pkg.zip")
            with zipfile.ZipFile(archive) as z:
                names = set(z.namelist())
        self.assertIn("LICENSE", names)
        self.assertNotIn(".mailmap", names)  # author-identity mapping is repository metadata, not payload

    def test_readmes_point_to_the_license(self):
        for readme in ("README.md", "README.en.md"):
            self.assertIn("(LICENSE)", (REPO / readme).read_text(encoding="utf-8"), readme)


if __name__ == "__main__":
    unittest.main()
