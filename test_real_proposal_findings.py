"""Round 13: gaps discovered with a real proposal. The first twelve batches used repository fixtures. Running a 9-slide public-sector RHEL-standardization proposal in submission mode found 18 justified findings without excessive blocking, but missed three issues. Reproduce rules with synthetic data without including the original in this public repository."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "skills/create-winning-proposal/scripts"))
sys.path.insert(0, str(REPO / "skills/create-proposal-document/scripts"))
import proposal_gate as pg  # noqa: E402
import quality_gate as qg  # noqa: E402
from test_proposal_gate import ready_data  # noqa: E402


class VendorDependentCommitmentTests(unittest.TestCase):
    """Manufacturer-dependent commitments previously passed as bidder commitments. "심각도1 1시간 내 대응" is valid only if the manufacturer SLA applies to the relevant contract/subscription tier. Citing public documentation differs from obtaining applicability confirmation for this engagement."""

    def _data(self, **claim_over) -> dict:
        data = ready_data()
        data["claims"][0].update(claim_over)
        return data

    def test_citing_a_vendor_document_is_not_a_confirmation(self):
        data = self._data(depends_on_vendor="Red Hat",
                          evidence_refs=["제조사 SLA 공개 문서"])
        failures = pg.evaluate(data)
        self.assertTrue(any("depends on Red Hat" in f for f in failures), failures)

    def test_a_present_confirmation_clears_it(self):
        data = self._data(depends_on_vendor="Red Hat")
        data["vendor_confirmations"] = [
            {"id": "V1", "vendor": "Red Hat", "kind": "support", "required": True, "present": True}]
        self.assertEqual(pg.evaluate(data), [])

    def test_a_confirmation_for_another_vendor_does_not_count(self):
        data = self._data(depends_on_vendor="Red Hat")
        data["vendor_confirmations"] = [
            {"id": "V1", "vendor": "다른 제조사", "kind": "support", "required": True, "present": True}]
        self.assertTrue(any("depends on Red Hat" in f for f in pg.evaluate(data)))

    def test_a_promised_but_not_submitted_confirmation_does_not_count(self):
        data = self._data(depends_on_vendor="Red Hat")
        data["vendor_confirmations"] = [
            {"id": "V1", "vendor": "Red Hat", "kind": "support", "required": True, "present": False}]
        failures = pg.evaluate(data)
        self.assertTrue(any("depends on Red Hat" in f for f in failures))
        self.assertTrue(any("V1" in f and "missing" in f for f in failures))

    def test_vendor_name_must_be_a_real_name(self):
        self.assertTrue(any("must be a non-empty vendor name" in f
                            for f in pg.evaluate(self._data(depends_on_vendor="  "))))

    def test_draft_mode_does_not_demand_it_yet(self):
        data = self._data(depends_on_vendor="Red Hat")
        data["mode"] = "draft"
        data["artifact_required"] = False
        self.assertFalse(any("depends on Red Hat" in f for f in pg.evaluate(data)))


class TimeSensitiveClaimTests(unittest.TestCase):
    """Lifecycle, EOL, and version claims become outdated without reference dates."""

    def _claim(self, **over) -> dict:
        data = ready_data()
        data["claims"].append({"id": "C9", "text": "해당 제품은 2032년까지 지원된다",
                               "kind": "material", "status": "supported",
                               "evidence_refs": ["제조사 라이프사이클 문서"], **over})
        return data

    def test_missing_as_of_blocks(self):
        self.assertTrue(any("lacks a valid 'as_of'" in f
                            for f in pg.evaluate(self._claim(time_sensitive=True))))

    def test_iso_dates_are_accepted(self):
        for value in ("2026-09", "2026-09-06"):
            with self.subTest(value=value):
                self.assertEqual(pg.evaluate(self._claim(time_sensitive=True, as_of=value)), [])

    def test_free_text_is_not_a_date(self):
        for value in ("2026년 여름", "최근", "2026/09", "2026-13"):
            with self.subTest(value=value):
                self.assertTrue(any("lacks a valid 'as_of'" in f
                                    for f in pg.evaluate(self._claim(time_sensitive=True, as_of=value))))

    def test_untagged_claims_are_unaffected(self):
        self.assertEqual(pg.evaluate(self._claim()), [])


class NumberRelationTests(unittest.TestCase):
    """SLA tables require correct relationships between values, not merely valid individual values."""

    SLA = [{"id": "S3F", "label": "심각도3 최초", "value": 4, "unit": "시간", "at_most": "S3C"},
           {"id": "S3C", "label": "심각도3 지속", "value": 8, "unit": "시간"},
           {"id": "S4F", "label": "심각도4 최초", "value": 8, "unit": "시간", "at_least": "S3F"},
           {"id": "S4C", "label": "심각도4 지속", "value": 2, "unit": "일", "at_least": "S3C"}]

    def _rows(self, **over):
        rows = [dict(r) for r in self.SLA]
        for rid, changes in over.items():
            next(r for r in rows if r["id"] == rid).update(changes)
        return rows

    def test_a_consistent_sla_table_passes(self):
        self.assertEqual(pg.check_numbers(self._rows()), [])

    def test_first_response_longer_than_continued_is_blocked(self):
        failures = pg.check_numbers(self._rows(S3F={"value": 12}))
        self.assertTrue(any("S3F" in f and "이하" in f for f in failures), failures)

    def test_units_are_converted_before_comparing(self):
        """Detect swapped values where units change, such as 4시간 → 2일."""
        failures = pg.check_numbers(self._rows(S4C={"value": 1, "unit": "분"}))
        self.assertTrue(any("S4C" in f and "이상" in f for f in failures), failures)

    def test_non_duration_units_compare_only_within_the_same_unit(self):
        same = [{"id": "A", "label": "a", "value": 3, "unit": "대", "at_most": "B"},
                {"id": "B", "label": "b", "value": 5, "unit": "대"}]
        self.assertEqual(pg.check_numbers(same), [])
        mixed = [{"id": "A", "label": "a", "value": 3, "unit": "대", "at_most": "B"},
                 {"id": "B", "label": "b", "value": 5, "unit": "명"}]
        self.assertTrue(any("units differ" in f for f in pg.check_numbers(mixed)))

    def test_structural_errors(self):
        for rows, needle in (
            ([{"id": "A", "label": "a", "value": 1, "unit": "시간", "at_most": "Z"}], "unknown at_most"),
            ([{"id": "A", "label": "a", "value": 1, "unit": "시간", "at_least": "A"}], "compares itself"),
        ):
            with self.subTest(needle=needle):
                self.assertTrue(any(needle in f for f in pg.check_numbers(rows)),
                                pg.check_numbers(rows))


class SuperlativeVocabularyTests(unittest.TestCase):
    """Unsupported superlative modifiers, excluding factual grade names."""

    def test_ungrounded_superlatives_are_flagged(self):
        for phrase, word in (("최첨단 보안 기술 적용", "최첨단"), ("압도적 성능", "압도적"),
                             ("탁월한 안정성", "탁월한"), ("독보적 경쟁력", "독보적"),
                             ("최상위의 품질", "최상위")):
            with self.subTest(phrase=phrase):
                self.assertIn(word, qg.BANNED_KO)
                self.assertTrue(qg.banned_hits(phrase, word), phrase)

    def test_factual_tier_names_are_not_flagged(self):
        """Actual partner/certification grade names are factual descriptions."""
        for phrase in ("Red Hat 최상위 파트너 등급", "최상위 인증 자격 보유",
                       "제조사 최고 등급 인증"):
            with self.subTest(phrase=phrase):
                hits = [w for w in qg.BANNED_KO if qg.banned_hits(phrase, w)]
                self.assertEqual(hits, [], phrase)


if __name__ == "__main__":
    unittest.main()
