"""edit_preservation, deck_stage_gate, verification_report: fail-closed behaviour of the three workflow checks."""
from __future__ import annotations

import hashlib
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "skills/create-proposal-document/scripts"))
sys.path.insert(0, str(ROOT / "skills/create-best-proposal/scripts"))
import deck_stage_gate as stage  # noqa: E402
import edit_preservation as edit  # noqa: E402
import verification_report as vreport  # noqa: E402


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class EditPreservationTests(unittest.TestCase):
    ORIGINAL = ("총 사업비는 1,200만원이며 36개월 동안 수행한다. 마감은 2026-12-31이다. REQ-014 대응. "
                "구축 범위는 추정이며 [unverified] 상태다. 장애 대응은 하지 않는다. 자세한 내용은 https://example.org/a 참고. "
                "\"SLA 99.9%\" 인용. `run.sh --safe` 실행.")

    def test_pure_rewording_passes(self):
        revised = ("사업비는 1200만원, 수행 기간은 36 개월이다. 마감일은 2026-12-31. REQ-014 대응. "
                   "구축 범위는 추정이며 [unverified] 상태다. 장애 대응은 하지 않는다. 참고: https://example.org/a. "
                   "\"SLA 99.9%\" 인용. `run.sh --safe` 실행.")
        self.assertEqual(edit.compare(self.ORIGINAL, revised)["verdict"], "PASS")

    def test_changed_or_lost_facts_block(self):
        cases = {
            "numbers": self.ORIGINAL.replace("36개월", "24개월"),
            "dates": self.ORIGINAL.replace("2026-12-31", "2027-01-31"),
            "ids": self.ORIGINAL.replace("REQ-014", "REQ-015"),
            "urls": self.ORIGINAL.replace("https://example.org/a", "https://example.org/b"),
            "quotes": self.ORIGINAL.replace("SLA 99.9%", "SLA 99.99%"),
            "code": self.ORIGINAL.replace("`run.sh --safe`", "`run.sh`"),
            "hedges": self.ORIGINAL.replace("추정이며 [unverified]", "확정이며"),
        }
        for kind, revised in cases.items():
            report = edit.compare(self.ORIGINAL, revised)
            self.assertEqual(report["verdict"], "BLOCKED", kind)
            self.assertIn(kind, report["blocking"] if kind != "numbers" else report["blocking"] + ["numbers"], kind)

    def test_invented_figure_blocks(self):
        report = edit.compare("납기는 30일이다.", "납기는 30일이며 만족도는 98%이다.")
        self.assertEqual(report["verdict"], "BLOCKED")
        self.assertIn("98%", report["added"]["numbers"])

    def test_dropped_negation_is_a_review_item_not_a_pass(self):
        report = edit.compare("추가 비용은 없다.", "추가 비용을 부담한다.")
        self.assertEqual(report["verdict"], "REVIEW")

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.md", Path(tmp) / "b.md"
            a.write_text("기간 36개월", encoding="utf-8")
            b.write_text("기간 24개월", encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(edit.main([str(a), str(b)]), 1)
                self.assertEqual(edit.main([str(a), str(a)]), 0)
            with redirect_stderr(io.StringIO()):
                self.assertEqual(edit.main([str(a), str(Path(tmp) / "none.md")]), 2)


class DeckStageGateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.spec = b"palette: navy\nfont: Pretendard\n"
        (self.dir / "brief.md").write_text("brief", encoding="utf-8")
        (self.dir / "design_spec.md").write_bytes(self.spec)
        self.titles = ["현행 시스템 장애의 70%는 노후 장비에서 발생한다", "단계별 이관으로 서비스 중단 없이 전환한다"]
        (self.dir / "page_plan.json").write_text(json.dumps(
            {"slides": [{"id": f"S{i}", "action_title": t} for i, t in enumerate(self.titles, 1)]}, ensure_ascii=False), encoding="utf-8")
        self.write_slides(self.titles)
        self.write_manifest()

    def write_slides(self, titles):
        slides = [{"type": "cover", "title": "표지"}] + [{"type": "bullets", "title": t} for t in titles]
        (self.dir / "slides.json").write_text(json.dumps({"slides": slides}, ensure_ascii=False), encoding="utf-8")

    def write_manifest(self, route="generate", approver="김검수", digest=None):
        design = {"file": "design_spec.md", "approved_by": approver, "approved_sha256": digest or sha(self.spec)}
        (self.dir / "stages.json").write_text(json.dumps({"route": route, "stages": {
            "brief": {"file": "brief.md"}, "design_spec": design,
            "page_plan": {"file": "page_plan.json"}, "slides": {"file": "slides.json"}}}), encoding="utf-8")

    def test_complete_workspace_passes(self):
        self.assertEqual(stage.check(self.dir), [])

    def test_unapproved_or_edited_spec_blocks(self):
        self.write_manifest(approver="")
        self.assertTrue(any("not approved" in p for p in stage.check(self.dir)))
        self.write_manifest()
        (self.dir / "design_spec.md").write_bytes(self.spec + b"font: Other\n")
        self.assertTrue(any("changed after approval" in p for p in stage.check(self.dir)))

    def test_quick_route_skips_approval_but_not_the_brief(self):
        self.write_manifest(route="quick", approver="")
        self.assertEqual(stage.check(self.dir), [])
        (self.dir / "brief.md").unlink()
        self.assertTrue(any("brief" in p for p in stage.check(self.dir)))

    def test_label_titles_and_plan_deck_mismatch_block(self):
        (self.dir / "page_plan.json").write_text(json.dumps({"slides": [{"id": "S1", "action_title": "Overview"}]}), encoding="utf-8")
        self.assertTrue(any("label, not a claim" in p for p in stage.check(self.dir)))
        (self.dir / "page_plan.json").write_text(json.dumps(
            {"slides": [{"id": f"S{i}", "action_title": t} for i, t in enumerate(self.titles, 1)]}, ensure_ascii=False), encoding="utf-8")
        self.write_slides(list(reversed(self.titles)))
        self.assertTrue(any("do not match page_plan" in p for p in stage.check(self.dir)))

    def test_manifest_cannot_point_outside_the_workspace(self):
        data = json.loads((self.dir / "stages.json").read_text(encoding="utf-8"))
        data["stages"]["brief"]["file"] = "../outside.md"
        (self.dir / "stages.json").write_text(json.dumps(data), encoding="utf-8")
        self.assertTrue(any("outside the workspace" in p for p in stage.check(self.dir)))


class VerificationReportTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.data = b"deck bytes"
        (self.dir / "deck.pptx").write_bytes(self.data)

    def report(self, **override):
        base = {"artifact": "deck.pptx", "artifact_sha256": sha(self.data), "scope": "slides 1-10, text and layout",
                "checks": [{"name": "layout lint", "level": "static", "status": "pass"},
                           {"name": "render", "level": "rendered", "status": "pass", "tool": "soffice 24", "evidence": ["out/png"]}],
                "not_inspected": []}
        base.update(override)
        path = self.dir / "report.json"
        path.write_text(json.dumps(base), encoding="utf-8")
        return path

    def test_valid_report_and_deepest_level(self):
        problems, deepest = vreport.validate(self.report())
        self.assertEqual((problems, deepest), ([], "rendered"))

    def test_hash_mismatch_means_checks_do_not_apply(self):
        problems, _ = vreport.validate(self.report(artifact_sha256="0" * 64))
        self.assertTrue(any("sha256 does not match" in p for p in problems))

    def test_rendered_pass_needs_tool_and_evidence(self):
        checks = [{"name": "render", "level": "rendered", "status": "pass"}]
        problems, deepest = vreport.validate(self.report(checks=checks))
        self.assertTrue(any("needs a tool and evidence" in p for p in problems))

    def test_not_inspected_must_be_declared_and_scores_are_refused(self):
        checks = [{"name": "contrast", "level": "static", "status": "not-inspected"}]
        problems, deepest = vreport.validate(self.report(checks=checks))
        self.assertTrue(any("missing from not_inspected" in p for p in problems))
        self.assertEqual(deepest, "none")
        problems, _ = vreport.validate(self.report(quality_score=92))
        self.assertTrue(any("score fields" in p for p in problems))

    def test_cli_exit_codes(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(vreport.main([str(self.report())]), 0)
            self.assertEqual(vreport.main([str(self.report(scope=""))]), 1)
        with redirect_stderr(io.StringIO()):
            self.assertEqual(vreport.main([str(self.dir / "missing.json")]), 2)


if __name__ == "__main__":
    unittest.main()
