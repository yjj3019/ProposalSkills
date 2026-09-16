# Capture & Positioning — RFP 이전 포지셔닝

공고가 나오기 전이나 공고 직후, 무엇을 강조하고 무엇을 보완해야 하는지 정리하는 작성
양식이다. 결과는 **Pink 입력 보강용**이다. `bid_decision`, audit JSON, 제출 게이트를
대체하지 않으며 audit 스키마에 필드를 추가하지 않는다. 별도 메모(`capture.md`)로 둔다.

## 1. 적용 조건

- RFI·사전규격 공개 단계
- 사전영업·요구 협의 단계
- 공동 제안·협력사·제조사 역할 분담 결정
- 경쟁 구도가 결과를 좌우하는 사업
- capability gap 또는 가격 포지션 판단이 필요한 경우

본 RFP만 받은 상태에서 바로 작성하는 경우에는 §2 중 `decision_drivers`와
`capability_gaps`만 채워도 된다.

## 2. 작성 양식

모든 항목에 구분 태그를 붙인다.

- `FACT` — 공고·공식 Q&A·발주처 공개자료·승인 사내자료로 확인됨(출처 기재)
- `HYPOTHESIS` — 추론. 확인 방법과 확인 기한을 함께 적는다
- `UNKNOWN` — 모름. 질의·영업 확인 대상으로 넘긴다

```
opportunity_summary     사업 목적·범위·일정 (FACT 위주)
decision_drivers[]      발주처가 중시하는 판단 기준 — 각 항목에 태그·출처
positioning_axes[]      비교축별 우리 위치 — 강점/보완/불리
capability_gaps[]       요구 대비 부족 역량 — 치유 방법(협력·인력·인증)·owner·기한
pursuit_risks[]         참여 자체의 위험 — 일정·자격·인력·가격·계약 조건
price_posture           known range / cost floor / commercial constraints / unknowns
```

## 3. 비교축 (경쟁사 이름보다 축 중심)

전환 위험, 서비스 중단 영향, 운영 안정성, 기술지원 체계, 보안, 확장성, 호환성,
공급사 종속(vendor dependency), 유사 실적, 투입 인력, 가격·TCO

각 축에 대해 "발주처가 이 축을 중시한다는 근거"(`FACT`/`HYPOTHESIS`)와
"우리가 이 축에서 증명할 수단"을 짝으로 적는다. 증명 수단이 없으면 강점으로 쓰지 않는다.

## 4. Price Posture

Price-to-Win(낙찰가 추정)은 쓰지 않는다. 아래만 기록한다.

- known range: 공고에 공개된 사업 예산·기초금액 등 공식 값
- cost floor: 사내 원가 기준 하한(외부 문서에 넣지 않음)
- commercial constraints: 라이선스 단가 구조, 제조사 조건, 분할 납품
- unknowns: 확인하지 못한 가격 변수

## 5. 생성하지 않는 것

- 근거 없는 경쟁사 약점, 경쟁사 가격·전략 추정
- 발주처 의사결정자 신원·성향
- 비공개 예산, 예상 낙찰가격
- 수주확률·승률

## 6. Pink로 넘기는 방법

- `decision_drivers`의 `FACT` → 평가 항목별 `evaluator_question` 작성 근거
  ([evaluator-journey.md](evaluator-journey.md))
- 강점 축 + 증명 수단 → Win Theme 후보(각 theme은 `req_ids` 필수)
- `capability_gaps` → bid 4단 판정의 조건부 조건 후보(owner·기한 필수)
- `HYPOTHESIS`·`UNKNOWN` → 질의 목록. 제안서 본문 사실로 쓰지 않는다
