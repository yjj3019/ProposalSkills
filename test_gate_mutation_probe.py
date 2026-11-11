"""gate_mutation_probe.py: the mutation catalog must stay valid, and the probe must classify correctly.

The real probe takes minutes, so it is run manually (python gate_mutation_probe.py). These tests keep the
catalog from rotting (every mutation must still match its source exactly once and still compile) and
exercise the runner on a tiny synthetic project."""
from __future__ import annotations

import py_compile
import tempfile
import unittest
from pathlib import Path

import gate_mutation_probe as probe

REPO = Path(__file__).resolve().parent


class CatalogTests(unittest.TestCase):
    def test_names_are_unique_and_every_test_module_exists(self):
        names = [m.name for m in probe.MUTATIONS]
        self.assertEqual(len(names), len(set(names)))
        for mutation in probe.MUTATIONS:
            for module in mutation.tests:
                self.assertTrue((REPO / f"{module}.py").is_file(), f"{mutation.name}: {module}")

    def test_every_mutation_matches_exactly_once_and_still_compiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            for mutation in probe.MUTATIONS:
                source = (REPO / mutation.path).read_text(encoding="utf-8")
                mutated = probe.replace_once(source, mutation.old, mutation.new)  # raises if 0 or 2+ matches
                self.assertNotEqual(mutated, source, mutation.name)
                target = Path(tmp) / (mutation.name + ".py")
                target.write_text(mutated, encoding="utf-8")
                py_compile.compile(str(target), doraise=True, cfile=str(target) + "c")

    def test_catalog_covers_both_gates(self):
        self.assertEqual({m.path for m in probe.MUTATIONS}, {probe.PROPOSAL, probe.UNIFIED})


class ReplaceOnceTests(unittest.TestCase):
    def test_rejects_missing_duplicate_and_noop(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            probe.replace_once("abc", "x", "y")
        with self.assertRaisesRegex(ValueError, "exactly once"):
            probe.replace_once("aa", "a", "b")
        with self.assertRaisesRegex(ValueError, "invalid"):
            probe.replace_once("abc", "a", "a")
        with self.assertRaisesRegex(ValueError, "invalid"):
            probe.replace_once("abc", "", "a")

    def test_replaces_the_single_match(self):
        self.assertEqual(probe.replace_once("x > 0", "> 0", ">= 0"), "x >= 0")


class LineEndingTests(unittest.TestCase):
    def test_multiline_mutation_matches_and_keeps_crlf(self):
        mutation = probe.Mutation("m", "f.py", "a\nb", "a\nc", "why")
        self.assertEqual(probe.apply_mutation("x\r\na\r\nb\r\n", mutation), "x\r\na\r\nc\r\n")
        self.assertEqual(probe.apply_mutation("x\na\nb\n", mutation), "x\na\nc\n")


class ClassifyTests(unittest.TestCase):
    def test_outcomes(self):
        self.assertEqual(probe.classify(0, "Ran 3 tests in 0.1s\n\nOK\n"), ("survived", []))
        failed = "FAIL: test_a (m.C.test_a)\nRan 3 tests in 0.1s\n\nFAILED (failures=1)\n"
        self.assertEqual(probe.classify(1, failed), ("killed", ["test_a"]))
        errored = "ERROR: test_b (m.C.test_b)\nRan 3 tests in 0.1s\n\nFAILED (errors=1)\n"
        self.assertEqual(probe.classify(1, errored), ("crashed", ["test_b"]))
        self.assertEqual(probe.classify(1, "boom")[0], "error")
        self.assertEqual(probe.classify(0, "Ran 0 tests in 0.0s\n\nNO TESTS RAN\n")[0], "error")

    def test_exit_status_zero_with_failure_text_is_not_survived(self):
        self.assertNotEqual(probe.classify(0, "FAIL: test_a (m)\nRan 1 test in 0s\nOK")[0], "survived")

    def test_exit_code_mapping(self):
        def r(outcome):
            return probe.Result("n", outcome, "w")
        self.assertEqual(probe.exit_code([r("killed")]), 0)
        self.assertEqual(probe.exit_code([r("killed"), r("survived")]), 1)
        self.assertEqual(probe.exit_code([r("crashed")]), 1)
        self.assertEqual(probe.exit_code([r("survived"), r("invalid")]), 2)
        self.assertEqual(probe.exit_code([r("error")]), 2)


TOY_GATE = "def allow(amount):\n    if amount <= 0:\n        return False\n    return amount < 100\n"
STRONG_TESTS = """import unittest
from toy_gate import allow


class Guard(unittest.TestCase):
    def test_zero_blocked(self):
        self.assertFalse(allow(0))

    def test_big_blocked(self):
        self.assertFalse(allow(100))

    def test_ok(self):
        self.assertTrue(allow(5))
"""
WEAK_TESTS = """import unittest
from toy_gate import allow


class Guard(unittest.TestCase):
    def test_ok(self):
        self.assertTrue(allow(5))
"""


class RunnerOnToyProjectTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "proj"
        self.root.mkdir()
        (self.root / "toy_gate.py").write_text(TOY_GATE, encoding="utf-8")
        (self.root / "test_toy.py").write_text(STRONG_TESTS, encoding="utf-8")

    @staticmethod
    def mutation(name, old, new):
        return probe.Mutation(name, "toy_gate.py", old, new, "toy rule", ("test_toy",))

    def outcomes(self, *mutations):
        results, problem = probe.run_probe(self.root, tuple(mutations), jobs=2, timeout=60)
        self.assertEqual(problem, "")
        return {r.name: r.outcome for r in results}

    def test_kill_and_invalid_are_distinguished(self):
        got = self.outcomes(
            self.mutation("zero-check", "amount <= 0", "amount < 0"),
            self.mutation("limit-check", "amount < 100", "True"),
            self.mutation("syntax", "return False", "return ("),
            self.mutation("absent", "does not occur", "x"),
        )
        self.assertEqual(got, {"zero-check": "killed", "limit-check": "killed",
                               "syntax": "invalid", "absent": "invalid"})

    def test_a_mutation_the_suite_cannot_see_survives(self):
        (self.root / "test_toy.py").write_text(WEAK_TESTS, encoding="utf-8")
        self.assertEqual(self.outcomes(self.mutation("zero-check", "amount <= 0", "amount < 0")),
                         {"zero-check": "survived"})

    def test_errors_without_assertions_are_crashed_not_killed(self):
        got = self.outcomes(self.mutation("rename", "def allow(", "def allowed("))
        self.assertEqual(got, {"rename": "crashed"})

    def test_failing_baseline_aborts_instead_of_reporting_kills(self):
        (self.root / "toy_gate.py").write_text("def allow(amount):\n    return True\n", encoding="utf-8")
        results, problem = probe.run_probe(self.root, (self.mutation("m", "True", "False"),),
                                           jobs=1, timeout=60)
        self.assertEqual(results, [])
        self.assertIn("baseline is not green", problem)

    def test_working_tree_is_never_modified(self):
        before = (self.root / "toy_gate.py").read_text(encoding="utf-8")
        self.outcomes(self.mutation("zero-check", "amount <= 0", "amount < 0"))
        self.assertEqual((self.root / "toy_gate.py").read_text(encoding="utf-8"), before)

    def test_timeout_is_an_error_not_a_pass(self):
        (self.root / "test_toy.py").write_text(
            "import time, unittest\n\n\nclass T(unittest.TestCase):\n    def test_slow(self):\n"
            "        time.sleep(30)\n", encoding="utf-8")
        results, problem = probe.run_probe(self.root, (self.mutation("m", "amount <= 0", "amount < 0"),),
                                           jobs=1, timeout=2, check_baseline=False)
        self.assertEqual(problem, "")
        self.assertEqual(results[0].outcome, "error")


if __name__ == "__main__":
    unittest.main()
