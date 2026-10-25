# Writing rules (writing-style)

These rules were commonly observed in 16 winning proposals. Their purpose is to let evaluators read quickly
and score accurately: write verifiable sentences rather than decorative prose.

## 1. Basic style

- **Endings**: Korean PPTX body text defaults to noun endings (Korean examples: "~ 제공", "~ 구성").
  Lead statements and DOCX body text use complete polite sentences ending in "~합니다".
  Do not mix styles within a document (polite leads + noun-form bullets is the only permitted combination).
- **Length**: aim for at most 60 characters per lead sentence. At most 40 characters per bullet line (split when exceeding 2 lines).
- **Subject**: avoid repeatedly using the Korean example "당사는". Name the actor only when it changes (proposer/buyer/vendor/consortium partner).
- **Active voice**: replace the Korean example "~될 수 있습니다" with "~합니다/제공합니다". Keep responsibility clear.

## 2. Banned exaggerations (hard rule)

The following **Korean examples are prohibited unless objective evidence and scope appear on the same page**:

> 최고, 완벽, 혁신적, 획기적, 100%, 무중단, 완전 자동화, 위험 제로, 유일한, 업계 1위

Exception: buyer source wording (RFP/evaluation table) may be quoted verbatim with attribution.
Do not repeat such quotations as the proposer's factual claims.

**English banned-word dictionary** (apply the same discipline to English output; includes idiomatic English exaggerations rather than a 1:1 translation):

> best, best-in-class, world-class, industry-leading, leading, unique, only,
> perfect, flawless, innovative, revolutionary, cutting-edge, state-of-the-art,
> next-generation, 100%, zero downtime, zero risk, fully automated, fully compliant,
> complete/total coverage, seamless, effortless, guaranteed, bulletproof,
> future-proof, unlimited, instant, significant savings

Replacement principle (same as Korean): precise capability + boundary + evidence + expected benefit.
Preserved mixed-language examples:
"industry-leading performance" → "measured N TPS under [조건], verified by [출처]";
"zero downtime" → "target [가용률/RTO] with [이중화 구성], validated by [시험]";
"guaranteed 40% savings" → "estimated up to 40% against [기준선], subject to [전제]".
Attributed quotations from buyer sources are exceptions, but must not be repeated as proposer factual claims.

Korean replacement examples (practice in winning proposals):

| Banned expression | Replacement wording + evidence format |
|---|---|
| 업계 최고의 기술력 | "{제조사} 최상위 파트너 인증, 공인 기술자격 N명 보유" (include certification table) |
| 무중단 서비스 | "관리 노드 3중화 + 로드밸런서 이중화로 단일 장애점(SPOF) 제거" (include architecture) |
| 100% 장애 예방 | "월 1회 예방점검 N개 항목 수행으로 장애 사전 감지" (include inspection item table) |
| 혁신적인 솔루션 | "검증된"/"안정적인" + reference table (buyer, period, scale) |
| 완전 자동화 | "설치·배포 자동화(범위: OS 프로비저닝~패치), 승인 절차는 수동 유지" |

## 2-1. Ambiguous commitments (AMBIGUOUS_COMMITMENT)

Exaggerations inflate promises; ambiguous commitments obscure them. Korean examples include "지원 가능",
"검토 예정", "협의 가능", "제공할 수 있음", "적극 검토", "노력하겠습니다" for proposer actions.
Without **who / what / when / under which conditions / to what extent**, evaluators read no commitment.

Korean examples:

| BAD | BETTER |
|---|---|
| 필요 시 기술지원이 가능합니다. | Critical 장애 접수 후 30분 이내 1차 응답하고 원격 분석을 즉시 착수합니다. |
| 성능 저하 시 튜닝 지원 예정입니다. | 월간 성능 보고에서 기준 초과 항목을 식별하고, 다음 정기점검에서 튜닝 결과를 보고합니다. |
| 개선 방안을 적극 검토하겠습니다. | 개선 요청은 변경관리 절차로 접수해 영향도 분석 결과를 10영업일 이내 회신합니다. |

The words themselves are not banned. These are valid cases:

- The sentence identifies who sets the execution condition. Korean example: "발주처가 승인하는 경우 추가 교육 제공이 가능합니다."
- Product/system capability description. Korean example: "클러스터는 노드 추가로 수평 확장이 가능합니다."
- Buyer/evaluator as subject. Korean example: "발주처는 결과 보고서를 검토할 수 있습니다."
- Sentences specifying time, frequency, or quantity.

In RFI responses, use estimated ranges, alternatives, and clarification questions instead of commitments (commitments themselves are blocked by the gate).
If no evidence supports a figure, leave `[NEEDS INPUT: owner — 항목]` rather than covering the gap with vague wording.

`quality_gate.py` reports service actions paired with vague predicates as a **nonblocking warning** labeled `[모호확약]`.
This sentence-level heuristic can produce false positives and negatives. It does not affect submission decisions; a human reviews and corrects context.

## 3. Numeric notation

- Units required for counts, capacity, duration, and money (Korean unit examples: 대, 식, TB, M/M, 개월, 백만원).
- Use thousands separators and only necessary decimal places. Use tilde (~) consistently for ranges.
- For calculated figures (benefits/savings), **footnote the formula and assumptions**.
- Dates: YYYY.MM.DD or the Korean format YYYY년 M월; use one format throughout.
- Reference dates: annotate changeable figures (staff, track record, finance), for example the Korean "(2026.6월 기준)".

## 4. Terminology consistency

- On first mention use the full name (abbreviation), then the abbreviation. Korean example: "서비스 수준 협약(SLA)".
- An appendix glossary of abbreviations is conventional (common across analyzed samples).
- Follow official manufacturer product names. No arbitrary Korean transliterations or unofficial abbreviations.
- Use the buyer's RFP self-reference consistently (Korean examples: "당행", "당사", "우리 공사").
- Do not mix names for one concept (Korean examples: "장애 대응" and "장애 처리"). Establish a glossary first.

## 5. Paragraph and bullet structure

- Maximum bullet depth: 2. Convert to a table if 3 or more levels are needed.
- Keep parallel bullets grammatically consistent (all noun forms or all verb forms).
- Do not leave scope vague with Korean expressions "등", "및 기타": open-ended scope creates contractual risk.
  Close long lists with the Korean example "총 N개 항목, 전체 목록은 별첨 X".

## 6. Emphasis

- Bold only 1~2 key points per page. Do not combine underline and italics.
- Do not create hierarchy with manually applied bold: use heading styles (Heading 1/Heading 2).
- Use the single prescribed primary color for emphasis (see visual-style.md). Red is reserved for risks and reductions.
