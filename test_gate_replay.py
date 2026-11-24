"""gate_replay.py finds a decision that changed between two versions of a gate."""
import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import gate_replay

ROOT = Path(__file__).resolve().parent
GATE_V1 = "def evaluate(data):\n    return ['blocked'] if data.get('mode') == 'submission' else []\n"
GATE_V2 = "def evaluate(data):\n    return ['blocked'] if data.get('mode') in ('submission', 'review') else []\n"
GATE_V1_REFACTORED = ("def _mode(data):\n    return data.get('mode')\n\n\n"
                      "def evaluate(data):\n    failures = []\n    if _mode(data) == 'submission':\n"
                      "        failures.append('blocked')\n    return failures\n")
SEED = {"bid_decision": "bid", "mode": "draft", "requirements": [{"id": "R1", "state": "approved"}]}
GIT_ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "test@example.com", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "test@example.com", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}


def replay(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = gate_replay.main(list(argv))
    return code, out.getvalue()


class GateReplayTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = Path(self._tmp.name)
        (self.repo / "gate.py").write_text(GATE_V2, encoding="utf-8")
        (self.repo / "seed.json").write_text(json.dumps(SEED), encoding="utf-8")
        self.old = self.repo / "gate_before.py"

    def args(self, *extra):
        return ("--repo", str(self.repo), "--target", "gate.py", "--per-seed", "4", *extra)

    def test_a_refactor_that_keeps_every_decision_is_identical(self):
        self.old.write_text(GATE_V2.replace("in ('submission', 'review')", "in ('review', 'submission')"), encoding="utf-8")
        code, text = replay(*self.args("--old-file", str(self.old)))
        self.assertEqual(code, 0, text)
        self.assertIn("REPLAY: IDENTICAL", text)
        self.assertRegex(text, r"cases=[1-9]")

    def test_a_changed_decision_is_found_and_shown(self):
        self.old.write_text(GATE_V1, encoding="utf-8")
        code, text = replay(*self.args("--old-file", str(self.old)))
        self.assertEqual(code, 1, text)
        self.assertIn("REPLAY: DIFFERENT", text)
        self.assertIn("old: ('ok', [])", text)
        self.assertIn("new: ('ok', ['blocked'])", text)

    def test_a_different_exception_counts_as_a_difference(self):
        self.old.write_text("def evaluate(data):\n    return data['missing']\n", encoding="utf-8")
        (self.repo / "gate.py").write_text("def evaluate(data):\n    return data['other']\n", encoding="utf-8")
        code, text = replay(*self.args("--old-file", str(self.old)))
        self.assertEqual(code, 1, text)
        self.assertIn("raise", text)

    def test_the_old_version_can_come_from_a_git_ref(self):
        run = lambda *a: subprocess.run(["git", "-C", str(self.repo), *a], capture_output=True, text=True, env=GIT_ENV, check=True)
        run("init", "-q", "-b", "main")
        (self.repo / "gate.py").write_text(GATE_V1, encoding="utf-8")
        run("add", "-A")
        run("commit", "-q", "-m", "v1")
        (self.repo / "gate.py").write_text(GATE_V1_REFACTORED, encoding="utf-8")
        code, text = replay(*self.args("--old-ref", "HEAD"))
        self.assertEqual(code, 0, text)
        (self.repo / "gate.py").write_text(GATE_V2, encoding="utf-8")
        code, text = replay(*self.args("--old-ref", "HEAD"))
        self.assertEqual(code, 1, text)

    def test_problems_are_errors_not_passes(self):
        self.old.write_text("def other(data):\n    return []\n", encoding="utf-8")
        self.assertEqual(replay(*self.args("--old-file", str(self.old)))[0], 2)  # no evaluate()
        self.old.write_text("raise RuntimeError('broken')\n", encoding="utf-8")
        code, text = replay(*self.args("--old-file", str(self.old)))
        self.assertEqual(code, 2)
        self.assertIn("failed to load", text)
        self.old.write_text(GATE_V1, encoding="utf-8")
        (self.repo / "seed.json").write_text(json.dumps({"no": "bid_decision"}), encoding="utf-8")
        code, text = replay(*self.args("--old-file", str(self.old)))
        self.assertEqual(code, 2)
        self.assertIn("nothing was compared", text)

    def test_the_run_is_deterministic_for_a_seed(self):
        self.old.write_text(GATE_V1, encoding="utf-8")
        first = replay(*self.args("--old-file", str(self.old), "--seed", "7"))
        second = replay(*self.args("--old-file", str(self.old), "--seed", "7"))
        self.assertEqual(first, second)

    def test_the_repository_gate_loads_and_matches_itself(self):
        gate = ROOT / gate_replay.DEFAULT_TARGET
        code, text = replay("--repo", str(ROOT), "--old-file", str(gate), "--max-seeds", "2", "--per-seed", "3")
        self.assertEqual(code, 0, text)
        self.assertRegex(text, r"seeds=2 cases=[1-9]")


if __name__ == "__main__":
    unittest.main()
