# 마스터 플레이북 — 한 장 결정 트리

에이전트는 본 파일을 매 세션 초반에 따른다. 세부 문체·스키마는 형제 reference로 위임한다.

## 1. 30초 트리아지

```
사용자 요청
 ├─ RFI·사전규격·경쟁구도 포지셔닝? ───────→ Capture 메모 (+ Pink 입력)
 ├─ "참여할까 / bid 판단"만? ──────────────→ Decision
 ├─ "이 문서 검토해"만? ──────────────────→ Review-only
 ├─ 골격·theme·조견표만 / 초안 초기? ─────→ Pink (~30%, 본문 전량 금지)
 ├─ 평가자 시점 전수 비판 / ~70% 초안? ───→ Red (전면 재작성 금지)
 ├─ 제출 직전 승인? ─────────────────────→ Gold (5항목 + unified_gate)
 ├─ XLSX·보안질의·조견표 대량? ───────────→ Matrix (+ bulk_matrix.py)
 ├─ "발표용 / PT" ? ──────────────────────→ PT (본문 동기화 필수)
 ├─ RFP 없이 공동사업·아이디어? ──────────→ Discovery (제출 프레임 금지)
 └─ 그 외 제안서 작성 ────────────────────→ Full
```

### Pink / Red / Gold 계약 (S1)

| 경로 | 시점 | 필수 산출 | 금지 |
|---|---|---|---|
| **Pink** | 본문 전 | 유형·목차·리드문 맵·조견표 뼈대·win_themes(req_ids)·bid 판정·평가 항목별 핵심 장표와 증거 위치 | 장표 전량 작성, 미검증 실적 채움 |
| **Red** | 초안 후 | 평가표 항목별 충족 근거 위치·약점(Critical/Major)·미링크 theme·미기입 매트릭스 행 | 원본 통째 재작성(최소 수정), 평가점수·수주확률 산출 |
| **Gold** | 제출 전 | pre-submission 5항목 + `unified_gate` READY/CONDITIONAL-GO | 미검사 패키지를 pass로 추정 |

Pink·Red 점검 기준(뼈대 논리, 10초 탐색): [evaluator-journey.md](evaluator-journey.md).
Capture 메모는 Pink 입력만 보강한다. bid 판정·게이트를 대체하지 않는다:
[capture-and-positioning.md](capture-and-positioning.md).

**장표 제작 전에 요구사항·평가 항목·리드문 구조를 먼저 확정한다.** PowerPoint를 열고 내용을
채우며 논리를 찾지 않는다. 순서는 요구 원장 → 평가표 원장 → Win Theme → 리드문 맵 →
`slides.json` → PPTX다.

## 2. Full 차단 조건 (작성 시작 전)

다음 중 하나면 Full 본문 작성 금지:

| 조건 | 판정 | 산출 |
|---|---|---|
| 자격 판단 자료 자체 없음 | intake-incomplete | 필요 입력 목록 |
| 치유 불가 자격·역량 미달 | no-bid | 불참 사유 메모 |
| 마감 경과 + 제출 목적 | no-bid | 메모 (벤치마크면 simulation-only) |
| 치유 가능 결격 + 조건 미승인 | conditional-bid 대기 | 조건 카드만 |

## 3. Full 체크리스트 (축약)

- [ ] A. Bid 확정 + 출처 서열 + stale sweep
- [ ] B. 요구 원자화 + 조견표 + Win Theme≤3 + 리드문 맵
- [ ] C. 본문 (1p 1메시지, 근거 병기, 과장어 0, 모호 확약 정리, 핵심 기술 장표 6문 검토)
- [ ] D. 시각·렌더·패키지 분리 검사
- [ ] E. meta→audit → unified_gate → 제출 직전 5항목

## 4. 상태 어휘 (스킬 간 통일)

| 상태 | 의미 | 외부 제출 |
|---|---|---|
| DECISION_MEMO_ONLY | no-bid / intake-incomplete | 불가 |
| DRAFT / DISCOVERY | 초안·탐색·Pink | 불가 |
| NO-GO / BLOCKED | BLOCKING 잔존 또는 게이트 실패 | 불가 |
| CONDITIONAL-GO | 조건 전부 owner·기한·accepted | **내부만** |
| SUBMISSION-READY / READY | 게이트 통과 + 리허설·접수계획 (**동일 의미**) | 가능(실제 제출 후 증적) |

품질 점수와 상태를 혼동하지 않는다. **상태는 게이트가 결정**한다.

## 5. 유형 신호

| 유형 | 신호 키워드 |
|---|---|
| A 구축 | 구축, 도입, 마이그레이션, 데이터센터, 플랫폼 |
| B 유지보수 | 유지보수, SLA, 예방점검, 기술지원, 구독 갱신 |
| C 기술답변 | 조견표, BMT, 표준제품, 항목별 답변, RFI |

변형: DCO/상주→B, U2L/DR→A, 표준화 권고→C.

## 6. 언어·산출물

| 조건 | 기본 산출 | 게이트 lang |
|---|---|---|
| 한국어 RFP·국내 공공/금융 | PPTX 장표 | ko |
| 영문 RFP·해외 | DOCX 또는 지정 양식 | en |
| 이중 제출 | 언어별 본문 분리 | both |

## 7. 실패 패턴 (시뮬에서 반복)

1. 작성 품질만 높이고 audit/eligibility 비움 → NO-GO
2. approved에 evidence_refs 없음 → 반낙관 차단
3. draft 마커를 submission 게이트에 통과시키려 함 → 차단 (stage 분리)
4. no-bid를 "게이트 버그"로 오해 → DECISION_MEMO_ONLY로 명시
5. 유형 C에서 샘플 5행만 작성 → bulk_matrix + 별첨 전체

## 8. 근거·경계 reference

| 필요할 때 | 문서 |
|---|---|
| 공공 규범과 스키마 대응, 상수 금지 값 | `../create-winning-proposal/references/korean-public-proposal-regulatory-basis.md` |
| 핵심 기술 장표의 서술 깊이 | [technical-depth-six-questions.md](technical-depth-six-questions.md) |
| 해외 방법론·외부 저장소 개념을 들일 때 | [external-method-boundaries.md](external-method-boundaries.md) |
| 발주처 지정 출력 규격 | `../create-proposal-document/references/deck-production.md` §1-2 발주처 지정 출력 규격(output_spec) |
