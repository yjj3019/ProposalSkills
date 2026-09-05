# 업종 프로파일 — 있는 것과 없는 것

## 왜 하나뿐인가

기관 유형별 프로파일은 **검증할 수 있을 때만** 값어치가 있다. "병원 제안서는 환자 안전을
다뤄야 한다" 같은 문장은 이 저장소 없이도 어떤 모델이나 내놓는다. 스킬이 더하는 것은
자명하지 않은 실무 지식이어야 하는데, 그것은 지어낼 수 없고 지어내면 확인할 방법도 없다.

그래서 여기에는 **공공(`public.md`) 하나만** 있다. 이 저장소의 지침 대부분이 이미 공공 입찰을
전제로 쓰여 있어서, 새로 쓰는 것이 아니라 흩어져 있던 것을 모은 것이기 때문이다.

기업·교육·의료는 **분류 축과 게이트 규칙까지만** 제공하고 내용은 비워 뒀다. 해당 업종의
실무자가 실제 사업 경험으로 채우는 것이 옳다. 빈 채로 두는 편이, 확인되지 않은 내용을
"프로파일"이라는 이름으로 신뢰하게 만드는 것보다 낫다.

## 분류는 이름이 아니라 축이다

기관 이름 하나로 정하지 않는다. 공공병원·국립대학처럼 속성이 겹치는 조직이 있고, 같은
기관이라도 사업 성격과 구매 단계에 따라 필요한 근거가 다르다. audit의 `context` 블록에
기록하며, 게이트가 이 값을 읽어 요구사항을 바꾼다.

| 축 | 값 | 무엇을 바꾸는가 |
|---|---|---|
| `buyer_types[]` | `public` `private` `education` `healthcare` (복수) | 공공이면 평가표 원장 필수 |
| `engagement` | `build` `operate` `migrate` `education` `consulting` `service-improvement` `product-selection` `policy` | 아키타입(목차 뼈대) 선택 |
| `stage` | `explore` `internal-review` `rfp-response` `presentation` `final-submission` | 제출 단계 검사 적용 시점 |
| `reading_mode` | `screen-presentation` `print-evaluation` `individual-review` `appendix` | 장표 규격(deck_profiles)과 대조 |
| `constraints[]` | `sensitive-data` `business-continuity` `closed-network` `regulated-industry` | 민감정보면 패키지 검사 3종 `pass` 필수 |

RFP·계약·제출 양식의 명시 요구가 언제나 이 분류보다 우선한다. 분류가 애매하면 추정하지
말고 미확정으로 두고 질문한다.

## 새 프로파일을 추가할 때

`public.md`의 구조를 따른다 — 추가로 물어야 할 것, 제안서가 입증해야 할 것, 검토 주체,
주의할 주장, 그리고 **그중 기계가 검사할 수 있는 것**. 마지막 항목이 비어 있다면 그 프로파일은
아직 지침이지 게이트가 아니다. 그 사실을 문서에 적는다.

법령·인증 적용 여부는 사업 범위·데이터·관할·기준일에 따라 달라진다. 기관 유형만 보고
일괄 강제하지 않는다.
