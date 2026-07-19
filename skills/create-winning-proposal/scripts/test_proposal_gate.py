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
        "checks": {"consistency": True, "arithmetic": True, "submission": True},
        "artifact_required": True,
        "render": {"verified": True},
    }


class ProposalGateTests(unittest.TestCase):
    def test_ready(self):
        self.assertEqual(evaluate(ready_data()), [])

    def test_accepted_conditional_bid(self):
        data = ready_data()
        data["bid_decision"] = "conditional-bid"
        data["bid_conditions"] = [{"id": "B1", "owner": "Legal", "deadline": "2026-08-20", "accepted": True}]
        self.assertEqual(evaluate(data), [])

    def test_analysis_does_not_require_render(self):
        data = ready_data()
        data["mode"] = "analysis"
        data["artifact_required"] = False
        data["render"] = {"verified": False}
        self.assertEqual(evaluate(data), [])

    def test_missing_schema_is_blocked(self):
        self.assertIn("missing field: requirements", evaluate({"mode": "review"}))

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
