"""task_contract, eval_metrics, xlsx_check, cross_format_numbers and the skill_audit capability inventory."""
from __future__ import annotations

import io
import json
import re
import shutil
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import ooxml_fixtures as fixtures
import skill_audit

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "skills/create-best-proposal/scripts"))
sys.path.insert(0, str(ROOT / "skills/create-proposal-document/scripts"))
import cross_format_numbers as cross  # noqa: E402
import eval_metrics as metrics  # noqa: E402
import task_contract as contract  # noqa: E402
import xlsx_check  # noqa: E402
from test_hwpx import hwpx, para  # noqa: E402


def base_contract(**extra) -> dict:
    data = {"goal": "Submit the technical proposal", "scope": ["technical volume"], "non_goals": ["price volume"],
            "outputs": ["proposal.pptx"], "allowed_actions": ["read", "write-workspace", "run-checks"],
            "write_boundary": "work/", "test_oracle": ["unified_gate", "sensitive_scan"], "max_attempts": 2,
            "time_budget_minutes": 240, "stop_conditions": ["buyer amendment"], "recovery": "restore last hashed copy"}
    data.update(extra)
    return data


class TaskContractTests(unittest.TestCase):
    def walk(self, c, *steps):
        for target, kwargs in steps:
            c = contract.advance(c, target, **kwargs)
        return c

    def test_a_complete_contract_is_valid_and_gaps_are_named(self):
        self.assertEqual(contract.validate(base_contract()), [])
        bad = base_contract(scope=[], max_attempts=0, allowed_actions=["read", "publish"])
        text = "\n".join(contract.validate(bad))
        self.assertIn("scope", text)
        self.assertIn("max_attempts", text)
        self.assertIn("publish is allowed but has no approval", text)
        ok = base_contract(allowed_actions=["read", "publish"], approvals=[{"action": "publish", "by": "PM"}])
        self.assertEqual(contract.validate(ok), [])

    def test_verified_needs_evidence_and_every_oracle_check_passing(self):
        c = self.walk(base_contract(), ("Running", {}), ("Verifying", {}))
        with self.assertRaisesRegex(ValueError, "evidence_links"):
            contract.advance(c, "Verified", results={"unified_gate": "pass", "sensitive_scan": "pass"})
        with self.assertRaisesRegex(ValueError, "sensitive_scan"):
            contract.advance(c, "Verified", evidence=["log.jsonl"], results={"unified_gate": "pass"})
        done = contract.advance(c, "Verified", evidence=["log.jsonl"], results={"unified_gate": "pass", "sensitive_scan": "pass"})
        self.assertEqual(done["state"], "Verified")
        with self.assertRaisesRegex(ValueError, "not an allowed move"):
            contract.advance(done, "Running")

    def test_illegal_moves_and_missing_reasons_are_refused(self):
        with self.assertRaisesRegex(ValueError, "not an allowed move"):
            contract.advance(base_contract(), "Verified")
        running = contract.advance(base_contract(), "Running")
        with self.assertRaisesRegex(ValueError, "--cause"):
            contract.advance(running, "Failed")
        with self.assertRaisesRegex(ValueError, "--blocker"):
            contract.advance(running, "Blocked")
        blocked = contract.advance(running, "Blocked", blocker="RFP amendment pending")
        with self.assertRaisesRegex(ValueError, "--note"):
            contract.advance(blocked, "Running")
        self.assertEqual(contract.advance(blocked, "Running", note="amendment received")["state"], "Running")

    def test_retries_are_counted_and_stop_at_the_budget(self):
        c = self.walk(base_contract(), ("Running", {}), ("Failed", {"cause": "font missing"}), ("Running", {}))
        self.assertEqual(c["attempts"], 1)
        c = self.walk(c, ("Failed", {"cause": "font missing"}), ("Running", {}))
        self.assertEqual(c["attempts"], 2)
        c = contract.advance(c, "Failed", cause="font missing")
        with self.assertRaisesRegex(ValueError, "max_attempts is used up"):
            contract.advance(c, "Running")

    def test_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.json"
            path.write_text(json.dumps(base_contract()), encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(contract.main(["validate", str(path)]), 0)
                self.assertEqual(contract.main(["advance", str(path), "Running"]), 0)
                self.assertEqual(contract.main(["advance", str(path), "Verified"]), 1)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["state"], "Running")
            with redirect_stderr(io.StringIO()):
                self.assertEqual(contract.main(["validate", str(Path(tmp) / "none.json")]), 2)


def run(task, arm, verified, claimed=True, cost=1.0, conditions="m1, 10 min", **extra):
    return {"task": task, "arm": arm, "conditions": conditions, "claimed_complete": claimed, "verified": verified,
            "seconds": 10, "cost": cost, **extra}


class EvalMetricsTests(unittest.TestCase):
    def test_metrics_count_unverified_against_success_and_false_completion_against_claims(self):
        runs = [run("a", "baseline", True), run("b", "baseline", False), run("c", "baseline", None),
                run("a", "candidate", True), run("b", "candidate", True), run("c", "candidate", True, cost=3.0)]
        by_arm = metrics.load(runs)
        base, cand = metrics.metrics(list(by_arm["baseline"].values())), metrics.metrics(list(by_arm["candidate"].values()))
        self.assertAlmostEqual(base["verified_success_rate"], 1 / 3)
        self.assertAlmostEqual(base["false_completion_rate"], 1 / 3)
        self.assertEqual(base["not_verified"], 1)
        self.assertAlmostEqual(base["cost_per_verified"], 3.0)
        self.assertEqual(cand["verified_success_rate"], 1.0)
        self.assertAlmostEqual(cand["cost_per_verified"], 5.0 / 3)

    def test_regression_rate_and_empty_denominators(self):
        runs = [run("a", "baseline", True, prior_pass=True, regressed=True), run("a", "candidate", False, claimed=False)]
        by_arm = metrics.load(runs)
        self.assertEqual(metrics.metrics(list(by_arm["baseline"].values()))["regression_rate"], 1.0)
        cand = metrics.metrics(list(by_arm["candidate"].values()))
        self.assertIsNone(cand["false_completion_rate"])
        self.assertIsNone(cand["cost_per_verified"])
        self.assertIsNone(cand["regression_rate"])

    def test_unpaired_or_unrecorded_conditions_are_refused(self):
        cases = {
            "missing task": [run("a", "baseline", True), run("b", "baseline", True), run("a", "candidate", True)],
            "different conditions": [run("a", "baseline", True), run("a", "candidate", True, conditions="m2")],
            "duplicate": [run("a", "baseline", True), run("a", "baseline", True), run("a", "candidate", True)],
            "no conditions": [run("a", "baseline", True, conditions=""), run("a", "candidate", True, conditions="")],
            "bad verified": [run("a", "baseline", "yes"), run("a", "candidate", True)],
            "negative cost": [run("a", "baseline", True, cost=-1), run("a", "candidate", True)],
        }
        for label, runs in cases.items():
            with self.assertRaises(ValueError, msg=label):
                metrics.load(runs)

    def test_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runs.json"
            path.write_text(json.dumps([run("a", "baseline", True), run("a", "candidate", True)]), encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(metrics.main([str(path)]), 0)
            self.assertIn("no significance test", out.getvalue())
            path.write_text(json.dumps([run("a", "baseline", True)]), encoding="utf-8")
            with redirect_stderr(io.StringIO()):
                self.assertEqual(metrics.main([str(path)]), 2)


def sheet(*cells: str) -> str:
    return ('<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1">'
            + "".join(cells) + "</row></sheetData></worksheet>")


class XlsxCheckTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def book(self, name, *cells, extra=None):
        return fixtures.xlsx(self.dir / name, {"xl/worksheets/sheet1.xml": sheet(*cells), **(extra or {})})

    def test_error_cells_and_ref_formulas_block(self):
        path = self.book("a.xlsx", '<c r="A1" t="e"><v>#DIV/0!</v></c>', '<c r="B1"><f>Sheet2!#REF!+1</f><v>3</v></c>')
        blocked, _ = xlsx_check.verdict(xlsx_check.inspect(path))
        text = "\n".join(blocked)
        self.assertIn("error values A1=#DIV/0!", text)
        self.assertIn("#REF!", text)

    def test_formula_without_cached_value_is_a_warning_not_a_pass_claim(self):
        path = self.book("b.xlsx", '<c r="A1"><f>1+1</f></c>', '<c r="B1"><f>2+2</f><v>4</v></c>')
        blocked, warnings = xlsx_check.verdict(xlsx_check.inspect(path))
        self.assertEqual(blocked, [])
        self.assertTrue(any("1 formula(s) have no cached value" in w and "NOT VERIFIED" in w for w in warnings))

    def test_clean_workbook_and_unsafe_or_non_xlsx_inputs(self):
        path = self.book("c.xlsx", '<c r="A1"><f>1+1</f><v>2</v></c>')
        with redirect_stdout(io.StringIO()):
            self.assertEqual(xlsx_check.main([str(path)]), 0)
        evil = self.book("d.xlsx", '<c r="A1"/>', extra={"xl/workbook.xml": '<!DOCTYPE w [<!ENTITY a "b">]><workbook/>'})
        bad = self.dir / "e.xlsx"
        bad.write_bytes(b"not a zip")
        with redirect_stderr(io.StringIO()):
            self.assertEqual(xlsx_check.main([str(evil)]), 2)
            self.assertEqual(xlsx_check.main([str(bad)]), 2)

    def test_hidden_sheet_and_external_links_are_warnings(self):
        workbook = ('<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                    '<sheets><sheet name="Calc" sheetId="1" state="hidden" r:id="rId1"/></sheets></workbook>')
        rels = '<Relationships><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>'
        path = self.book("f.xlsx", '<c r="A1"><v>1</v></c>', extra={
            "xl/workbook.xml": workbook, "xl/_rels/workbook.xml.rels": rels,
            "xl/externalLinks/externalLink1.xml": "<externalLink/>"})
        _, warnings = xlsx_check.verdict(xlsx_check.inspect(path))
        self.assertTrue(any("hidden sheet" in w for w in warnings))
        self.assertTrue(any("external workbook link" in w for w in warnings))

    @unittest.skipUnless(shutil.which("soffice") or shutil.which("libreoffice"), "LibreOffice is required for --recalc")
    def test_recalc_blocks_a_stale_cached_value(self):
        main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
        rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        part = "application/vnd.openxmlformats-officedocument.spreadsheetml"
        path = self.dir / "g.xlsx"  # a complete package LibreOffice can open; cached 5, real result 2
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                       '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                       '<Default Extension="xml" ContentType="application/xml"/>'
                       f'<Override PartName="/xl/workbook.xml" ContentType="{part}.sheet.main+xml"/>'
                       f'<Override PartName="/xl/worksheets/sheet1.xml" ContentType="{part}.worksheet+xml"/></Types>')
            z.writestr("_rels/.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                       f'<Relationship Id="rId1" Type="{rel}/officeDocument" Target="xl/workbook.xml"/></Relationships>')
            z.writestr("xl/workbook.xml", f'<workbook xmlns="{main}" xmlns:r="{rel}"><sheets><sheet name="Calc" sheetId="1" r:id="rId1"/></sheets></workbook>')
            z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                       f'<Relationship Id="rId1" Type="{rel}/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
            z.writestr("xl/worksheets/sheet1.xml", sheet('<c r="A1"><f>1+1</f><v>5</v></c>'))
        out = io.StringIO()
        with redirect_stdout(out):
            code = xlsx_check.main([str(path), "--recalc"])
        self.assertEqual(code, 1, out.getvalue())
        self.assertIn("differs from recalculated", out.getvalue())


class CrossFormatTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.ledger = self.dir / "ledger.json"
        self.ledger.write_text(json.dumps([{"id": "N1", "label": "기간", "value": 36, "unit": "개월"},
                                           {"id": "N2", "label": "인원", "value": 12, "unit": "명"}]), encoding="utf-8")

    def docs(self, hwpx_text):
        docx = fixtures.docx(self.dir / "a.docx", "<w:p><w:r><w:t>사업 기간 36개월, 투입 12명</w:t></w:r></w:p>")
        hw = hwpx(self.dir / "b.hwpx", para(hwpx_text))
        return docx, hw

    def test_agreeing_formats_pass_and_a_stale_format_is_reported_as_divergent(self):
        docx, hw = self.docs("사업 기간 36개월, 투입 12명")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(cross.main([str(docx), str(hw), "--numbers", str(self.ledger)]), 0)
        docx, hw = self.docs("사업 기간 24개월, 투입 12명")
        out = io.StringIO()
        with redirect_stdout(out):
            code = cross.main([str(docx), str(hw), "--numbers", str(self.ledger)])
        self.assertEqual(code, 1)
        self.assertIn("[DIVERGENT] N1: found elsewhere but missing in b.hwpx", out.getvalue())

    def test_unreadable_file_is_exit_2_never_a_pass(self):
        bad = self.dir / "x.docx"
        bad.write_bytes(b"not a zip")
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(cross.main([str(bad), "--numbers", str(self.ledger)]), 2)


class InventoryTests(unittest.TestCase):
    def test_inventory_lists_capabilities_and_deny_turns_them_into_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "demo"
            (skill / "scripts").mkdir(parents=True)
            (skill / "SKILL.md").write_text("---\nname: demo\ndescription: d\nlicense: MIT\n---\nbody\n", encoding="utf-8")
            (skill / "scripts" / "go.py").write_text(
                "import subprocess, os\nimport urllib.request\nurllib.request.urlopen('x')\nos.environ.get('K')\nsubprocess.run(['x'])\n",
                encoding="utf-8")
            inventory = skill_audit.capability_inventory(skill)
            self.assertEqual(set(inventory), {"process", "network", "environment"})
            with redirect_stdout(io.StringIO()):
                self.assertEqual(skill_audit.main([tmp, "--root-license", "MIT", "--inventory"]), 0)
                self.assertEqual(skill_audit.main([tmp, "--root-license", "MIT", "--deny", "network"]), 1)
            with redirect_stderr(io.StringIO()):
                self.assertEqual(skill_audit.main([tmp, "--root-license", "MIT", "--deny", "nonsense"]), 2)

    def test_shipped_skills_do_not_reach_the_network(self):
        for skill in skill_audit.skill_dirs(ROOT / "skills"):
            self.assertNotIn("network", skill_audit.capability_inventory(skill), skill.name)


class VerdictVocabularyTests(unittest.TestCase):
    """The mapping table must not drift from what the tools really print."""

    def test_every_listed_script_exists_and_prints_the_listed_words(self):
        doc = (ROOT / "skills/create-best-proposal/references/verdict-vocabulary.md").read_text(encoding="utf-8")
        table = doc.split("## Mapping of tool output", 1)[1]
        files = {p.name: p for p in ROOT.rglob("*.py") if ".git" not in p.parts}
        checked = 0
        for line in table.splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 3 or not cells[0].startswith("`"):
                continue
            scripts = re.findall(r"`([\w.-]+\.py)`", cells[0])
            self.assertTrue(scripts, line)
            source = "\n".join(files[name].read_text(encoding="utf-8") for name in scripts).lower()
            for token in re.findall(r"`([^`]+)`", cells[1]):
                if "*" in token or token.endswith(".py"):
                    continue
                self.assertIn(token.lower(), source, f"{scripts}: prints {token!r}?")
                checked += 1
        self.assertGreater(checked, 25)


if __name__ == "__main__":
    unittest.main()
