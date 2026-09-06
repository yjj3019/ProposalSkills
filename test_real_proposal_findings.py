"""13차 — 실제 제안서를 게이트에 태워 찾은 구멍.

열두 배치는 전부 이 저장소가 만든 픽스처 기준이었다. 실제 공공 제안서(RHEL 표준화,
9장) 한 건을 제출 모드로 태워 보니 게이트가 잡은 18건은 모두 근거가 있었고 과민 차단은
없었다. 대신 **잡지 못한 것**이 세 가지 나왔다. 원문은 싣지 않고 규칙만 합성 데이터로
재현한다(공개 저장소).
"""
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
    """제조사에 기대는 확약이 자사 확약처럼 통과했다.

    "심각도1 1시간 내 대응"은 제조사 SLA가 그 계약·구독 등급에 적용될 때만 성립한다.
    제조사 공개 문서를 인용하는 것과, 이 사업에 적용된다는 확약을 받는 것은 다르다.
    """

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
    """라이프사이클·EOL·버전 주장은 기준일이 없으면 시간이 지나 거짓이 된다."""

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
    """SLA 표는 값 하나하나가 아니라 값 사이의 관계가 맞아야 한다."""

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
        """4시간 → 2일처럼 단위가 바뀌는 자리에서 뒤바뀐 값을 잡는다."""
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
    """근거를 붙일 수 없는 최상급 수식어. 사실 명칭인 등급 표기는 제외한다."""

    def test_ungrounded_superlatives_are_flagged(self):
        for phrase, word in (("최첨단 보안 기술 적용", "최첨단"), ("압도적 성능", "압도적"),
                             ("탁월한 안정성", "탁월한"), ("독보적 경쟁력", "독보적"),
                             ("최상위의 품질", "최상위")):
            with self.subTest(phrase=phrase):
                self.assertIn(word, qg.BANNED_KO)
                self.assertTrue(qg.banned_hits(phrase, word), phrase)

    def test_factual_tier_names_are_not_flagged(self):
        """파트너·인증 등급의 실제 명칭은 사실 서술이다."""
        for phrase in ("Red Hat 최상위 파트너 등급", "최상위 인증 자격 보유",
                       "제조사 최고 등급 인증"):
            with self.subTest(phrase=phrase):
                hits = [w for w in qg.BANNED_KO if qg.banned_hits(phrase, w)]
                self.assertEqual(hits, [], phrase)


if __name__ == "__main__":
    unittest.main()
