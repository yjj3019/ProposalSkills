import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "skills/create-proposal-document/scripts"))
from quality_gate import read_names, run, blocking  # noqa: E402


def pptx(path: Path, texts: dict[int, str], extra: str = "") -> None:
    with zipfile.ZipFile(path, "w") as z:
        for number, text in texts.items():
            z.writestr(f"ppt/slides/slide{number}.xml", f"<p><t>{text}</t>{extra}</p>")


class QualityGateTests(unittest.TestCase):
    def test_slide_numbers_are_natural(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "deck.pptx"
            pptx(path, {i: "최고" if i == 11 else "일반" for i in range(1, 12)})
            self.assertIn("슬라이드 11", run(path, [], set(), "ko")[0])

    def test_evidence_words_do_not_exempt_overclaim(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "deck.pptx"
            pptx(path, {1: "평가 기준과 출처가 있어도 우리는 최고입니다"})
            self.assertTrue(any("최고" in failure for failure in run(path, [], set(), "ko")))

    def test_normal_technical_english_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "deck.pptx"
            pptx(path, {1: "This change is leading to better throughput; payload = []"})
            self.assertEqual(run(path, [], set(), "en"), [])

    def test_names_preserve_spaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "names.txt"
            path.write_text("ABC 금융 그룹\n", encoding="utf-8")
            self.assertEqual(read_names(path), ["ABC 금융 그룹"])

    def test_theme_colors_are_not_claimed_as_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "deck.pptx"
            pptx(path, {1: "일반"}, '<a:schemeClr val="accent6"/>')
            self.assertTrue(any("NOT INSPECTED" in failure
                                for failure in run(path, [], {"1F3864"}, "ko")))

    def test_unused_master_colors_do_not_fail_palette(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "deck.pptx"
            pptx(path, {1: "일반", 2: "일반"}, '<a:srgbClr val="1F3864"/>')
            with zipfile.ZipFile(path, "a") as z:
                z.writestr("ppt/slideMasters/slideMaster1.xml",
                           '<a:srgbClr val="E97132"/>')
            failures = run(path, [], {"1F3864"}, "ko")
            self.assertFalse(any("#E97132" in failure for failure in failures))
            self.assertTrue(any("NOT INSPECTED" in failure for failure in failures))

    def test_theme_notice_is_nonblocking(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "deck.pptx"
            pptx(path, {1: "일반"}, '<a:schemeClr val="accent6"/>')
            items = run(path, [], {"1F3864"}, "ko")
            self.assertTrue(any("NOT INSPECTED" in f for f in items))
            self.assertEqual(blocking(items), [])  # 테마 경고만 있으면 차단 0건

    def test_draft_marker_warns_in_draft_blocks_in_submission(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "deck.pptx"
            pptx(path, {1: "투입인력: 입력요망"})
            draft = run(path, [], set(), "ko", "draft")
            self.assertEqual(blocking(draft), [])  # 초안: 비차단 경고
            self.assertTrue(any("검토필요" in f for f in draft))
            sub = run(path, [], set(), "ko", "submission")
            self.assertTrue(blocking(sub))  # 제출: 차단

    def test_hard_placeholder_blocks_in_both_stages(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "deck.pptx"
            pptx(path, {1: "본문 TBD 잔존"})
            self.assertTrue(blocking(run(path, [], set(), "ko", "draft")))
            self.assertTrue(blocking(run(path, [], set(), "ko", "submission")))

    # --- C4 네거티브 골든: 시뮬 B10(과장어)·C10(플레이스홀더) 승격 회귀 ---
    def test_golden_overclaim_deck_is_blocked(self):
        """B10형: 과장어 주입 덱은 근거 유무와 무관하게 차단되어야 한다."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "b10.pptx"
            pptx(path, {1: "본 솔루션은 업계 1위이며 무중단 100% 완벽 대응",
                        2: "world-class and best-in-class throughput"})
            ko = blocking(run(path, [], set(), "ko"))
            en = blocking(run(path, [], set(), "en"))
            self.assertTrue(any("무중단" in f or "100%" in f or "완벽" in f or "업계 1위" in f for f in ko))
            self.assertTrue(any("world-class" in f or "best-in-class" in f for f in en))

    def test_golden_placeholder_deck_is_blocked(self):
        """C10형: 플레이스홀더 잔존 덱은 제출 단계에서 차단되어야 한다."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c10.pptx"
            pptx(path, {1: "구성도 placeholder", 2: "담당자 ○○○ 기재"})
            self.assertTrue(blocking(run(path, [], set(), "ko", "submission")))


if __name__ == "__main__":
    unittest.main()
