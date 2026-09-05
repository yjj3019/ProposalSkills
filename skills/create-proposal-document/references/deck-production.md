# 장표 생산 (deck-production) — slides.json → PPTX → 검사

visual-style.md의 규격을 **매번 손으로 재현하지 않는다.** 장표 계획을 `slides.json`으로 쓰고
`build_deck.py`로 생성한 뒤 `deck_check.py`로 레이아웃·렌더를 검사한다. 모델이 하는 일은
**내용(리드문·표 데이터·도식 요소)을 채우는 것**이고, 좌표·색·폰트·위계는 스크립트가 고정한다.

```bash
python scripts/build_deck.py slides.json -o 제안서.pptx --strict          # 생성
python scripts/deck_check.py 제안서.pptx --max-pages 40 --exclude-cover-toc \
       --require-req-ids --stage draft --render --png-dir out/png \
       --emit-render render.json                                            # 린트+렌더+증적
python scripts/quality_gate.py 제안서.pptx --stage draft                    # 텍스트 검수
```

`render.json`을 meta의 `render` 블록에 넣으면 audit의 `render.verified/artifact_hash/tool/evidence`가
채워진다(deck_check가 렌더 성공 + 차단 0일 때만 `verified:true`). 사람은 `out/png`의 썸네일로
잘림·겹침·폰트 대체를 육안 확인한다 — 스크립트는 그것을 대신하지 않는다.

## 1. slides.json 스키마

```jsonc
{
  "meta": {
    "title": "…제안서", "subtitle": "…", "doc_name": "헤더 표기 문서명",
    "buyer": "발주처(RFP 표기 그대로)", "bidder": "제안사", "date": "YYYY-MM-DD",
    "page_limit": 40,                 // 있으면 초과 시 --strict 실패
    "require_req_ids": true,          // 본문 장표 REQ-ID 누락 경고(기본 true; 유형 C는 status_tag로 대체 가능)
    "palette": {"primary": "1F3864"}, // 선택. 브랜드 토큰 있으면 여기에. 없으면 visual-style 폴백
    "font": "맑은 고딕"
  },
  "slides": [ /* 아래 유형 */ ]
}
```

모든 본문 장표 공통 필드: `breadcrumb`(헤더 목차 경로), `title`(명사형), `lead`(결론 1~3줄, ≤60자
권장), `caption`(그림 N./표 N. + 기준일), `source`(출처), `req_ids`(대응 요구 ID 배열), `notes`(발표자
노트), `status_tag`(유형 C: `(완료) 26. …`).

| type | 용도 | 고유 필드 |
|---|---|---|
| `cover` | 표지 | (meta 사용) `title`,`subtitle` 재정의 가능 |
| `toc` | 목차 | `items[]` — 2열 자동 배치 |
| `section` | 간지 | `no`(Ⅰ…), `title`, `items[]` |
| `matrix` | 조견표 | `rows[{id,text,support,response_loc,note}]`, `rows_per_slide`(기본 12) — 자동 분할·헤더 반복·"(계속 n/N)" |
| `table` | 표 1개 | `columns[]`, `rows[[…]]`, `col_widths[]`, `right_cols[]`(숫자열 우측정렬) |
| `process` | 단계 프로세스 | `steps[{title,desc[]}]` — ≤6단계 셰브론, 초과 시 박스 |
| `zones` | 구성도 | `zones[{title,items[{title,desc[]}]}]`, `legend[]` — 계층 위→아래, 영역 라벨+카드 |
| `gantt` | 추진일정 | `months`, `month_labels[]`, `tasks[{name,start,end,phase,label,milestones[{at,label}]}]` |
| `staff` | 인력 프로필 | `people[{name,role,grade,years,certs[],mm}]` |
| `cards` | 차별점·기대효과·3단 논리 | `items[{title,value,desc[],evidence}]` — 2~4열 |
| `bullets` | 텍스트 나열(최소화) | `items[]` — 항상 경고, 450자 초과 시 분할 경고 |
| `closing` | 마무리 | `title`, `lead` |

수용여부(`support`) 표기는 공통 코드 `O/부분/조건부/X/N/A/확인필요`에 텍스트를 병기한다
(`"O 수용"`, `"△ 조건부"`) — 색만으로 구분하지 않는 규칙의 구현이다.

## 2. 도식은 네이티브 도형으로 그린다

구성도·프로세스·간트는 이미지가 아니라 **편집 가능한 PPT 도형**으로 생성된다(zones/process/gantt).
이유: 발주처가 원본 PPTX 제출을 요구하는 경우가 많고, 검수자가 텍스트를 검색·수정할 수 있어야 하며,
quality_gate가 도식 안의 잔존 고객명·과장어까지 읽어야 한다. 외부 도구 그림(draw.io·mermaid PNG)은
다음 경우에만 쓴다: 네트워크 토폴로지처럼 선 연결이 핵심인 도식. 이때도 캡션·범례·REQ-ID는
장표 텍스트로 두고, 그림에는 alt text를 넣는다.

## 3. 사내 양식 템플릿 사용

`--template 사내양식.pptx`를 주면 그 파일의 마스터(배경·로고)를 사용한다. 조건: 16:9(13.333×7.5in),
"빈 화면(Blank)" 레이아웃 존재. 좌표 그리드는 동일하므로 로고가 헤더/푸터 영역(상단 0.25~0.55in,
하단 6.95~7.25in)과 겹치면 템플릿 쪽 로고 위치를 조정한다. 브랜드 토큰은 `meta.palette`로 넘긴다.

## 4. 페이지 배분 — 배점표 → 절대 페이지

`page_limit`이 있으면 percent가 아닌 **장 수**로 배분한다. 공식: 배점 비율 × (제한 − 고정장).
고정장 = 표지 1 + 목차 1 + 조견표 ⌈요구 수/12⌉ + 간지(장 수) + 마무리 1(제한 산정 포함 여부는
RFP 규정으로 확인, 보통 표지·목차 제외).

예) 제한 40p, 기술평가 사업이해 10·수행전략 20·기술구성 25·이관 15·사업관리 10(=80), 요구 7건:
고정장 = 조견표 1 + 간지 5 = 6 → 본문 34장 → 사업이해 4 · 수행전략 9 · 기술구성 10 · 이관 7 · 사업관리 4.
배점이 큰 장은 리드문을 먼저 쓰고 도식 중심으로, 작은 장은 표 1개로 압축한다.

## 5. 생산 단계 체크

1. 리드문 맵(제목+lead만 있는 slides.json) → `build_deck.py --strict` → 리드문만 이어 읽어 스토리 확인.
2. 본문 채움 → `deck_check.py --stage draft` (경고 목록이 작업 목록).
3. 제출 후보 → `deck_check.py --stage submission --require-req-ids --render --emit-render` +
   `quality_gate.py --stage submission --names 금지명.txt` → render.json을 meta에 반영 → unified_gate.
4. 사람: PNG 썸네일 전 장 육안 확인, 발주처 PowerPoint 버전에서 1회 열어 폰트 대체 확인.

## 6. 한계 (통과로 추정하지 않는다)

- LibreOffice 렌더는 PowerPoint와 줄바꿈·폰트 대체가 다를 수 있다 → 최종은 PowerPoint 확인.
- deck_check는 텍스트 오버플로를 밀도(600자)와 폰트로만 추정한다. 표 셀 넘침은 썸네일로 확인.
- 이미지 전용 장표는 텍스트 검사가 불가능하므로 `[경고]`로 표시되고 렌더 육안 확인이 필수다.
