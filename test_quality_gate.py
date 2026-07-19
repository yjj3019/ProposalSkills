import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "skills/create-proposal-document/scripts"))
from quality_gate import read_names, run  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
