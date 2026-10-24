"""Synthetic regression cases for metadata boundaries and optional evidence tools."""
from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import install_skill
import package_plugin

ROOT = Path(__file__).resolve().parent
DOC_SCRIPTS = ROOT / "skills/create-proposal-document/scripts"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


visual = load("visual_compare", DOC_SCRIPTS / "visual_compare.py")
extraction = load("extract_rfp", DOC_SCRIPTS / "extract_rfp.py")
amendment = load("compare_requirements", ROOT / "skills/create-winning-proposal/scripts/compare_requirements.py")


class PrivateWorkspace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def json(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path


class MetadataBoundaryTests(PrivateWorkspace):
    def skill(self, name="create-best-proposal"):
        directory = self.root / "skills" / name
        shutil.copytree(install_skill.SKILLS_ROOT / name, directory, ignore=install_skill.COPY_IGNORE)
        return directory

    def test_raw_bool_and_scalar_variants_return_diagnostics(self):
        for name in (install_skill.FLAGSHIP, *sorted(install_skill.SIBLINGS)):
            directory = self.skill(name)
            metadata = directory / "agents/openai.yaml"
            original = metadata.read_text(encoding="utf-8")
            for value in ('"false"', "1", "null"):
                with self.subTest(name=name, value=value):
                    metadata.write_text('interface:\n  display_name: Test\npolicy:\n  allow_implicit_invocation: '
                                        + value + '\n', encoding="utf-8")
                    problems = install_skill.skill_schema_problems(directory)
                    self.assertTrue(any("must be a boolean" in p for p in problems), problems)
            for value in ("false", "1", '"text"'):
                for field in ("policy", "interface"):
                    with self.subTest(name=name, field=field, value=value):
                        metadata.write_text((f"interface: {value}\n" if field == "interface" else
                                             f"interface:\n  display_name: Test\npolicy: {value}\n"), encoding="utf-8")
                        self.assertTrue(any("must be an object" in p for p in
                                            install_skill.skill_schema_problems(directory)))
            metadata.write_text(original, encoding="utf-8")
            self.assertEqual(install_skill.skill_schema_problems(directory), [])

    def test_claude_quoted_boolean_rejected_and_unknown_extension_opt_in(self):
        directory = self.skill("create-proposal-document")
        path = directory / "SKILL.md"
        original = path.read_text(encoding="utf-8")
        path.write_text(original.replace("disable-model-invocation: true", 'disable-model-invocation: "false"'), encoding="utf-8")
        self.assertTrue(any("must be a boolean" in p for p in install_skill.skill_schema_problems(directory)))
        path.write_text(original.replace("---\n", "---\nfuture-host-extension: value\n", 1), encoding="utf-8")
        self.assertEqual(install_skill.skill_schema_problems(directory), [])
        self.assertTrue(any("unsupported" in p for p in
                            install_skill.skill_schema_problems(directory, strict_common=True)))

    def test_package_rejects_bad_content_before_zip_creation(self):
        source = self.root / "package"
        for relative in package_plugin.PACKAGE_FILES:
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, path)
        shutil.copytree(ROOT / "skills", source / "skills", ignore=install_skill.COPY_IGNORE)
        target = source / "skills/create-best-proposal/agents/openai.yaml"
        target.write_text("interface:\n  display_name: Test\npolicy: false\n", encoding="utf-8")
        output = self.root / "rejected.zip"
        with self.assertRaisesRegex(ValueError, "policy must be an object"):
            package_plugin.build_archive(output, root=source)
        self.assertFalse(output.exists())
        target.write_text("interface:\n  display_name: Test\n", encoding="utf-8")
        package_plugin.build_archive(output, root=source)
        self.assertTrue(output.is_file())

    def test_invalid_source_is_rejected_before_install(self):
        directory = self.skill()
        (directory / "agents/openai.yaml").write_text("interface: false\n", encoding="utf-8")
        destination = self.root / "install"
        with patch.object(install_skill, "SKILLS_ROOT", directory.parent):
            with self.assertRaises(SystemExit):
                install_skill.install_all(destination, [directory.name], False)
        self.assertFalse(destination.exists())

    def test_plain_yaml_non_string_description_is_rejected(self):
        directory = self.skill("create-proposal-document")
        path = directory / "SKILL.md"
        original = path.read_text(encoding="utf-8")
        for value in ("null", "~", "1.5", "1e3", ".nan", ".inf", "[x]", '["x"]', "{}", "!!int 3"):
            with self.subTest(value=value):
                path.write_text("---\nname: create-proposal-document\ndescription: " + value
                                + "\ndisable-model-invocation: true\n---\n", encoding="utf-8")
                self.assertTrue(install_skill.skill_schema_problems(directory))
        path.write_text(original, encoding="utf-8")
        self.assertEqual(install_skill.skill_schema_problems(directory), [])


class ExtractionTests(PrivateWorkspace):
    def setUp(self):
        super().setUp()
        self.source = self.root / "source.docx"
        self.source.write_bytes(b"synthetic source, not an OOXML conversion test")
        self.document = {"schema_name": "DoclingDocument", "texts": [{"text": "가상의 요구", "prov": []}],
                         "tables": [{"data": {"table_cells": [{"text": "123", "row_span": 2}]}}]}

    def test_import_preserves_structure_without_fabricated_pages_or_approval(self):
        incoming = self.json("input.json", self.document)
        original = self.source.read_bytes()
        result = extraction.extract(self.source, self.root / "run", imported_json=incoming)
        self.assertEqual(result["document"], self.document)
        self.assertEqual(result["source"]["sha256"], visual.sha256(self.source))
        self.assertEqual(len(result["source"]["sha256"]), 64)
        self.assertEqual(result["capabilities"]["page"], "unavailable")
        self.assertEqual(result["review_status"], "UNREVIEWED")
        self.assertFalse(result["submission_approval"])
        self.assertEqual(self.source.read_bytes(), original)
        with self.assertRaises(FileExistsError):
            extraction.extract(self.source, self.root / "run", imported_json=incoming)

    def test_invalid_import_never_produces_success_sidecar(self):
        for number, invalid in enumerate(({"texts": []}, {"schema_name": "DoclingDocument", "texts": [4]})):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                extraction.extract(self.source, self.root / f"run-{number}",
                                   imported_json=self.json(f"input-{number}.json", invalid))
            self.assertFalse((self.root / f"run-{number}/extraction.json").exists())

    def test_pdf_requires_models_and_path_escape_is_rejected(self):
        self.source = self.root / "source.pdf"
        self.source.write_bytes(b"%PDF-synthetic")
        with self.assertRaises(ValueError):
            extraction.extract(self.source, self.root / "run")
        models = self.root / "models"
        models.mkdir()
        with self.assertRaises(ValueError):
            extraction.validate_models(models, {"revision": "test", "files": {"../source.pdf": visual.sha256(self.source)}})

    def test_timeout_never_produces_an_extraction(self):
        with patch.object(extraction.subprocess, "run", side_effect=subprocess.TimeoutExpired("test", 1)):
            with self.assertRaises(subprocess.TimeoutExpired):
                extraction.extract(self.source, self.root / "run", timeout=1)
        self.assertFalse((self.root / "run/extraction.json").exists())

    def test_ocr_review_points_to_unchanged_numeric_text_and_table_cells(self):
        self.document["texts"] = [
            {"text": value} for value in ("운영 09:00~18:00", "점검 O9.00~1800", "OO:OO~OO:OO", "수량 105")]
        original = copy.deepcopy(self.document)
        result = extraction.make_sidecar(self.source, self.document, {"ocr": True})
        self.assertEqual(result["document"], original)
        review = result["ocr_review"]
        self.assertTrue(review["required"])
        expected = [
            ("/document/texts/0/text", ["numeric_content"]),
            ("/document/texts/1/text", ["numeric_content", "time_format_review"]),
            ("/document/texts/2/text", ["time_format_review"]),
            ("/document/texts/3/text", ["numeric_content"]),
            ("/document/tables/0/data/table_cells/0/text", ["numeric_content"]),
        ]
        self.assertEqual([(item["pointer"], item["reasons"]) for item in review["candidates"]], expected)
        for item in review["candidates"]:
            value = result
            for part in item["pointer"].split("/")[1:]:
                value = value[int(part)] if isinstance(value, list) else value[part]
            self.assertIsInstance(value, str)
        self.assertFalse(result["submission_approval"])
        self.assertEqual(result["review_status"], "UNREVIEWED")
        self.assertIn("non-exhaustive", review["coverage"])

    def test_ocr_review_does_not_claim_import_or_non_ocr_provenance(self):
        for setting in (False, "unknown"):
            self.assertNotIn("ocr_review", extraction.make_sidecar(self.source, self.document, {"ocr": setting}))
        empty = extraction.make_sidecar(self.source, {"schema_name": "DoclingDocument"}, {"ocr": True})
        self.assertEqual(empty["ocr_review"]["candidates"], [])
        self.assertTrue(empty["ocr_review"]["required"])

    def test_worker_records_ocr_settings_only_when_enabled(self):
        for enabled in (False, True):
            output = self.root / str(enabled)
            output.mkdir()
            argv = ["extract_rfp.py", str(self.source), "--worker", "--output", str(output)]
            if enabled:
                argv.append("--ocr")
            with patch.object(sys, "argv", argv), patch.object(extraction, "convert", return_value=(self.document, "test")):
                self.assertEqual(extraction.main(), 0)
            converter = json.loads((output / "converter.json").read_text(encoding="utf-8"))
            self.assertEqual(converter["ocr_settings"], extraction.OCR_SETTINGS if enabled else None)


class AmendmentTests(PrivateWorkspace):
    def test_renumber_and_text_changes_preserve_human_ids(self):
        original = {"id": "REQ-001", "text": "가상 수량 10", "source_clause_label": "1.1"}
        a = self.json("before.json", {"requirements": [original]})
        b = self.json("after.json", {"requirements": [{**original, "source_clause_label": "2.1"}]})
        result = amendment.compare(a, b)
        self.assertEqual(result["changes"][0]["change"], "reference-changed")
        self.assertEqual(result["changes"][0]["id"], "REQ-001")
        b = self.json("after.json", {"requirements": [{**original, "text": "가상 수량 11"}]})
        self.assertEqual(amendment.compare(a, b)["changes"][0]["change"], "modified")
        self.assertFalse(result["submission_approval"])

    def test_duplicate_ids_do_not_silently_merge_requirements(self):
        item = {"id": "REQ-001", "text": "가상", "source_clause_label": "1"}
        path = self.json("revision.json", {"requirements": [item, item]})
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            amendment.read_revision(path)


class VisualComparisonTests(PrivateWorkspace):
    environment = {"renderer": "synthetic", "renderer_version": "1", "font_profile": "test-fonts"}

    def snapshots(self):
        pdf = self.root / "input.pdf"
        pdf.write_bytes(b"%PDF-synthetic; rendering is mocked in unit tests")
        source = self.root / "source.txt"
        source.write_text("before", encoding="utf-8")
        visual.snapshot(pdf, source, self.environment, self.root / "baseline", "test-role")
        source.write_text("after", encoding="utf-8")
        visual.snapshot(pdf, source, self.environment, self.root / "candidate")

    def test_environment_mismatch_is_incomparable_without_rendering(self):
        self.snapshots()
        path = self.root / "candidate/manifest.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["environment"]["font_profile"] = "other-fonts"
        path.write_text(json.dumps(value), encoding="utf-8")
        with patch.object(visual, "render") as render:
            result = visual.compare(self.root / "baseline", self.root / "candidate", self.root / "result", max_changed_ratio=0)
        self.assertEqual(result["status"], "INCOMPARABLE")
        render.assert_not_called()

    def test_tampered_pdf_and_existing_output_are_rejected(self):
        self.snapshots()
        (self.root / "candidate/document.pdf").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            visual.compare(self.root / "baseline", self.root / "candidate", self.root / "result", max_changed_ratio=0)
        self.assertFalse((self.root / "result").exists())

    def test_render_failure_is_error_and_never_visual_approval(self):
        self.snapshots()
        with patch.object(visual.subprocess, "run", side_effect=FileNotFoundError):
            result = visual.compare(self.root / "baseline", self.root / "candidate", self.root / "result", max_changed_ratio=0)
        self.assertEqual(result["status"], "ERROR")
        self.assertFalse(result["visual_review_approved"])

    def test_page_pixels_and_page_count_are_compared_individually(self):
        from PIL import Image
        self.snapshots()
        left = self.root / "left.png"
        right = self.root / "right.png"
        Image.new("RGB", (10, 10), "white").save(left)
        changed = Image.new("RGB", (10, 10), "white")
        changed.putpixel((3, 4), (0, 0, 0))
        changed.save(right)
        version = subprocess.CompletedProcess([], 0, stdout=b"test", stderr=b"")
        for number, pages, expected in ((0, [[left], [left]], "SAME"),
                                        (1, [[left], [right]], "DIFFERENT"),
                                        (2, [[left], [left, right]], "DIFFERENT")):
            with self.subTest(expected=expected), patch.object(visual, "render", side_effect=pages), \
                    patch.object(visual.subprocess, "run", return_value=version):
                result = visual.compare(self.root / "baseline", self.root / "candidate", self.root / f"result-{number}", max_changed_ratio=0)
            self.assertEqual(result["status"], expected)
            self.assertFalse(result["visual_review_approved"])
        self.assertEqual(result["page_counts"], {"baseline": 1, "candidate": 2})

    @unittest.skipUnless(shutil.which("pdftoppm") and shutil.which("pdfinfo"), "Poppler unavailable")
    def test_real_poppler_same_and_changed_pdf(self):
        from PIL import Image, ImageDraw
        source = self.root / "source.txt"
        source.write_text("synthetic visual fixture", encoding="utf-8")
        for name in ("before", "after"):
            image = Image.new("RGB", (300, 200), "white")
            if name == "after":
                ImageDraw.Draw(image).rectangle((30, 30, 100, 100), fill="black")
            pdf = self.root / f"{name}.pdf"
            image.save(pdf, "PDF")
            visual.snapshot(pdf, source, self.environment, self.root / name, "test-role")
        same = visual.compare(self.root / "before", self.root / "before", self.root / "same", max_changed_ratio=0)
        changed = visual.compare(self.root / "before", self.root / "after", self.root / "different", max_changed_ratio=0)
        self.assertEqual(same["status"], "SAME", same)
        self.assertEqual(changed["status"], "DIFFERENT", changed)
        self.assertTrue((self.root / "different/result.json").is_file())


if __name__ == "__main__":
    unittest.main()
