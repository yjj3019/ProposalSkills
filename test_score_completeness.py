import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "skills/create-winning-proposal/scripts"))
from test_proposal_gate import ready_data  # noqa: E402
from score_completeness import score, quality_score  # noqa: E402


class ScoreCompletenessTests(unittest.TestCase):
    def test_ready_audit_is_audit_valid_not_submission_ready(self):
        """이 스크립트는 실제 파일을 보지 않으므로 제출 준비로 승격하지 않는다."""
        out = score(ready_data(), None)
        self.assertEqual(out["status"], "AUDIT-VALID")
        self.assertEqual(out["readiness_score"], 100.0)
        self.assertEqual(out["blocking_count"], 0)

    def test_draft_audit_keeps_its_mode_label(self):
        d = ready_data()
        d.update(mode="draft", artifact_required=False)
        d["checks"]["submission"] = False
        d["package"]["required"] = False
        d["submission"]["cleared"] = False
        self.assertEqual(score(d, None)["status"], "DRAFT-READY")

    def test_quality_high_but_gate_block_is_no_go(self):
        d = ready_data()
        d["submission"]["deadline"] = "2021-05-20T17:00:00+09:00"  # 만료
        metrics = {"compliance_coverage": 0.95, "claim_support_rate": 0.9,
                   "defect_penalty": 0.1, "rehearsal_score": 0.8}
        out = score(d, metrics)
        self.assertEqual(out["status"], "NO-GO")          # 품질 높아도 게이트가 결정
        self.assertGreater(out["quality_score"], 80)      # 품질 축은 별도로 높게 유지
        self.assertGreater(out["blocking_count"], 0)

    def test_antigravity_audit_is_no_go(self):
        d = ready_data()
        d["requirements"] = [{"id": "R%d" % i, "mandatory": True, "state": "approved"}
                             for i in range(1, 6)]
        d["submission"]["deadline"] = "2021-05-20T17:00:00+09:00"
        d.pop("eligibility")
        out = score(d, None)
        self.assertEqual(out["status"], "NO-GO")
        self.assertLess(out["readiness_score"], 100.0)

    def test_quality_formula_weights(self):
        # 완벽 지표 -> 100, 무결점 가중 확인
        self.assertEqual(quality_score({"compliance_coverage": 1, "claim_support_rate": 1,
                                         "defect_penalty": 0, "rehearsal_score": 1}), 100.0)

    def test_conditional_bid_blocked_annotates_downgrade(self):
        d = ready_data()
        d["bid_decision"] = "conditional-bid"
        d["bid_conditions"] = [{"id": "B1", "owner": "L",
                                "deadline": "2099-01-01T00:00:00+09:00", "accepted": True}]
        d["attachments"] = [{"name": "서식1", "required": True, "present": False}]
        out = score(d, None)
        self.assertEqual(out["status"], "NO-GO")
        self.assertEqual(out.get("downgraded_from"), "CONDITIONAL-GO")
        self.assertTrue(out.get("downgrade_cause"))

    def test_conditional_bid_is_conditional_go(self):
        d = ready_data()
        d["mode"] = "draft"  # conditional-bid는 내부 진행 상태 — submission 모드에서는 NO-GO
        d["bid_decision"] = "conditional-bid"
        d["bid_conditions"] = [{"id": "B1", "owner": "Legal",
                                "deadline": "2099-08-20T17:00:00+09:00", "accepted": True}]
        out = score(d, None)
        self.assertEqual(out["status"], "CONDITIONAL-GO")

    def test_conditional_bid_in_submission_mode_is_no_go(self):
        d = ready_data()
        d["bid_decision"] = "conditional-bid"
        d["bid_conditions"] = [{"id": "B1", "owner": "Legal",
                                "deadline": "2099-08-20T17:00:00+09:00", "accepted": True}]
        out = score(d, None)
        self.assertEqual(out["status"], "NO-GO")
        self.assertEqual(out.get("downgraded_from"), "CONDITIONAL-GO")

    def test_quality_metrics_are_validated(self):
        d = ready_data()
        self.assertEqual(score(d, {"compliance_coverage": 1.5, "claim_support_rate": "0.9",
                                   "defect_penalty": -2, "rehearsal_score": 1})["status"], "INVALID")
        self.assertEqual(score(d, {})["status"], "INVALID")
        ok = score(d, {"compliance_coverage": 1, "claim_support_rate": 1,
                       "defect_penalty": 0, "rehearsal_score": 1})
        self.assertEqual(ok["quality_score"], 100.0)


if __name__ == "__main__":
    unittest.main()
