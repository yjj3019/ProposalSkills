"""Source inventory proposals must fail closed without manufacturing human approval."""
import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "skills/create-best-proposal/scripts"))
sys.path.insert(0, str(REPO / "skills/create-winning-proposal/scripts"))
import check_source_inventory as checker  # noqa: E402
import proposal_gate  # noqa: E402


class SourceInventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "rfp.pdf"
        self.source.write_bytes(b"synthetic")
        self.sidecar = self.root / "extraction.json"
        self.data = {"schema_version": 1, "kind": "proposal-rfp-extraction",
                     "source": {"sha256": hashlib.sha256(b"synthetic").hexdigest(), "format": ".pdf"},
                     "review_status": "UNREVIEWED", "submission_approval": False, "document": {}}
        self.sidecar.write_text(json.dumps(self.data), encoding="utf-8")

    def item(self, ident="rfp", required=True, source="rfp.pdf", extraction="extraction.json"):
        return {"id": ident, "required": required, "source_path": source, "extraction_path": extraction}

    def check(self, *sources, **extra):
        return checker.check_inventory({"sources": list(sources), **extra}, self.root)

    def test_review_and_inventory_remain_open_and_block_gate(self):
        result = self.check(self.item(), existing_inputs=[])
        self.assertEqual(result["sources"][0]["status"], "extracted_unreviewed")
        self.assertEqual(result["inventory_completeness"], "UNVERIFIED")
        self.assertEqual(result["conflict_check"], "CHECKED")
        self.assertEqual([i["id"] for i in result["inputs"]], ["source-rfp", "source-inventory-completeness"])
        audit = json.loads((REPO / "skills/create-best-proposal/fixtures/audit_ready_financial.json").read_text(encoding="utf-8"))
        audit["inputs"] = result["inputs"]
        failures = proposal_gate.evaluate(audit)
        self.assertTrue(any("blocking input source-rfp is open" in f for f in failures))
        self.assertTrue(any("blocking input source-inventory-completeness is open" in f for f in failures))

    def test_missing_corrupt_mismatch_unknown_and_optional(self):
        self.sidecar.write_text("{", encoding="utf-8")
        result = self.check(self.item("broken"), self.item("missing", None, "missing.pdf", None),
                            self.item("optional", False, "optional.pdf", None))
        self.assertEqual([i["status"] for i in result["sources"]],
                         ["inspection_failed", "source_missing", "source_missing"])
        self.assertEqual([i["id"] for i in result["inputs"]],
                         ["source-broken", "source-missing", "source-inventory-completeness"])
        self.data["source"]["sha256"] = "0" * 64
        self.sidecar.write_text(json.dumps(self.data), encoding="utf-8")
        self.assertEqual(self.check(self.item())["sources"][0]["status"], "source_mismatch")

    def test_optional_uninspectable_is_not_silent_and_closed_collision_is_reported(self):
        with patch.object(Path, "lstat", side_effect=PermissionError):
            result = self.check(self.item(required=False),
                                existing_inputs=[{"id": "source-rfp", "status": "closed"}])
        self.assertEqual(result["sources"][0]["status"], "inspection_failed")
        self.assertEqual(result["inputs"][0]["class"], "non-blocking")
        self.assertEqual(result["conflicting_input_ids"], ["source-rfp"])
        self.assertEqual(self.check(self.item())["conflict_check"], "NOT_CHECKED")

    def test_invalid_manifest_and_outside_paths_fail(self):
        for manifest in ({"sources": []}, {"sources": [{"id": "x"}]},
                         {"sources": [self.item(required="false")]},
                         {"sources": [self.item(), self.item()]},
                         {"sources": [self.item(source="../outside.pdf")]},
                         {"sources": [self.item()], "existing_inputs": [{"id": "x"}, {"id": "x"}]}):
            with self.subTest(manifest=manifest), self.assertRaises(ValueError):
                checker.check_inventory(manifest, self.root)

    def test_detects_source_and_extraction_changes(self):
        real_digest = checker.digest
        counts = {self.source: 0, self.sidecar: 0}

        def changed(path):
            counts[path] += 1
            return "changed" if path == self.source and counts[path] == 2 else real_digest(path)

        with patch.object(checker, "digest", side_effect=changed):
            result = self.check(self.item())
        self.assertEqual(result["sources"][0]["status"], "source_changed")
        self.assertEqual(result["inputs"][0]["status"], "open")

        def disappears(path):
            if path == self.source and counts[path] >= 1:
                raise FileNotFoundError
            counts[path] += 1
            return real_digest(path)

        counts = {self.source: 0, self.sidecar: 0}
        with patch.object(checker, "digest", side_effect=disappears):
            result = self.check(self.item(extraction="missing.json"))
        self.assertEqual(result["sources"][0]["status"], "source_changed")

        counts = {self.source: 0, self.sidecar: 0}

        def sidecar_changes(path):
            counts[path] += 1
            return "changed" if path == self.sidecar and counts[path] == 2 else real_digest(path)

        with patch.object(checker, "digest", side_effect=sidecar_changes):
            result = self.check(self.item())
        self.assertEqual(result["sources"][0]["status"], "extraction_changed")

    def test_cli_does_not_overwrite_or_emit_private_paths(self):
        manifest = self.root / "sources.json"
        manifest.write_text(json.dumps({"sources": [self.item()]}), encoding="utf-8")
        output = self.root / "report.json"
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(checker.main([str(manifest), "--output", str(output)]), 0)
            first = output.read_bytes()
            self.assertEqual(checker.main([str(manifest), "--output", str(output)]), 2)
        self.assertEqual(output.read_bytes(), first)
        self.assertNotIn(str(self.root), output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
