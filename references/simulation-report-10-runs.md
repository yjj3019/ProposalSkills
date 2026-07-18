# 제안서 스킬 v2 10회 시뮬레이션 보고서

실행일: 2026-07-18  
방식: 서로 다른 10개 원시 시나리오를 독립 에이전트 세션에 제공했다. 각 세션은 `create-winning-proposal` 스킬과 해당 시나리오만 읽고, 파일을 수정하지 않은 채 Bid 판단, 요구사항·근거, 구조/수정안, 제출 게이트, 스킬 자체의 약점을 보고했다.

## 실행 결과

| 회 | 시나리오 | 판정 | 올바르게 포착한 핵심 | 발견된 스킬 문제 | 반영한 해결책 |
|---:|---|---|---|---|---|
| 1 | 공공 AI 상담 RFP | no-bid/조건 검토 | 실적·RTO 증빙 부재, 8쪽 배분, 국내 리전 범위 과장 위험 | 자료 미제공과 자격 부재 구분 부족, 페이지 의미 불명확 | `intake-incomplete` 추가, 자격/증빙 구분, 페이지 구성요소 확인, 증거 범위 확장 금지 |
| 2 | 민간 물류 최적화 | conditional-bid | 기준선 없는 절감률·혁신 주장 차단, pilot 구조 | 조건부 입찰을 스크립트가 무조건 차단, 분석에도 렌더 요구, 스키마 누락 거짓 통과 | 승인된 조건부 입찰 허용, `artifact_required`, 모든 필수 JSON 필드 검증 |
| 3 | DB 이전 기술 제안 | conditional-bid | PostgreSQL 15/16, 12/16주 충돌과 무중단 근거 부족 | 명시 요구와 추론 구분, 기술 모순 심각도, 분석 렌더 예외 | requirement `basis`, Critical 모순 기준, 분석 전용 렌더 예외 |
| 4 | 금융 보안 질의서 | conditional-bid | 외부 API 금지, 미확인 보안 답변 차단, XLSX 직접 응답 | 제안서 중심 구조, 민감 근거 배포 방식 부족 | XLSX 보안질의 경로, 원본 행/수식/숨김시트 보존, redacted/controlled evidence |
| 5 | 자격 미달 공공입찰 | no-bid | ISO·실적 자격 미달을 문구로 해결하지 않음 | 명백한 no-bid에도 전체 작성 가능, 내부 승인 오해, 컨소시엄 예외 | no-bid 즉시 중단·의사결정 메모, 내부 승인 한계, 허용된 컨소시엄만 검토 |
| 6 | 3년 가격 제안 | conditional-bid | 160백만원 모순, 3년 운영비·할인·VAT 산식 제시 | 표준 가격 계산 순서 없음 | 일회성+반복비×기간→소계→할인 기준/금액→세금→최종합계 규칙 |
| 7 | 엄격한 제출 형식 | conditional-bid | DOCX 보존 경로, 서명·첨부·PDF/A·페이지 게이트 | PDF/A profile/검증, 서명 권한, page semantics, timezone 부족 | PDF/A 검증 증거, 서명/인감 유형·권한, 페이지 범위, 마감 timezone, 패키지 체크 |
| 8 | 수정공고 충돌 | conditional-bid | 수정공고 국내 리전·8/28 우선, Q&A의 백업 범위 | 같은 source tier 내부 우선순위와 stale sweep 부족 | amendment>base, Q&A clarification 규칙, amendment acknowledgement, 폐기 값 전수 검색 |
| 9 | 영문 해외 제안 | no-bid/조건 검토 | 100% secure, 40% 보장, zero downtime 제거; 24/7 격차 | 안전한 대체 문구와 claim 심각도 예시 부족 | unsafe→bounded evidence replacement 표와 claim 분류 보강 |
| 10 | 기존 제안서 검토 | blocked | placeholder/conflict marker, 50/35명, 범위 모순, 보안 승인자 | review-only 표준과 검증 불가 처리, 최소 수정 필드 부족 | 비례형 review path, 검증 범위 명시, 사실·owner·기한·승인·재계산 최소 수정 규칙 |

## 반복 문제

1. **Bid 분류 모호성**: 자격 부재, 증빙 미제공, 일반 정보 부족이 섞였다.
   - 해결: `intake-incomplete / bid / conditional-bid / no-bid` 4단계와 치유 가능성·owner·deadline·approval 조건을 정의했다.
2. **게이트와 문서 규칙 불일치**: 조건부 입찰과 분석-only 작업이 거짓 차단됐다.
   - 해결: 승인된 조건부 입찰과 `artifact_required: false`를 지원했다.
3. **JSON 누락 거짓 통과**: 누락 목록이 빈 배열로 처리될 수 있었다.
   - 해결: 필수 top-level 필드와 `checks`를 강제하고 예시 스키마를 추가했다.
4. **문서 유형 편향**: DOCX 제안서 외 XLSX·짧은 검토 경로가 약했다.
   - 해결: 보안질의서/XLSX 경로와 비례형 review-only 경로를 추가했다.
5. **제출 형식 미세 규칙 부족**: page semantics, deadline timezone, signature authority, PDF/A 검증이 빠졌다.
   - 해결: strict submission checklist를 보강했다.
6. **상충 자료 우선순위 부족**: 수정공고와 Q&A의 역할이 불명확했다.
   - 해결: amendment, Q&A, template, evaluation sheet의 역할과 stale-value sweep를 정의했다.
7. **가격·과장 문구 처리 부족**: 정확한 계산 순서와 안전한 대체가 없었다.
   - 해결: 가격 산식 순서와 unsafe-claim 대체표를 추가했다.

## 회귀 검증

- `quick_validate.py`: `Skill is valid!`
- `python -m unittest discover -s skills/create-winning-proposal/scripts -p test_*.py -v`: 5 tests passed
- 회귀 항목: 정상 제출 통과, 승인된 conditional-bid 통과, 분석-only 렌더 예외, 누락 스키마 차단, 다중 실패 차단

## 남은 한계

- 실제 회사 RFP, 수주/탈락 제안서, 브랜드 DOCX, 가격표, 승인 정책으로 검증하지 않았다.
- 실제 Microsoft Word 기반 한글 페이지 렌더와 PDF/A 검증은 템플릿이 제공돼야 실행할 수 있다.
- 법률·보안·가격 승인 주체는 조직별로 지정해야 한다.
- 한국어 자동 문체검사는 조직 용어집과 정상/오류 말뭉치가 확보되기 전까지 결정론적 규칙에 한정한다.
