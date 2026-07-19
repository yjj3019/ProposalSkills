# ProposalSkills

모델에 종속되지 않는 제안서 문서 제작 스킬과 조사 자료를 관리합니다. 핵심 `SKILL.md`, 참조자료, 검증 스크립트는 ChatGPT, Claude, Gemini, Grok 등에서 동일하게 사용할 수 있습니다.

## 수록 스킬 2종

| 스킬 | 성격 | 이런 작업에 사용 |
|---|---|---|
| [`create-proposal-document`](skills/create-proposal-document/SKILL.md) | 한국어 · PPTX 장표형 중심(DOCX 지원) · 실제 수주 제안서에서 추출한 내용 패턴 뱅크 포함 | 한국어 IT 제안서(구축/유지보수·기술지원/기술답변서)를 실제로 **작성**할 때. 조견표, 리드문 장표 문법, 문체·과장어 규칙, 예방점검/테스트/사업관리 등 검증된 내용 뼈대 제공 |
| [`create-winning-proposal`](skills/create-winning-proposal/SKILL.md) | 한/영 · 모델 중립 · 프로세스 통제 중심 | 입찰 **프로세스 거버넌스**가 필요할 때: bid/no-bid 판정, 요구사항 원장과 승인 체인, 감사 JSON + 결정론적 제출 게이트, DOCX 템플릿 보존 |

두 스킬은 충돌하지 않습니다. 전자는 콘텐츠·문체·시각 레이어, 후자는 거버넌스 레이어입니다. 상호 대조 분석과 개선 반영 내역은 [스킬 대조 분석](references/skill-comparison-and-improvements.md)에 있습니다.

## AI에게 전달했을 때 설치

AI에게 이 저장소와 함께 **“README의 설치 지침에 따라 스킬을 설치해줘”**라고 요청합니다. AI는 사용 중인 플랫폼의 스킬 상위 디렉터리를 확인한 뒤 다음 명령을 실행합니다.

```bash
python install_skill.py --dest <AI의 스킬 상위 디렉터리> --name create-proposal-document
python install_skill.py --dest <AI의 스킬 상위 디렉터리> --name create-winning-proposal
python install_skill.py --dest <AI의 스킬 상위 디렉터리> --all   # 두 스킬 모두
```

`--name`을 생략하면 기존 동작과 같이 `create-winning-proposal`을 설치합니다. `AI_SKILLS_DIR` 환경 변수가 설정된 환경에서는 `--dest`를 생략할 수 있습니다. Codex는 `CODEX_HOME`이 설정되어 있으면 `<CODEX_HOME>/skills`를 자동 선택합니다. 기존 설치는 덮어쓰지 않습니다.

`agents/openai.yaml`은 OpenAI 계열 UI를 위한 선택적 메타데이터일 뿐이며 핵심 스킬의 실행 의존성이 아닙니다. 다른 AI에서는 `SKILL.md`와 필요한 `references/`를 프로젝트 지침, 지식 파일, 시스템 지침 또는 프롬프트 컨텍스트로 제공하면 됩니다.

## 문서 검토 실행 환경

공통 검토 환경에는 Python 문서 라이브러리, LibreOffice, Poppler, 한글 폰트가 포함됩니다.

```bash
docker build -t proposal-skills .
docker run --rm proposal-skills
```

문서를 처리할 때 작업 폴더를 `/workspace`로 마운트하고 필요한 스킬의 검사기를 실행합니다.

```bash
docker run --rm -v "$PWD:/workspace" proposal-skills \
  python skills/create-proposal-document/scripts/quality_gate.py /workspace/proposal.pptx
```

Windows PowerShell에서는 마운트 인수를 `-v "${PWD}:/workspace"`로 사용합니다. 거버넌스 감사 JSON과 LibreOffice 변환 예시는 다음과 같습니다.

```bash
docker run --rm -v "$PWD:/workspace" proposal-skills \
  python skills/create-winning-proposal/scripts/proposal_gate.py /workspace/audit.json
docker run --rm -v "$PWD:/workspace" proposal-skills \
  libreoffice --headless --convert-to pdf --outdir /workspace/output /workspace/proposal.docx
```

Docker 없이 Python 라이브러리만 설치하려면 `python -m pip install -r requirements.txt` 후 `python runtime_check.py --python-only`로 확인합니다. 최종 제출본의 기준 렌더러가 Microsoft Word 또는 PowerPoint라면 해당 애플리케이션에서 별도 최종 검수를 수행합니다.

## 자료

- [스킬 대조 분석과 상호 개선 반영](references/skill-comparison-and-improvements.md)
- [스킬 자료 수집 노트](references/proposal-skill-materials-research.md)
- [관련 공개 Git 저장소](references/proposal-related-git-repositories.md)
- [39개 저장소·Gist 정밀 분석](references/repository-deep-audit.md)
- [10회 시뮬레이션과 개선 결과](references/simulation-report-10-runs.md)
