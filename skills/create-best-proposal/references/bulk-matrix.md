# Bulk compliance and response matrix (SI-C1)

Prevent the **5-sample-row failure** in type C (technical responses) and RFPs with 30–60+ items.

## Principles

1. Generate **every row** mechanically. Summary slides show the top N rows plus a full-appendix note
   (Korean example: "전체 N건 별첨").
2. Fixed support codes (Korean values preserved): `O | 부분 | 조건부 | X | N/A | 확인필요`.
3. Partial/conditional/X/N/A rows require **reason, alternative, and roadmap** columns.
4. Retain REQ-ID, source location (page/clause), and response location (slide/sheet cell) in each row.

## CSV/JSON input

Required columns: `id, section, item, text`
Optional columns: `mandatory, support, product, note, source_loc, response_loc`

```bash
python scripts/bulk_matrix.py requirements.json -o matrix.md --summary-rows 8
python scripts/bulk_matrix.py requirements.csv -o matrix.csv --format csv
```

## Output

- Markdown compliance matrix (proposal body/appendix).
- Summary block: support statistics (O/부분/X/…; original Korean codes) + highest-risk rows.
- JSON sidecar: draft audit requirements[] (`state` defaults to pending).

## Slide placement

| Output | Content |
|---|---|
| Body, 1–2 pages | Statistics + top N high-weight/unsupported risks |
| Full appendix | Complete matrix (separate file if page-limited) |
| Each response slide | REQ-ID + support status in a corner |

If an original XLSX questionnaire exists, draft with bulk_matrix, then **transfer responses to the original sheet**
and check structural preservation (row order/formulas/hidden sheets).
