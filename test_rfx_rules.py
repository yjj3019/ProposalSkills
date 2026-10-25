"""Round 9: procurement-document rules change gate behavior (public RFx review). Evaluation methods, requirement strength, and document kinds vary; reducing them to total 100, a mandatory bool, and one RFP prevents faithful ledgers or falsely blocks them. Reproduce public-case rules with synthetic data, excluding originals."""
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
    """Evaluation methods come from source documents, not institution classifications."""

    def test_technical_with_separate_price_volume_uses_declared_total(self):
        """A ledger may contain only technical 90 points with price separately bound; do not require changing it to 100."""
        self.assertTrue(any("sum to 90, not 100" in f for f in
                            _criteria([{"id": "T", "label": "기술", "weight": 90}], [["T"]])))
        self.assertEqual(_criteria([{"id": "T", "label": "기술", "weight": 90}], [["T"]],
                                   evaluation_total=90), [])

    def test_sub_criteria_must_sum_to_their_parent_not_to_100(self):
        """Stage-1 technical 100 = quantitative 20 + qualitative 80; adding parents and children yields 200."""
        entries = [{"id": "T", "label": "기술", "weight": 100, "stage": "1단계"},
                   {"id": "T1", "label": "정량", "weight": 20, "parent": "T"},
                   {"id": "T2", "label": "정성", "weight": 80, "parent": "T"}]
        self.assertEqual(_criteria(entries, [["T1"], ["T2"]]), [])
        entries[1]["weight"] = 30
        self.assertTrue(any("sub-criteria sum to 110" in f for f in _criteria(entries, [["T1"], ["T2"]])))

    def test_cutoff_is_preserved_not_computed(self):
        """Record sectional cutoffs (85% of technical maximum) without predicting evaluation scores."""
        entries = [{"id": "T", "label": "기술", "weight": 90, "minimum_ratio": 0.85,
                    "source": "공고 §5 협상적격 기준"},
                   {"id": "P", "label": "가격", "weight": 10}]
        self.assertEqual(_criteria(entries, [["T"], ["P"]]), [])
        entries[0]["minimum_ratio"] = 85  # Mistakenly recording the percentage directly.
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
        failures = _criteria(entries, [["T1"]])  # Only T2 is unmapped.
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
    """Required/recommended/optional/conditional/reference: recommended-length overruns differ from mandatory violations."""

    def test_strength_is_derived_from_mandatory_when_absent(self):
        self.assertEqual(pg.requirement_strength({"mandatory": True}), "required")
        self.assertEqual(pg.requirement_strength({"mandatory": False}), "optional")
        self.assertEqual(pg.requirement_strength({}), "required")  # fail-closed

    def test_unsupported_and_contradictory_values_are_schema_errors(self):
        data = ready_data()
        data["requirements"][0]["strength"] = "nice-to-have"
        self.assertTrue(any("unsupported strength" in f for f in pg.validate_schema(data)))
        data["requirements"][0]["strength"] = "optional"  # Contradicts mandatory:true.
        self.assertTrue(any("contradicts mandatory=True" in f for f in pg.validate_schema(data)))

    def test_conditional_needs_its_condition(self):
        data = ready_data()
        data["requirements"][0].update(strength="conditional")
        data["requirements"][0].pop("mandatory")
        self.assertTrue(any("lacks a condition" in f for f in pg.validate_schema(data)))
        data["requirements"][0]["condition"] = "클라우드 구간을 제안하는 경우"
        self.assertEqual(pg.validate_schema(data), [])
        # Conditional requirements count as mandatory and block if unapproved.
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
    """Document kind and procurement stage are separate axes; specify RFI differences instead of disabling checks."""

    def test_rfx_type_is_validated(self):
        self.assertEqual(pg.validate_context({"rfx_type": "rfi"}), [])
        self.assertTrue(any("rfx_type" in f for f in pg.validate_context({"rfx_type": "tender"})))

    def test_rfi_response_does_not_require_a_public_scoring_ledger(self):
        data = ready_data()
        data["context"] = {"buyer_types": ["public"], "stage": "explore", "rfx_type": "rfi"}
        data["claims"] = []  # No commitments.
        self.assertFalse(any("evaluation_criteria ledger" in f for f in pg.evaluate(data)))
        data["context"]["rfx_type"] = "rfp"
        self.assertTrue(any("evaluation_criteria ledger" in f for f in pg.evaluate(data)))

    def test_rfi_response_must_not_carry_commitments(self):
        """Do not promote RFI estimates to definite contractual commitments."""
        data = ready_data()
        data["context"] = {"buyer_types": ["private"], "stage": "explore", "rfx_type": "rfi"}
        failures = pg.evaluate(data)  # C1 in ready_data is a commitment.
        self.assertTrue(any("commitment in an RFI response" in f for f in failures), failures)

    def test_rfi_keeps_eligibility_and_format_checks(self):
        """Hanil Hospital-style RFI: qualification and submission-format requirements still apply."""
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
