import unittest

from proposal_gate import evaluate


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
        "render": {"verified": True},
        "package": {"required": True, "inspected": True},
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
