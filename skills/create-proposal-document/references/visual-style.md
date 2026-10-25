# Visual specifications (visual-style)

**The organization's brand-document skill, when installed, is the single source for brand tokens (colors, fonts, layout).**
Use those tokens unchanged; apply this file only for proposal-specific rules on top.
Without a brand skill, use the neutral defaults in §0.

## 0. Neutral defaults (only without a brand skill)

- Choose **one primary color**, a dark solid enterprise tone, and use it consistently throughout.
  Emphasis, table headers, and dividers use only the primary color and its dark/medium/light tints.
- Use dark gray body text (around #202020) and light backgrounds. Dark-background pages prohibited.
- Only two semantic colors: warning/decrease (red), achievement/increase (green), consistently in data contexts only.
- No neon/rainbow palettes. Use the buyer's required font; otherwise one system-standard Korean sans-serif
  family throughout, differentiating heading hierarchy by weight.
- A user-provided template overrides these defaults.

**One fallback token set** (use unchanged when neither a brand skill nor a user template exists;
reinventing it each run breaks consistency):

| Token | Value | Use |
|---|---|---|
| Primary | `#1F3864` | Table headers, titles, emphasis |
| Tints | `#8FAADC` / `#D6E0F0` / `#EDF1F8` | Secondary elements / zebra / light boxes |
| Body | `#202020`, secondary `#595959` | Text |
| Warning/positive | `#C00000` / `#1F7A3D` | Semantic colors (data contexts only) |
| Font | 맑은 고딕 (fallback: system Korean sans-serif) | Throughout |
| Sizes | Title 22~24pt · lead 12~13pt (bold) · body 10~11pt · table 9~10pt · caption 8~9pt | Hierarchy |

> This ladder is for **detailed evaluation submissions**. Presentations use body text of at least 18pt;
> executive summaries use 14pt. Specifications by artifact type live in `scripts/deck_profiles.py`,
> selected with `--profile`. Do not force the same size on printed scoring documents and screen presentations.

**Precedence**: this skill's visual rules (no dark backgrounds, message-first layout, etc.) **override**
generic design guidance from format skills (pptx/docx) when they conflict.
Overall: buyer RFP rules > user template > brand skill tokens > this file.

## 1. Accessibility floor (conservative design reference)

- Normal text contrast **at least 4.5:1**; large text (18pt+ or 14pt Bold+) **at least 3:1**
  (WCAG 2.2 reference: a web standard, not grounds for print legal-conformance claims).
- **Never encode status by color alone**: pair color with labels/symbols for acceptance, progress, and risk.
  Preserved Korean/symbol examples: O/부분/X, ●/◐/○, ↑/↓, "완료/진행/지연".
- Primary-color text is for large text/headings only; body-size text is dark gray.
- Caption diagrams/charts and include alt text in output files.
  Korean caption format example: "그림 N. 설명".

## 2. Page (slide) layout — message priority

Top-to-bottom visual order = message importance (same as proposal-structure.md's page composition rules).

Korean layout example:

```
[헤더] 문서명 | Ⅲ. 제안기술 부문 > 1. 상세 추진전략     (breadcrumb, 9~10pt)
[제목] 네트워크 구성 방안                               (primary-color family, highest hierarchy)
[리드문] 이 페이지의 결론 1~3줄                          (larger or bolder than body)
[본문] 도식 1개 또는 표 1~2개                            (minimize text lists)
[캡션/출처/REQ-ID] 기준일·출처·대응 요구사항 번호        (small secondary gray)
[푸터] 제안사 로고/워드마크 + 페이지 번호
```

- Use styles for hierarchy: Heading 1/Heading 2/Body in DOCX, master layouts in PPTX.
  Do not imitate hierarchy with manual bold/size changes (automatic contents and bulk edits must remain possible).
- Type C (technical responses) shows item number/status in the top-right corner. Korean example: `(완료) 26. …`.

## 3. Proposal-specific components

### Compliance matrix (requirements response)
- Columns: Requirement | Acceptance | Proposal response | Page | Notes.
- Header: primary background + white text. Data: white/light primary-tint zebra rows.
- Pair acceptance symbols with text (preserved codes: O/부분/X). No color-only distinction.

### SLA table
- Rows: severity 1~4 with definitions. Columns: response time, action target, escalation level.
- Only severity 1 may be emphasized (bold). Avoid red backgrounds: warning color is for text/icons only.

### Staff profiles
- Card/table: Name (check masking policy) | Grade/position | Experience years | Qualifications | Allocation (M/M).
- Photos only if required by the buyer. Use official qualification names.

### Track-record table
- Columns: Project | Buyer | Period | Main products/technologies | Scale (scope). Most recent first.
- If over 3 pages, put representative records in the body and the full list in an appendix.
- **Protect other customers' identifying information**: confirm permission to disclose; anonymize nonpublic records
  (Korean example: "금융권 A사") and state that the name is anonymized.

### Schedule Gantt
- Monthly columns, phase row groups. Milestones use ◆ plus a label.
- Distinguish phases only with primary-color tints. Warning color only for delay/risk.

### Architecture diagrams
- Zones: light background boxes + zone labels (never distinguish zones by color alone).
- Keep hierarchy flow consistently top-to-bottom or left-to-right. Legend required (line types, icon meanings).
- Follow manufacturer logo guidelines; no arbitrary changes.

## 4. Common table rules

- Every table: explicit header row (minimal merging), units in headers/footnotes, source/reference date below.
- Right-align numeric columns with consistent units; left-align text.
- Split tables across pages with repeated headers and the Korean continuation label "계속".

## 5. Converting to DOCX

- When the buyer requires A4 documents, keep the same structure/lead rules and apply the brand skill's DOCX specifications if available.
- Heading 1 = chapter (Ⅰ·Ⅱ); Heading 2 = section; Heading 3 = subsection. Generate contents automatically from styles.
- Keep body font size/line spacing consistent. Do not evade page limits by shrinking text; condense content instead.
