"""회귀 테스트 — 제안 맥락 분류(F07 축소판).

분류가 문서에만 있으면 검증되지 않는다. 이 테스트는 분류가 실제로 **게이트 요구사항을
바꾸는지**를 고정한다. 업종별 서술 지침의 타당성은 사람이 판단할 영역이다.
"""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent
BEST = REPO / "skills/create-best-proposal"
FIXTURES = BEST / "fixtures"
SECTORS = REPO / "skills/create-winning-proposal/references/sectors"

sys.path.insert(0, str(REPO / "skills/create-winning-proposal/scripts"))
sys.path.insert(0, str(BEST / "scripts"))
import proposal_gate as pg  # noqa: E402
import build_audit_from_meta as bam  # noqa: E402


def audit() -> dict:
    return json.loads((FIXTURES / "audit_ready_financial.json").read_text(encoding="utf-8"))


def public_audit() -> dict:
    data = audit()
    data["context"] = {"buyer_types": ["public"], "engagement": "build",
                       "stage": "final-submission", "reading_mode": "print-evaluation"}
    data["evaluation_criteria"] = [
        {"id": "E-TECH", "label": "기술평가", "weight": 80},
        {"id": "E-PRICE", "label": "가격평가", "weight": 20},
    ]
    data["requirements"][0]["criterion_ids"] = ["E-TECH"]
    data["requirements"][1]["criterion_ids"] = ["E-PRICE"]
    return data


class AxisValidationTests(unittest.TestCase):
    def test_valid_combinations_pass(self):
        for ctx in ({"buyer_types": ["public", "healthcare"]},
                    {"buyer_types": ["education"], "engagement": "education"},
                    {"stage": "presentation", "reading_mode": "screen-presentation"},
                    {"constraints": ["sensitive-data", "closed-network"]},
                    {}):
            with self.subTest(ctx=ctx):
                self.assertEqual(pg.validate_context(ctx), [])

    def test_unknown_values_are_rejected(self):
        cases = [({"buyer_types": ["hospital"]}, "buyer_types"),
                 ({"engagement": "구축"}, "engagement"),
                 ({"stage": "submitted"}, "stage"),
                 ({"reading_mode": "projector"}, "reading_mode"),
                 ({"constraints": ["gdpr"]}, "constraints"),
                 ({"buyer_types": []}, "non-empty"),
                 ("public", "must be an object")]
        for ctx, needle in cases:
            with self.subTest(ctx=ctx):
                self.assertTrue(any(needle in f for f in pg.validate_context(ctx)),
                                pg.validate_context(ctx))

    def test_missing_context_is_backward_compatible(self):
        self.assertEqual(pg.validate_context(None), [])
        self.assertEqual(pg.evaluate(audit()), [])


class PublicProcurementTests(unittest.TestCase):
    """공공 + 제출 단계면 평가표가 필수다."""

    def test_public_submission_requires_the_criteria_ledger(self):
        data = public_audit()
        data.pop("evaluation_criteria")
        self.assertTrue(any("evaluation_criteria ledger" in f for f in pg.evaluate(data)))

    def test_private_buyer_does_not_require_it(self):
        data = public_audit()
        data["context"]["buyer_types"] = ["private"]
        data.pop("evaluation_criteria")
        for req in data["requirements"]:
            req.pop("criterion_ids", None)
        self.assertEqual(pg.evaluate(data), [])

    def test_complete_public_audit_passes(self):
        self.assertEqual(pg.evaluate(public_audit()), [])

    def test_weights_must_sum_to_100(self):
        data = public_audit()
        data["evaluation_criteria"][1]["weight"] = 30
        self.assertTrue(any("sum to 110" in f for f in pg.evaluate(data)))

    def test_criterion_without_a_requirement_is_blocked(self):
        data = public_audit()
        data["requirements"][1].pop("criterion_ids")
        failures = pg.evaluate(data)
        self.assertTrue(any("no requirement mapped" in f and "E-PRICE" in f for f in failures), failures)

    def test_requirement_referencing_an_unknown_criterion_is_blocked(self):
        data = public_audit()
        data["requirements"][0]["criterion_ids"] = ["E-NOPE"]
        self.assertTrue(any("unknown evaluation criteria" in f for f in pg.evaluate(data)))

    def test_structural_errors_are_reported(self):
        for mutate, needle in (
                (lambda d: d["evaluation_criteria"].append({"label": "x", "weight": 0}), "lacks a non-empty id"),
                (lambda d: d["evaluation_criteria"].append({"id": "E-TECH", "label": "dup", "weight": 0}), "duplicate id"),
                (lambda d: d["evaluation_criteria"][0].update(weight="80"), "weight must be"),
                (lambda d: d["evaluation_criteria"][0].update(label=""), "lacks a label"),
                (lambda d: d.update(evaluation_criteria="기술 80 가격 20"), "must be an array")):
            with self.subTest(needle=needle):
                data = public_audit()
                mutate(data)
                self.assertTrue(any(needle in f for f in pg.evaluate(data)), pg.evaluate(data))


class ReadingModeTests(unittest.TestCase):
    """읽는 조건과 실제 장표 규격이 어긋나면 잡는다."""

    def test_presentation_context_rejects_a_submission_deck(self):
        data = public_audit()
        data["context"]["reading_mode"] = "screen-presentation"
        data["render"]["output_profile"] = "detailed-submission"
        self.assertTrue(any("expects deck profile" in f for f in pg.evaluate(data)))

    def test_matching_profile_passes(self):
        data = public_audit()
        data["context"]["reading_mode"] = "screen-presentation"
        data["render"]["output_profile"] = "presentation"
        self.assertEqual(pg.evaluate(data), [])

    def test_no_profile_recorded_is_not_a_failure(self):
        data = public_audit()
        data["context"]["reading_mode"] = "screen-presentation"
        self.assertNotIn("output_profile", data["render"])
        self.assertEqual(pg.evaluate(data), [])


class SensitiveDataTests(unittest.TestCase):
    def test_sensitive_data_demands_passed_package_checks(self):
        data = public_audit()
        data["context"]["constraints"] = ["sensitive-data"]
        data["package"]["checks"]["hidden-content"] = "not-applicable"
        failures = pg.evaluate(data)
        self.assertTrue(any("sensitive-data" in f and "hidden-content" in f for f in failures), failures)

    def test_without_the_constraint_not_applicable_is_allowed(self):
        data = public_audit()
        data["package"]["checks"]["macros"] = "not-applicable"
        self.assertEqual(pg.evaluate(data), [])


class BuilderPassthroughTests(unittest.TestCase):
    def _meta(self) -> dict:
        return json.loads((FIXTURES / "meta_sample.json").read_text(encoding="utf-8"))

    def test_context_and_criteria_survive_conversion(self):
        meta = self._meta()
        meta["context"] = {"buyer_types": ["public"], "stage": "rfp-response"}
        meta["evaluation_criteria"] = [{"id": "E1", "label": "기술", "weight": 100}]
        meta["requirements"][0]["criterion_ids"] = ["E1"]
        built = bam.build_audit(meta)
        self.assertEqual(built["context"]["buyer_types"], ["public"])
        self.assertEqual(len(built["evaluation_criteria"]), 1)
        self.assertEqual(built["requirements"][0]["criterion_ids"], ["E1"])

    def test_malformed_inputs_are_rejected_with_position(self):
        meta = self._meta()
        meta["evaluation_criteria"] = [{"id": "E1", "label": "기술", "weight": 100}, "가격 20"]
        with self.assertRaises(ValueError) as ctx:
            bam.build_audit(meta)
        self.assertIn("evaluation_criteria[1]", str(ctx.exception))
        meta = self._meta()
        meta["context"] = "공공"
        with self.assertRaises(ValueError):
            bam.build_audit(meta)


class SectorDocumentationTests(unittest.TestCase):
    """제공하는 것과 제공하지 않는 것을 문서가 분명히 말해야 한다."""

    def test_only_the_public_profile_ships(self):
        profiles = sorted(p.name for p in SECTORS.glob("*.md"))
        self.assertEqual(profiles, ["README.md", "public.md"])

    def test_readme_states_why_the_others_are_absent(self):
        text = (SECTORS / "README.md").read_text(encoding="utf-8")
        self.assertIn("검증할 수 있을 때만", text)
        for axis in ("buyer_types", "engagement", "stage", "reading_mode", "constraints"):
            self.assertIn(axis, text, axis)

    def test_public_profile_separates_machine_checks_from_judgement(self):
        text = (SECTORS / "public.md").read_text(encoding="utf-8")
        self.assertIn("기계가 검사하는 것", text)
        self.assertIn("검사하지 않는 것", text)
        self.assertIn("evaluation_criteria", text)

    def test_documented_axis_values_match_the_code(self):
        text = (SECTORS / "README.md").read_text(encoding="utf-8")
        for value in (pg.BUYER_TYPES | pg.STAGES | pg.READING_MODES | pg.CONSTRAINTS):
            self.assertIn(value, text, f"문서에 없는 값: {value}")


if __name__ == "__main__":
    unittest.main()
