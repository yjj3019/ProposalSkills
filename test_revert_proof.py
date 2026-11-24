"""revert_proof.py judges a change by running its tests on the code the change started from."""
import contextlib
import io
import os
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

import revert_proof

GIT_ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "test@example.com", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "test@example.com", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}
MODULE_OLD = "def price(x):\n    return x\n"
MODULE_NEW = "def price(x):\n    return x * 2\n"
TEST_NEW = ("import unittest\nimport mod\n\n\nclass T(unittest.TestCase):\n"
            "    def test_new_rule(self):\n        self.assertEqual(mod.price(2), 4)\n\n"
            "    def test_old_rule(self):\n        self.assertEqual(mod.price(0), 0)\n")


def git(repo, *args):
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, env=GIT_ENV)
    assert done.returncode == 0, done.stderr
    return done.stdout


def commit(repo, files, message):
    for name, text in files.items():
        path = Path(repo, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)


class RevertProofTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = Path(self._tmp.name)
        git(self.repo, "init", "-q", "-b", "main")
        commit(self.repo, {"mod.py": MODULE_OLD, "README.md": "base\n"}, "base")
        git(self.repo, "checkout", "-q", "-b", "topic")

    def judge(self, title=""):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = revert_proof.main(["--repo", str(self.repo), "--base", "main", "--head", "topic", "--title", title,
                                      "--timeout", "120"])
        return code, out.getvalue()

    def test_a_test_that_fails_on_the_old_code_is_proof(self):
        commit(self.repo, {"mod.py": MODULE_NEW, "test_mod.py": TEST_NEW}, "fix")
        code, text = self.judge()
        self.assertEqual(code, 0, text)
        self.assertIn("PROVEN (1 test(s)", text)
        self.assertIn("test_mod.T.test_new_rule", text)
        self.assertNotIn("test_old_rule", text.split("PROVEN")[1])

    def test_tests_that_already_pass_on_the_old_code_are_not_proof(self):
        commit(self.repo, {"mod.py": MODULE_NEW + "\n# tidied\n", "test_mod.py": TEST_NEW.replace("price(2), 4", "price(0), 0")}, "fix")
        code, text = self.judge()
        self.assertEqual(code, 1, text)
        self.assertIn("UNPROVEN (every changed test also passes on the old code", text)

    def test_shipped_code_without_any_test_is_unproven(self):
        commit(self.repo, {"mod.py": MODULE_NEW}, "fix")
        code, text = self.judge()
        self.assertEqual(code, 1, text)
        self.assertIn("no test was added or edited", text)

    def test_a_documentation_change_needs_no_proof(self):
        commit(self.repo, {"README.md": "changed\n"}, "docs")
        code, text = self.judge()
        self.assertEqual(code, 0, text)
        self.assertIn("NOT NEEDED", text)

    def test_a_title_that_promises_no_behaviour_change_is_not_judged(self):
        commit(self.repo, {"mod.py": MODULE_NEW}, "refactor")
        code, text = self.judge("refactor: split price")
        self.assertEqual(code, 0, text)
        self.assertIn("NOT JUDGED", text)
        self.assertIn("gate_replay.py", text)

    def test_a_test_that_fails_on_the_change_itself_blocks(self):
        commit(self.repo, {"mod.py": MODULE_NEW, "test_mod.py": TEST_NEW.replace("price(2), 4", "price(2), 5")}, "fix")
        code, text = self.judge()
        self.assertEqual(code, 1, text)
        self.assertIn("BLOCKED", text)

    def test_a_new_test_module_the_old_code_cannot_import_counts_as_failing(self):
        commit(self.repo, {"extra.py": "VALUE = 3\n", "test_extra.py":
                           "import unittest\nimport extra\n\n\nclass T(unittest.TestCase):\n"
                           "    def test_value(self):\n        self.assertEqual(extra.VALUE, 3)\n"}, "feature")
        code, text = self.judge()
        self.assertEqual(code, 0, text)
        self.assertIn("PROVEN", text)

    def test_unreadable_refs_are_an_error_not_a_pass(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = revert_proof.main(["--repo", str(self.repo), "--base", "no-such-ref"])
        self.assertEqual(code, 2)
        self.assertIn("ERROR", out.getvalue())

    def test_failure_headers_of_both_python_layouts_name_the_same_test(self):
        new_layout = "FAIL: test_a (test_m.C.test_a)\nERROR: test_b (test_m.C.test_b) (sub=1)\nRan 5 tests in 0.1s\n"
        old_layout = "FAIL: test_a (test_m.C)\nERROR: test_b (test_m.C)\nRan 5 tests in 0.1s\n"
        expected = (5, {"test_m.C.test_a", "test_m.C.test_b"})
        self.assertEqual(revert_proof.parse_failures(new_layout), expected)
        self.assertEqual(revert_proof.parse_failures(old_layout), expected)

    def test_archive_members_cannot_leave_the_destination(self):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as tar:
            info = tarfile.TarInfo("../escape.txt")
            info.size = 1
            tar.addfile(info, io.BytesIO(b"x"))
        with tempfile.TemporaryDirectory() as dest:
            with self.assertRaises(revert_proof.ToolError):
                revert_proof.safe_extract(buffer.getvalue(), Path(dest))

    def test_only_tracked_python_code_counts_as_shipped(self):
        for path in ("mod.py", "skills/x/scripts/gate.py"):
            self.assertTrue(revert_proof.is_shipped(path), path)
        for path in ("test_mod.py", "skills/x/scripts/test_gate.py", "references/tool.py", "README.md",
                     "skills/x/fixtures/sample.py", ".github/scripts/t.py"):
            self.assertFalse(revert_proof.is_shipped(path), path)


if __name__ == "__main__":
    unittest.main()
