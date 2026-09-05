"""11차 — 사업 성격이 목차를 바꾼다.

분류 값이 존재하는 것과 그 값이 생산 경로를 바꾸는 것은 다르다. `engagement`가
`operate`인데 IT 구축 목차를 그대로 쓰면 기관명만 바뀐 제안서가 된다.

이 저장소에 목차 근거가 있는 유형은 셋뿐이다(구축·유지보수·기술답변서). 근거 없는
목차를 지어내지 않으므로, 매핑이 없는 사업 성격에는 유형을 강제하지 않는다.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent
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
        """발주처가 목차를 지정하면 표준과 달라도 된다 — 이유를 적으면 통과한다."""
        self.assertEqual(outline("operate", proposal_archetype="build", sections=BUILD_OK,
                                 archetype_rationale="RFP 별지 3이 구축 목차를 지정"), [])

    def test_submission_records_which_outline_was_used(self):
        failures = outline("build")
        self.assertTrue(any("submission requires proposal_archetype" in f for f in failures), failures)

    def test_unsupported_archetype_is_a_schema_error(self):
        self.assertTrue(any("unsupported value" in f
                            for f in outline("build", proposal_archetype="workshop")))


class RequiredSectionTests(unittest.TestCase):
    """목차 뼈대가 요구하는 절이 빠지면 그 사업에서 답해야 할 것을 통째로 빠뜨린 것이다."""

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
        """목차 원장이 없으면 절 검사는 하지 않는다 — 없는 목차를 만들어내지 않는다."""
        self.assertEqual(outline("build", proposal_archetype="build"), [])


class UnmappedEngagementTests(unittest.TestCase):
    """교육·컨설팅·정책에는 이 저장소에 목차 근거가 없다. 강제하지도, 조용히 넘기지도 않는다."""

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
    """읽는 환경과 문서 역할은 다른 축이다."""

    def test_individual_review_does_not_force_a_document_role(self):
        """개인 열람은 임원 요약본일 수도 상세 기술평가서일 수도 있다."""
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
            proc = subprocess.run([sys.executable, str(BEST / "scripts/build_audit_from_meta.py"),
                                   str(mp), "-o", str(ap)], capture_output=True, text=True,
                                  encoding="utf-8", errors="replace")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            audit = json.loads(ap.read_text(encoding="utf-8"))
        self.assertEqual(audit["proposal_archetype"], "maintenance")
        self.assertEqual(audit["archetype_rationale"], "RFP 지정")
        self.assertEqual(audit["sections"], [{"title": "지원 체계"}])

    def test_slides_are_not_mistaken_for_an_outline(self):
        """slides[]는 요구 대응 매핑이지 목차가 아니다 — 부분 매핑을 목차로 읽으면
        있는 절을 없다고 잡는다."""
        meta = {"mode": "draft", "bid_decision": "bid", "requirements": [], "claims": [],
                "proposal_archetype": "build",
                "slides": [{"no": 3, "title": "요구사항 대응표", "req_ids": []}]}
        with tempfile.TemporaryDirectory() as d:
            mp, ap = Path(d) / "m.json", Path(d) / "a.json"
            mp.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
            subprocess.run([sys.executable, str(BEST / "scripts/build_audit_from_meta.py"),
                            str(mp), "-o", str(ap)], check=True, capture_output=True)
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
        self.assertIn("soffice", text)  # 렌더는 pip 밖 의존성임을 적어 둔다


if __name__ == "__main__":
    unittest.main()
