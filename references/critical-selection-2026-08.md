# 비판적 선정 — 외부·내부 개선 반영 (2026-08)

## 비판 기준

1. **반낙관 유지**: 모델 자기점수·winrate 퍼센트로 GO 하지 않는다.
2. **얇은 추가**: 108-skill 엔진·RAG·GraphRAG 이식 금지.
3. **증거 기반**: 시뮬 readiness 병목·아키텍처 coupling·Shipley 중간 단계에 직접 대응.
4. **라이선스**: 개념·스키마만 흡수, 외부 문장/코드 복제 없음.

## 최종 선정 (반영)

| ID | 항목 | 반영 위치 | 비판 메모 |
|---|---|---|---|
| S1 | Pink/Red/Gold 경로 계약 | `create-best-proposal` SKILL + master-playbook | Shipley 전 7색 도입은 과중 → 3단계만 |
| S2 | 조견표 열 확장(fit/eval/theme/risk) | bulk_matrix + audit requirements 필드 | 전체 새 스키마 강제 대신 optional 열 |
| S3 | Win theme → req_ids 링크 검증 | build_audit_from_meta | 미링크 theme은 경고, strict 시 실패 |
| S4 | unified_gate → explain 배선 | unified_gate.py `--explain` | 기본 on으로 조치표 출력 |
| S5 | no-bid 기본 CLI = DECISION_MEMO | proposal_gate.py main | explain 없이도 의도 정지 구분 |
| S6 | 설치 기본=flagship + --with-deps | install_skill.py | vendor 복사는 무거워 deps 동시 설치 |
| S7 | AI-slop 최소 패턴 | quality_gate.py | 금지어 확장 수준; 문체 모델 아님 |
| S8 | 상태 별칭 문서화 | unified-gates.md | 코드 enum 분리보다 문서 계약 우선 |
| S9 | sibling-map 환경변수 정합 | sibling-map.md | 존재하지 않는 CLI 플래그 제거 |

## 기각 (의도적 비반영)

| 후보 | 기각 사유 |
|---|---|
| Winrate predictor / Pwin % | 반낙관 위반 위험, 시뮬·조직 데이터 없음 |
| 전면 RFP shred 엔진 | 언어·형식 편차 큼 → 1차는 사람+매트릭스 유지 |
| RAG/AutoRFP 이식 | 승인 라이브러리·환각 벤치 미비 |
| Vale 풀 스택 | 한국어 말뭉치 없음 |
| 508 전면 자동화 | 부분 기계 가능하나 범위 대비 가치 낮음 |
| vendor/에 gate 복사 | 이중 유지보수 → --with-deps로 대체 |

## 검증

- `python -m unittest discover -s . -p "test_*.py" -q`
- `python skills/create-winning-proposal/scripts/test_proposal_gate.py -q`
- `python skills/create-best-proposal/scripts/test_best_proposal.py -q`
