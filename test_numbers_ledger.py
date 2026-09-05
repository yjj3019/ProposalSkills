"""회귀 테스트 — 수치 원장(F06 잔여): 산술을 게이트가 직접 계산하고, 문서와 대조한다.

`checks.arithmetic: true`는 사람이 기록하는 자기선언이라 본문에 100+200=900이 적혀
있어도 통과했다. 원장에 값을 적으면 합계·비율은 게이트가, 문서 일치는 check_numbers가 본다.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent
BEST = REPO / "skills/create-best-proposal"
DOC = REPO / "skills/create-proposal-document"
FIXTURES = BEST / "fixtures"
CN = DOC / "scripts/check_numbers.py"

sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "skills/create-winning-proposal/scripts"))
sys.path.insert(0, str(BEST / "scripts"))
import ooxml_fixtures as fixtures  # noqa: E402
import proposal_gate as pg  # noqa: E402
import build_audit_from_meta as bam  # noqa: E402
sys.path.insert(0, str(DOC / "scripts"))
import check_numbers as cn  # noqa: E402


def run(*args: object) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", cwd=str(REPO))


def ledger() -> list[dict]:
    return [
        {"id": "N1", "label": "총 사업비", "value": 3700000000, "unit": "KRW",
         "source": "견적서 v3", "components": ["N2", "N3"]},
        {"id": "N2", "label": "구축비", "value": 2500000000, "unit": "KRW", "source": "견적서 v3"},
        {"id": "N3", "label": "유지보수비", "value": 1200000000, "unit": "KRW", "source": "견적서 v3"},
    ]


class ArithmeticTests(unittest.TestCase):
    """합계·비율을 게이트가 실제로 계산한다."""

    def test_correct_ledger_passes(self):
        self.assertEqual(pg.check_numbers(ledger()), [])

    def test_wrong_sum_is_blocked(self):
        bad = ledger()
        bad[0]["value"] = 3900000000
        failures = pg.check_numbers(bad)
        self.assertTrue(any("합계가 맞지 않는다" in f for f in failures), failures)

    def test_mixed_units_in_a_sum_are_blocked(self):
        bad = ledger()
        bad[1]["unit"] = "개월"
        self.assertTrue(any("mixes units" in f for f in pg.check_numbers(bad)))

    def test_percentage_is_recomputed(self):
        entries = ledger() + [{"id": "N4", "label": "유지보수 비중", "value": 30.0, "unit": "%",
                               "percent_of": "N1", "amount": 1200000000}]
        self.assertTrue(any("비율이 맞지 않는다" in f for f in pg.check_numbers(entries)))
        entries[-1]["value"] = 32.4324
        self.assertEqual(pg.check_numbers(entries), [])

    def test_structural_errors_are_reported_with_position(self):
        cases = [
            ([{"id": "N1", "label": "x", "value": "3,700", "unit": "KRW"}], "must be a JSON number"),
            ([{"id": "N1", "label": "x", "value": 1}], "lacks a unit"),
            ([{"label": "x", "value": 1, "unit": "KRW"}], "lacks a non-empty id"),
            ([{"id": "N1", "label": "x", "value": 1, "unit": "KRW"},
              {"id": "N1", "label": "y", "value": 2, "unit": "KRW"}], "duplicate id"),
            ([{"id": "N1", "label": "x", "value": 1, "unit": "KRW", "components": ["ZZ"]}],
             "unknown components"),
            ("not a list", "must be an array"),
        ]
        for entries, needle in cases:
            with self.subTest(needle=needle):
                self.assertTrue(any(needle in f for f in pg.check_numbers(entries)),
                                pg.check_numbers(entries))

    def test_tolerance_allows_rounding(self):
        entries = [
            {"id": "N1", "label": "합계", "value": 100.0, "unit": "KRW", "components": ["N2", "N3"]},
            {"id": "N2", "label": "a", "value": 33.33, "unit": "KRW"},
            {"id": "N3", "label": "b", "value": 66.66, "unit": "KRW"},
        ]
        self.assertEqual(pg.check_numbers(entries), [])  # 0.01 차이는 기본 허용오차 안


class GateBindingTests(unittest.TestCase):
    """제출 모드에서 arithmetic 자기선언은 원장에 결속된다."""

    def _audit(self) -> dict:
        return json.loads((FIXTURES / "audit_ready_financial.json").read_text(encoding="utf-8"))

    def test_submission_requires_a_ledger(self):
        data = self._audit()
        data.pop("numbers")
        self.assertTrue(any("numbers ledger" in f for f in pg.evaluate(data)))

    def test_draft_does_not_require_a_ledger(self):
        data = self._audit()
        data.pop("numbers")
        data.update(mode="draft", artifact_required=False)
        data["checks"]["submission"] = False
        data["package"]["required"] = False
        data["submission"]["cleared"] = False
        self.assertNotIn("numbers", str(pg.evaluate(data)))

    def test_wrong_arithmetic_blocks_even_when_declared_true(self):
        data = self._audit()
        data["numbers"][0]["value"] = 9900000000  # 합계 불일치
        self.assertIs(data["checks"]["arithmetic"], True)
        self.assertTrue(any("합계가 맞지 않는다" in f for f in pg.evaluate(data)))

    def test_builder_preserves_the_ledger(self):
        meta = json.loads((FIXTURES / "meta_sample.json").read_text(encoding="utf-8"))
        meta["numbers"] = ledger()
        built = bam.build_audit(meta)
        self.assertEqual(len(built["numbers"]), 3)
        self.assertEqual(pg.check_numbers(built["numbers"]), [])

    def test_builder_rejects_a_non_object_entry(self):
        meta = json.loads((FIXTURES / "meta_sample.json").read_text(encoding="utf-8"))
        meta["numbers"] = ledger() + ["총 사업비 37억"]
        with self.assertRaises(ValueError) as ctx:
            bam.build_audit(meta)
        self.assertIn("numbers[3]", str(ctx.exception))


class DocumentComparisonTests(unittest.TestCase):
    """원장 값이 실제 문서에 있는지 대조한다(한글 표기 변형 포함)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.entries = self.dir / "numbers.json"
        self.entries.write_text(json.dumps(
            [{"id": "N1", "label": "총 사업비", "value": 3700000000, "unit": "KRW"},
             {"id": "N2", "label": "이관 VM", "value": 400, "unit": "대"},
             {"id": "N3", "label": "내부 소계", "value": 123456, "unit": "KRW", "must_appear": False}],
            ensure_ascii=False), encoding="utf-8")

    def _deck(self, text: str) -> Path:
        return fixtures.pptx(self.dir / "d.pptx", raw={
            "ppt/slides/slide1.xml": f"<a:p><a:r><a:t>{text}</a:t></a:r></a:p>"})

    def _check(self, text: str, *extra: object) -> subprocess.CompletedProcess:
        return run(CN, self._deck(text), "--numbers", self.entries, *extra)

    def test_korean_and_digit_notations_both_match(self):
        for text in ("총 사업비 37억원, 400대 이관",
                     "총 사업비 3,700,000,000원 / 이관 대상 400대",
                     "사업비 3700000000원과 VM 400대"):
            with self.subTest(text=text):
                proc = self._check(text)
                self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_stale_number_in_the_deck_is_blocked(self):
        proc = self._check("총 사업비 35억원, 400대 이관")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("찾지 못했다", proc.stdout)

    def test_digit_boundary_is_respected(self):
        """370억은 37억이 아니다 — 부분 문자열로 통과시키지 않는다."""
        proc = self._check("총 사업비 370억원, 4000대")
        self.assertEqual(proc.returncode, 1)

    def test_must_appear_false_is_skipped(self):
        proc = self._check("총 사업비 37억원, 400대")
        self.assertIn("대조 제외", proc.stdout)
        self.assertNotIn("123456", proc.stdout.replace("123,456", ""))

    def test_emit_records_the_comparison(self):
        out = self.dir / "numbers_check.json"
        proc = self._check("총 사업비 37억원, 400대", "--emit", out)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        data = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(data["checked"], 2)
        self.assertEqual(data["matched"], 2)
        self.assertEqual(data["mismatched"], [])

    def test_audit_source_is_accepted(self):
        audit = self.dir / "audit.json"
        audit.write_text(json.dumps({"numbers": json.loads(self.entries.read_text(encoding="utf-8"))},
                                    ensure_ascii=False), encoding="utf-8")
        proc = run(CN, self._deck("총 사업비 37억원, 400대"), "--audit", audit)
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_broken_document_is_a_usage_error(self):
        bad = self.dir / "bad.pptx"
        bad.write_bytes(b"not a zip")
        proc = run(CN, bad, "--numbers", self.entries)
        self.assertEqual(proc.returncode, 2)


if __name__ == "__main__":
    unittest.main()
