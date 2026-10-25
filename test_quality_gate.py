import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "skills/create-proposal-document/scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ooxml_fixtures as fixtures  # noqa: E402
from quality_gate import read_names, run, blocking  # noqa: E402


def pptx(path: Path, texts: dict[int, str], extra: str = "") -> None:
    """Build valid packages with shared fixtures; never use missing-required-part files as positive controls."""
    fixtures.pptx(path, raw={f"ppt/slides/slide{number}.xml": f"<p><t>{text}</t>{extra}</p>"
                             for number, text in texts.items()})


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
            self.assertEqual(blocking(items), [])  # Theme warnings alone produce zero blockers.

    def test_draft_marker_warns_in_draft_blocks_in_submission(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "deck.pptx"
            pptx(path, {1: "투입인력: 입력요망"})
            draft = run(path, [], set(), "ko", "draft")
            self.assertEqual(blocking(draft), [])  # Draft: nonblocking warning.
            self.assertTrue(any("검토필요" in f for f in draft))
            sub = run(path, [], set(), "ko", "submission")
            self.assertTrue(blocking(sub))  # Submission: blocker.

    def test_hard_placeholder_blocks_in_both_stages(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "deck.pptx"
            pptx(path, {1: "본문 TBD 잔존"})
            self.assertTrue(blocking(run(path, [], set(), "ko", "draft")))
            self.assertTrue(blocking(run(path, [], set(), "ko", "submission")))

    # --- C4 negative goldens: simulation B10 exaggeration/C10 placeholder promotion regressions ---
    def test_golden_overclaim_deck_is_blocked(self):
        """B10: decks with injected exaggerated language must block regardless of evidence."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "b10.pptx"
            pptx(path, {1: "본 솔루션은 업계 1위이며 무중단 100% 완벽 대응",
                        2: "world-class and best-in-class throughput"})
            ko = blocking(run(path, [], set(), "ko"))
            en = blocking(run(path, [], set(), "en"))
            self.assertTrue(any("무중단" in f or "100%" in f or "완벽" in f or "업계 1위" in f for f in ko))
            self.assertTrue(any("world-class" in f or "best-in-class" in f for f in en))

    def test_golden_placeholder_deck_is_blocked(self):
        """C10: decks with unresolved placeholders must block at submission."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c10.pptx"
            pptx(path, {1: "구성도 placeholder", 2: "담당자 ○○○ 기재"})
            self.assertTrue(blocking(run(path, [], set(), "ko", "submission")))


if __name__ == "__main__":
    unittest.main()
