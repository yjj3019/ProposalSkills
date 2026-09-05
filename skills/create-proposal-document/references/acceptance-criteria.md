# 수락 기준 (acceptance-criteria)

`review-checklist.md`의 **8대 검수 항목**을 사람 / 기계 / 런타임 세 층으로 나눈다.
완료 선언은 세 층이 모두 닫히고, 형제 거버넌스 게이트가 요구되는 제출 건에서는
`--with-deps` 경로의 제출 준비도까지 통과해야 한다.

범례: **H**=사람 판단, **M**=저장소 스크립트(Docker 불필요), **R**=LibreOffice/Poppler·폰트 런타임

| # | 항목 | Human (H) | Machine (M) | Runtime (R) |
|---|---|---|---|---|
| 1 | 요구사항 전수 매핑 | 부분수용·X 사유/대안 적정성, 조판 후 페이지 번호 최종 확인 | `mapping_check.py` 양방향 REQ-ID; 조견표 템플릿 행 상태 | — (페이지 번호 이미지는 R§8과 연계 가능) |
| 2 | 리드문 스토리 | 리드문만 이어 읽기, 1페이지 1메시지, 요약 5질문 | `page-message-map.md` 존재·공란 여부(수동 표) | — |
| 3 | 과장어·근거 | 같은 장 근거·범위 승인, `[unverified]` 보고 | `quality_gate.py` 과장어·AI-slop·플레이스홀더 | — |
| 4 | 수치·버전·일정 일관성 | 인력/일정/버전/EOL 교차 대조, 웹 최신성 | 대조표·원장 파일 존재 확인(스크립트는 힌트만) | EOL·버전 웹 확인은 사람+네트워크 |
| 5 | 고객명·재사용 | RFP 표기 일치, 반입 검사 승인 | `quality_gate.py --names` | — |
| 6 | 형식 요건(RFP) | 페이지 제한·표지·별첨·인감·파일명 해석 | 제출 체크리스트 문서화 | PDF/A·용량은 변환 도구로 측정(R) |
| 7 | 시각 규격 | 접근성·캡션·대체텍스트, 색+레이블 병행 | `quality_gate.py --palette` | 폰트 임베드·깨짐은 렌더(R) |
| 8 | 최종 렌더·패키지 | 육안(잘림·넘침), Critical 마감, 리허설·증적 | `package_inspect.py`; `runtime_check.py` 준비도 | LibreOffice PDF 변환 + `pdftoppm` 이미지; MS Office가 최종 기준이면 별도 확인 |

## 기계 명령 빠른 참조

```bash
# 런타임 준비(파이썬만)
python runtime_check.py --python-only

# 텍스트·팔레트 게이트
python skills/create-proposal-document/scripts/quality_gate.py deck.pptx \
  --names banned_names.txt --palette "1F3864,8FAADC" --stage submission

# 조견표 양방향
python skills/create-proposal-document/scripts/mapping_check.py matrix.md --doc deck.pptx

# 원본 패키지 힌트
python skills/create-proposal-document/scripts/package_inspect.py deck.pptx

# Docker 런타임(렌더 포함 환경)
docker build -t proposal-skills .
docker run --rm -v "$PWD:/workspace" proposal-skills python runtime_check.py
```

## 완료(Done)와의 관계

- 이 표의 8행이 모두 닫히면 **문서 스킬 완료** 후보다.
- **제출 준비 완료(SUBMISSION-READY)** 는 추가로 create-winning-proposal /
  create-best-proposal 게이트·승인·증적이 필요하다 → SKILL.md «완료 선언 조건».
