# ProposalSkills

[English](README.en.md)

제안요청서(RFP)를 분석하고, 제안서(PPTX)를 작성·검토해 제출을 준비하는 스킬 모음입니다.
공통 작업 지침과 상세 운영 문서는 영어로 제공합니다.

## 설치

### Codex · ChatGPT 데스크톱

Codex CLI에서 마켓플레이스를 등록하고 설치합니다.

```bash
codex plugin marketplace add yjj3019/ProposalSkills --ref main
codex plugin add proposal-skills@proposal-skills-marketplace
```

설치 후 앱을 다시 시작하고 새 대화에서 사용하세요.

### Claude Code

```text
/plugin marketplace add yjj3019/ProposalSkills
/plugin install proposal-skills@proposal-skills-marketplace
```

세 스킬이 함께 설치됩니다. 업데이트·직접 설치·ZIP 배포는 [관리 가이드](references/marketplace-management.md)를 참고하세요.

## 사용

RFP·수정공고·평가표·지정 양식과 보유 근거를 제공하고 요청합니다.

> create-best-proposal 스킬로 첨부 RFP의 제안서를 작성해줘.
> 요구사항과 근거를 정리하고 PPTX를 만든 뒤, 수치와 장표 품질을 검토해줘.

Codex는 `$create-best-proposal`, Claude 플러그인은 `/proposal-skills:create-best-proposal`로 시작합니다.
ChatGPT는 지원되는 환경에서 설치된 스킬을 선택합니다.

## 포함된 스킬

| 스킬 | 역할 |
|---|---|
| [제안서 통합 작성](skills/create-best-proposal/SKILL.md) | 작성·검토·제출 검사의 통합 진입점 |
| [제안서 콘텐츠 작성](skills/create-proposal-document/SKILL.md) | 콘텐츠·문체·PPTX 제작 |
| [제안서 근거·제출 검토](skills/create-winning-proposal/SKILL.md) | 요구·근거·승인 요건 검증 |

전체 작업은 통합 작성 스킬로 시작하세요. 내용 작성이나 제출 검토만 필요하면 해당 스킬 이름을 명시해 요청하세요.

## 실행 환경과 검증

PPTX 생성·검사는 Python 3.10+와 `python-pptx`, 자동 렌더는 LibreOffice·Poppler가 필요합니다.
플러그인을 설치해도 실행 도구가 함께 설치되지는 않습니다. 자동 검사를 통과해도 사실 확인·장표 검토·제출 승인은 별도로 필요합니다.
고객 자료와 산출물은 이 공개 저장소 밖에 보관하세요.

[작성·검토 가이드](skills/create-proposal-document/references/quality-first-authoring.md) ·
[장표 규격](skills/create-proposal-document/references/deck-production.md) ·
[제출 검사](skills/create-winning-proposal/references/audit-schema.md) ·
[개발·기여](AGENTS.md)

## 보조 점검 도구

모두 표준 라이브러리만 쓰며, 확인하지 못한 범위를 출력하고 사람의 검토를 대신하지 않습니다. 종료 코드는 각 스크립트 상단 설명을 보세요.

| 스크립트 | 용도 |
|---|---|
| [`sensitive_scan.py`](skills/create-best-proposal/scripts/sensitive_scan.py) | 공유 전에 PPTX·DOCX·XLSX·텍스트에서 비밀키와 개인정보 탐지. 읽지 못한 파일은 건너뛰지 않고 보고 |
| [`edit_preservation.py`](skills/create-proposal-document/scripts/edit_preservation.py) | 문장 다듬기에서 수치·날짜·ID·링크·인용·불확실 표시가 사라지거나 생기면 차단 |
| [`deck_story_check.py`](skills/create-proposal-document/scripts/deck_story_check.py) | 제목만 이어 읽는 "고스트 덱" 출력, 중복 제목과 출처 없는 수치 표시 |
| [`plain_language_check.py`](skills/create-proposal-document/scripts/plain_language_check.py) | 긴 문장, 풀이 없는 약어, 자기 해설, 군더더기, 이중 피동 |
| [`deck_stage_gate.py`](skills/create-proposal-document/scripts/deck_stage_gate.py) | 덱 작업 폴더 게이트: 승인된 디자인 명세를 해시에 묶고 계획과 `slides.json` 일치 확인 |
| [`verification_report.py`](skills/create-best-proposal/scripts/verification_report.py) | 검사 보고서가 납품 파일과 일치하고 검사 깊이를 과장하지 않는지 검증 |
| [`retry_guard.py`](skills/create-best-proposal/scripts/retry_guard.py), [`evidence_chain.py`](skills/create-best-proposal/scripts/evidence_chain.py), [`handoff_lint.py`](skills/create-best-proposal/scripts/handoff_lint.py) | 수정·재검증 반복 중단 규칙, 변조 흔적이 남는 검사 기록, 인계 노트 점검 |
| `gate_mutation_probe.py`, `skill_audit.py`, `merge_guard.py`, `hook_guard_bash.py` | 저장소 도구: 게이트 약화 탐침, 스킬 안전·라이선스 감사, PR 준비 상태 확인(권고용), 위험 명령 차단 훅(선택) |

릴리스 노트: [CHANGELOG.md](CHANGELOG.md).

## 라이선스

[MIT](LICENSE)

[Third-party notices](THIRD-PARTY-NOTICES.md)
