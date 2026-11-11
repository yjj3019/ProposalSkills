"""Regression tests for gate rules that the mutation probe (gate_mutation_probe.py) found unguarded.

Each test fails when the named rule is weakened. Before these tests existed, the weakened gate passed
every focused suite: an exception without evidence, a boolean ledger value, a deadline without a time
zone, and an upper-case artifact hash were all accepted without any test noticing."""
from __future__ import annotations

import copy
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "skills/create-winning-proposal/scripts"))
sys.path.insert(0, str(REPO / "skills/create-best-proposal/scripts"))
import proposal_gate as pg  # noqa: E402
import unified_gate as ug  # noqa: E402
from test_proposal_gate import ready_data  # noqa: E402


def unmet_requirement(exception):
    data = ready_data()
    data["requirements"][0].update(support="X", fit="GAP", exception=exception)
    return pg.evaluate(data)


def blocked_as_unmet(failures):
    return any("approved but not met" in f for f in failures)


class BuyerExceptionTests(unittest.TestCase):
    """_exception_granted: an unmet mandatory requirement is excused only by approver AND evidence."""

    def test_complete_exception_is_accepted(self):
        self.assertEqual(unmet_requirement({"granted_by": "발주처 계약담당", "evidence": ["질의응답 회신 3항"]}), [])

    def test_approver_without_evidence_is_still_blocked(self):
        for evidence in ([], ["TBD"], [""], None, "추후 확인"):
            exception = {"granted_by": "발주처 계약담당"}
            if evidence is not None:
                exception["evidence"] = evidence
            self.assertTrue(blocked_as_unmet(unmet_requirement(exception)), evidence)

    def test_evidence_without_a_real_approver_is_still_blocked(self):
        for approver in ("", "TBD", "미정", None):
            exception = {"evidence": ["질의응답 회신 3항"]}
            if approver is not None:
                exception["granted_by"] = approver
            self.assertTrue(blocked_as_unmet(unmet_requirement(exception)), approver)


class LedgerNumberTypeTests(unittest.TestCase):
    """_is_number: JSON booleans are not numbers, so True cannot masquerade as an amount of 1."""

    def test_boolean_value_is_rejected(self):
        for flag in (True, False):
            data = copy.deepcopy(ready_data())
            data["numbers"][2]["value"] = flag
            failures = pg.evaluate(data)
            self.assertTrue(any("N3" in f and "finite JSON number" in f for f in failures), flag)

    def test_boolean_cannot_satisfy_a_sum(self):
        data = copy.deepcopy(ready_data())
        data["numbers"] = [
            {"id": "N1", "label": "총액", "value": 2, "unit": "KRW", "source": "견적서", "components": ["N2", "N3"]},
            {"id": "N2", "label": "A", "value": True, "unit": "KRW", "source": "견적서"},
            {"id": "N3", "label": "B", "value": True, "unit": "KRW", "source": "견적서"},
        ]
        self.assertTrue(pg.check_numbers(data["numbers"]))

    def test_real_numbers_still_pass(self):
        self.assertEqual(pg.check_numbers(ready_data()["numbers"]), [])


class DeadlineTimezoneTests(unittest.TestCase):
    """is_iso_datetime: a deadline needs a time zone; 17:00 with no zone is a different instant per reader."""

    def test_submission_deadline_without_timezone_is_rejected(self):
        for value in ("2099-12-31T17:00:00", "2099-12-31T17:00:00.000"):
            data = ready_data()
            data["submission"]["deadline"] = value
            self.assertTrue(any("ISO datetime with timezone" in f for f in pg.evaluate(data)), value)

    def test_date_only_deadline_is_rejected(self):
        data = ready_data()
        data["submission"]["deadline"] = "2099-12-31"
        self.assertTrue(any("ISO datetime with timezone" in f for f in pg.evaluate(data)))

    def test_bid_condition_deadline_without_timezone_is_rejected(self):
        data = ready_data()
        data["bid_conditions"] = [{"id": "B1", "text": "보안 서약", "deadline": "2099-12-31T17:00:00",
                                   "state": "accepted", "evidence_refs": ["공고문 4항"]}]
        self.assertTrue(any("B1" in f and "timezone" in f for f in pg.evaluate(data)))

    def test_zone_aware_forms_are_accepted(self):
        for value in ("2099-12-31T17:00:00+09:00", "2099-12-31T08:00:00Z"):
            self.assertTrue(pg.is_iso_datetime(value), value)


class ArtifactHashCaseTests(unittest.TestCase):
    """unified_gate._norm_digest: hex case and the sha256: prefix must not change a hash comparison."""

    def test_normalization_ignores_case_and_prefix(self):
        lower = "ab" * 32
        for form in (lower, "sha256:" + lower, "SHA256:" + lower.upper(), "  " + lower.upper() + "  "):
            self.assertEqual(ug._norm_digest(form), lower, form)

    def test_malformed_values_normalize_to_empty(self):
        for form in ("", "sha256:abc", "g" * 64, None, 12345, ["a" * 64]):
            self.assertEqual(ug._norm_digest(form), "", form)

    def test_uppercase_hash_of_a_changed_file_is_still_a_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / "final.pptx"
            doc.write_bytes(b"reviewed version")
            stale = hashlib.sha256(b"older version").hexdigest().upper()
            problems = ug.bind_document({"render": {"artifact_hash": "SHA256:" + stale}}, doc)
            self.assertEqual(len(problems), 1)

    def test_uppercase_hash_of_the_actual_file_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / "final.pptx"
            doc.write_bytes(b"reviewed version")
            actual = hashlib.sha256(b"reviewed version").hexdigest().upper()
            self.assertEqual(ug.bind_document({"render": {"artifact_hash": "sha256:" + actual}}, doc), [])


if __name__ == "__main__":
    unittest.main()
