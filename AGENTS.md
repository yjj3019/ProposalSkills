# AGENTS.md — 이 저장소를 다루는 AI를 위한 지침

이 저장소는 **한국어 IT/공공 제안서 작성 스킬 3종**을 담고 있습니다. 사용자가 이 저장소를
가리키며 "설치해줘"라고 하면 아래 한 줄을 실행하십시오. 어떤 디렉터리에 넣을지 사용자에게
되묻지 마십시오 — 스크립트가 이 컴퓨터에 설치된 AI CLI를 찾아 각각의 스킬 디렉터리에 넣습니다.

```bash
python install_skill.py --auto
```

Python이 없으면 `python3`로 시도하고, 그래도 없으면 사용자에게 Python 3.10 이상을 설치해
달라고 요청하십시오. 외부 패키지는 설치에 필요 없습니다.

## 설치 위치

`--auto`는 홈 디렉터리에서 각 도구의 표시를 찾아 해당 스킬 경로에 설치합니다.

| 감지 대상 | 설치 경로 |
|---|---|
| `~/.claude/` 존재 | `~/.claude/skills/` |
| `~/.codex/` 존재 | `~/.agents/skills/` (AGENTS.md 공용 규약) |
| `~/.grok/` 존재 | `~/.grok/skills/` |
| `~/.agents/` 존재 | `~/.agents/skills/` |
| 아무것도 없음 | `~/.agents/skills/` |

환경변수 `AI_SKILLS_DIR` 또는 `CODEX_HOME`이 있으면 그 경로도 대상에 포함됩니다.
설치 전에 대상만 확인하려면 `python install_skill.py --list-targets`.
특정 경로에 넣으려면 `python install_skill.py --dest <경로> --all`.

세 스킬을 **모두** 설치하는 것이 기본값입니다. 플래그십(`create-best-proposal`)만 설치하면
통합 게이트가 형제 게이트를 찾지 못해 제출 판정 경로가 끊깁니다.

이미 설치돼 있으면 건너뜁니다(`Skip (exists)`). 최신본으로 교체하려면 `--force`를 붙입니다.

## 설치 후 확인

스크립트가 스킬별로 `SKILL.md`·`scripts/`·`references/` 존재를 검증하고 결과를 출력합니다.
`Installed with problems`가 보이면 그 줄의 누락 파일을 사용자에게 알리십시오.

동작 확인이 필요하면:

```bash
python <설치경로>/create-best-proposal/scripts/unified_gate.py \
       <설치경로>/create-best-proposal/fixtures/audit_ready_financial.json --audit-only --no-explain
```

`STATUS: AUDIT-VALID`가 나오면 정상입니다.

## 설치 후 사용법

사용자가 제안서 작업을 요청하면 `create-best-proposal` 스킬을 진입점으로 사용하십시오.
나머지 둘은 그 스킬이 필요할 때 불러옵니다. 직접 열지 마십시오.

## 파일 시스템이 없는 환경 (ChatGPT 웹 등)

`install_skill.py`를 실행할 수 없습니다. 대신 `skills/create-best-proposal/` 폴더를 프로젝트
지식 파일로 업로드하도록 사용자에게 안내하십시오. 스크립트 실행이 필요한 게이트 단계는
로컬 CLI(Claude Code·Codex·Grok)에서 수행해야 합니다.

## 이 저장소를 수정할 때

- 변경 후 `python -m unittest discover -s . -p "test_*.py" -q`가 통과해야 합니다.
- 게이트 동작을 바꾸면 `test_gate_integrity.py`에 재현 테스트를 추가하십시오.
- 게이트 계약(제출 판정 규칙)은 `README.md`와
  `skills/create-winning-proposal/references/audit-schema.md`에 문서화돼 있습니다. 코드와
  문서를 함께 갱신하십시오.
