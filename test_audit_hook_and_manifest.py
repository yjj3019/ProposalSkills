"""Regression tests for the repository audit: shell parsing in the hook guard and the install manifest."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import hook_guard_bash as hook
import install_skill


class HookParsingTests(unittest.TestCase):
    DENIED = (
        "echo ok & rm -rf /", "(rm -rf /)", "if true; then rm -rf /; fi", "for i in 1; do rm -rf ~; done", "! rm -rf /",
        "while true; do git reset --hard; done", "case x in a) rm -rf /;; esac", "echo $(rm -rf /)",
        'echo "$(rm -rf /)"', "echo `rm -rf /`", "cat <(rm -rf /)", "ls # note\nrm -rf /", "rm -rf / > out.log",
        "git push -d origin main", "git push --forc origin main", "git push --del origin main", "git push --mirr",
        "git reset --har", "git clean --forc", "git checkout -f", "git checkout --force main", "git checkout -- :/",
        "git restore :/", "git switch -f main", "git switch --discard-changes main", "git branch -d -f topic",
        "bash -lc 'rm -rf /'", "sh -ec 'git reset --hard'", "sh -e -c 'rm -rf /'",
    )
    ALLOWED = (
        "mv notes.txt .", "mv ../a.txt ./", "rm -rf ./build", "git push origin main", "git push -u origin topic",
        "git checkout main", "git switch topic", "git branch -d topic", "echo 'rm -rf /'", "echo 'a; rm -rf /'",
        "echo '$(rm -rf /)'", 'echo "a & b"', "echo $(date)", "ls 2>&1 | head", "python x.py > out.log 2>&1",
        "(cd build && ls)", "if test -f a; then echo yes; fi", "bash -lc 'ls'", "git log --format='%h; %s'",
    )

    def test_commands_hidden_by_shell_syntax_are_denied(self):
        for command in self.DENIED:
            with self.subTest(command=command):
                self.assertIsNotNone(hook.deny_reason(command))

    def test_look_alikes_stay_allowed(self):
        for command in self.ALLOWED:
            with self.subTest(command=command):
                self.assertIsNone(hook.deny_reason(command))

    def test_moving_a_broad_folder_is_still_denied(self):
        for command in ("mv . /tmp/x", "mv / /tmp", "mv a /etc"):
            with self.subTest(command=command):
                self.assertIsNotNone(hook.deny_reason(command))

    def test_extremely_nested_input_fails_closed(self):
        payload = json.dumps({"tool_input": {"command": "$(" * 3000 + "ls" + ")" * 3000}})
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(hook.main(io.StringIO(payload)), 2)


class InstallManifestTests(unittest.TestCase):
    NAME = "create-winning-proposal"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.target = install_skill.install(self.root, self.NAME)
        self.manifest = self.target / install_skill.MANIFEST_NAME

    def record(self, relative, text):
        path = self.target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        data["files"][relative] = install_skill._sha256(path)
        self.manifest.write_text(json.dumps(data), encoding="utf-8")
        return path

    def update(self):
        with contextlib.redirect_stderr(io.StringIO()) as err:
            install_skill.install(self.root, self.NAME, force=True)
        return err.getvalue()

    def test_manifest_records_every_installed_file(self):
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.assertEqual(data["schema"], 1)
        self.assertIn("SKILL.md", data["files"])
        self.assertEqual(data["files"]["SKILL.md"], install_skill._sha256(self.target / "SKILL.md"))

    def test_file_dropped_upstream_is_removed_with_its_empty_folder(self):
        old = self.record("retired/old_gate.py", "print('old')\n")
        self.update()
        self.assertFalse(old.exists())
        self.assertFalse(old.parent.exists())

    def test_edited_file_dropped_upstream_is_kept_and_reported(self):
        old = self.record("scripts/old_gate.py", "print('old')\n")
        old.write_text("print('edited')\n", encoding="utf-8")
        self.assertIn("scripts/old_gate.py", self.update())
        self.assertTrue(old.exists())

    def test_unrecorded_user_file_is_never_removed(self):
        keep = self.target / "scripts/my_notes.py"
        keep.write_text("x = 1\n", encoding="utf-8")
        self.update()
        self.assertTrue(keep.exists())

    def test_manifest_entries_cannot_reach_outside_the_install(self):
        outside = self.root / "outside.txt"
        outside.write_text("synthetic\n", encoding="utf-8")
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        digest = install_skill._sha256(outside)
        data["files"].update({"../outside.txt": digest, str(outside): digest, str(outside).replace("\\", "/"): digest})
        self.manifest.write_text(json.dumps(data), encoding="utf-8")
        self.update()
        self.assertTrue(outside.exists())

    def test_corrupt_manifest_owns_nothing(self):
        keep = self.target / "scripts/my_notes.py"
        keep.write_text("x = 1\n", encoding="utf-8")
        self.manifest.write_text("{", encoding="utf-8")
        self.update()
        self.assertTrue(keep.exists())
        self.assertIn("files", json.loads(self.manifest.read_text(encoding="utf-8")))

    def test_outdated_install_is_not_reported_as_current(self):
        lines = install_skill.install_all(self.root, [self.NAME], False)
        self.assertIn("Skip (exists)", lines[0])
        gate = self.target / "scripts/proposal_gate.py"
        gate.write_text("# older release\n" + gate.read_text(encoding="utf-8"), encoding="utf-8")
        lines = install_skill.install_all(self.root, [self.NAME], False)
        self.assertIn("Skip (outdated)", lines[0])
        self.assertIn("--force", lines[0])
        install_skill.install_all(self.root, [self.NAME], True)
        self.assertEqual(install_skill.outdated_files(self.target), [])

    def test_symlinked_manifest_is_refused(self):
        # Simulated so the rule also runs on Windows runners, which cannot create symlinks.
        before = self.manifest.read_bytes()
        manifest_name = install_skill.MANIFEST_NAME
        with patch.object(Path, "is_symlink", lambda path: path.name == manifest_name):
            with self.assertRaisesRegex(SystemExit, "manifest is a symlink"):
                install_skill.install(self.root, self.NAME, force=True)
        self.assertEqual(self.manifest.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
