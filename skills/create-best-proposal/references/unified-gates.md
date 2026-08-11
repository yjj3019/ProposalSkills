# 통합 게이트 운용

## 1. 계층

```
quality_gate.py     문서 텍스트·색 (과장어, placeholder, 잔존명, 팔레트)
       ↓
proposal_gate.py    audit JSON 구조·반낙관·제출 준비도
       ↓
score_completeness  readiness / quality 수치 (상태는 게이트)
       ↓
unified_gate.py     위 조합 + DECISION_MEMO_ONLY UX + 종료 코드 표준화
```

## 2. quality_gate stage 결정 트리 (SI-B2)

```
고객에게 이대로 제출할 수 있는가?
  ├─ 아니오 (내부 초안·사실 수집 중) → --stage draft
  │     [NEEDS INPUT] / ［입력요망］ → 경고(비차단)
  └─ 예 (제출 후보) → --stage submission  (기본)
        미확정 마커 1건이라도 → 차단
애매하면 submission으로 먼저 돌린 뒤, 경고를 draft 기준으로 재분류.
```

예시:
```bash
# 초안 회람
python ../create-proposal-document/scripts/quality_gate.py draft.pptx --stage draft --lang ko

# 제출 후보
python ../create-proposal-document/scripts/quality_gate.py final.pptx --stage submission \
  --names prior_customers.txt --palette "1F3864,8FAADC,D6E0F0,EDF1F8,C00000,1F7A3D,202020,595959"
```

## 3. proposal_gate / unified_gate 결과 접두사 (SI-B3)

| 출력 | exit | 의미 |
|---|---:|---|
| READY | 0 | 제출 게이트 통과 |
| CONDITIONAL-GO | 0* | accepted conditional-bid + 그 외 통과 (*unified는 0, 내부 전용 고지) |
| DECISION_MEMO_ONLY | 1 | no-bid / intake-incomplete — 본문 작성 대상 아님 |
| BLOCKED | 1 | 제출 차단 (증빙·결함·패키지 등) |
| INVALID | 2 | audit 스키마 오류 |

no-bid를 "must be bid" 일반 오류와 섞지 않는다. 메시지는
`DECISION_MEMO_ONLY: bid_decision=no-bid; ...` 형태.

## 4. 반낙관 3가드 (필수)

1. **evidence_refs**: mandatory+approved → 비어 있지 않은 근거 목록
2. **deadline**: submission 모드 ISO+타임존, 현재시각 이후
3. **eligibility**: submission 원장 필수; 미충족+치유불가 → bid 금지

## 5. 금융 제출 (SI-B4)

`flags.financial: true` 이면 `regulatory_checks` 필수.
각 항목 status=`met`일 때 evidence 필수. gap/in-progress → 차단.
골든 픽스처: `fixtures/audit_ready_financial.json`

## 6. unified_gate 사용

```bash
python scripts/unified_gate.py audit.json
python scripts/unified_gate.py audit.json --doc 제안서.pptx --stage submission
python scripts/unified_gate.py audit.json --doc 제안서.pptx --stage draft --lang ko
```

문서 경로를 주면 quality_gate를 먼저 실행하고, 실패 시 audit 평가 전 BLOCKED.
형제 스크립트를 못 찾으면 명확한 오류 메시지 후 exit 2.
