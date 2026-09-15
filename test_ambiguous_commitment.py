"""회귀 테스트 — 모호 확약(AMBIGUOUS_COMMITMENT) 경고.

제안사 행위를 "가능/예정/검토"로 흐린 문장은 잡되, 조건 주체가 명시된 문장·기능 설명·
발주처 주어 문장은 잡지 않는다. 오탐 검증 전까지 제출을 막지 않는 경고여야 한다.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "skills/create-proposal-document/scripts"))
sys.path.insert(0, str(REPO))
import ooxml_fixtures as fixtures  # noqa: E402
from quality_gate import ambiguous_commitments, blocking, run  # noqa: E402


class DetectionTests(unittest.TestCase):
    def test_vague_commitments_are_detected(self):
        for sentence in ("필요 시 기술지원이 가능합니다.",
                         "성능 저하 시 튜닝 지원 예정입니다.",
                         "개선 방안을 적극 검토하겠습니다.",
                         "요청 시 협의 가능"):
            with self.subTest(sentence=sentence):
                self.assertEqual(len(ambiguous_commitments(sentence)), 1)

    def test_condition_owned_by_named_party_is_not_flagged(self):
        self.assertEqual(ambiguous_commitments("발주처가 승인하는 경우 추가 교육 제공이 가능합니다."), [])

    def test_capability_description_is_not_flagged(self):
        for sentence in ("클러스터는 노드 추가로 수평 확장이 가능합니다.",
                         "API로 외부 시스템과 연동할 수 있습니다."):
            with self.subTest(sentence=sentence):
                self.assertEqual(ambiguous_commitments(sentence), [])

    def test_buyer_as_subject_is_not_flagged(self):
        self.assertEqual(ambiguous_commitments("발주처는 결과 보고서를 검토할 수 있습니다."), [])

    def test_quantified_commitment_is_not_flagged(self):
        self.assertEqual(ambiguous_commitments("Critical 장애 접수 후 30분 이내 1차 대응이 가능합니다."), [])

    def test_judged_per_sentence_not_per_block(self):
        block = "월 1회 정기점검을 수행합니다. 필요 시 기술지원이 가능합니다."
        self.assertEqual(ambiguous_commitments(block), ["필요 시 기술지원이 가능합니다."])


class GateContractTests(unittest.TestCase):
    def _deck(self, tmp: str, text: str) -> Path:
        path = Path(tmp) / "deck.pptx"
        fixtures.pptx(path, raw={"ppt/slides/slide1.xml": f"<p><t>{text}</t></p>"})
        return path

    def test_warning_never_blocks_submission(self):
        with tempfile.TemporaryDirectory() as tmp:
            items = run(self._deck(tmp, "필요 시 기술지원이 가능합니다."), [], set(), "ko", "submission")
            self.assertTrue(any(i.startswith("[모호확약]") for i in items))
            self.assertEqual(blocking(items), [])

    def test_english_only_check_skips_korean_heuristic(self):
        with tempfile.TemporaryDirectory() as tmp:
            items = run(self._deck(tmp, "필요 시 기술지원이 가능합니다."), [], set(), "en", "submission")
            self.assertFalse(any(i.startswith("[모호확약]") for i in items))

    def test_overclaim_still_blocks_alongside_the_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            items = run(self._deck(tmp, "무중단 서비스 지원이 가능합니다."), [], set(), "ko", "submission")
            self.assertTrue(any(i.startswith("[모호확약]") for i in items))
            self.assertTrue(any("무중단" in i for i in blocking(items)))


if __name__ == "__main__":
    unittest.main()
