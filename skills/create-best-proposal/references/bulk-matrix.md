# 대량 조견표·응답 매트릭스 (SI-C1)

유형 C(기술답변서)와 30~60+ 항목 RFP에서 **샘플 5행만 쓰는 실패**를 막는다.

## 원칙

1. **전수 행**을 기계 생성한다. 요약 장표는 상위 N행 + "전체 N건 별첨" 문구.
2. 지원여부 코드 고정: `O | 부분 | 조건부 | X | N/A | 확인필요`
3. 부분/조건부/X/N/A는 **사유·대안·로드맵** 열 필수.
4. 각 행에 REQ-ID·원문 위치(페이지/항)·응답 위치(슬라이드/시트셀) 유지.

## 입력 CSV/JSON

필수 열: `id, section, item, text`
선택 열: `mandatory, support, product, note, source_loc, response_loc`

```bash
python scripts/bulk_matrix.py requirements.json -o matrix.md --summary-rows 8
python scripts/bulk_matrix.py requirements.csv -o matrix.csv --format csv
```

## 출력

- Markdown 조견표 (제안서 본문·별첨용)
- 요약 블록: 지원 통계 (O/부분/X/…) + 상위 리스크 행
- JSON 사이드카: audit requirements[] 초안용 (`state` 기본 pending)

## 장표 배치

| 산출 | 내용 |
|---|---|
| 본문 1~2p | 통계 + 고배점·미지원 리스크 Top N |
| 별첨 전체 | 전수 매트릭스 (페이지 제한 시 별도 파일) |
| 각 응답 장 | 모서리에 REQ-ID + 지원상태 |

XLSX 원본 질의서가 있으면 bulk_matrix 결과로 초안을 만든 뒤 **원본 시트에 옮겨 적고**
구조 보존 검사를 한다(행 순서·수식·숨김 시트).
