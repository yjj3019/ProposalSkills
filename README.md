# ProposalSkills

모델에 종속되지 않는 제안서 문서 제작 스킬과 조사 자료를 관리합니다. 핵심 `SKILL.md`, 참조자료, 검증 스크립트는 ChatGPT, Claude, Gemini, Grok 등에서 동일하게 사용할 수 있습니다.

## AI에게 전달했을 때 설치

AI에게 이 저장소와 함께 **“README의 설치 지침에 따라 스킬을 설치해줘”**라고 요청합니다. AI는 사용 중인 플랫폼의 스킬 상위 디렉터리를 확인한 뒤 다음 명령을 실행합니다.

```bash
python install_skill.py --dest <AI의 스킬 상위 디렉터리>
```

`AI_SKILLS_DIR` 환경 변수가 설정된 환경에서는 `python install_skill.py`만 실행합니다. Codex는 `CODEX_HOME`이 설정되어 있으면 `<CODEX_HOME>/skills`를 자동 선택합니다. 기존 설치는 덮어쓰지 않습니다.

`skills/create-winning-proposal/agents/openai.yaml`은 OpenAI 계열 UI를 위한 선택적 메타데이터일 뿐이며 핵심 스킬의 실행 의존성이 아닙니다. 다른 AI에서는 `SKILL.md`와 필요한 `references/`를 프로젝트 지침, 지식 파일, 시스템 지침 또는 프롬프트 컨텍스트로 제공하면 됩니다.

- [설치 가능한 제안서 스킬](skills/create-winning-proposal/SKILL.md)
- [스킬 자료 수집 노트](references/proposal-skill-materials-research.md)
- [관련 공개 Git 저장소](references/proposal-related-git-repositories.md)
- [39개 저장소·Gist 정밀 분석](references/repository-deep-audit.md)
- [10회 시뮬레이션과 개선 결과](references/simulation-report-10-runs.md)
ProposalSkills
