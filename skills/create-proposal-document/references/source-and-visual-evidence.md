# Optional source extraction, amendment, and visual regression tools

Store every output in the customer's work folder. Sources, JSON, page images, and diffs may contain sensitive content:
never write them into public repositories or installed skill folders.
Continue using existing generation/submission gates. These sidecars are not audit JSON and never update approvals automatically.
Example paths are relative to the user-selected work folder; locate scripts in their installed location.

## Translated PDF references

Treat a translated PDF as an unverified reading aid, not the authoritative RFP or evidence. Keep the original and
verify the page mapping of any bilingual output before comparing it with the translation. Compare each relevant
page against the original, including table headers and cells, footnotes, requirements IDs, numbers and units,
conditions, exclusions, and negations. Mark uncertain or missing content `[unverified]`; do not infer or copy it
into a requirement or commitment as confirmed.

Check both rendered pages and extracted/searchable text, including text and image regions on mixed pages.
Check for untranslated or partially translated passages even when conversion succeeds. Tables may remain in the source language or as images;
a visually readable identifier or value may extract incorrectly or not at all. An extraction mismatch is a review
warning, not by itself proof that the visible page is wrong. Verify translated meaning and any questionable value
against the original before updating the requirements/evidence register.

## 1. Structured RFP extraction

`scripts/extract_rfp.py` connects PDF/DOCX with DoclingDocument JSON. Existing JSON can be imported without Docling.
Record source full SHA-256 and JSON hash separately; a human confirms that imported JSON actually matches the source.
Do not use Docling's internal origin hash as SHA-256.

```bash
python scripts/extract_rfp.py input.pdf --import-json docling.json --output extraction-run
```

Direct conversion requires `docling` in a separately selected environment. No automatic installation/download.
PDF requires prepared models and a manifest with a `revision` string and `files` object
(model-folder-relative paths → full SHA-256). Check the actual model revision, tool/model licenses, and missing models.
Manifest verification covers only listed files; it does not prove completeness of all actually used models.
For OCR, prepare Korean/English EasyOCR models in `artifacts/easyocr`.
OCR is disabled without `--ocr`.

```bash
python scripts/extract_rfp.py input.pdf --artifacts models --model-manifest models.json --ocr --output extraction-run
```

`--ocr` uses Korean/English EasyOCR with confidence threshold=0 and OCR scale=3 (216 DPI),
preserving low-confidence candidates and recording settings in `converter.ocr_settings`.
Output-image DPI differs from internal OCR render DPI.
Preserving low-confidence text can reduce filter omissions but increase noise.
Higher resolution does not consistently improve numeric/time recognition; do not increase it indiscriminately.

With OCR, `ocr_review.candidates` supplies sidecar-wide JSON Pointers and review reasons.
It assists review of numeric paragraphs/table cells and suspicious time formats such as `O9.00~1800`.
`time_format_review` is not an error determination; even source `0900~1800` may require checking.
Compare well-formed numbers with the original too. It cannot detect all omissions or nonnumeric misrecognitions;
an empty list does not establish accuracy. It does not authenticate each item's actual OCR provenance,
automatically correct source content/numbers/times, or approve them. Imported JSON has unverified OCR settings.

Actual conversion comparison on 2026-10-24 (Docling 2.142.1/EasyOCR 1.7.2 CPU):
two clean synthetic documents were converted to 150/300 DPI image PDFs.
Settings were selected on the existing sample and frozen; an additional sample with different times/amounts/quantities
was used only for validation. CER = edit distance/reference character count after NFKC/whitespace removal,
preserving punctuation/numbers. Table cells were compared in row/column order, counting omitted sentences as errors.

| Synthetic sample | Input DPI | Previous CER (threshold 0.5) | Updated CER (threshold 0) |
|---|---:|---:|---:|
| Existing document (95 reference characters) | 150 | 22.11% | 9.47% |
| Existing document | 300 | 18.95% | 10.53% |
| Additional document (103 reference characters) | 150 | 35.92% | 9.71% |
| Additional document | 300 | 47.57% | 10.68% |

Missing SLA/title text and the additional sample's quantity sentence were recovered;
text/positions of the existing table's 6 cells were preserved.
The additional sample recovered 2/2 omitted quantities; amounts remained accurate.
Time strings still had 0/6 exact matches after the change: colons, periods, digit errors remained.
These paragraphs receive `time_format_review`; the flag itself does not improve recognition accuracy.
Internal-render experiments at 300/432 DPI showed no consistent improvement and were not adopted.
The text-PDF control retained CER 0%.
This is omission-mitigation evidence from small synthetic samples, not an accuracy guarantee for real Korean RFPs.
See [official Docling options](https://docling-project.github.io/docling/reference/pipeline_options/) for configuration semantics.

### Scanned time ranges: optional RapidOCR comparison

Keep EasyOCR as default. For upright Korean scanned PDFs, an optional profile disables automatic rotation classification
and OCRs full pages. It may replace digital text too; never apply it indiscriminately to digital/mixed PDFs.
Validate real RFPs with rotation/skew/noise separately.

```bash
python scripts/extract_rfp.py scan.pdf --artifacts models --model-manifest models-rapid.json --ocr --ocr-engine rapidocr --output extraction-run
```

The separately validated combination is Docling 2.142.1, RapidOCR 3.10.0, ONNX Runtime 1.31.0,
CPU with 2 threads. The optional profile fixes device/threads to these settings.
Do not add it to default requirements. Prepare models beforehand; no downloads or automatic engine substitutions during conversion.
Use [Docling model preparation](https://docling-project.github.io/docling/usage/advanced_options/)
`RapidOcrModel.download_models(backend="onnxruntime", lang="iso:ko", model_size="small", local_dir=...)`.
Place all files below in the model folder and record full SHA-256/revision in the manifest.
Despite the `small` option name, this combination's Korean recognizer is PP-OCRv5 mobile.

- `RapidOcr/ch_PP-OCRv5_det_mobile.onnx`
- `RapidOcr/ch_ppocr_mobile_v2.0_cls_mobile.onnx` (required for initialization even with classification disabled)
- `RapidOcr/korean_PP-OCRv5_rec_mobile.onnx`

Profile: `lang=["iso:ko"], backend="onnxruntime", model_size="small", text_score=0,
scale=3, use_cls=false, force_full_page_ocr=true`.
Explicitly supply actual model paths and verify all three manifest entries/hashes.
Record engine, settings, package versions, manifest in `converter`.
No string correction or majority-vote merging.

Comparison on the same synthetic samples (2026-10-24):

| Engine/method | Exact time-range matches | Observed limitations/adoption |
|---|---:|---|
| Default EasyOCR | 0/6 | Keep existing omission-mitigation settings |
| EasyOCR grayscale/Otsu/adaptive binarization | Each 0/2 | Standalone OCR of existing document at two DPIs; no improvement, rejected |
| Tesseract 5.5.3 / tesserocr 2.12.0 / tessdata_best kor+eng, original PSM 3/6 | Each 2/2 | Standalone OCR; CER 71.58% or 32.63~33.68%; table omissions, rejected |
| RapidOCR automatic line rotation classification | 0/6 | Korean/time strings reversed in full conversion; rejected |
| RapidOCR classification off, region OCR | 6/6 | Full-conversion title damage persisted with backend/300 DPI changes; rejected |
| RapidOCR classification off, full page | 6/6 | Adopted as optional; Korean title content, 6 table cells/positions, amounts, quantities preserved |

The final profile's CER is 2.11% at both 150/300 DPI for the existing document and 0% for both additional documents.
Reconverted four scans and the digital PDF control through the product extraction worker CLI.
The digital control worsened from non-OCR CER 0% to 2.11% with this profile: prefer the default non-OCR route for text PDFs.
Two errors in the existing title (`○○→OO`) remained, so the full title was not counted as an exact match.
Standalone RapidOCR grayscale/Otsu/adaptive binarization also showed no improvement and were not added.
Engine comparisons used local conversion with [official RapidOCR models](https://rapidai.github.io/RapidOCRDocs/main/model_list/)
and [Tesseract best models](https://github.com/tesseract-ocr/tessdata_best).
Standalone OCR's 2 cases and full Docling conversion's 6 have different denominators.
They are DPI variants of two clean synthetic documents, not six independent real RFPs.
Even well-formed times need source comparison; extraction remains UNREVIEWED. UI was outside validation scope.

Disable remote services/external plugins, set HF/Transformers offline flags and prohibit EasyOCR downloads.
This is not OS network isolation. Model/backend versions may have other communication paths:
first validate synthetic samples in an approved isolated environment before confidential material.
Missing models/dependencies, timeout, partial conversion are errors; do not auto-recover by downloading.
`--timeout` accepts 1~1800 seconds.

`extraction.json` retains `UNREVIEWED` and `submission_approval: false`.
Preserve native JSON cells/spans/pages/bboxes. In `capabilities`, available means observed for some items,
not complete location coverage. Do not fabricate missing DOCX pages/coordinates.
Paragraph/table-cell/JSON-pointer locations are not stable IDs across revisions.

Humans compare source/candidates, moving only approved content into existing register fields such as
`exact_text/source/evidence_refs`. Successful extraction/confidence is not factual accuracy or approval probability.
Divide Korean gold sets into digital/scanned PDF, DOCX, merged cells, cross-page tables.
Record exact matches for amounts/deadlines/qualifications, omissions/duplicates, table structure/location coverage,
time/memory. Do not promise accuracy before measurement.

## 2. Amendment comparison

Governance `compare_requirements.py` compares only revisions matched by a human under the same IDs.
Input: `{"requirements": [{"id": "REQ-001", "text": "가상의 요구", "source_clause_label": "1.1"}]}`.
The Korean text is an example input. IDs are stable internal identifiers; source_clause_label is revision-specific numbering.

```bash
python compare_requirements.py before.json after.json --output amendment-diff.json
```

Record additions/removals/text/reference changes, before/after values, text diffs. No automatic similarity matching.
Keep the same ID for renumbering; a human records split/merge/ambiguous repeated-text relationships.
An unchanged diff does not prove the absence of missing requirements or mismatched IDs.
Re-review changed responses, evidence, figures, page references; stale-sweep removed values.

## 3. PDF visual comparison

`scripts/visual_compare.py` uses Poppler `pdftoppm`/`pdfinfo` and Pillow.
Pillow is common in PPTX environments, but verify its presence; no automatic installation.
This independent implementation draws on diff-pdf-visually's page-level regression principle;
it requires neither ImageMagick nor extra comparison packages.

Create environment JSON after checking actual renderer versions and font files.
`renderer`, `renderer_version`, `font_profile` are nonempty strings.
Prefer a font_profile identifier pointing to an externally maintained list of font-file hashes.
Declarations are not actual font-detection evidence.

```bash
python scripts/visual_compare.py snapshot approved.pdf --source approved.pptx --environment env.json --reviewer reviewer-role --output baseline
python scripts/visual_compare.py snapshot candidate.pdf --source candidate.pptx --environment env.json --output candidate
python scripts/visual_compare.py compare baseline candidate --max-changed-ratio 0 --output comparison-run
```

Record a baseline reviewer after actual PDF review. The reviewer string is not authenticated electronic approval
and does not replace audit human approval.
Each snapshot keeps a PDF copy, source/PDF hashes, environment.
Baseline/candidate source hashes may legitimately differ; verify each against its own file.
Hashes do not establish PDF-to-source conversion fidelity.

Defaults: DPI=150, channel_delta=8. Count pixels whose recorded RGB channel difference **exceeds** delta.
A page is DIFFERENT when changed_ratio **exceeds** explicit `--max-changed-ratio`.
Any different page makes the whole result DIFFERENT, as do page-count/size differences.
Never hide small significant changes in an all-page average.
Review bboxes/diff PNGs and calibrate tolerance/DPI using small-number/line/Korean-omission samples.
Thresholds are not print-quality certification.

Exit codes: SAME=0, DIFFERENT=1, ERROR/usage error=2, INCOMPARABLE=3.
Different renderer/font/OS environments mean INCOMPARABLE; compare like engines first.
PowerPoint↔LibreOffice requires separate baselines/manual review.
Execution failures/incomplete pages must not count as SAME.
Write before/after/diff/result.json only to a new run folder.
Never overwrite existing folders/baselines or automatically delete/update them.
Users clean only their own runs according to retention policy.

SAME is a change-detection result at those settings; it does not certify source fidelity, facts, persuasion,
or absence of table overflow. `visual_review_approved` always stays false.
Continue existing `deck_check.py --render`, all-page review, final PowerPoint font checks, integrated gates.
To retain PDF, separately export from the approved renderer and pass it to snapshot.
Do not change the existing renderer's temporary-PDF lifetime or audit schema.

Design references: [Agent Skills](https://agentskills.io/specification),
[diff-pdf-visually](https://github.com/bgeron/diff-pdf-visually),
[Docling offline configuration](https://github.com/docling-project/docling/blob/main/docs/usage/advanced_options.md).
No external code/templates were copied. Separately check terms for actual adopted revisions of optional packages/models.
