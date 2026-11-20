"""Regression tests for malformed evidence and verification-report inputs."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parent / "skills/create-best-proposal/scripts"


class EvidenceBoundaryTests(unittest.TestCase):
    def test_chain_rejects_unrepresentable_metric_totals_without_losing_records(self):
        script = SCRIPTS / "evidence_chain.py"
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp).resolve() / "log.jsonl"
            args = [sys.executable, str(script), "append", str(log), "--command", "check", "--exit-code", "0", "--cost", "1e308"]
            first = subprocess.run(args, capture_output=True, timeout=30)
            self.assertEqual(first.returncode, 0, first.stderr)
            before = log.read_bytes()
            second = subprocess.run(args, capture_output=True, timeout=30)
            self.assertEqual(second.returncode, 2, second.stderr)
            self.assertEqual(log.read_bytes(), before)
            self.assertNotIn(b"Traceback", second.stderr)
            self.assertEqual(subprocess.run([sys.executable, str(script), "verify", str(log)], capture_output=True, timeout=30).returncode, 0)
            record = json.loads(before)
            record["seq"] = 2
            record["prev"] = record["hash"]
            body = {key: value for key, value in record.items() if key != "hash"}
            record["hash"] = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False,
                                                       separators=(",", ":")).encode("utf-8")).hexdigest()
            log.write_bytes(before + (json.dumps(record) + "\n").encode("utf-8"))
            result = subprocess.run([sys.executable, str(script), "verify", str(log)], capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertNotIn(b"Traceback", result.stderr)
            self.assertNotIn(b"total cost=inf", result.stdout)
            record = json.loads(before)
            record["cost"] = 10**309
            body = {key: value for key, value in record.items() if key != "hash"}
            record["hash"] = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False,
                                                       separators=(",", ":")).encode("utf-8")).hexdigest()
            log.write_text(json.dumps(record) + "\n", encoding="utf-8")
            result = subprocess.run([sys.executable, str(script), "verify", str(log)], capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertNotIn(b"Traceback", result.stderr)
            seconds_log = Path(tmp).resolve() / "seconds.jsonl"
            seconds_args = [sys.executable, str(script), "append", str(seconds_log), "--command", "check", "--exit-code", "0", "--seconds", "1e308"]
            self.assertEqual(subprocess.run(seconds_args, capture_output=True, timeout=30).returncode, 0)
            before = seconds_log.read_bytes()
            self.assertEqual(subprocess.run(seconds_args, capture_output=True, timeout=30).returncode, 2)
            self.assertEqual(seconds_log.read_bytes(), before)

    def test_chain_rejects_nonfinite_metrics_and_malformed_records(self):
        script = SCRIPTS / "evidence_chain.py"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            for field in ("--seconds", "--cost"):
                for value in ("nan", "inf", "-inf"):
                    with self.subTest(field=field, value=value):
                        log = root / (field[2:] + value)
                        result = subprocess.run([sys.executable, str(script), "append", str(log), "--command", "check",
                                                 "--exit-code", "0", f"{field}={value}"], capture_output=True, timeout=30)
                        self.assertEqual(result.returncode, 2)
                        self.assertFalse(log.exists())
                        self.assertNotIn(b"Traceback", result.stderr)
            for content in ("[]\n", "{}\n"):
                with self.subTest(record=content):
                    log = root / "malformed"
                    log.write_text(content, encoding="utf-8")
                    result = subprocess.run([sys.executable, str(script), "verify", str(log)], capture_output=True, timeout=30)
                    self.assertIn(result.returncode, (1, 2))
                    self.assertNotIn(b"Traceback", result.stderr)
            log = root / "valid"
            result = subprocess.run([sys.executable, str(script), "append", str(log), "--command", "check",
                                     "--exit-code", "0", "--seconds", "1.5", "--cost", "0"], capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(subprocess.run([sys.executable, str(script), "verify", str(log)], capture_output=True, timeout=30).returncode, 0)
            record = json.loads(log.read_text(encoding="utf-8"))
            record["cost"] = float("nan")
            body = {key: value for key, value in record.items() if key != "hash"}
            record["hash"] = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False,
                                                       separators=(",", ":")).encode("utf-8")).hexdigest()
            log.write_text(json.dumps(record) + "\n", encoding="utf-8")
            result = subprocess.run([sys.executable, str(script), "verify", str(log)], capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertNotIn(b"Traceback", result.stderr)

    def test_report_rejects_uninformative_render_metadata(self):
        script = SCRIPTS / "verification_report.py"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / "artifact").write_bytes(b"output")
            base = {"artifact": "artifact", "artifact_sha256": hashlib.sha256(b"output").hexdigest(),
                    "scope": "all pages", "checks": [{"name": "render", "level": "rendered", "status": "pass",
                    "tool": "renderer", "evidence": ["page.png"]}], "not_inspected": []}
            cases = (("scope", None), ("scope", 42), ("tool", None), ("tool", 42),
                     ("evidence", "page.png"), ("evidence", [None]), ("evidence", [""]),
                     ("evidence", [{"unrelated": "not evidence"}]))
            for field, value in cases:
                with self.subTest(field=field, value=value):
                    report = json.loads(json.dumps(base))
                    (report if field == "scope" else report["checks"][0])[field] = value
                    path = root / "report.json"
                    path.write_text(json.dumps(report), encoding="utf-8")
                    result = subprocess.run([sys.executable, str(script), str(path)], capture_output=True, timeout=30)
                    self.assertEqual(result.returncode, 1, result.stdout)
                    self.assertNotIn(b"Traceback", result.stderr)
                    if field != "scope":
                        self.assertIn(b"deepest passing level: none", result.stdout)
            path.write_text(json.dumps(base), encoding="utf-8")
            self.assertEqual(subprocess.run([sys.executable, str(script), str(path)], capture_output=True, timeout=30).returncode, 0)
            base["checks"][0]["evidence"] = [{"path": "page.png", "sha256": "a" * 64}]
            path.write_text(json.dumps(base), encoding="utf-8")
            self.assertEqual(subprocess.run([sys.executable, str(script), str(path)], capture_output=True, timeout=30).returncode, 0)
            base["checks"][0]["tool"] = None
            base["checks"].insert(0, {"name": "lint", "level": "static", "status": "pass"})
            path.write_text(json.dumps(base), encoding="utf-8")
            result = subprocess.run([sys.executable, str(script), str(path)], capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn(b"deepest passing level: static", result.stdout)


if __name__ == "__main__":
    unittest.main()
