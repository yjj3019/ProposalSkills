"""9차 — 발주 문서에서 읽어낸 규칙이 게이트를 바꾼다(공개 RFx 검토 반영).

공고마다 평가 방식·요구 강도·문서 종류가 다르다. 그 차이를 "합계 100"·"필수 불리언"·
"RFP 하나"로 환원하면 실제 공고를 원장에 옮길 수 없거나, 옮기면 잘못 차단된다.
각 테스트는 공개 사례에서 확인한 규칙을 합성 데이터로 재현한다(원문은 싣지 않는다).
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
from test_support import run_script  # noqa: E402
BEST = REPO / "skills/create-best-proposal"
WIN = REPO / "skills/create-winning-proposal"
sys.path.insert(0, str(WIN / "scripts"))
sys.path.insert(0, str(BEST / "scripts"))
import proposal_gate as pg  # noqa: E402
import bulk_matrix as bm  # noqa: E402
from test_proposal_gate import ready_data  # noqa: E402


def _criteria(entries, req_map, **extra):
    data = {"requirements": [{"id": f"R{i}", "text": "x", "criterion_ids": ids}
                             for i, ids in enumerate(req_map, 1)],
            "evaluation_criteria": entries}
    data.update(extra)
    return pg.check_evaluation_criteria(data)


class EvaluationLedgerTests(unittest.TestCase):
    """평가 방식은 기관 분류가 아니라 원문에서 온다."""

    def test_technical_with_separate_price_volume_uses_declared_total(self):
        """기술 부문 90점만 원장에 있고 가격은 별책 — 100으로 고치라고 하면 안 된다."""
        self.assertTrue(any("sum to 90, not 100" in f for f in
                            _criteria([{"id": "T", "label": "기술", "weight": 90}], [["T"]])))
        self.assertEqual(_criteria([{"id": "T", "label": "기술", "weight": 90}], [["T"]],
                                   evaluation_total=90), [])

    def test_sub_criteria_must_sum_to_their_parent_not_to_100(self):
        """1단계 기술평가 100 = 정량 20 + 정성 80. 상·하위를 한 번에 더하면 200이 된다."""
        entries = [{"id": "T", "label": "기술", "weight": 100, "stage": "1단계"},
                   {"id": "T1", "label": "정량", "weight": 20, "parent": "T"},
                   {"id": "T2", "label": "정성", "weight": 80, "parent": "T"}]
        self.assertEqual(_criteria(entries, [["T1"], ["T2"]]), [])
        entries[1]["weight"] = 30
        self.assertTrue(any("sub-criteria sum to 110" in f for f in _criteria(entries, [["T1"], ["T2"]])))

    def test_cutoff_is_preserved_not_computed(self):
        """부문 과락(기술 배점한도의 85%)은 기록만 한다 — 게이트는 심사 점수를 예측하지 않는다."""
        entries = [{"id": "T", "label": "기술", "weight": 90, "minimum_ratio": 0.85,
                    "source": "공고 §5 협상적격 기준"},
                   {"id": "P", "label": "가격", "weight": 10}]
        self.assertEqual(_criteria(entries, [["T"], ["P"]]), [])
        entries[0]["minimum_ratio"] = 85  # 퍼센트를 그대로 적은 실수
        self.assertTrue(any("minimum_ratio must be in (0, 1]" in f for f in _criteria(entries, [["T"], ["P"]])))

    def test_undisclosed_weights_are_recorded_not_invented(self):
        entries = [{"id": "T", "label": "기술", "disclosed": False},
                   {"id": "P", "label": "가격", "disclosed": False}]
        self.assertEqual(_criteria(entries, [["T"], ["P"]]), [])
        entries[0]["weight"] = 80
        self.assertTrue(any("undisclosed but carries a weight" in f for f in _criteria(entries, [["T"], ["P"]])))

    def test_parent_with_children_is_mapped_through_its_leaves(self):
        entries = [{"id": "T", "label": "기술", "weight": 100},
                   {"id": "T1", "label": "정량", "weight": 20, "parent": "T"},
                   {"id": "T2", "label": "정성", "weight": 80, "parent": "T"}]
        failures = _criteria(entries, [["T1"]])  # T2만 미대응
        self.assertTrue(any("no requirement mapped: ['T2']" in f for f in failures), failures)

    def test_structural_errors(self):
        cases = [
            ([{"id": "A", "label": "a", "weight": 100, "parent": "Z"}], "unknown parent"),
            ([{"id": "A", "label": "a", "weight": 50, "parent": "B"},
              {"id": "B", "label": "b", "weight": 50, "parent": "A"}], "cyclic"),
            ([{"id": "A", "label": "a", "weight": 100, "minimum_score": 120}], "exceeds its weight"),
            ([{"id": "A", "label": "a", "weight": 100, "disclosed": "yes"}], "disclosed must be a boolean"),
        ]
        for entries, needle in cases:
            with self.subTest(needle=needle):
                self.assertTrue(any(needle in f for f in _criteria(entries, [["A"]])),
                                _criteria(entries, [["A"]]))
        self.assertTrue(any("evaluation_total must be a positive" in f for f in
                            _criteria([{"id": "A", "label": "a", "weight": 100}], [["A"]],
                                      evaluation_total=0)))

    def test_builder_carries_the_declared_total(self):
        meta = {"mode": "draft", "bid_decision": "bid", "requirements": [], "claims": [],
                "evaluation_total": 90,
                "evaluation_criteria": [{"id": "T", "label": "기술", "weight": 90}]}
        with tempfile.TemporaryDirectory() as d:
            mp, ap = Path(d) / "m.json", Path(d) / "a.json"
            mp.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
            proc = run_script(BEST / "scripts/build_audit_from_meta.py", mp, "-o", ap)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(json.loads(ap.read_text(encoding="utf-8"))["evaluation_total"], 90)


class RequirementStrengthTests(unittest.TestCase):
    """필수/권장/선택/조건부/참고 — 권장 분량 초과와 필수 위반은 같은 무게가 아니다."""

    def test_strength_is_derived_from_mandatory_when_absent(self):
        self.assertEqual(pg.requirement_strength({"mandatory": True}), "required")
        self.assertEqual(pg.requirement_strength({"mandatory": False}), "optional")
        self.assertEqual(pg.requirement_strength({}), "required")  # fail-closed

    def test_unsupported_and_contradictory_values_are_schema_errors(self):
        data = ready_data()
        data["requirements"][0]["strength"] = "nice-to-have"
        self.assertTrue(any("unsupported strength" in f for f in pg.validate_schema(data)))
        data["requirements"][0]["strength"] = "optional"  # mandatory:true와 모순
        self.assertTrue(any("contradicts mandatory=True" in f for f in pg.validate_schema(data)))

    def test_conditional_needs_its_condition(self):
        data = ready_data()
        data["requirements"][0].update(strength="conditional")
        data["requirements"][0].pop("mandatory")
        self.assertTrue(any("lacks a condition" in f for f in pg.validate_schema(data)))
        data["requirements"][0]["condition"] = "클라우드 구간을 제안하는 경우"
        self.assertEqual(pg.validate_schema(data), [])
        # 조건부는 필수로 센다 — 미승인이면 차단
        data["requirements"][0].update(state="drafted")
        self.assertTrue(any("R1 is not approved" in f for f in pg.evaluate(data)))

    def test_recommended_not_met_needs_a_rationale_in_submission(self):
        data = ready_data()
        data["requirements"].append({"id": "R2", "text": "분량 30쪽 이내(권장)",
                                     "strength": "recommended", "state": "drafted"})
        failures = pg.evaluate(data)
        self.assertTrue(any("recommended requirement R2 is not met and lacks a rationale" in f
                            for f in failures), failures)
        data["requirements"][1]["rationale"] = "별첨 증빙 포함 34쪽 — 발주처 Q&A에서 권장임을 확인"
        self.assertEqual(pg.evaluate(data), [])

    def test_matrix_maps_korean_strength_words(self):
        for word, want in (("필수", "required"), ("권장", "recommended"), ("선택", "optional"),
                           ("조건부", "conditional"), ("참고", "informational"), ("", "required")):
            with self.subTest(word=word):
                row = bm.normalize({"id": "R1", "필수": word, "support": "O"}, 1)
                self.assertEqual(row["strength"], want)
                self.assertEqual(row["mandatory"], want in pg.MANDATORY_STRENGTHS)
        row = bm.normalize({"id": "R1", "필수": "Y", "강도": "조건부", "support": "O"}, 1)
        self.assertEqual(row["strength"], "conditional")
        self.assertEqual(bm.to_audit_requirements([row])[0]["strength"], "conditional")

    def test_builder_preserves_strength_and_condition(self):
        meta = {"mode": "draft", "bid_decision": "bid", "claims": [],
                "requirements": [{"id": "R1", "text": "x", "strength": "conditional",
                                  "condition": "옵션 제안 시", "state": "pending"}]}
        with tempfile.TemporaryDirectory() as d:
            mp, ap = Path(d) / "m.json", Path(d) / "a.json"
            mp.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(run_script(BEST / "scripts/build_audit_from_meta.py",
                                        mp, "-o", ap).returncode, 0)
            req = json.loads(ap.read_text(encoding="utf-8"))["requirements"][0]
        self.assertEqual((req["strength"], req["condition"]), ("conditional", "옵션 제안 시"))


class RfxTypeTests(unittest.TestCase):
    """문서 종류는 구매 단계와 다른 축이다. RFI라서 검사를 끄는 게 아니라 무엇이 다른지 명시한다."""

    def test_rfx_type_is_validated(self):
        self.assertEqual(pg.validate_context({"rfx_type": "rfi"}), [])
        self.assertTrue(any("rfx_type" in f for f in pg.validate_context({"rfx_type": "tender"})))

    def test_rfi_response_does_not_require_a_public_scoring_ledger(self):
        data = ready_data()
        data["context"] = {"buyer_types": ["public"], "stage": "explore", "rfx_type": "rfi"}
        data["claims"] = []  # 확약 없음
        self.assertFalse(any("evaluation_criteria ledger" in f for f in pg.evaluate(data)))
        data["context"]["rfx_type"] = "rfp"
        self.assertTrue(any("evaluation_criteria ledger" in f for f in pg.evaluate(data)))

    def test_rfi_response_must_not_carry_commitments(self):
        """RFI의 추정치를 확정 계약 약속으로 승격하지 않는다."""
        data = ready_data()
        data["context"] = {"buyer_types": ["private"], "stage": "explore", "rfx_type": "rfi"}
        failures = pg.evaluate(data)  # ready_data의 C1은 commitment
        self.assertTrue(any("commitment in an RFI response" in f for f in failures), failures)

    def test_rfi_keeps_eligibility_and_format_checks(self):
        """한일병원형 RFI: 참여자격·제출 형식 요구는 그대로 검사한다."""
        data = ready_data()
        data["context"] = {"buyer_types": ["healthcare"], "stage": "explore", "rfx_type": "rfi"}
        data["claims"] = []
        data["eligibility"][0]["met"] = False
        data["eligibility"][0]["curable"] = False
        data["attachments"][0]["present"] = False
        failures = pg.evaluate(data)
        self.assertTrue(any("attachment" in f for f in failures), failures)
        self.assertTrue(any("eligib" in f.lower() or "E1" in f for f in failures), failures)


if __name__ == "__main__":
    unittest.main()
