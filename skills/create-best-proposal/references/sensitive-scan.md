# Sensitive-data scan (`scripts/sensitive_scan.py`)

Run it before a proposal, appendix, evidence file, or audit JSON leaves your machine: shared with a
reviewer, attached to a bid, bundled for submission, or committed. Standard library only; it never
modifies a file and never prints a full value.

```bash
python scripts/sensitive_scan.py final.pptx appendix.docx evidence/            # files and folders
python scripts/sensitive_scan.py final.pptx --allow-kind email --allow-kind mobile-phone   # bidder's own contacts
python scripts/sensitive_scan.py evidence/ --json
```

Exit codes: `0` clean, `1` findings, `2` incomplete (something could not be read) or usage error.

## What it finds

| Kind | Severity | Notes |
|---|---|---|
| Credentials: AWS keys, private-key headers, GitHub/GitLab/Slack/Google/npm tokens, `sk-` style keys, `password = "..."`, `scheme://user:password@host` | high | Placeholders such as `changeme` or `your-api-key-here` are ignored. |
| `resident-registration-number` (주민등록번호 / 외국인등록번호) | high | A valid birth date is required. The note says whether the official checksum also holds; numbers issued since October 2020 are random and need not satisfy it, so a checksum failure is still reported. |
| `payment-card-number` | high | Luhn-valid 16-digit numbers only. |
| `email`, `mobile-phone` | medium | Documentation domains (`example.com`) are ignored. Staff resumes and contact slides are the usual source. |
| `internal-ip` | low | `10.x`, `172.16-31.x`, `192.168.x`. Confirm the address is not the customer's real network. |

## What it reads

Plain text and code files, plus the text of `.pptx`, `.docx`, and `.xlsx` (slides, notes, comments,
headers/footers, shared strings, chart caches, and author/company metadata). Text split across runs is
joined first, so a number cannot hide between two formatting runs. XML with DTD/entity declarations is
refused, and unzipped size and part count are capped.

## What it cannot tell you

- Anything it cannot read is printed as `UNSCANNED` and makes the result `INCOMPLETE`: unsupported
  types, binary files, oversized or corrupt archives, and embedded images/OLE objects (text inside
  images is never inspected).
- A name, a project code, or an amount can be confidential without matching any pattern. Customer-name
  checks remain a human review item (see the review checklist).
- Findings are leads for a human, not a privacy or legal determination, and CLEAN means only that these
  patterns were absent from the files that were read.

This scanner does not feed `unified_gate.py`: submission readiness is still decided by the gates. Use it as
a separate step, and record the result in your own submission checklist.
