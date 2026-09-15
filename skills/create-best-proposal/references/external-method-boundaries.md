# 외부 방법론 적용 경계

해외 제안 방법론과 공개 스킬 저장소에는 쓸 만한 작성 습관이 많다. 그러나 그 규칙은 다른
조달 제도를 전제로 한다. 이 문서는 무엇을 heuristic으로 빌리고 무엇을 가져오지 않는지 정한다.

## 1. 원칙

- 외부 방법론은 **작성 품질을 높이는 heuristic**이다. truth source가 아니다.
- 사실·규격·배점·자격은 언제나 해당 사업의 공고 원문에서 온다.
- 외부 저장소의 문장·코드·점수 모델을 복사하지 않는다. 개념만 자체 문장으로 옮긴다.

권위 순위:

실제 수정공고 > 본 RFP > 공식 Q&A > 평가표 > 지정 제출양식 > 승인된 사내자료 >
현행 공식 외부자료 > 일반 방법론

공식 규범 목록은 `../create-winning-proposal/references/korean-public-proposal-regulatory-basis.md`.

## 2. 빌려 쓰는 개념

| 개념 | 이 저장소에서의 형태 |
|---|---|
| Capture(사전 포지셔닝) | [capture-and-positioning.md](capture-and-positioning.md) — Pink 입력 보강, 게이트 비대체 |
| Evaluator Journey | [evaluator-journey.md](evaluator-journey.md) — Pink/Red 점검 기준 |
| 기술 서술 깊이 | [technical-depth-six-questions.md](technical-depth-six-questions.md) |
| Evidence-first | 기존 `claims[]`·`evidence_refs` 원장 |
| 리뷰 단계 규율(Pink/Red/Gold) | [master-playbook.md](master-playbook.md) 경로 계약 |
| 확약 과잉 경계 | `writing-style.md` 모호 확약 규칙 + RFI 확약 차단 게이트 |
| 위험·방법론 구조 | 유형 A/B/C 목차 뼈대 |

## 3. 가져오지 않는 것

| 대상 | 이유 |
|---|---|
| 미국 FAR, Section L/M 구조 | 국내 제안요청서·평가표 체계와 다름 |
| 미국 연방 past performance 평가 규칙(CPARS 등) | 국내 실적 증명 방식과 다름 |
| 국제기구·해외 개발은행 고유 조달 규칙 | 적용 제도가 다름 |
| 중국 군용 문서 표준·등급보호·국산화 요건 | 적용 제도가 다름 |
| Price-to-Win 추정 | 근거 없는 낙찰가 추정 위험. 필요 시 Price Posture만 사용 |
| 외부 저장소의 채점·수주확률 모델 | 검증 불가, 평가 예측 금지 원칙과 충돌 |
| 외부 고객명·실적·가격·예시 문구 | 라이선스·사실성 문제 |
| 문화 일반화("한국형 서사는 기승전결") | 근거 없는 규칙. 서사 패턴은 선택 사항 |

## 4. 새 개념을 들여올 때 확인

1. 한국 IT 제안서 품질을 실제로 높이는가
2. 기존 reference·게이트와 중복되지 않는가
3. 공고 원문 우선 원칙과 충돌하지 않는가
4. 근거 없는 상수·규칙을 만들지 않는가
5. fail-closed 제출 게이트를 약화하지 않는가
6. 테스트 또는 점검 절차로 확인 가능한가

하나라도 아니면 들이지 않고 사유를 남긴다.
