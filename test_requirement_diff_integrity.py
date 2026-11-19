"""Reject ambiguous revision JSON before producing requirement change evidence."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent / "skills/create-winning-proposal/scripts/compare_requirements.py"


class RequirementDiffIntegrityTests(unittest.TestCase):
    def test_duplicate_json_members_are_rejected_at_every_level(self):
        valid = '{"requirements":[{"id":"R1","text":"synthetic","source_clause_label":"1"}]}'
        cases = (
            '{"requirements":[],"requirements":[]}',
            '{"requirements":[{"id":"R1","id":"R2","text":"synthetic","source_clause_label":"1"}]}',
            '{"requirements":[{"id":"R1","\\u0069d":"R2","text":"synthetic","source_clause_label":"1"}]}',
            '{"requirements":[{"id":"R1","text":"synthetic","source_clause_label":"1","extra":{"x":1,"x":2}}]}',
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            before, after = root / "before.json", root / "after.json"
            before.write_text(valid, encoding="utf-8")
            for i, bad in enumerate(cases):
                with self.subTest(case=bad):
                    output = root / f"diff-{i}.json"
                    after.write_text(bad, encoding="utf-8")
                    result = subprocess.run([sys.executable, str(SCRIPT), str(before), str(after), "--output", str(output)],
                                            capture_output=True, timeout=30)
                    self.assertEqual(result.returncode, 2, result.stderr.decode("utf-8", errors="replace"))
                    self.assertFalse(output.exists())
            after.write_text(valid, encoding="utf-8")
            output = root / "valid-diff.json"
            result = subprocess.run([sys.executable, str(SCRIPT), str(before), str(after), "--output", str(output)],
                                    capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["changes"], [])


if __name__ == "__main__":
    unittest.main()
