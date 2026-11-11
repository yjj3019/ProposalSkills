"""deck_story_check and plain_language_check: ghost-deck and plain-language rules."""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "skills/create-proposal-document/scripts"))
import deck_story_check as story  # noqa: E402
import plain_language_check as plain  # noqa: E402


def deck(*titles, **extra):
    slides = [{"type": "cover", "title": "표지"}]
    slides += [{"type": "bullets", "title": t, **extra} for t in titles]
    return {"slides": slides}


GOOD = ["노후 장비가 장애의 70%를 차지해 교체가 시급하다", "단계별 이관으로 서비스 중단 없이 전환한다"]


class GhostDeckTests(unittest.TestCase):
    def test_claim_titles_pass_and_structural_slides_are_ignored(self):
        ghost, blocked, _ = story.check(deck(*GOOD, source="x"))
        self.assertEqual(blocked, [])
        self.assertEqual(len(ghost), 2)

    def test_missing_and_duplicate_titles_block_but_labels_only_warn(self):
        _, blocked, warnings = story.check(deck("개요", "짧은 제목", GOOD[0], GOOD[0]))
        self.assertIn("repeats slide", "\n".join(blocked))
        self.assertEqual(sum("label, not a claim" in w for w in warnings), 2)
        self.assertFalse(any("label" in b for b in blocked))
        _, blocked, _ = story.check({"slides": [{"type": "bullets", "title": ""}]})
        self.assertTrue(any("no title" in b for b in blocked))

    def test_noun_phrase_title_and_unsourced_figure_warn_without_blocking(self):
        _, blocked, warnings = story.check(deck("서비스 중단 최소화를 위한 단계별 이관 방안"))
        self.assertEqual(blocked, [])
        self.assertTrue(any("noun phrase" in w for w in warnings))
        slide = deck(GOOD[0])
        _, _, warnings = story.check(slide)
        self.assertTrue(any("no `source`" in w for w in warnings))

    def test_cli_exit_codes_and_strict(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "slides.json"
            path.write_text(json.dumps(deck(GOOD[0]), ensure_ascii=False), encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(story.main([str(path)]), 0)
                self.assertEqual(story.main([str(path), "--strict"]), 1)
            with redirect_stderr(io.StringIO()):
                self.assertEqual(story.main([str(Path(tmp) / "none.json")]), 2)


class PlainLanguageTests(unittest.TestCase):
    def rules(self, text, **kw):
        return {w.split("]")[0][1:] for w in plain.lint(text, **kw)}

    def test_long_sentence(self):
        self.assertIn("long-sentence", self.rules("가" * 120 + "."))
        self.assertNotIn("long-sentence", self.rules("짧은 문장이다."))

    def test_acronym_needs_expansion_at_first_use(self):
        self.assertIn("acronym", self.rules("SLA를 준수한다."))
        self.assertNotIn("acronym", self.rules("서비스 수준 협약(SLA)을 준수한다. SLA는 월 단위로 보고한다."))
        self.assertNotIn("acronym", self.rules("SLA(서비스 수준 협약)을 준수한다."))
        self.assertNotIn("acronym", self.rules("RFP 요구를 따른다."))

    def test_self_narration_filler_and_passive_stack(self):
        found = self.rules("본 장에서는 구성을 살펴보겠습니다. 점검이 이루어지게 됩니다. 보안이 중요하다고 할 수 있습니다.")
        self.assertTrue({"self-narration", "passive-stack", "filler"} <= found)

    def test_clean_text_and_cli(self):
        self.assertEqual(plain.lint("PM이 매주 금요일까지 보고서를 제출한다."), [])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.md"
            path.write_text("본 장에서는 살펴보겠습니다.", encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(plain.main([str(path)]), 0)
                self.assertEqual(plain.main([str(path), "--strict"]), 1)
            with redirect_stderr(io.StringIO()):
                self.assertEqual(plain.main([str(Path(tmp) / "none.md")]), 2)


if __name__ == "__main__":
    unittest.main()
