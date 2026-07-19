import unittest
import json
import tempfile
from pathlib import Path

from proposal_gate import evaluate, main, validate_schema


def ready_data():
    return {
        "mode": "submission",
        "bid_decision": "bid",
        "bid_conditions": [],
        "requirements": [{"id": "R1", "mandatory": True, "state": "approved"}],
        "claims": [{"id": "C1", "kind": "commitment", "status": "supported", "owner_approved": True}],
        "unresolved_tokens": [],
        "attachments": [{"name": "form", "required": True, "present": True}],
        "source_conflicts": [],
        "inputs": [],
        "defects": [],
        "checks": {"consistency": True, "arithmetic": True, "submission": True},
        "artifact_required": True,
        "render": {
            "verified": True, "artifact_hash": "sha256:test", "tool": "renderer-v1",
            "evidence": ["all pages reviewed"],
        },
        "package": {
            "required": True, "inspected": True, "artifact_hash": "sha256:test",
            "tool": "ooxml-check-v1", "checks": {
                "metadata": "pass", "notes": "pass", "comments": "pass",
                "hidden-content": "pass", "embedded-files": "not-applicable",
                "external-links": "pass", "macros": "not-applicable",
                "stale-customer-data": "pass", "price-leakage": "pass",
            }, "reviewer": "QA",
        },
        "submission": {
            "cleared": True,
            "rehearsal_evidence": ["test upload opened"],
            "receipt_plan": "save portal confirmation",
            "receipt_evidence": [],
        },
    }


class ProposalGateTests(unittest.TestCase):
    def test_ready(self):
        self.assertEqual(evaluate(ready_data()), [])

    def test_accepted_conditional_bid(self):
        data = ready_data()
        data["bid_decision"] = "conditional-bid"
        data["bid_conditions"] = [{"id": "B1", "owner": "Legal", "deadline": "2026-08-20T17:00:00+09:00", "accepted": True}]
        self.assertEqual(evaluate(data), [])

    def test_analysis_does_not_require_render(self):
        data = ready_data()
        data["mode"] = "analysis"
        data["artifact_required"] = False
        data["render"] = {"verified": False}
        self.assertEqual(evaluate(data), [])

    def test_missing_schema_is_blocked(self):
        self.assertIn("missing field: requirements", evaluate({"mode": "review"}))

    def test_open_pm_gates_are_blocked(self):
        data = ready_data()
        data["inputs"] = [{"id": "I1", "class": "blocking", "status": "open"}]
        data["defects"] = [{"id": "D1", "severity": "major", "status": "open"}]
        data["package"] = {"required": True, "inspected": False}
        data["submission"] = {"cleared": False, "rehearsal_evidence": [], "receipt_plan": ""}
        failures = evaluate(data)
        self.assertIn("blocking input I1 is open", failures)
        self.assertIn("major defect D1 is open", failures)
        self.assertIn("package inspection is missing or failed", failures)
        self.assertIn("submission is not cleared", failures)
        self.assertIn("submission rehearsal evidence is missing", failures)
        self.assertIn("submission receipt plan is missing", failures)

    def test_wrong_types_are_invalid_without_exception(self):
        data = ready_data()
        data["requirements"] = None
        self.assertEqual(validate_schema(data), ["requirements must be an array"])
        self.assertEqual(evaluate(data), ["requirements must be an array"])

    def test_cli_returns_two_for_invalid_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.json"
            data = ready_data()
            data["requirements"] = None
            path.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(main(["proposal_gate.py", str(path)]), 2)

    def test_unknown_pm_values_are_invalid(self):
        data = ready_data()
        data["inputs"] = [{"id": "I1", "class": "required", "status": "open"}]
        data["defects"] = [{"id": "D1", "severity": "fatal", "status": "open"}]
        failures = validate_schema(data)
        self.assertTrue(any("unsupported class" in failure for failure in failures))
        self.assertTrue(any("unsupported severity" in failure for failure in failures))

    def test_conditional_bid_deadline_requires_timezone(self):
        data = ready_data()
        data["bid_decision"] = "conditional-bid"
        data["bid_conditions"] = [{"id": "B1", "owner": "Legal", "deadline": "tomorrow", "accepted": True}]
        self.assertTrue(any("ISO deadline" in failure for failure in validate_schema(data)))

    def test_closed_major_requires_closure_evidence(self):
        data = ready_data()
        data["defects"] = [{"id": "D1", "severity": "major", "status": "closed"}]
        failures = validate_schema(data)
        self.assertTrue(any("closure evidence" in failure for failure in failures))
        self.assertTrue(any("closure reviewer" in failure for failure in failures))
        self.assertTrue(any("closed_at" in failure for failure in failures))
        self.assertTrue(any("reverified scope" in failure for failure in failures))

    def test_verified_artifacts_require_evidence(self):
        data = ready_data()
        data["render"] = {"verified": True}
        data["package"] = {"required": True, "inspected": True}
        failures = evaluate(data)
        self.assertIn("render verification lacks artifact_hash", failures)
        self.assertIn("package inspection lacks checks", failures)

    def test_nested_evidence_types_are_invalid(self):
        data = ready_data()
        data["render"]["evidence"] = "looked good"
        data["package"]["checks"] = []
        failures = validate_schema(data)
        self.assertIn("render evidence must be an array", failures)
        self.assertIn("package checks must be an object", failures)

    def test_submission_requires_complete_package_scope(self):
        data = ready_data()
        data["package"]["checks"] = {"metadata": "pass"}
        failures = evaluate(data)
        self.assertIn("missing required package check: notes", failures)
        self.assertIn("missing required package check: price-leakage", failures)

    def test_blocked(self):
        data = ready_data()
        data.update(
            bid_decision="no-bid",
            requirements=[{"id": "R1", "mandatory": True, "state": "drafted"}],
            claims=[{"id": "C1", "kind": "commitment", "status": "unsupported", "owner_approved": False}],
            unresolved_tokens=["[NEEDS INPUT: legal]"],
            attachments=[{"name": "signature", "required": True, "present": False}],
            source_conflicts=["schedule 12 vs 16 weeks"],
            checks={"consistency": False, "arithmetic": True, "submission": False},
            render={"verified": False},
        )
        failures = evaluate(data)
        self.assertEqual(len(failures), 10)
        self.assertIn("requirement R1 is not approved", failures)


if __name__ == "__main__":
    unittest.main()
