"""Routing lint: each skill description keeps the signal terms that its trigger phrases rely on.

Deterministic and offline. It catches a description edit that silently drops the vocabulary real requests use
and a negative phrase that would collide with a skill's route terms. It does not measure model behaviour.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

import install_skill

REPO = Path(__file__).resolve().parent
CASES = json.loads((REPO / "references" / "trigger-eval-cases.json").read_text(encoding="utf-8"))
CASES = {k: v for k, v in CASES.items() if not k.startswith("_")}


def description(skill: str) -> str:
    fm = install_skill.parse_frontmatter((REPO / "skills" / skill / "SKILL.md").read_text(encoding="utf-8"))
    return str(fm.get("description", "")).lower()


def words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9가-힣/_-]+", text.lower()))


class TriggerLintTests(unittest.TestCase):
    def test_every_skill_has_cases_and_enough_of_them(self):
        self.assertEqual(set(CASES), set(install_skill.available_skills()))
        for skill, case in CASES.items():
            self.assertGreaterEqual(len(case["should_trigger"]), 2, skill)
            self.assertGreaterEqual(len(case["should_not_trigger"]), 2, skill)

    def test_description_carries_the_route_terms(self):
        for skill, case in CASES.items():
            text = description(skill)
            missing = [t for t in case["route_terms"] if t.lower() not in text]
            self.assertLessEqual(len(missing), len(case["route_terms"]) // 3,
                                 f"{skill}: description lost route terms {missing}")

    def test_positive_phrases_contain_a_route_term_or_name_the_skill(self):
        for skill, case in CASES.items():
            terms = {t.lower() for t in case["route_terms"]}
            for phrase in case["should_trigger"]:
                low = phrase.lower()
                self.assertTrue(skill in low or any(t in low for t in terms), f"{skill}: {phrase!r}")

    def test_negative_phrases_do_not_hit_any_route_term(self):
        for skill, case in CASES.items():
            terms = {t.lower() for t in case["route_terms"]}
            for phrase in case["should_not_trigger"]:
                self.assertFalse(words(phrase) & terms, f"{skill}: {phrase!r} collides with a route term")

    def test_siblings_are_explicit_only_and_flagship_is_implicit(self):
        for skill in CASES:
            fm = install_skill.parse_frontmatter((REPO / "skills" / skill / "SKILL.md").read_text(encoding="utf-8"))
            explicit_only = str(fm.get("disable-model-invocation", "")).lower() == "true"
            self.assertEqual(explicit_only, skill != "create-best-proposal", skill)


if __name__ == "__main__":
    unittest.main()
