#!/usr/bin/env python3
"""Optional local Docling extraction. Output is unreviewed source material, not an audit."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from visual_compare import read_object, sha256, write_json


OCR_SETTINGS = {"lang": ["ko", "en"], "confidence_threshold": 0.0, "scale": 3.0}
TIME_RANGE = re.compile(r"([0-9OoIl:.]{3,6})\s*[~～–-]\s*([0-9OoIl:.]{3,6})")
COLON_TIME = re.compile(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]")


def review_candidates(document: dict) -> list[dict]:
    """Non-exhaustive review pointers into the unchanged sidecar document."""
    items = [(f"/document/texts/{i}/text", item.get("text", ""))
             for i, item in enumerate(document.get("texts", []))]
    for i, table in enumerate(document.get("tables", [])):
        data = table.get("data", {})
        if isinstance(data, dict):
            items.extend((f"/document/tables/{i}/data/table_cells/{j}/text", cell.get("text", ""))
                         for j, cell in enumerate(data.get("table_cells", [])) if isinstance(cell, dict))
    candidates = []
    for pointer, text in items:
        if not isinstance(text, str):
            raise ValueError("Invalid Docling text")
        reasons = ["numeric_content"] if re.search(r"\d", text) else []
        if any(not all(COLON_TIME.fullmatch(value) for value in match.groups())
               for match in TIME_RANGE.finditer(text)):
            reasons.append("time_format_review")
        if reasons:
            candidates.append({"pointer": pointer, "reasons": reasons})
    return candidates


def capabilities(document: dict) -> dict:
    """Describe observed provenance only; DOCX need not have physical pages."""
    items = document.get("texts", []) + document.get("tables", [])
    provenance = [p for item in items if isinstance(item, dict)
                  for p in item.get("prov", []) if isinstance(p, dict)]
    return {
        "page": "available" if any(isinstance(p.get("page_no"), int) and p["page_no"] > 0
                                   for p in provenance) else "unavailable",
        "bbox": "available" if any(isinstance(p.get("bbox"), dict) for p in provenance) else "unavailable",
        "table_structure": "available" if any(isinstance(t.get("data"), dict)
                                              for t in document.get("tables", [])) else "unavailable",
        "coverage": "item-level provenance may be partial; inspect each item",
    }


def make_sidecar(source: Path, document: dict, converter: dict) -> dict:
    if document.get("schema_name") != "DoclingDocument":
        raise ValueError("Expected a DoclingDocument JSON export")
    if not isinstance(document.get("texts", []), list) or not isinstance(document.get("tables", []), list):
        raise ValueError("Invalid Docling item arrays")
    for item in document.get("texts", []) + document.get("tables", []):
        if not isinstance(item, dict) or not isinstance(item.get("prov", []), list):
            raise ValueError("Invalid Docling item/provenance")
    result = {
        "schema_version": 1, "kind": "proposal-rfp-extraction",
        "source": {"sha256": sha256(source), "format": source.suffix.lower()},
        "converter": converter, "capabilities": capabilities(document),
        "review_status": "UNREVIEWED", "submission_approval": False,
        # Preserve the complete native export, including optional spans/provenance.
        # Docling's origin.binary_hash is NOT our source SHA-256.
        "document": document,
    }
    if converter.get("ocr") is True:
        result["ocr_review"] = {
            "required": True, "candidates": review_candidates(document),
            "coverage": "non-exhaustive; missing text and other recognition errors may not be listed",
            "warning": "Low-confidence candidates retained; pointers are review aids, not errors or approvals. "
                       "OCR enabled does not prove each item came from OCR. Compare against original pages.",
        }
    return result


def validate_models(folder: Path, manifest: dict) -> None:
    if not folder.is_dir():
        raise ValueError("Prepared local model directory required")
    if not isinstance(manifest.get("revision"), str) or not manifest["revision"].strip():
        raise ValueError("Model manifest revision required")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("Model manifest needs relative file paths and SHA-256 values")
    for relative, expected in files.items():
        path = (folder / relative).resolve()
        if not path.is_relative_to(folder.resolve()) or not path.is_file() or sha256(path) != expected:
            raise ValueError("Model file missing, outside artifacts directory, or hash mismatch")


def convert(source: Path, artifacts: Path | None, ocr: bool) -> tuple[dict, str]:
    """Worker-only import: no models or Docling needed for JSON import mode."""
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import EasyOcrOptions, PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    options = PdfPipelineOptions(
        artifacts_path=artifacts, enable_remote_services=False, allow_external_plugins=False,
        do_ocr=ocr, do_table_structure=True,
    )
    if ocr:
        if artifacts is None or not (artifacts / "easyocr").is_dir():
            raise ValueError("Prepared easyocr models are required")
        # Retain uncertain lines for review instead of silently discarding requirements.
        options.ocr_options = EasyOcrOptions(**OCR_SETTINGS, download_enabled=False,
                                             model_storage_directory=str(artifacts / "easyocr"))
    converter = DocumentConverter(allowed_formats=[InputFormat.PDF, InputFormat.DOCX],
                                  format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)})
    converted = converter.convert(source)
    status = getattr(converted.status, "value", converted.status)
    if status != "success":
        raise ValueError("Conversion was not fully successful")
    return converted.document.export_to_dict(), importlib.metadata.version("docling")


def extract(source: Path, output: Path, *, imported_json: Path | None = None,
            artifacts: Path | None = None, model_manifest: Path | None = None,
            ocr: bool = False, timeout: int = 240) -> dict:
    if source.suffix.lower() not in {".pdf", ".docx"} or not source.is_file():
        raise ValueError("A local PDF or DOCX is required")
    if timeout < 1 or timeout > 1800:
        raise ValueError("timeout must be 1..1800 seconds")
    original_hash = sha256(source)
    manifest = None
    if imported_json is None and source.suffix.lower() == ".pdf":
        if artifacts is None or model_manifest is None:
            raise ValueError("PDF conversion requires prepared --artifacts and --model-manifest")
        manifest = read_object(model_manifest)
        validate_models(artifacts, manifest)
    if ocr and (source.suffix.lower() != ".pdf" or imported_json is not None):
        raise ValueError("--ocr is only supported for direct PDF conversion")
    output.mkdir(parents=True, exist_ok=False)
    if imported_json is not None:
        import_hash = sha256(imported_json)
        document = read_object(imported_json)
        if sha256(imported_json) != import_hash:
            raise ValueError("Imported JSON changed while reading")
        converter = {"name": "docling-json-import", "export_sha256": import_hash,
                     "source_binding": "caller supplied; verify export against original",
                     "ocr": "unknown"}
    else:
        env = {**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
               "HF_DATASETS_OFFLINE": "1", "PYTHONUTF8": "1"}
        command = [sys.executable, str(Path(__file__).resolve()), "--worker", str(source.resolve()),
                   "--output", str(output.resolve())]
        if artifacts:
            command += ["--artifacts", str(artifacts.resolve())]
        if ocr:
            command.append("--ocr")
        # Native model/runtime failures are errors, never partial successful extractions.
        try:
            subprocess.run(command, env=env, capture_output=True, check=True, timeout=timeout)
        except subprocess.CalledProcessError as exc:
            # Private diagnostics can contain paths/document content. Do not echo them
            # into public logs; the operator can inspect this run's local error file.
            with (output / "worker-error.log").open("xb") as stream:
                stream.write(exc.stderr or b"Worker failed without diagnostics")
            raise
        document = read_object(output / "document.json")
        worker = read_object(output / "converter.json")
        converter = {**worker, "models": manifest, "ocr": ocr,
                     "remote_services": False, "external_plugins": False,
                     "download_policy": "local artifacts + offline flags; not network isolation"}
    result = make_sidecar(source, document, converter)
    if result["source"]["sha256"] != original_hash:
        raise ValueError("Source changed during extraction")
    write_json(output / "extraction.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="New private directory; never overwritten")
    parser.add_argument("--import-json", type=Path, help="Import an existing DoclingDocument without dependencies")
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--model-manifest", type=Path)
    parser.add_argument("--ocr", action="store_true", help="Prepared Korean/English EasyOCR models required")
    parser.add_argument("--timeout", default=240, type=int)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        if args.worker:
            document, version = convert(args.source, args.artifacts, args.ocr)
            write_json(args.output / "document.json", document)
            write_json(args.output / "converter.json", {
                "name": "docling", "version": version,
                "ocr_settings": OCR_SETTINGS if args.ocr else None,
            })
        else:
            extract(args.source, args.output, imported_json=args.import_json, artifacts=args.artifacts,
                    model_manifest=args.model_manifest, ocr=args.ocr, timeout=args.timeout)
            print("EXTRACTED-UNREVIEWED (not approved requirements)")
        return 0
    except (ImportError, OSError, ValueError, TypeError, subprocess.SubprocessError) as exc:
        print(f"Extraction failed: {type(exc).__name__}; inspect private run diagnostics if present; "
              "no approved ledger was produced", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
