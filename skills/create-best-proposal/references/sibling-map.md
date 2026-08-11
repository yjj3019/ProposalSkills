# 형제 스킬 reference 맵

본 스킬은 오케스트레이션·통합 도구에 집중한다. 전문 뱅크는 형제 스킬에 있다.
경로 기준: `skills/create-best-proposal/` 에서의 상대 경로.

## create-proposal-document (콘텐츠)

| 주제 | 파일 |
|---|---|
| 참여·제출·가격·XLSX | `../create-proposal-document/references/bid-and-submission.md` |
| 접수·요구 추출 | `../create-proposal-document/references/intake-and-requirements.md` |
| 유형별 목차·리드문 | `../create-proposal-document/references/proposal-structure.md` |
| 문체·과장어 | `../create-proposal-document/references/writing-style.md` |
| 문구 패턴 | `../create-proposal-document/references/phrase-library.md` |
| 사업관리·점검·테스트 뼈대 | `../create-proposal-document/references/content-patterns.md` |
| 근거·주장 | `../create-proposal-document/references/evidence-and-claims.md` |
| 시각 토큰 | `../create-proposal-document/references/visual-style.md` |
| 8대 검수 | `../create-proposal-document/references/review-checklist.md` |
| 기계 검수 | `../create-proposal-document/scripts/quality_gate.py` |

## create-winning-proposal (거버넌스)

| 주제 | 파일 |
|---|---|
| audit JSON 스키마·반낙관 | `../create-winning-proposal/references/audit-schema.md` |
| 요구·근거 원장 | `../create-winning-proposal/references/requirements-and-evidence.md` |
| 리뷰 상태·산출 | `../create-winning-proposal/references/review-and-output.md` |
| 구조 아키타입 | `../create-winning-proposal/references/structure-and-design.md` |
| 영문 문구 | `../create-winning-proposal/references/writing-and-phrases.md` |
| 보안·자동화 절제 | `../create-winning-proposal/references/automation-and-security.md` |
| 라이선스 | `../create-winning-proposal/references/source-patterns.md` |
| 익명 패턴 | `../create-winning-proposal/references/anonymized-proposal-patterns.md` |
| 결정론 게이트 | `../create-winning-proposal/scripts/proposal_gate.py` |

## 저장소 루트

| 주제 | 파일 |
|---|---|
| 완성도 2축 점수 | `../../score_completeness.py` |
| 설치기 | `../../install_skill.py` |

## 단독 설치 시

형제 파일이 없으면:
1. 본 스킬 `references/master-playbook.md` + `unified-gates.md`로 최소 경로 수행
2. audit는 `build_audit_from_meta.py` + 형제 저장소/설치 권고를 사용자에게 고지
3. quality_gate/proposal_gate 경로를 `--doc-skill-root` / 환경변수로 지정 가능
   (`unified_gate.py` 참조)
