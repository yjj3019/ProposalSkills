# Technical narrative depth — six questions before writing

An internal review process to prevent keyword-only technical slides (Korean examples:
"고가용성 구성", "자동화 적용", "보안 강화"). Answers are writing notes, not slide copy.
Compress them into the §3 structure.

## 1. Scope

- Key items in type C technical responses.
- Architecture, migration, HA/DR, security, performance, SLA, data, operations automation.
- Slides responding to high-weight technical evaluation criteria.

Do not apply to general introduction/organization/schedule slides.

## 2. Six questions

| # | Question | Signs of an insufficient answer |
|---|---|---|
| 1 | What does it solve — which requirement/metric/constraint? | No REQ-ID; begins with technology names rather than the problem |
| 2 | Why this approach — alternatives considered and selection reason? | Only generic assurances (Korean examples: "업계 표준", "검증된 기술", "안정적") |
| 3 | How does it work — components/data flow/transition order? | Boxes only; no flows/protocols/sequence |
| 4 | How is it built/operated — configuration/deployment/monitoring/change procedures? | No operating owner or procedures |
| 5 | How is it verified — test method/metrics/pass criteria? | Only a test promise (Korean example: "테스트 수행"), no criteria |
| 6 | What happens on failure — detection/mitigation/recovery/manual-intervention boundary? | No failure scenario; only a recovery claim (Korean example: "자동 복구") |

Self-check: after deleting every adjective, do components/mechanisms/numbers/procedures remain?
If nothing remains, rewrite.

## 3. Compressed slide structure

```text
Lead          Conclusion (summary of Q1 + Q2)
Body diagram  Mechanism (core of Q3, Q4)
Body table    Verification/evidence (Q5: test criteria/results/sources)
Caption       Risks/boundaries (Q6 summary + scope)
```

If one slide cannot hold it, split mechanism and verification across two slides with connected leads.

## 4. Expressions requiring scope and evidence

The banned-expression list and replacement patterns in `../create-proposal-document/references/writing-style.md`
§2 govern these claims (Korean examples preserved): 무중단, zero data loss, 100% 자동복구, 완벽, 유일,
최고, 압도적, 완전 자동화. This document maintains no separate dictionary.

Additional technical-slide rules:

- State availability/recovery goals as **target + measurement conditions + assumptions** (e.g. RTO target and failover-test conditions).
- Put performance figures with test environment/load conditions/source on the same slide.
- Distinguish automated segments from human-approval segments.

Without evidence, follow the existing policy (Korean placeholder preserved):
`[NEEDS INPUT: owner — 항목]` or `[unverified]`.

## 5. Korean examples (structure only; original wording preserved)

BAD lead: "고가용성 아키텍처로 안정적인 서비스를 제공합니다."

BETTER lead: "관리 노드 3중화와 스토리지 복제로 단일 장애점을 제거하고,
전환 시험으로 목표 복구시간 충족 여부를 검수 단계에서 확인합니다."

BETTER caption: "적용 범위: 운영계 클러스터. 재해복구 사이트 전환은 별도 절차(수동 승인) — REQ-ID"
