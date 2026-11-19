"""edit_preservation, deck_stage_gate, verification_report: fail-closed behaviour of the three workflow checks."""
from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
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

    def test_explicit_phrase_detects_change_outside_heuristics(self):
        original = "승인 범위는 내부 검토로 한정한다."
        revised = "승인 범위는 외부 공개로 한다."
        self.assertEqual(edit.compare(original, revised)["verdict"], "PASS")
        self.assertEqual(edit.compare(original, revised)["semantic_review"], "NOT VERIFIED")
        self.assertEqual(edit.compare(original, revised, ["내부 검토"])["verdict"], "BLOCKED")
        self.assertEqual(edit.compare(original, "범위는 내부 검토로 한정한다.", ["내부 검토"])["verdict"], "PASS")
        with self.assertRaises(ValueError):
            edit.compare(original, revised, ["누락된 문구"])

    def test_counts_only_does_not_print_protected_or_extracted_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b, protected = root / "a", root / "b", root / "list.json"
            a.write_text('"confidential phrase" retained', encoding="utf-8")
            b.write_text('"other phrase" retained', encoding="utf-8")
            protected.write_text(json.dumps(["confidential phrase"]), encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(edit.main([str(a), str(b), "--preserve-list", str(protected), "--counts-only", "--json"]), 1)
            self.assertNotIn("confidential phrase", out.getvalue())
            self.assertNotIn("other phrase", out.getvalue())
            self.assertEqual(json.loads(out.getvalue())["protected_counts"][0]["after"], 0)

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

    def test_semantic_notice_works_with_ascii_console(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.txt"
            source.write_text("Synthetic text.", encoding="utf-8")
            result = subprocess.run([sys.executable, str(ROOT / "skills/create-proposal-document/scripts/edit_preservation.py"), str(source), str(source)],
                                    capture_output=True, env={**os.environ, "PYTHONIOENCODING": "ascii"}, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(b"SEMANTIC REVIEW: NOT VERIFIED", result.stdout)


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

    def test_buyer_prescribed_label_is_allowed_only_when_marked(self):
        rows = [{"id": "S1", "action_title": "추진 일정", "prescribed": True}, {"id": "S2", "action_title": "추진 방안"}]
        (self.dir / "page_plan.json").write_text(json.dumps({"slides": rows}, ensure_ascii=False), encoding="utf-8")
        self.write_slides(["추진 일정", "추진 방안"])
        problems = stage.check(self.dir)
        self.assertEqual(len(problems), 1)
        self.assertIn("S2", problems[0])

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

    def test_optional_evidence_file_integrity_and_path_scope(self):
        evidence = self.dir / "render.png"
        evidence.write_bytes(b"synthetic render")
        item = {"path": "render.png", "sha256": sha(b"synthetic render")}
        checks = [{"name": "render", "level": "rendered", "status": "pass", "tool": "renderer", "evidence": [item]}]
        report = self.report(checks=checks)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(vreport.main(["--verify-evidence", str(self.dir), str(report)]), 0)
            evidence.write_bytes(b"changed")
            self.assertEqual(vreport.main(["--verify-evidence", str(self.dir), str(report)]), 1)
            item["path"] = "../outside.png"
            self.assertEqual(vreport.main(["--verify-evidence", str(self.dir), str(self.report(checks=checks))]), 1)
            item["path"] = "render.png"
            item["sha256"] = sha(b"changed")
            self.assertEqual(vreport.main(["--verify-evidence", str(self.dir), str(self.report(checks=checks))]), 0)

    def test_evidence_link_is_not_followed(self):
        target = self.dir / "real.png"
        link = self.dir / "link.png"
        target.write_bytes(b"synthetic")
        try:
            link.symlink_to(target)
        except OSError:
            self.skipTest("symbolic links unavailable")
        report = {"checks": [{"evidence": [{"path": "link.png", "sha256": sha(b"synthetic")}]}]}
        self.assertTrue(vreport.evidence_problems(report, self.dir))
        report["checks"][0]["evidence"][0]["path"] = "real.png"
        self.assertEqual(vreport.evidence_problems(report, self.dir), [])

    def test_hash_mismatch_means_checks_do_not_apply(self):
        problems, _ = vreport.validate(self.report(artifact_sha256="0" * 64))
        self.assertTrue(any("sha256 does not match" in p for p in problems))

    def test_duplicate_json_fields_are_invalid(self):
        path = self.dir / "duplicate.json"
        path.write_text('{"scope":"a", "scope":"b"}', encoding="utf-8")
        self.assertTrue(vreport.validate(path)[0])

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
