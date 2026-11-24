"""The decision register and the defect ledger stay tied to the code they describe."""
import json
import tempfile
import unittest
from pathlib import Path

import repo_records as rr

ROOT = Path(__file__).resolve().parent
ENTRY = """### D01 Example

- **Decision:** x is done this way.
- **Why:** because the other way broke y.
- **Revisit only if:** y changes.
- **Lives in:** `mod.py`
- **Pinned by:** `test_mod.py::Tests.test_it`
"""
ROW = {"date": "2026-11-24", "change": "#1", "class": "bypass", "what": "w", "escaped": "e", "mechanism": "m"}


class RepositoryRecordsTests(unittest.TestCase):
    def test_the_repository_records_are_clean(self):
        self.assertEqual(rr.check_decisions(ROOT), [])
        self.assertEqual(rr.check_ledger(ROOT), [])

    def test_every_decision_names_an_existing_pinning_test(self):
        text = (ROOT / rr.DECISIONS).read_text(encoding="utf-8")
        self.assertGreaterEqual(text.count("\n### D"), 8)
        self.assertEqual(rr.main([str(ROOT)]), 0)

    def test_ledger_records_what_was_fixed_in_this_audit(self):
        rows = [json.loads(line) for line in (ROOT / rr.LEDGER).read_text(encoding="utf-8").splitlines()]
        self.assertGreaterEqual(len(rows), 8)
        # the audit's four changes stay recorded; later fixes append rows, so this is a subset check
        self.assertLessEqual({"#58", "#59", "#60", "#66"}, {r["change"] for r in rows})


class DecisionCheckTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = Path(self._tmp.name)
        (self.repo / "references").mkdir()
        (self.repo / "mod.py").write_text("x = 1\n", encoding="utf-8")
        (self.repo / "test_mod.py").write_text("import unittest\n\n\nclass Tests(unittest.TestCase):\n    def test_it(self):\n        pass\n",
                                               encoding="utf-8")

    def check(self, text):
        (self.repo / rr.DECISIONS).write_text(text, encoding="utf-8")
        return rr.check_decisions(self.repo)

    def test_a_complete_entry_passes(self):
        self.assertEqual(self.check(ENTRY), [])

    def test_a_missing_or_placeholder_field_is_reported(self):
        self.assertTrue(any("lacks a real 'Why'" in p for p in self.check(ENTRY.replace("because the other way broke y.", "TBD"))))
        self.assertTrue(any("'Revisit only if'" in p for p in self.check(ENTRY.replace("- **Revisit only if:** y changes.\n", ""))))

    def test_a_decision_cannot_outlive_its_path_or_its_test(self):
        self.assertTrue(any("does not exist" in p for p in self.check(ENTRY.replace("`mod.py`", "`gone.py`"))))
        self.assertTrue(any("no test 'test_gone'" in p for p in self.check(ENTRY.replace("test_it", "test_gone"))))
        self.assertTrue(any("no class 'Other'" in p for p in self.check(ENTRY.replace("Tests.test_it", "Other.test_it"))))
        self.assertTrue(any("no such test file" in p for p in self.check(ENTRY.replace("test_mod.py::", "test_none.py::"))))
        self.assertTrue(any("names no pinning test" in p for p in self.check(ENTRY.replace("`test_mod.py::Tests.test_it`", "nothing"))))

    def test_duplicate_ids_and_an_empty_register_are_reported(self):
        self.assertTrue(any("appears twice" in p for p in self.check(ENTRY + "\n" + ENTRY)))
        self.assertTrue(any("no `### Dnn` entries" in p for p in self.check("# nothing here\n")))


class LedgerCheckTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = Path(self._tmp.name)
        (self.repo / "references").mkdir()
        (self.repo / "test_guard.py").write_text("import unittest\n\n\nclass G(unittest.TestCase):\n    def test_class(self):\n        pass\n",
                                                 encoding="utf-8")

    def check(self, rows, classes=None, threshold=3, raw=None):
        text = raw if raw is not None else "".join(json.dumps(r) + "\n" for r in rows)
        (self.repo / rr.LEDGER).write_text(text, encoding="utf-8")
        (self.repo / rr.GUARDS).write_text(json.dumps({"threshold": threshold, "classes": classes or {}}), encoding="utf-8")
        return rr.check_ledger(self.repo)

    def test_valid_rows_below_the_threshold_pass(self):
        self.assertEqual(self.check([ROW, ROW]), [])

    def test_the_third_entry_of_a_class_demands_a_guard(self):
        problems = self.check([ROW, ROW, ROW])
        self.assertTrue(any("needs a guard test" in p for p in problems), problems)
        guard = {"bypass": {"test": "test_guard.py::G.test_class", "how": "runs every gate and fails on the class"}}
        self.assertEqual(self.check([ROW, ROW, ROW], guard), [])

    def test_a_guard_must_resolve_and_belong_to_a_class_in_the_ledger(self):
        missing = {"bypass": {"test": "test_guard.py::G.test_gone", "how": "x"}}
        self.assertTrue(any("no test 'test_gone'" in p for p in self.check([ROW], missing)))
        stale = {"other": {"test": "test_guard.py::G.test_class", "how": "x"}}
        self.assertTrue(any("not in the ledger" in p for p in self.check([ROW], stale)))
        self.assertTrue(any("must say `how`" in p for p in self.check([ROW], {"bypass": {"test": "test_guard.py::G.test_class"}})))

    def test_malformed_rows_are_reported(self):
        cases = {
            "bad date": {**ROW, "date": "24-11-2026"},
            "bad change": {**ROW, "change": "PR 66"},
            "bad class": {**ROW, "class": "Not Kebab"},
            "placeholder": {**ROW, "mechanism": "TBD"},
            "extra field": {**ROW, "extra": "x"},
        }
        for label, row in cases.items():
            with self.subTest(label):
                self.assertTrue(self.check([row]), label)
        self.assertTrue(self.check(None, raw='{"date": "2026-11-24", "date": "2026-11-25"}\n'))
        self.assertTrue(self.check(None, raw=json.dumps(ROW) + "\n\n"))
        self.assertTrue(self.check(None, raw="not json\n"))

    def test_a_threshold_that_cannot_work_is_rejected(self):
        for threshold in (1, True, "3"):
            with self.subTest(threshold=threshold):
                self.assertTrue(any("`threshold`" in p for p in self.check([ROW], threshold=threshold)))


if __name__ == "__main__":
    unittest.main()
