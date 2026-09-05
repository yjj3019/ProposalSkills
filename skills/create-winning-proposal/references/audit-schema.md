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
  "render": {"verified": true, "render_succeeded": true, "layout_checked": true, "visual_review_approved": true, "visual_reviewer": "제안PM 김검토", "artifact_hash": "sha256:<64 hex>", "tool": "renderer version", "evidence": ["all pages reviewed"]},
  "package": {"required": true, "inspected": true, "artifact_hash": "sha256:<64 hex>", "tool": "package inspector version", "checks": {"metadata": "pass", "notes": "pass", "comments": "pass", "hidden-content": "pass", "embedded-files": "not-applicable", "external-links": "pass", "macros": "not-applicable", "stale-customer-data": "pass", "price-leakage": "pass"}, "reviewer": "QA lead"},
  "submission": {"cleared": true, "rehearsal_evidence": ["test upload opened"], "receipt_plan": "save portal confirmation", "receipt_evidence": []},
  "flags": {"financial": false},
  "regulatory_checks": [{"id": "REG1", "requirement": "전자금융 감독규정(망분리)", "status": "met", "evidence": ["점검 확인서"], "owner": "보안담당"}],
  "vendor_confirmations": [{"id": "V1", "kind": "support", "required": true, "present": true}],
  "numbers": [{"id": "N1", "label": "총 사업비", "value": 3700000000, "unit": "KRW", "source": "견적서 v3", "components": ["N2", "N3"]},
              {"id": "N2", "label": "구축비", "value": 2500000000, "unit": "KRW", "source": "견적서 v3"},
              {"id": "N3", "label": "유지보수비", "value": 1200000000, "unit": "KRW", "source": "견적서 v3"}]
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
- `win_themes`(선택): `[{id, statement, req_ids[], proof?}]`. 각 theme의 `req_ids`는
  비어 있지 않아야 한다(장식 theme 금지). 게이트 필수 필드는 아니나 meta 빌더
  `--strict`와 작성 규율이 강제한다.
- requirements 항목 선택 필드(후방호환): `fit` ∈ {STRONG, PARTIAL, GAP},
  `eval_weight`, `win_theme_id`, `risk`, `support`, `evidence_refs`(approved 시 필수).
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
  승인 자기선언은 차단된다. submission 모드에서는 `claims[]`도 같다 —
  `status: supported|qualified`인 material·commitment 주장에 `evidence_refs`가 없으면 차단.
- **검토 상태 ≠ 준수 상태**: `state`(검토가 어디까지 왔는가)와 `support`/`fit`(요구를
  충족하는가)은 다른 축이다. `support: X`(또는 `미지원`)이거나 `fit: GAP`인 항목을
  `state: approved`로 두면 차단된다 — "미지원임을 검토자가 확인했다"가 "충족했다"로
  승격되지 않는다. 발주처가 허용한 예외만 인정하며, 그때는
  `exception: {granted_by, evidence: []}`를 기록한다.
- **미수용 표기의 별칭**: `X`, `X 미수용`, `미수용`, `미지원`, `✗`, `부적합`은 모두 같은 상태로
  본다 — 표기 변형 하나로 승인 모순 검사를 빠져나가지 못한다(`N/A`·`해당없음`은 미지원이 아니다).
  `exception`과 `response_refs`는 meta→audit 변환에서 그대로 보존된다.
- **응답 위치 ≠ 근거**: 조견표의 응답 위치는 `response_refs`에 넣는다. `evidence_refs`는
  주장을 뒷받침하는 출처(확인서·시험성적서·제조사 회신)다. `bulk_matrix.py`도 두 필드를
  분리해 생성한다 — `slide:99`가 사실의 증거로 승격되지 않는다.
- **분류(context)**: `{buyer_types[], engagement, stage, reading_mode, constraints[], rfx_type}`.
  기관 이름이 아니라 축으로 분류하며(공공병원 → `["public","healthcare"]`), 게이트가 이 값을 읽어
  요구사항을 바꾼다. 값 목록과 각 축이 무엇을 바꾸는지는 [sectors/README.md](sectors/README.md)
  참조. RFP의 명시 요구가 언제나 분류보다 우선한다. **제출 모드는 `buyer_types`와 `stage`가
  필수**다 — 분류가 없으면 분류가 바꾸는 검사가 전부 조용히 꺼지므로, 누락을 정상값으로 두지
  않는다(초안·검토 단계는 후방호환으로 허용).
- **문서 종류(context.rfx_type)**: `rfp`(기본) | `rfi` | `rfq`. 구매 단계(`stage`)와 다른 축이다.
  `rfi`이면 (1) 공공이라도 평가표 원장을 요구하지 않고, (2) `kind: commitment` 주장을 차단한다
  — RFI 응답은 계약 제안이 아니므로 추정치가 확약 문장으로 승격되면 안 된다. 자격(`eligibility`)·
  첨부·형식 검사는 RFI에서도 그대로다(RFI라는 이유로 자격 요구를 생략하지 않는다).
- **평가표(evaluation_criteria)**: `{id, label, weight, parent?, stage?, method?, minimum_ratio?,
  minimum_score?, disclosed?, source?}` 배열과 선택적 `evaluation_total`(원장의 만점, 기본 100).
  `buyer_types`에 `public`이 있고 제출 단계이면 필수다 — 공공 입찰에서 배점표는 목차·분량·근거
  배분의 기준이므로, 없으면 무엇에 점수가 걸렸는지 모르는 채로 쓴 것이다.
  원문의 평가 방식은 "합계 100"으로 환원되지 않으므로 다음을 구분한다.
  - **최상위 항목의 합 = `evaluation_total`**. 기술 90점만 원장에 있고 가격이 별책이면
    `evaluation_total: 90`으로 적는다(100으로 고치지 않는다).
  - **하위 항목(`parent`)의 합 = 상위 항목의 배점**. 1단계 기술평가 100 = 정량 20 + 정성 80처럼
    계층을 그대로 옮기며, 상·하위를 한 번에 더해 100을 넘기는 이중 합산을 막는다.
  - **배점 미공개는 `disclosed: false`**로, `weight` 없이 기록한다. 게이트가 80:20을 지어내지 않는다.
  - **과락은 `minimum_ratio`(배점한도 대비 비율, 0.85 = 85%) 또는 `minimum_score`**로 보존만
    한다. 게이트는 심사 점수를 예측하거나 "기술 미달"을 판정하지 않는다 — 협상적격 기준의 85%는
    기술능력평가분야 **배점한도**의 85%(만점 90이면 76.5)이지 총점 85가 아니며, 적용 여부는
    공고마다 확인한다.
  각 요구는 `requirements[].criterion_ids`로 **말단** 배점 항목에 연결하며, 대응 요구가 없는 말단
  항목은 차단한다(목차가 통째로 빠진 신호). `reading_mode`가 규격을 기대하는데
  `render.output_profile`이 **없거나** 다르면 제출 모드에서 차단한다(누락 = 미검사).
- **제출 묶음(attachments)**: `{name, required?, present?, role?, file?, format?, sha256?,
  copies?, channel?, anonymity_checked?, price_screened?, reviewer?}`. 제출은 파일 하나가 아니라
  기명 원본·익명 사본·밀봉 가격서·별책 워크시트가 함께 나가고 파일마다 규칙이 다르다.
  `role`(`proposal` | `proposal-anonymous` | `price` | `form` | `certificate` | `presentation` |
  `appendix` | `other`)을 적으면 그 역할의 규칙이 붙는다 — 역할이 없으면 예전처럼 존재 여부만
  본다(후방호환). 제출 모드에서 `present: true`인 항목은:
  - `sha256`이 필요하다 — 묶음의 어느 바이트를 검사했는지 남긴다.
  - `proposal-anonymous`이면 `anonymity_checked: true`와 `reviewer`가 필요하다. 본문뿐 아니라
    노트·문서속성·파일명의 식별 표기를 검사하고(`quality_gate.py --names`), 로고·그림 속 표기는
    사람이 확인한다. 익명 사본만 있고 기명 원본이 없으면 경고한다.
  - `price`가 아닌 산출물은 `price_screened: true`가 필요하다 — 가격을 담으면 안 되는 기술본에
    가격이 섞였는지 확인한 기록이다.
  - `proposal`·`proposal-anonymous`·`price` 역할이 둘 이상이면 차단한다(어느 파일이 제출본인지
    하나로 정한다).
  `unified_gate.py --bundle <폴더>`는 각 첨부를 실제 파일과 해시 대조한다(`file`이 있으면 그
  이름, 없으면 `name`). 검토 뒤 바뀌었거나 없는 첨부를 잡는다.
- **요구 강도(requirements[].strength)**: `required` | `recommended` | `optional` | `conditional`
  | `informational`. 없으면 `mandatory`에서 유도한다(미기재 = `required`, fail-closed). 둘 다 있고
  서로 어긋나면 스키마 오류다. `conditional`은 `condition`(어떤 조건에서 필수가 되는가)이 필요하며
  필수로 센다. `recommended`를 따르지 않은 채 제출하려면 `rationale`을 적어야 한다 — 권장 분량
  초과와 필수 위반은 같은 무게가 아니지만, 권장을 조용히 잊는 것과 사유를 갖고 넘기는 것은
  구분돼야 한다. 조견표(`bulk_matrix.py`)의 `필수` 열에 적힌 권장·선택·조건부·참고는 강도로
  옮겨진다.
- **수치 원장(numbers)**: `numbers[] = {id, label, value(JSON 숫자), unit, source?, components?[],
  percent_of?, amount?, tolerance?(기본 0.005), must_appear?}`. `components`가 있으면 값이 구성
  요소의 합과 같아야 하고(단위가 섞이면 차단), `percent_of`+`amount`가 있으면 비율을 다시
  계산한다. **제출 모드는 원장 없이 `checks.arithmetic: true`만으로 통과하지 못한다.** 원장
  값이 실제 문서에 있는지는 `check_numbers.py`가 대조하며, 중간 계산값은
  `must_appear: false`로 제외한다. 값은 유한한 JSON 숫자여야 하고(`Infinity`·`NaN` 차단),
  자기 자신을 `components`나 `percent_of`로 참조할 수 없으며, `percent_of`에는 유한한
  `amount`와 0이 아닌 모수가 있어야 한다(계산 불가는 통과가 아니라 미검증이다). 단위가
  통화(`KRW`·`원`·`USD` 등)이면 합계 검산에 상대 오차가 아니라 **1원 단위 절대 오차**를 쓴다.
  제출 모드에서 원장이 비어 있으면 `numbers_not_applicable`에 사유를 적어야 한다.
  문서 대조는 **평가위원이 보는 본문**만 인정하며(노트·레이아웃·마스터에만 있으면 차단),
  소수·단위·부호를 구분한다 — `37.5개월`은 `37`의 근거가 아니고 `37개월`은 `37원`의 근거가
  아니며 `-37`은 `37`의 근거가 아니다.
- **검증 의무는 취소되지 않는다**: `mode: submission`이면 `artifact_required` 값과 무관하게
  렌더 검증·해시 형식·패키지 검사를 요구한다. `artifact_required: false`는 draft/review에서만
  의미가 있다 — 입력값 하나로 제출 검사를 끄지 못한다.
- **렌더 성공 ≠ 육안 승인**: 제출 모드는 `render.visual_review_approved: true`와
  `render.visual_reviewer`(실명)를 요구한다. `deck_check.py`는 이 값을 항상 false로 기록하며,
  PNG 썸네일을 확인한 사람이 직접 바꾼다. PDF 변환 성공은 디자인 승인이 아니다.
- **검사 기록의 누락 = 미검사**: `render.layout_checked`는 **필수**다. false이면 물론이고,
  **필드를 생략해도 차단**한다 — 지우면 요구가 사라지던 구멍을 막았다. `verified: true`인데
  `render_succeeded: false`처럼 서로 모순되는 기록도 차단한다. `build_audit_from_meta.py`는
  입력 meta에 있는 `render_succeeded`·`layout_checked`·`visual_review_approved`·
  `visual_reviewer`·`output_profile`을 그대로 옮긴다(없는 승인을 만들어내지는 않는다).
- **산출물 해시 결속(artifact binding)**: submission 모드에서 `artifact_required: true`이면
  `render.artifact_hash`와 `package.artifact_hash`는 실제 sha256 값(`sha256:<64 hex>`)이어야
  하고 서로 같아야 한다. 문자열 라벨(`sha256:proposal`)은 차단된다. 판정은
  `unified_gate.py --doc <최종파일>`로 받으며, 전달한 파일의 해시가 audit의 해시와 다르면
  차단된다(검토 이후 바뀐 파일에 과거 판정을 재사용할 수 없다). 문서 없이 audit만
  점검하려면 `--audit-only`를 쓰고, 이때 최선의 결과는 `SUBMISSION-READY`가 아니라
  `AUDIT-VALID`다.
- **단계 강제(stage)**: `mode: submission` audit은 `--stage submission`으로만 검사한다.
  `--stage draft`로 낮춰 `[NEEDS INPUT]`을 경고로 만드는 우회는 사용 오류(exit 2)다.
- **시뮬레이션 산출물**: `artifact_mode: simulation-only`는 `mode: submission`과 함께 쓸 수
  없다 — 내부 확인용 산출물은 외부 제출 준비 상태로 승격되지 않는다.
- **ID 무결성**: `requirements[]`·`claims[]`의 각 항목에는 비어 있지 않은 고유 `id`가 있어야
  한다. ID를 지워 원장을 익명화하거나 중복 ID로 근거를 뒤섞을 수 없다.
- **원장 항목의 내용**: 제출 모드에서 `requirements[]`·`claims[]`의 각 항목에는 사람이 읽을 수
  있는 내용이 있어야 한다 — `text`, `label`, `title`, `summary`, `description` 중 하나. ID만 있는
  껍데기 원장은 "R1 승인"이 무엇을 승인한 기록인지 확인할 수 없다(초안 단계의 부분 원장은 허용).
- **informational 주장의 면제 사유**: `kind: informational`은 근거(`evidence_refs`) 검사를
  면제받는 유일한 유형이므로, 제출 모드에서는 `rationale`(왜 근거가 필요 없는지)을 요구한다.
  근거 없는 성능·실적 주장을 informational로 재분류해 빠져나가는 경로를 막는다.
- **마감일 검증(deadline)**: `submission.deadline`은 timezone 포함 ISO-8601. submission
  모드는 필수이며, 기준 현재시각(`PROPOSAL_GATE_NOW`로 주입 가능, 기본 UTC now)보다
  과거이면 차단한다. 만료된 RFP를 `cleared: true`로 통과시킬 수 없다.
- **플레이스홀더는 근거가 아니다**: `evidence_refs`, `render.artifact_hash/tool/evidence`,
  `package.artifact_hash/tool/reviewer`, `submission.rehearsal_evidence/receipt_plan`,
  `regulatory_checks[].evidence`, `defects[].closure_evidence`에 `TBD`, `TODO`, `???`,
  `[NEEDS INPUT]`, `입력요망`, `미정` 등이 있으면 비어 있는 것으로 취급해 차단한다.
- **엄격 불리언(strict boolean)**: `accepted`, `present`, `cleared`, `verified`, `inspected`,
  `owner_approved`, `met`, `curable`, `mandatory`, `required`는 JSON `true`/`false`만 허용한다.
  `"yes"`/`"pending"`/`"no"` 같은 문자열은 INVALID AUDIT(exit 2)다. `mandatory`·`required`를
  생략하면 필수로, claim `kind`를 생략하면 `material`로 취급한다(fail-closed). `kind`는
  `material | commitment | informational` 중 하나여야 한다.
- **조건부 입찰의 범위**: `conditional-bid`는 `mode: draft|review|analysis`에서만 CONDITIONAL-GO가
  된다. `mode: submission`이면 차단된다 — 조건부는 내부 계속 진행 상태이지 외부 제출 클리어가
  아니다. 각 `bid_conditions[].deadline`은 현재시각 이후여야 한다.
- **자격 일관성(eligibility)**: `eligibility[] = {id, criterion, mandatory, met, curable}`.
  submission 모드는 원장 필수. 미충족(`met:false`)이면서 `curable:false`면 `bid`/
  `conditional-bid` 불가(no-bid만 허용); 미충족+`curable:true`면 단독 `bid` 불가
  (조건부입찰 또는 불참). 치유 불가능한 자격 미달을 낙관적 `bid`로 선언할 수 없다.

## eligibility · conditional-bid 작성 예제 (자주 틀리는 부분)

**eligibility 원장** — 제출 모드 필수. 각 필수 자격 기준을 met/curable로 표기한다.

```json
"eligibility": [
  {"id": "E1", "criterion": "동종 실적 3억 이상 2건", "mandatory": true, "met": true,  "curable": true},
  {"id": "E2", "criterion": "SW사업자 등록",          "mandatory": true, "met": true,  "curable": true},
  {"id": "E3", "criterion": "정보보호 전문서비스 지정", "mandatory": false, "met": true, "rationale": "가점 항목-비필수"}
]
```

**치유 항목을 어디에 담느냐가 상태를 가른다(중요).** 동일한 "실적 1건 부족"이라도 표현 위치에 따라
게이트 상태가 달라진다 — 작성자가 의도에 맞게 선택해야 한다.

- **CONDITIONAL-GO를 원하면**: 치유 항목을 `eligibility`(met:false, curable:true) + **accepted `bid_condition`**
  으로 모델링하고 `bid_decision:"conditional-bid"`, `mode`는 `draft` 또는 `review`. 제출물에 지금 당장
  있어야 하는 서류로 만들지 않는다. 조건 기한은 미래 시각이어야 한다.
  ```json
  "mode": "draft",
  "bid_decision": "conditional-bid",
  "bid_conditions": [
    {"id": "B1", "owner": "사업총괄", "deadline": "2099-08-30T17:00:00+09:00", "accepted": true,
     "note": "컨소시엄 실적 보강으로 E-실적 기준 충족"}
  ],
  "eligibility": [{"id": "E1", "criterion": "실적 2건", "mandatory": true, "met": false, "curable": true}]
  ```
- **NO-GO(정상 차단)가 맞으면**: 치유 항목이 **이번 봉투에 반드시 present여야 하는** 필수 서류/제조사
  확약서라면 `attachments`/`vendor_confirmations`에 `required:true, present:false`로 둔다. 제출 모드에서는
  이것이 하드 차단이라 `conditional-bid`라도 NO-GO로 내려간다(fail-closed, 의도된 동작).
- **결정 시점 검토**는 `mode:"review"`, **실제 봉투 제출**은 `mode:"submission"`로 분리한다. review 모드는
  마감·eligibility 원장·제출 리허설 강제를 적용하지 않으므로 추진 판단에 적합하다.

치유 불가 미달은 `curable:false` + `bid_decision:"no-bid"`. 치유 가능한데 조건을 아직 못 걸었으면
`no-bid` 또는 미수락 `conditional-bid`(→ 차단)로 두되, 낙관적 단독 `bid`로 선언하지 않는다.

## 게이트 결과 설명 — `proposal_gate.py --explain`

차단 시 "무엇을 왜 고쳐야 하는지"를 마크다운 조치표로 출력한다. `no-bid`·`intake-incomplete`는 결함이
아니라 **DECISION_MEMO**(정상 불참/보류)로 분기하고, `conditional-bid`가 미결로 막히면
`CONDITIONAL-GO → NO-GO 다운그레이드`와 회복 조건을 함께 보여준다. `python proposal_gate.py --explain AUDIT.json`.

## 완성도 수치 일원화 — `score_completeness.py`(create-best-proposal/scripts, 루트에도 동일 진입점)

리뷰어마다 'overall 수치'를 다르게 계산해 값이 갈리던 문제를 없애기 위해 동일 audit에서
두 축을 결정론적으로 산출한다: 제출가능성(readiness, 세부 차원 충족률 + 게이트),
제안 품질(quality, `--quality` 지표 파일이 있을 때 `0.4·compliance + 0.3·claim_support
+ 0.2·(1−defect) + 0.1·rehearsal`). **최종 상태는 오직 게이트가 결정한다** — 품질 점수가
높아도 open BLOCKING이 있으면 NO-GO다. `python score_completeness.py AUDIT.json [QUALITY.json]`.
