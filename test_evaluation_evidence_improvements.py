"""Regression cases for evaluation accounting and evidence log writes."""
import io
import json
import sys
import subprocess
import tempfile
import hashlib
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "skills/create-best-proposal/scripts"))
import eval_metrics as evaluation
import evidence_chain as chain
import task_contract
import run_repo_tests


def run(task, arm, verified, **extra):
    return {"task": task, "arm": arm, "conditions": extra.pop("conditions", "same"), "verified": verified,
            "claimed_complete": True, **extra}


class EvaluationTests(unittest.TestCase):
    def test_numeric_input_and_aggregate_overflow_are_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runs.json"
            for kind in ("huge", "sum-cost", "sum-seconds"):
                records = [run(task, arm, True, cost=1, seconds=1)
                           for task in ("a", "b") for arm in ("baseline", "candidate")]
                if kind == "huge":
                    records[0]["cost"] = 10 ** 309
                else:
                    field = "cost" if kind == "sum-cost" else "seconds"
                    for item in records:
                        item[field] = 1e308
                path.write_text(json.dumps(records), encoding="utf-8")
                with self.subTest(kind=kind), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    self.assertEqual(evaluation.main([str(path)]), 2)
            path.write_text(json.dumps([run("a", arm, True, cost=1, seconds=2) for arm in ("baseline", "candidate")]), encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(evaluation.main([str(path)]), 0)

    def test_missing_and_known_cost_and_time(self):
        missing = evaluation.metrics([run("a", "baseline", True)])
        self.assertIsNone(missing["cost_per_verified"])
        self.assertIsNone(missing["seconds_total"])
        known = evaluation.metrics([run("a", "baseline", True, cost=0, seconds=0)])
        self.assertEqual(known["cost_per_verified"], 0)
        self.assertEqual(known["seconds_total"], 0)

    def test_paired_changes_and_unverified(self):
        records = []
        for i, (a, b) in enumerate([(True, True), (False, True), (True, False), (False, False), (None, True)]):
            records.extend([run(str(i), "baseline", a), run(str(i), "candidate", b)])
        self.assertEqual(evaluation.paired_counts(evaluation.load(records)),
                         dict(pass_pass=1, fail_pass=1, pass_fail=1, fail_fail=1, unverified=1))

    def test_planned_tasks_cannot_disappear_from_both_arms(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runs.json"
            path.write_text(json.dumps({"planned": ["a", "b"], "runs": [run("a", "baseline", True), run("a", "candidate", True)]}))
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(evaluation.main([str(path)]), 2)
            path.write_text(json.dumps({"planned": ["a"], "runs": [run("a", "baseline", True), run("a", "candidate", True)]}))
            with redirect_stdout(io.StringIO()):
                self.assertEqual(evaluation.main([str(path)]), 0)

    def test_invalid_numbers_conditions_and_boolean_lookalikes(self):
        for extra in ({"cost": float("nan")}, {"seconds": -1}, {"conditions": {}}, {"verified": 1}, {"prior_pass": True, "regressed": "false"}, {"prior_pass": False, "regressed": True}):
            item = run("a", "baseline", True)
            item.update(extra)
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                evaluation.load([item])

    def test_unverified_claim_does_not_report_zero_false_completion(self):
        result = evaluation.metrics([run("a", "baseline", None)])
        self.assertIsNone(result["false_completion_rate"])
        self.assertEqual(result["claimed_unverified"], 1)

    def test_attempt_history_requires_retry_permission_and_completion(self):
        records = [run("a", arm, True, retry_allowed=True, attempts=[{"id": "first", "status": "invalid"}, {"id": "second", "status": "completed"}]) for arm in ("baseline", "candidate")]
        self.assertEqual(evaluation.metrics(list(evaluation.load(records)["baseline"].values()))["attempts_recorded"], 2)
        records[0]["retry_allowed"] = False
        with self.assertRaises(ValueError):
            evaluation.load(records)
        records[0]["retry_allowed"] = True
        records[0]["attempts"][-1]["status"] = "started"
        with self.assertRaises(ValueError):
            evaluation.load(records)

    def test_duplicate_json_members_and_nonfinite_values_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runs.json"
            for bad in ('{"runs": [], "runs": []}', '{"x": NaN}'):
                path.write_text(bad, encoding="utf-8")
                with redirect_stderr(io.StringIO()):
                    self.assertEqual(evaluation.main([str(path)]), 2)

    def test_extended_context_and_legacy_context_are_labeled(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runs.json"
            context = {k: "synthetic" for k in evaluation.CONTEXT_EXTENDED}
            for label, conditions in (("DECLARED-MATCH", context), ("INCOMPLETE", "legacy")):
                path.write_text(json.dumps([run("a", arm, True, conditions=conditions) for arm in ("baseline", "candidate")]), encoding="utf-8")
                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(evaluation.main([str(path)]), 0)
                self.assertIn("CONTEXT: " + label, out.getvalue())


class AtomicEvidenceTests(unittest.TestCase):
    def test_concurrent_processes_do_not_lose_successful_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp).resolve() / "log.jsonl"
            script = ROOT / "skills/create-best-proposal/scripts/evidence_chain.py"
            processes = [subprocess.Popen([sys.executable, str(script), "append", str(log), "--command", f"check-{i}", "--exit-code", "0"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for i in range(4)]
            results = [process.communicate(timeout=30) for process in processes]
            codes = [process.returncode for process in processes]
            self.assertTrue(all(code in (0, 2) for code in codes), (codes, results))
            self.assertGreater(codes.count(0), 0)
            records = chain.read_log(log)
            self.assertEqual(len(records), codes.count(0))
            self.assertEqual(chain.verify(records), [])

    def test_empty_and_failed_checks_are_not_verified(self):
        self.assertTrue(chain.verify([]))
        self.assertEqual(chain.stale_commands([{"command": "failed", "exit_code": 1, "artifacts": []}]), ["failed"])
        self.assertEqual(chain.stale_commands([{"command": "unknown", "exit_code": 0, "artifacts": []}]), ["unknown"])

    def test_owner_hint_exists_only_while_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "log"
            owner = log.with_name(log.name + ".lock") / "owner.json"
            def inspect(*args):
                metadata = json.loads(owner.read_text(encoding="utf-8"))
                self.assertGreater(metadata["pid"], 0)
                self.assertTrue(metadata["started_utc"])
                return {"hash": "synthetic"}
            with patch.object(chain, "_append_locked", side_effect=inspect):
                chain.append(log, "test", 0, [])
            self.assertFalse(owner.exists())
    def test_lock_refuses_append_and_preserves_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "log"
            chain.append(log, "one", 0, [])
            before = log.read_bytes()
            lock = log.with_name(log.name + ".lock")
            lock.mkdir()
            with self.assertRaises(ValueError):
                chain.append(log, "two", 0, [])
            self.assertEqual(log.read_bytes(), before)
            lock.rmdir()
            chain.append(log, "two", 0, [])
            self.assertEqual(chain.verify(chain.read_log(log)), [])

    def test_failed_replace_keeps_previous_log_and_unlocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "log"
            chain.append(log, "one", 0, [])
            before = log.read_bytes()
            with patch.object(chain.os, "replace", side_effect=OSError("simulated")):
                with self.assertRaises(OSError):
                    chain.append(log, "two", 0, [])
            self.assertEqual(log.read_bytes(), before)
            self.assertFalse(log.with_name(log.name + ".lock").exists())
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), ["log"])


class ContractReportTests(unittest.TestCase):
    def test_report_matches_oracle_and_actual_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "deck.txt"
            artifact.write_text("initial", encoding="utf-8")
            contract = {"goal": "check", "write_boundary": "work", "recovery": "review",
                        "scope": ["x"], "non_goals": ["y"], "outputs": ["deck"],
                        "test_oracle": ["numbers"], "stop_conditions": ["failure"],
                        "max_attempts": 2, "time_budget_minutes": 10, "allowed_actions": ["read"]}
            report = {"artifact": "deck.txt", "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                      "scope": "numbers", "checks": [{"name": "numbers", "level": "static", "status": "pass"}],
                      "not_inspected": []}
            cp, rp = root / "contract.json", root / "report.json"
            cp.write_text(json.dumps(contract), encoding="utf-8")
            rp.write_text(json.dumps(report), encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(task_contract.main(["check-report", str(cp), str(rp)]), 0)
                artifact.write_text("changed", encoding="utf-8")
                self.assertEqual(task_contract.main(["check-report", str(cp), str(rp)]), 1)
                artifact.write_text("initial", encoding="utf-8")
                report["checks"][0]["status"] = "fail"
                rp.write_text(json.dumps(report), encoding="utf-8")
                self.assertEqual(task_contract.main(["check-report", str(cp), str(rp)]), 1)


class TestSummaryTests(unittest.TestCase):
    def test_zero_and_all_skipped_are_not_complete(self):
        class Stub:
            testsRun = 0
            skipped = []
            expectedFailures = []
            def wasSuccessful(self):
                return True
        result = Stub()
        self.assertFalse(run_repo_tests.is_complete(result))
        result.testsRun, result.skipped = 1, [(None, "not available")]
        self.assertFalse(run_repo_tests.is_complete(result))
        result.testsRun = 2
        self.assertTrue(run_repo_tests.is_complete(result))


if __name__ == "__main__":
    unittest.main()
