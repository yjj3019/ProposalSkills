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
