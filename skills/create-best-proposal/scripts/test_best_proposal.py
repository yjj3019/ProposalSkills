#!/usr/bin/env python3
"""Unit tests for create-best-proposal scripts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
FIXTURES = SKILL_DIR / "fixtures"
SKILLS_ROOT = SKILL_DIR.parent
REPO_ROOT = SKILLS_ROOT.parent

sys.path.insert(0, str(SCRIPT_DIR))
import build_audit_from_meta  # noqa: E402
import bulk_matrix  # noqa: E402


class BuildAuditTests(unittest.TestCase):
    def test_meta_sample_builds(self):
        meta = json.loads((FIXTURES / "meta_sample.json").read_text(encoding="utf-8"))
        audit = build_audit_from_meta.build_audit(meta)
        self.assertEqual(audit["bid_decision"], "bid")
        self.assertTrue(any(r["id"] == "R1" for r in audit["requirements"]))
        r1 = next(r for r in audit["requirements"] if r["id"] == "R1")
        self.assertTrue(r1["evidence_refs"])
        self.assertIn("mode", audit)
        self.assertIn("eligibility", audit)

    def test_strict_approved_without_evidence_fails(self):
        meta = {
            "mode": "draft",
            "bid_decision": "bid",
            "requirements": [
                {"id": "R1", "mandatory": True, "state": "approved", "evidence_refs": []},
            ],
        }
        with self.assertRaises(ValueError):
            build_audit_from_meta.build_audit(meta, strict=True)

    def test_cli_writes_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "audit.json"
            code = build_audit_from_meta.main([
                str(FIXTURES / "meta_sample.json"), "-o", str(out),
            ])
            self.assertEqual(code, 0)
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["mode"], "draft")


class BulkMatrixTests(unittest.TestCase):
    def test_json_full_rows(self):
        rows_in = [
            {"id": f"R{i:02d}", "item": f"항목{i}", "text": f"내용{i}",
             "support": "O" if i % 3 else "X", "mandatory": True}
            for i in range(1, 21)
        ]
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "req.json"
            src.write_text(json.dumps(rows_in, ensure_ascii=False), encoding="utf-8")
            out = Path(tmp) / "matrix.md"
            side = Path(tmp) / "reqs.json"
            code = bulk_matrix.main([
                str(src), "-o", str(out), "--summary-rows", "5",
                "--audit-sidecar", str(side),
            ])
            self.assertEqual(code, 0)
            md = out.read_text(encoding="utf-8")
            self.assertIn("20건 전수", md)
            self.assertIn("R20", md)
            side_data = json.loads(side.read_text(encoding="utf-8"))
            self.assertEqual(len(side_data), 20)

    def test_csv_load(self):
        csv_text = "id,item,text,support\nR1,기능,설명,O\nR2,보안,설명,부분\n"
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "r.csv"
            src.write_text(csv_text, encoding="utf-8")
            rows = [bulk_matrix.normalize(r, i) for i, r in enumerate(bulk_matrix.load_rows(src), 1)]
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[1]["support"], "부분")


class UnifiedGateTests(unittest.TestCase):
    def _run_unified(self, audit: Path, extra: list[str] | None = None) -> subprocess.CompletedProcess:
        cmd = [sys.executable, str(SCRIPT_DIR / "unified_gate.py"), str(audit)]
        if extra:
            cmd.extend(extra)
        return subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(REPO_ROOT),
        )

    def test_financial_ready_fixture(self):
        proc = self._run_unified(FIXTURES / "audit_ready_financial.json")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("STATUS: READY", proc.stdout)

    def test_decision_memo_no_bid(self):
        proc = self._run_unified(FIXTURES / "audit_decision_memo.json")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("DECISION_MEMO_ONLY", proc.stdout)

    def test_proposal_gate_financial_direct(self):
        gate = SKILLS_ROOT / "create-winning-proposal" / "scripts" / "proposal_gate.py"
        if not gate.is_file():
            self.skipTest("proposal_gate missing")
        proc = subprocess.run(
            [sys.executable, str(gate), str(FIXTURES / "audit_ready_financial.json")],
            capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("READY", proc.stdout)


class InstallDiscoveryTests(unittest.TestCase):
    def test_skill_discovered(self):
        sys.path.insert(0, str(REPO_ROOT))
        import install_skill
        names = install_skill.available_skills()
        self.assertIn("create-best-proposal", names)
        self.assertIn("create-proposal-document", names)
        self.assertIn("create-winning-proposal", names)


if __name__ == "__main__":
    unittest.main()
