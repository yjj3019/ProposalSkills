"""Focused mutation checks for ambiguous audit parsing at both CLI entry points."""
import json
import tempfile
import unittest
from pathlib import Path

from test_support import run_script

ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / "skills/create-best-proposal/fixtures/audit_ready_financial.json"
PROPOSAL = ROOT / "skills/create-winning-proposal/scripts/proposal_gate.py"
UNIFIED = ROOT / "skills/create-best-proposal/scripts/unified_gate.py"


class AuditParserMutationTests(unittest.TestCase):
    def check_entry(self, script, *args):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp).resolve() / "audit.json"
            valid = json.dumps(json.loads(FIXTURE.read_text(encoding="utf-8")), ensure_ascii=False)
            path.write_text(valid, encoding="utf-8")
            self.assertEqual(run_script(script, path, *args).returncode, 0)
            path.write_text('{"bid_decision":"no-bid",' + valid[1:], encoding="utf-8")
            result = run_script(script, path, *args)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

    def test_proposal_entry_rejects_duplicates(self):
        self.check_entry(PROPOSAL)

    def test_unified_entry_rejects_duplicates(self):
        self.check_entry(UNIFIED, "--audit-only", "--no-explain")


if __name__ == "__main__":
    unittest.main()
