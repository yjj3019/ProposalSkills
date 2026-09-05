# Meta → Audit 빌더 (SI-B1)

작성 초안의 슬라이드/요구 메타데이터를 거버넌스 audit JSON으로 옮긴다.
수동 이중 기입을 줄여 readiness 공백(시뮬 평균 ~64)을 줄이는 것이 목적이다.

## 입력 meta 스키마 (최소)

```json
{
  "mode": "submission",
  "bid_decision": "bid",
  "bid_conditions": [],
  "title": "사업명",
  "buyer": "발주처",
  "proposal_type": "A",
  "deadline": "2026-12-31T17:00:00+09:00",
  "flags": {"financial": false},
  "eligibility": [
    {"id": "E1", "criterion": "최근 3년 3억 실적", "mandatory": true, "met": true, "curable": false}
  ],
  "requirements": [
    {
      "id": "R1",
      "text": "이중화 구성",
      "mandatory": true,
      "state": "approved",
      "evidence_refs": ["slide:12", "조견표#R1"],
      "slide": 12
    }
  ],
  "claims": [
    {"id": "C1", "kind": "commitment", "text": "RTO 4h", "status": "supported", "owner_approved": true}
  ],
  "attachments": [
    {"name": "사업자등록증.pdf", "required": true, "present": true}
  ],
  "slides": [
    {"no": 1, "title": "표지", "lead": "...", "req_ids": []},
    {"no": 12, "title": "HA 구성", "lead": "...", "req_ids": ["R1"]}
  ],
  "unresolved_tokens": [],
  "defects": [],
  "inputs": [],
  "regulatory_checks": [],
  "vendor_confirmations": [],
  "render": {"verified": false},
  "package": {"required": true, "inspected": false},
  "submission": {
    "cleared": false,
    "rehearsal_evidence": [],
    "receipt_plan": ""
  }
}
```

## 빌더 동작

```bash
python scripts/build_audit_from_meta.py meta.json -o audit.json
python scripts/build_audit_from_meta.py meta.json --strict
```

- 필수 top-level 필드를 audit-schema 형태로 채움
- requirement.state=approved 인데 evidence_refs 비면 `--strict`에서 실패, 기본은 경고 필드
- slides[].req_ids ↔ requirements 양방향 불일치 시 `source_conflicts`에 기록
- render/package가 미검증이면 그대로 두어 게이트가 NO-GO (거짓 READY 방지)
- `artifact_required`·`package.required`는 **mode=submission일 때만 기본 true**. draft/review는 기본 false이므로
  리드문 맵 단계 audit이 `DRAFT-READY`에 도달할 수 있다(명시하면 그 값을 따른다).

## 사용 시점

1. 리드문 맵·조견표 초안 직후 → draft audit (mode=draft). **Pink 체크포인트 레시피**:
   요구 원장은 `state: drafted`가 아니라 검수 완료된 항목만 `approved`로 두면 "not approved"가 나온다 —
   Pink 단계는 `mode: "draft"`, 필수 요구 전부 `state: "approved"`가 아니어도 되도록 `bid_decision`·
   `eligibility`·`checks`만 채우고, 게이트의 "requirement … is not approved" 목록을 **작업 목록**으로 읽는다.
   DRAFT-READY는 본문 1차 완료(2단계) 후 evidence_refs를 채웠을 때 도달하는 것이 정상이다.
2. 본문 1차 완료 후 → evidence_refs 보강
3. 렌더·패키지 검사 후 → verified/inspected 갱신 → unified_gate

예제: `fixtures/meta_sample.json`
