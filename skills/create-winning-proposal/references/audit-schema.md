# Audit JSON schema

Create every top-level field; do not omit empty arrays.

```json
{
  "mode": "submission",
  "artifact_mode": "submission-candidate",
  "bid_decision": "conditional-bid",
  "bid_conditions": [{"id": "B1", "owner": "Legal", "deadline": "2026-08-20T17:00:00+09:00", "accepted": true}],
  "requirements": [{"id": "R1", "mandatory": true, "state": "approved", "rationale": "", "reviewer": "Security lead"}],
  "claims": [{"id": "C1", "kind": "commitment", "status": "supported", "owner_approved": true}],
  "unresolved_tokens": [],
  "attachments": [{"name": "signature.pdf", "required": true, "present": true}],
  "source_conflicts": [],
  "inputs": [{"id": "I1", "class": "non-blocking", "status": "closed"}],
  "defects": [{"id": "D1", "severity": "major", "status": "closed", "closure_evidence": ["sha256:fixed", "page 12 rechecked"], "reviewer": "QA lead", "closed_at": "2026-07-19T12:00:00+09:00", "reverified_scope": ["R1", "page 12"]}],
  "checks": {"consistency": true, "arithmetic": true, "submission": true},
  "artifact_required": true,
  "render": {"verified": true, "artifact_hash": "sha256:proposal", "tool": "renderer version", "evidence": ["all pages reviewed"]},
  "package": {"required": true, "inspected": true, "artifact_hash": "sha256:proposal", "tool": "package inspector version", "checks": {"metadata": "pass", "notes": "pass", "comments": "pass", "hidden-content": "pass", "embedded-files": "not-applicable", "external-links": "pass", "macros": "not-applicable", "stale-customer-data": "pass", "price-leakage": "pass"}, "reviewer": "QA lead"},
  "submission": {"cleared": true, "rehearsal_evidence": ["test upload opened"], "receipt_plan": "save portal confirmation", "receipt_evidence": []},
  "flags": {"financial": false},
  "regulatory_checks": [{"id": "REG1", "requirement": "전자금융 감독규정(망분리)", "status": "met", "evidence": ["점검 확인서"], "owner": "보안담당"}],
  "vendor_confirmations": [{"id": "V1", "kind": "support", "required": true, "present": true}]
}
```

- `mode`: submission, draft, review, or analysis.
- `artifact_mode`(선택): `submission-candidate` 또는 `simulation-only`. 마감 경과 등으로
  no-bid인 RFP를 벤치마크 작성할 때도 `bid_decision`은 바꾸지 않는다.
- Conditional-bid passes only when every condition has an owner, ISO-8601 date/time with timezone, and acceptance.
- Intake-incomplete and no-bid never pass submission readiness.
- Not-applicable mandatory items need rationale and reviewer.
- Material claims must be supported, qualified, or removed; commitments also need owner approval.
- Open blocking inputs and open Critical/Major defects block submission. `conditional-go` is an internal review state only.
- Allow only `blocking|non-blocking|assumption`, `critical|major|minor|note`, and `open|closed`. Unknown values invalidate the audit.
- Closing Critical/Major defects requires closure evidence, reviewer, ISO timestamp, and reverified scope.
- Use `artifact_required: false` only when no rendered artifact is requested.
- Set package inspection `required` for editable office files; missing capability is `inspected: false`, not a pass.
- Verified render/package states require artifact hash, tool identity, evidence/check results, and reviewer. These fields prove that a review event was recorded, not that its factual conclusion is true.
- In submission mode, a failed or not-inspected required package check blocks readiness.
- Submission package scope must cover metadata, notes, comments, hidden content, embedded files, external links, macros, stale customer data, and price leakage; use `not-applicable` only with reviewer accountability.
- Submission clearance requires rehearsal evidence and a receipt-capture plan. Add the actual receipt evidence after submission; do not fabricate it before submission.
- `flags`, `regulatory_checks`, `vendor_confirmations`(선택·후방호환): 없으면 검사하지 않는다.
  - `regulatory_checks[]` status ∈ {met, gap, in-progress, not-applicable}. `gap`·`in-progress`는 차단, `met`는 evidence 필수. `flags.financial: true`인 submission은 `regulatory_checks`가 비면 차단(금융 규제 미기재 방지).
  - `vendor_confirmations[]` kind ∈ {support, supply}. `required && !present`이면 차단 — 제조사 기술지원·공급 확약서 같은 계약 전 필수 제출물을 blocking으로 모델링한다.
- Record completed or documented-not-applicable consistency, arithmetic, and submission checks as `true`.

## 반낙관 하드닝(anti-optimism) — 자기선언 낙관 통과 차단

게이트는 자기보고 어서션의 *구조적 완전성*만 검증하고 *진위*는 검증하지 않는다.
따라서 모든 요구를 `approved`, 첨부를 `present`, 제출을 `cleared`로 낙관 선언하면
READY가 나오는 구멍이 있었다. 아래 3종 가드로 이를 막는다.

- **근거 필수(evidence)**: 필수 requirement가 `state: approved`이면 비어있지 않은
  `evidence_refs: []`(제안서 위치·산출물 해시 등)가 반드시 있어야 한다. 근거 없는
  승인 자기선언은 차단된다.
- **마감일 검증(deadline)**: `submission.deadline`은 timezone 포함 ISO-8601. submission
  모드는 필수이며, 기준 현재시각(`PROPOSAL_GATE_NOW`로 주입 가능, 기본 UTC now)보다
  과거이면 차단한다. 만료된 RFP를 `cleared: true`로 통과시킬 수 없다.
- **자격 일관성(eligibility)**: `eligibility[] = {id, criterion, mandatory, met, curable}`.
  submission 모드는 원장 필수. 미충족(`met:false`)이면서 `curable:false`면 `bid`/
  `conditional-bid` 불가(no-bid만 허용); 미충족+`curable:true`면 단독 `bid` 불가
  (조건부입찰 또는 불참). 치유 불가능한 자격 미달을 낙관적 `bid`로 선언할 수 없다.

## 완성도 수치 일원화 — `score_completeness.py`(저장소 루트)

리뷰어마다 'overall 수치'를 다르게 계산해 값이 갈리던 문제를 없애기 위해 동일 audit에서
두 축을 결정론적으로 산출한다: 제출가능성(readiness, 세부 차원 충족률 + 게이트),
제안 품질(quality, `--quality` 지표 파일이 있을 때 `0.4·compliance + 0.3·claim_support
+ 0.2·(1−defect) + 0.1·rehearsal`). **최종 상태는 오직 게이트가 결정한다** — 품질 점수가
높아도 open BLOCKING이 있으면 NO-GO다. `python score_completeness.py AUDIT.json [QUALITY.json]`.
