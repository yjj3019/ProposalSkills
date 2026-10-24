# ProposalSkills

[English](README.en.md) · 한국어

한국어 IT 제안서의 요구사항 분석부터 PPTX 제작·검토·제출 준비까지 돕는 스킬 모음입니다.
ChatGPT/Codex·Claude·Grok에서 공통 지침과 검증 스크립트를 사용합니다.

## 설치

마켓플레이스 설치와 로컬 직접 설치 중 하나를 선택합니다. 세 스킬은 함께 설치됩니다.

### Codex

```bash
codex plugin marketplace add yjj3019/ProposalSkills --ref main
codex plugin add proposal-skills@proposal-skills-marketplace
```

### Claude Code

```text
/plugin marketplace add yjj3019/ProposalSkills
/plugin install proposal-skills@proposal-skills-marketplace
```

### 로컬 직접 설치

```bash
git clone https://github.com/yjj3019/ProposalSkills.git
cd ProposalSkills
python install_skill.py --auto
```

설치 대상 확인은 `--list-targets`, 기존 설치 갱신은 `git pull` 후
`python install_skill.py --auto --force`를 사용합니다.
업데이트·ZIP 배포는 [마켓플레이스 관리 가이드](references/marketplace-management.md)를 참고하세요.

## 사용

진입점은 **`create-best-proposal`**입니다.
Codex는 `$create-best-proposal`, Claude Code 직접 설치는 `/create-best-proposal`,
Claude 플러그인은 `/proposal-skills:create-best-proposal`로 시작합니다.
ChatGPT는 지원되는 환경에서 등록된 스킬을 선택합니다. 파일 첨부는 스킬 설치와 다릅니다.

RFP·수정공고·평가표·지정 양식과 보유 근거를 제공하고 다음처럼 요청하세요.

> create-best-proposal 스킬로 첨부 RFP의 제안서를 작성해줘.
> 요구사항·평가기준을 정리하고, 근거가 없는 내용은 확인 필요로 남겨줘.
> 목차·핵심 메시지를 잡은 뒤 PPTX를 만들고 가능한 검사를 실행해줘.

진행 순서는 **요구·평가 원장 → 목차·핵심 메시지 → 장표 제작 → 검토·제출 검사**입니다.

| 스킬 | 역할 |
|---|---|
| [create-best-proposal](skills/create-best-proposal/SKILL.md) | 작성부터 제출 검사까지 통합 진행 |
| [create-proposal-document](skills/create-proposal-document/SKILL.md) | 콘텐츠·문체·장표 제작 |
| [create-winning-proposal](skills/create-winning-proposal/SKILL.md) | 근거·승인·제출 요건 검증 |

나머지 두 스킬은 통합 스킬이 사용하는 내부 레이어이며, 이름을 명시할 때만 직접 호출합니다.

## 검증 범위

자동 검사는 요구·근거·수치·파일 해시·제출 묶음의 정합성을 확인합니다.
주장의 진위, OCR 정확성, 장표의 설득력과 최종 시각 품질은 사람이 원문·실제 산출물과 대조합니다.
`AUDIT-VALID`는 기록 검사 통과이며 제출 승인이 아닙니다. `SUBMISSION-READY`는 해당 파일과
필수 검사·승인 기록이 일치할 때의 판정이며 수주 가능성을 보증하지 않습니다.

PPTX 생성·검사에는 `python-pptx`, 렌더 검사에는 LibreOffice·Poppler가 필요합니다.
파일·실행 도구가 없으면 텍스트 작성·검토까지 진행하고 실행하지 못한 검사는 미수행으로 남깁니다.
원문·고객 자료·작업 산출물은 이 공개 저장소 밖의 작업 폴더에 보관하세요.

## 상세 가이드

- [호스트별 설치·호출·실행 범위](skills/create-best-proposal/references/host-portability.md)
- [근거 중심 작성·Red 검토](skills/create-proposal-document/references/quality-first-authoring.md)
- [장표 제작·출력 규격](skills/create-proposal-document/references/deck-production.md)
- [원문 추출·OCR·수정공고·시각 비교](skills/create-proposal-document/references/source-and-visual-evidence.md)
- [제출 게이트·audit 스키마](skills/create-winning-proposal/references/audit-schema.md)
- [관련 프로젝트 분석](references/proposal-related-git-repositories.md)

## 개발·테스트

```bash
pip install -r requirements.txt
python -m unittest discover -s . -p "test_*.py" -q
```

기여 전 [AGENTS.md](AGENTS.md)의 변경·검증·공개 자료 규칙을 확인하세요.
