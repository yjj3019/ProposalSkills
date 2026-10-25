# ProposalSkills

[English](README.en.md)

RFP 분석부터 편집 가능한 PPTX 작성·검토·제출 검사까지 돕는 한국어 IT 제안서 플러그인입니다.

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
| [create-best-proposal](skills/create-best-proposal/SKILL.md) | 작성·검토·제출 검사의 통합 진입점 |
| [create-proposal-document](skills/create-proposal-document/SKILL.md) | 콘텐츠·문체·PPTX 제작 |
| [create-winning-proposal](skills/create-winning-proposal/SKILL.md) | 요구·근거·승인 요건 검증 |

내부 두 스킬은 통합 진입점에서 사용하며, 개별 작업은 이름을 명시해 호출합니다.

## 실행 환경과 검증

PPTX 생성·검사는 Python 3.10+와 `python-pptx`, 자동 렌더는 LibreOffice·Poppler가 필요합니다.
플러그인 설치가 실행 도구를 설치하지는 않습니다. 자동 검사 통과는 사실·시각 품질이나 제출 승인을 대신하지 않습니다.
고객 자료와 산출물은 이 공개 저장소 밖에 보관하세요.

[작성·검토 가이드](skills/create-proposal-document/references/quality-first-authoring.md) ·
[장표 규격](skills/create-proposal-document/references/deck-production.md) ·
[제출 검사](skills/create-winning-proposal/references/audit-schema.md) ·
[개발·기여](AGENTS.md)
