"""Round 11: engagement type changes outlines. Merely storing classification is insufficient; using an IT implementation outline for engagement=operate only replaces institution names. Only implementation, maintenance, and technical-response outlines have repository evidence; do not invent or force archetypes for unmapped engagements."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
from test_support import run_script  # noqa: E402
BEST = REPO / "skills/create-best-proposal"
WIN = REPO / "skills/create-winning-proposal"
DOC = REPO / "skills/create-proposal-document"
sys.path.insert(0, str(WIN / "scripts"))
import proposal_gate as pg  # noqa: E402


def outline(engagement: str | None, **over) -> list[str]:
    data = {"mode": "submission"}
    if engagement:
        data["context"] = {"engagement": engagement}
    data.update(over)
    return pg.check_outline(data)


def titles(*names: str) -> list[dict]:
    return [{"title": n} for n in names]


BUILD_OK = titles("사업 범위", "구축 방안", "추진 일정", "시험 및 검수", "추진체계")
MAINT_OK = titles("지원 대상 제품", "지원 체계", "SLA", "장애 대응")


class ArchetypeMatchingTests(unittest.TestCase):
    def test_engagement_picks_the_standard_outline(self):
        for engagement, expected in (("build", "build"), ("migrate", "build"),
                                     ("operate", "maintenance"),
                                     ("service-improvement", "maintenance"),
                                     ("product-selection", "technical-response")):
            with self.subTest(engagement=engagement):
                self.assertEqual(pg.ARCHETYPE_OF_ENGAGEMENT[engagement], expected)

    def test_mismatched_outline_is_blocked(self):
        failures = outline("operate", proposal_archetype="build", sections=BUILD_OK)
        self.assertTrue(any("does not match engagement 'operate'" in f for f in failures), failures)

    def test_a_buyer_specified_outline_is_accepted_with_a_reason(self):
        """Buyer-specified outlines may differ from standards; documented justification permits them."""
        self.assertEqual(outline("operate", proposal_archetype="build", sections=BUILD_OK,
                                 archetype_rationale="RFP 별지 3이 구축 목차를 지정"), [])

    def test_submission_records_which_outline_was_used(self):
        failures = outline("build")
        self.assertTrue(any("submission requires proposal_archetype" in f for f in failures), failures)

    def test_unsupported_archetype_is_a_schema_error(self):
        self.assertTrue(any("unsupported value" in f
                            for f in outline("build", proposal_archetype="workshop")))


class RequiredSectionTests(unittest.TestCase):
    """Missing archetype sections omit entire subjects the engagement must address."""

    def test_build_outline_needs_scope_and_acceptance(self):
        failures = outline("build", proposal_archetype="build",
                           sections=titles("구축 방안", "추진 일정", "추진체계"))
        self.assertTrue(any("'사업 범위'" in f for f in failures), failures)
        self.assertTrue(any("'시험·검수'" in f for f in failures))
        self.assertEqual(outline("build", proposal_archetype="build", sections=BUILD_OK), [])

    def test_maintenance_outline_needs_sla_and_incident_handling(self):
        failures = outline("operate", proposal_archetype="maintenance",
                           sections=titles("지원 대상 제품", "지원 체계"))
        self.assertTrue(any("'SLA'" in f for f in failures), failures)
        self.assertTrue(any("'장애 대응'" in f for f in failures))
        self.assertEqual(outline("operate", proposal_archetype="maintenance", sections=MAINT_OK), [])

    def test_section_titles_may_be_plain_strings(self):
        self.assertEqual(outline("operate", proposal_archetype="maintenance",
                                 sections=["지원 대상", "지원 체계", "SLA 수준", "장애 대응 절차"]), [])

    def test_ledger_is_optional_when_absent(self):
        """Without an outline ledger, skip section checks rather than invent an outline."""
        self.assertEqual(outline("build", proposal_archetype="build"), [])


class UnmappedEngagementTests(unittest.TestCase):
    """Training, consulting, and policy lack repository-backed outlines; neither force them nor silently ignore the gap."""

    def test_no_archetype_is_demanded(self):
        self.assertEqual(outline("education"), [])
        self.assertEqual(outline("consulting"), [])

    def test_using_an_it_outline_there_needs_a_reason(self):
        failures = outline("education", proposal_archetype="build", sections=BUILD_OK)
        self.assertTrue(any("has no standard outline in this repository" in f for f in failures),
                        failures)
        self.assertEqual(outline("education", proposal_archetype="build", sections=BUILD_OK,
                                 archetype_rationale="발주처가 IT 구축 양식을 지정"), [])


class ReadingModeTests(unittest.TestCase):
    """Reading environment and document role are separate axes."""

    def test_individual_review_does_not_force_a_document_role(self):
        """Individual review may use either executive summaries or detailed technical evaluation documents."""
        self.assertNotIn("individual-review", pg.READING_MODE_PROFILE)
        self.assertIn("individual-review", pg.READING_MODES)

    def test_presentation_and_print_still_map(self):
        self.assertEqual(pg.READING_MODE_PROFILE["screen-presentation"], "presentation")
        self.assertEqual(pg.READING_MODE_PROFILE["print-evaluation"], "detailed-submission")


class BuilderTests(unittest.TestCase):
    def test_archetype_and_sections_survive_conversion(self):
        meta = {"mode": "draft", "bid_decision": "bid", "requirements": [], "claims": [],
                "proposal_archetype": "maintenance", "archetype_rationale": "RFP 지정",
                "sections": [{"title": "지원 체계"}]}
        with tempfile.TemporaryDirectory() as d:
            mp, ap = Path(d) / "m.json", Path(d) / "a.json"
            mp.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
            proc = run_script(BEST / "scripts/build_audit_from_meta.py", mp, "-o", ap)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            audit = json.loads(ap.read_text(encoding="utf-8"))
        self.assertEqual(audit["proposal_archetype"], "maintenance")
        self.assertEqual(audit["archetype_rationale"], "RFP 지정")
        self.assertEqual(audit["sections"], [{"title": "지원 체계"}])

    def test_slides_are_not_mistaken_for_an_outline(self):
        """slides[] maps requirement responses, not outlines; treating partial mappings as outlines falsely reports existing sections as missing."""
        meta = {"mode": "draft", "bid_decision": "bid", "requirements": [], "claims": [],
                "proposal_archetype": "build",
                "slides": [{"no": 3, "title": "요구사항 대응표", "req_ids": []}]}
        with tempfile.TemporaryDirectory() as d:
            mp, ap = Path(d) / "m.json", Path(d) / "a.json"
            mp.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(run_script(BEST / "scripts/build_audit_from_meta.py",
                                        mp, "-o", ap).returncode, 0)
            audit = json.loads(ap.read_text(encoding="utf-8"))
        self.assertNotIn("sections", audit)


class GoldenFixtureTests(unittest.TestCase):
    def test_the_golden_build_proposal_has_the_required_sections(self):
        meta = json.loads((DOC / "fixtures/e2e-mini-rfp/meta.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["proposal_archetype"], "build")
        data = {"mode": "submission", "context": {"engagement": meta["context"]["engagement"]},
                "proposal_archetype": meta["proposal_archetype"], "sections": meta["sections"]}
        self.assertEqual(pg.check_outline(data), [])


class DependencyManifestTests(unittest.TestCase):
    def test_requirements_txt_lists_what_the_scripts_import(self):
        text = (REPO / "requirements.txt").read_text(encoding="utf-8")
        self.assertIn("python-pptx", text)
        self.assertIn("soffice", text)  # Document that rendering depends on software outside pip.


if __name__ == "__main__":
    unittest.main()
