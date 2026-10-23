# 원문 추출·수정공고·시각 회귀의 선택형 도구

모든 출력은 고객 작업 폴더에 보관한다. 원문·JSON·페이지 이미지·diff에는 민감한 내용이
포함될 수 있으므로 공개 저장소나 설치된 스킬 폴더에 쓰지 않는다. 기존 생성·제출 게이트는
그대로 사용한다. 아래 sidecar는 audit JSON이 아니며 승인 필드를 자동으로 갱신하지 않는다.
예시 경로는 사용자가 선택한 작업 폴더의 상대 경로이고 실행 스크립트는 설치 위치에서 찾는다.

## 1. RFP 구조 추출

`scripts/extract_rfp.py`는 PDF/DOCX와 DoclingDocument JSON을 연결한다. Docling이 없는 환경도
기존 JSON을 가져올 수 있다. 원문 full SHA-256과 JSON hash를 각각 기록하며, 가져온 JSON과
원문이 실제로 대응하는지는 사람이 확인한다. Docling 내부 origin hash를 SHA-256으로 쓰지 않는다.

```bash
python scripts/extract_rfp.py input.pdf --import-json docling.json --output extraction-run
```

직접 변환은 별도 선택 환경의 `docling`이 필요하다. 자동 설치·다운로드는 수행하지 않는다.
PDF는 미리 준비한 모델과 manifest를 요구한다. manifest는 `revision` 문자열과
`files` 객체(모델 폴더 기준 상대 경로 → full SHA-256)를 포함한다. 실제 사용 모델의 revision,
본체/모델 라이선스와 빠진 모델이 없는지 확인한다. manifest 검증은 나열된 파일에만 적용되며
실제 사용 모델 전체의 완전성을 자동 증명하지 않는다. OCR 사용 시 `artifacts/easyocr`에
한국어·영어 EasyOCR 모델을 준비한다. `--ocr`가 없으면 OCR은 꺼져 있다.

```bash
python scripts/extract_rfp.py input.pdf --artifacts models --model-manifest models.json --ocr --output extraction-run
```

원격 서비스·외부 플러그인을 끄고 HF/Transformers offline 플래그와 EasyOCR 다운로드 금지를
설정한다. 이 설정은 OS 네트워크 격리가 아니다. 모델/backend 버전에 따라 별도 통신 경로가
있을 수 있어 기밀 자료는 허용된 격리 환경에서 먼저 합성 표본으로 검증한다. 부족한 모델,
의존성, timeout, 부분 변환은 오류이며 다운로드로 자동 복구하지 않는다. `--timeout`은 1~1800초다.

`extraction.json`은 `UNREVIEWED`와 `submission_approval: false`를 유지한다. native 구조 JSON의
셀/span·페이지·bbox를 보존한다. `capabilities`의 available은 일부 항목에 관측됐다는 뜻으로,
전 항목 위치 coverage가 아니다. DOCX의 없는 페이지·좌표를 가짜 값으로 채우지 않는다.
문단/표 셀/JSON pointer는 위치 정보이지 개정 간 stable ID가 아니다.

사람은 원문과 후보를 대조해 승인한 내용만 기존 원장 형식의 `exact_text/source/evidence_refs`
등으로 옮긴다. 추출 성공·confidence는 사실 정확도나 승인 확률이 아니다. 한국어 골든셋은
디지털/스캔 PDF·DOCX·병합 셀·페이지 넘김 표로 나누고, 금액·기한·자격의 exact match,
누락/중복·표 구조·위치 coverage와 시간/메모리를 기록한다. 실측 전 정확도를 약속하지 않는다.

## 2. 수정공고 대조

거버넌스 레이어의 `compare_requirements.py`는 사람이 동일 ID로 매칭한 개정본만 비교한다.
입력은 `{"requirements": [{"id": "REQ-001", "text": "가상의 요구", "source_clause_label": "1.1"}]}`
형식이다. ID는 내부의 안정 식별자이며 source_clause_label은 개정별 원문 번호다.

```bash
python compare_requirements.py before.json after.json --output amendment-diff.json
```

추가/폐지/본문 변경/참조 변경과 전후 값·텍스트 diff를 남긴다. 자동 유사 매칭을 하지 않는다.
재번호는 같은 ID를 유지하고 분할·병합·반복 문구의 모호한 매칭은 사람이 관계를 기록한다.
변경이 없는 diff라도 원문의 요구 누락·잘못된 ID 매칭 부재를 증명하지 않는다. 변경 항목의
응답·증빙·수치·페이지 참조를 다시 검토하고, 폐지된 값은 stale sweep으로 찾는다.

## 3. PDF 시각 비교

`scripts/visual_compare.py`는 Poppler의 `pdftoppm`/`pdfinfo`와 Pillow를 사용한다. Pillow는
PPTX 환경에 흔히 함께 있지만 존재를 확인하며 자동 설치하지 않는다. diff-pdf-visually의
페이지 단위 회귀 원칙을 참고한 독립 구현으로, ImageMagick/추가 비교 패키지는 요구하지 않는다.

실제 렌더러의 버전과 글꼴 파일 집합을 확인해 환경 JSON을 작성한다. `renderer`,
`renderer_version`, `font_profile`은 비어 있지 않은 문자열이다. font_profile에는 글꼴 파일들의
hash 목록을 외부에서 관리하는 식별자를 권장한다. 선언값을 실제 글꼴 탐지 증거로 오인하지 않는다.

```bash
python scripts/visual_compare.py snapshot approved.pdf --source approved.pptx --environment env.json --reviewer reviewer-role --output baseline
python scripts/visual_compare.py snapshot candidate.pdf --source candidate.pptx --environment env.json --output candidate
python scripts/visual_compare.py compare baseline candidate --max-changed-ratio 0 --output comparison-run
```

기준본은 실제 PDF를 검토한 뒤 reviewer를 기록한다. reviewer 문자열은 인증된 전자승인이
아니며 제출 audit의 사람 승인을 대신하지 않는다. 각 snapshot은 PDF 복사·원문/PDF hash·
환경을 남긴다. baseline과 candidate의 원문 hash는 서로 달라도 정상이며 각 자기 파일의
무결성을 검사한다. PDF와 원문 간 변환 충실성까지 hash가 증명하지는 않는다.

기본 DPI=150, channel_delta=8이며 기록된 RGB 채널 차이가 delta를 **초과**한 픽셀을 센다.
각 페이지의 changed_ratio가 명시한 `--max-changed-ratio`를 **초과**하면 DIFFERENT다.
어느 한 페이지라도 다르면 전체 DIFFERENT이며 페이지 수·크기 차이도 동일하다. 전체 페이지
평균으로 작은 중요 변경을 숨기지 않는다. bbox와 diff PNG를 확인하고 작은 숫자·선·한글 누락
표본으로 오차/DPI를 보정한다. threshold는 인쇄 품질 인증값이 아니다.

종료 코드는 SAME=0, DIFFERENT=1, ERROR/사용오류=2, INCOMPARABLE=3이다. 렌더러·글꼴·OS
환경이 다르면 INCOMPARABLE이며 같은 엔진끼리 먼저 비교한다. PowerPoint↔LibreOffice는
별도 기준과 수동 검토가 필요하다. 실행 실패·불완전 페이지를 SAME으로 처리하지 않는다.
before/after/diff/result.json은 새 run 폴더에만 저장한다. 기존 폴더·기준본은 덮어쓰지 않고,
자동 삭제·기준본 갱신도 하지 않는다. 사용자는 보존 정책에 따라 자기 run만 정리한다.

SAME은 그 설정에서의 변화 검사 결과다. 원문 충실성·사실·설득력·표 넘침 부재를 인증하지
않고 `visual_review_approved`는 항상 false다. 기존 `deck_check.py --render`와 전 장 검토,
최종 PowerPoint 폰트 확인·통합 게이트를 계속 수행한다. PDF 보관을 원하면 승인된 렌더러의
PDF를 별도로 내보내 snapshot에 넘긴다. 기존 renderer의 임시 PDF 수명이나 audit 스키마는 바꾸지 않는다.

설계 참고: [Agent Skills](https://agentskills.io/specification),
[diff-pdf-visually](https://github.com/bgeron/diff-pdf-visually),
[Docling offline options](https://github.com/docling-project/docling/blob/main/docs/usage/advanced_options.md).
외부 코드·템플릿은 복제하지 않았다. 선택 패키지·모델은 실제 채택 revision의 조건을 별도 확인한다.
