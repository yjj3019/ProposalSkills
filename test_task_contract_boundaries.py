"""Task contracts reject malformed declarations without recording false approval."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent / "skills/create-best-proposal/scripts/task_contract.py"
BASE = {"goal": "test", "write_boundary": "work", "recovery": "restore", "scope": ["scope"],
        "non_goals": ["non-goal"], "outputs": ["out"], "test_oracle": ["check"],
        "stop_conditions": ["failure"], "max_attempts": 2, "time_budget_minutes": 5,
        "allowed_actions": ["read"]}


class TaskContractBoundaryTests(unittest.TestCase):
    def test_malformed_declarations_are_rejected_without_traceback(self):
        cases = [
            {"goal": None}, {"write_boundary": None}, {"recovery": 42},
            {"allowed_actions": [{}]}, {"allowed_actions": [["read"]]},
            {"allowed_actions": ["network"], "approvals": [{"action": "network", "by": None}]},
            {"allowed_actions": ["network"], "approvals": [{"action": [], "by": "reviewer"}]},
            {"allowed_actions": ["network"], "approvals": None},
            {"state": "Verified", "evidence_links": True, "results": {"check": "pass"}},
            {"state": "Verified", "evidence_links": [""], "results": {"check": "pass"}},
            {"state": "Verified", "test_oracle": [{}], "evidence_links": ["proof"], "results": {}},
            {"results": None}, {"evidence_links": None}, {"history": None},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp).resolve() / "contract.json"
            for case in cases:
                with self.subTest(case=case):
                    contract = copy.deepcopy(BASE)
                    contract.update(case)
                    path.write_text(json.dumps(contract), encoding="utf-8")
                    result = subprocess.run([sys.executable, str(SCRIPT), "validate", str(path)], capture_output=True, timeout=30)
                    self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                    self.assertNotIn(b"Traceback", result.stderr)
            contract = copy.deepcopy(BASE)
            contract.update(state="Verified", evidence_links=["report.json"], results={"check": "pass"})
            path.write_text(json.dumps(contract), encoding="utf-8")
            self.assertEqual(subprocess.run([sys.executable, str(SCRIPT), "validate", str(path)], capture_output=True, timeout=30).returncode, 0)

    def test_invalid_result_is_not_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp).resolve() / "contract.json"
            path.write_text(json.dumps(BASE), encoding="utf-8")
            before = path.read_bytes()
            result = subprocess.run([sys.executable, str(SCRIPT), "advance", str(path), "Running", "--result", "check=garbage"],
                                    capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertEqual(path.read_bytes(), before)
            result = subprocess.run([sys.executable, str(SCRIPT), "advance", str(path), "Running", "--result", "check=pass"],
                                    capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["results"]["check"], "pass")


if __name__ == "__main__":
    unittest.main()
