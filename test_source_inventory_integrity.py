"""Source inventories cannot silently select between duplicate JSON members."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent / "skills/create-best-proposal/scripts/check_source_inventory.py"


class SourceInventoryIntegrityTests(unittest.TestCase):
    def test_duplicate_manifest_keys_are_rejected_without_output(self):
        cases = (
            '{"sources":[],"sources":[]}',
            '{"sources":[{"id":"R1","required":true,"required":false}]}',
            '{"sources":[{"id":"R1","required":true,"\\u0072equired":false}]}',
            '{"sources":[{"id":"R1","required":true,"extra":{"x":1,"x":2}}]}',
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            manifest = root / "manifest.json"
            for i, case in enumerate(cases):
                with self.subTest(case=case):
                    manifest.write_text(case, encoding="utf-8")
                    output = root / f"bad-{i}.json"
                    result = subprocess.run([sys.executable, str(SCRIPT), str(manifest), "--output", str(output)],
                                            capture_output=True, timeout=30)
                    self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                    self.assertFalse(output.exists())
            manifest.write_text('{"sources":[{"id":"R1","required":true}]}', encoding="utf-8")
            result = subprocess.run([sys.executable, str(SCRIPT), str(manifest), "--output", str(root / "valid.json")],
                                    capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_duplicate_extraction_keys_never_count_as_unreviewed_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / "source.pdf").write_bytes(b"synthetic")
            digest = hashlib.sha256(b"synthetic").hexdigest()
            sidecar = {"schema_version": 1, "kind": "proposal-rfp-extraction", "review_status": "UNREVIEWED",
                       "submission_approval": False, "source": {"sha256": digest, "format": ".pdf"}, "document": {}}
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"sources": [{"id": "R1", "required": True, "source_path": "source.pdf",
                                                         "extraction_path": "extraction.json"}]}), encoding="utf-8")
            data = json.dumps(sidecar)
            cases = (data.replace('"submission_approval": false', '"submission_approval": true, "submission_approval": false'),
                     data.replace('"sha256":', '"sha256": "bad", "sha256":'))
            for i, case in enumerate(cases):
                with self.subTest(case=case):
                    (root / "extraction.json").write_text(case, encoding="utf-8")
                    output = root / f"bad-sidecar-{i}.json"
                    result = subprocess.run([sys.executable, str(SCRIPT), str(manifest), "--output", str(output)],
                                            capture_output=True, timeout=30)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    report = json.loads(output.read_text(encoding="utf-8"))
                    self.assertEqual(report["sources"][0]["status"], "inspection_failed")
                    self.assertTrue(any(item["id"] == "source-R1" and item["class"] == "blocking" for item in report["inputs"]))
            (root / "extraction.json").write_text(data, encoding="utf-8")
            output = root / "valid-sidecar.json"
            result = subprocess.run([sys.executable, str(SCRIPT), str(manifest), "--output", str(output)], capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["sources"][0]["status"], "extracted_unreviewed")


if __name__ == "__main__":
    unittest.main()
