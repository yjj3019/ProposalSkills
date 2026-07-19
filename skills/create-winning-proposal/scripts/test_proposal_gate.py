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
        "requirements": [{"id": "R1", "mandatory": True, "state": "approved",
                          "evidence_refs": ["proposal.md#3.1"]}],
        "eligibility": [{"id": "E1", "criterion": "3억 실적", "mandatory": True,
                         "met": True, "curable": True}],
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
            "deadline": "2099-12-31T17:00:00+09:00",
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

    def test_simulation_mode_does_not_override_no_bid(self):
        data = ready_data()
        data["artifact_mode"] = "simulation-only"
        data["bid_decision"] = "no-bid"
        self.assertIn("bid_decision must be 'bid' or accepted 'conditional-bid'", evaluate(data))

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


    # --- #6 종합 개선: 규제/제조사 확약 게이트 (후방호환) ---
    def test_baseline_without_optional_fields_still_ready(self):
        self.assertEqual(evaluate(ready_data()), [])

    def test_missing_vendor_confirmation_blocks(self):
        d = ready_data()
        d["vendor_confirmations"] = [{"id": "V1", "kind": "support", "required": True, "present": False}]
        self.assertTrue(any("vendor confirmation V1" in f for f in evaluate(d)))

    def test_present_vendor_confirmation_passes(self):
        d = ready_data()
        d["vendor_confirmations"] = [{"id": "V1", "kind": "supply", "required": True, "present": True}]
        self.assertEqual(evaluate(d), [])

    def test_regulatory_gap_blocks(self):
        d = ready_data()
        d["regulatory_checks"] = [{"id": "REG1", "status": "gap"}]
        self.assertTrue(any("regulatory check REG1 is gap" in f for f in evaluate(d)))

    def test_regulatory_met_without_evidence_blocks(self):
        d = ready_data()
        d["regulatory_checks"] = [{"id": "REG1", "status": "met"}]
        self.assertTrue(any("REG1 claims met without evidence" in f for f in evaluate(d)))

    def test_financial_flag_requires_regulatory_checks(self):
        d = ready_data()
        d["flags"] = {"financial": True}
        self.assertTrue(any("financial submission requires regulatory_checks" in f for f in evaluate(d)))

    def test_financial_flag_with_met_regulatory_passes(self):
        d = ready_data()
        d["flags"] = {"financial": True}
        d["regulatory_checks"] = [{"id": "REG1", "status": "met", "evidence": ["감독규정 준수 확인서"]}]
        self.assertEqual(evaluate(d), [])

    def test_unsupported_vendor_kind_is_invalid(self):
        d = ready_data()
        d["vendor_confirmations"] = [{"id": "V1", "kind": "warranty", "required": True, "present": True}]
        self.assertTrue(any("unsupported kind" in f for f in validate_schema(d)))

    # --- P0 반낙관 하드닝: 3종 가드 (자기선언 낙관 통과 차단) ---
    def test_approved_without_evidence_refs_blocks(self):
        d = ready_data()
        d["requirements"] = [{"id": "R1", "mandatory": True, "state": "approved"}]
        self.assertIn("requirement R1 approved without evidence_refs", evaluate(d))

    def test_approved_with_evidence_refs_passes(self):
        self.assertEqual(evaluate(ready_data()), [])

    def test_past_deadline_blocks(self):
        d = ready_data()
        d["submission"]["deadline"] = "2021-05-20T17:00:00+09:00"
        self.assertTrue(any("deadline has passed" in f for f in evaluate(d)))

    def test_missing_deadline_in_submission_blocks(self):
        d = ready_data()
        d["submission"].pop("deadline")
        self.assertIn("submission deadline is missing", evaluate(d))

    def test_non_iso_deadline_is_invalid(self):
        d = ready_data()
        d["submission"]["deadline"] = "next week"
        self.assertIn("submission deadline must be ISO datetime with timezone", validate_schema(d))

    def test_deadline_honours_now_override(self):
        import os
        d = ready_data()
        d["submission"]["deadline"] = "2026-08-01T17:00:00+09:00"
        os.environ["PROPOSAL_GATE_NOW"] = "2026-09-01T00:00:00+09:00"
        try:
            self.assertTrue(any("deadline has passed" in f for f in evaluate(d)))
        finally:
            del os.environ["PROPOSAL_GATE_NOW"]

    def test_incurable_eligibility_forbids_bid(self):
        d = ready_data()
        d["eligibility"] = [{"id": "E1", "criterion": "3억 실적", "mandatory": True,
                             "met": False, "curable": False}]
        self.assertTrue(any("incurable; bid not permitted" in f for f in evaluate(d)))

    def test_curable_eligibility_forbids_plain_bid(self):
        d = ready_data()
        d["eligibility"] = [{"id": "E1", "criterion": "SW 등록", "mandatory": True,
                             "met": False, "curable": True}]
        self.assertTrue(any("requires conditional-bid or no-bid" in f for f in evaluate(d)))

    def test_missing_eligibility_in_submission_blocks(self):
        d = ready_data()
        d.pop("eligibility")
        self.assertIn("submission requires eligibility ledger", evaluate(d))

    def test_eligibility_met_type_is_invalid(self):
        d = ready_data()
        d["eligibility"] = [{"id": "E1", "met": "yes"}]
        self.assertTrue(any("met must be a boolean" in f for f in validate_schema(d)))

    def test_missing_curable_defaults_incurable(self):
        # curable 생략은 fail-closed: conditional-bid로도 우회 불가.
        d = ready_data()
        d["bid_decision"] = "conditional-bid"
        d["bid_conditions"] = [{"id": "B1", "owner": "Legal",
                                "deadline": "2099-08-20T17:00:00+09:00", "accepted": True}]
        d["eligibility"] = [{"id": "E1", "mandatory": True, "met": False}]  # curable 미지정
        self.assertTrue(any("incurable; bid not permitted" in f for f in evaluate(d)))

    def test_evidence_refs_empty_string_blocks(self):
        d = ready_data()
        d["requirements"] = [{"id": "R1", "mandatory": True, "state": "approved",
                              "evidence_refs": ["", None]}]
        self.assertIn("requirement R1 approved without evidence_refs", evaluate(d))

    def test_antigravity_optimistic_audit_is_blocked(self):
        """Antigravity false-pass 재현: approved(무증빙)+만료마감+자격원장부재→반드시 차단."""
        d = ready_data()
        d["requirements"] = [
            {"id": "RFP-REQ-0%d" % i, "mandatory": True, "state": "approved"} for i in range(1, 6)
        ]
        d["submission"]["deadline"] = "2021-05-20T17:00:00+09:00"
        d.pop("eligibility")
        failures = evaluate(d)
        self.assertTrue(any("approved without evidence_refs" in f for f in failures))
        self.assertTrue(any("deadline has passed" in f for f in failures))
        self.assertIn("submission requires eligibility ledger", failures)

if __name__ == "__main__":
    unittest.main()
