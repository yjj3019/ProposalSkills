# AGENTS.md — 이 저장소를 다루는 AI를 위한 지침

이 저장소는 **한국어 IT/공공 제안서 작성 스킬 3종**을 담고 있습니다. 사용자가 이 저장소를
가리키며 "설치해줘"라고 하면 아래 한 줄을 실행하십시오. 어떤 디렉터리에 넣을지 사용자에게
되묻지 마십시오 — 스크립트가 이 컴퓨터에 설치된 AI CLI를 찾아 각각의 스킬 디렉터리에 넣습니다.

```bash
python install_skill.py --auto
```

Python이 없으면 `python3`로 시도하고, 그래도 없으면 사용자에게 Python 3.10 이상을 설치해
달라고 요청하십시오. 외부 패키지는 설치에 필요 없습니다.

## 스킬 라우팅 (모델 공통)

| 역할 | 스킬 | 호출 |
|---|---|---|
| **진입점 (flagship)** | `create-best-proposal` | 암시·명시 모두. 「제안서 작성」은 항상 여기로 |
| **내부 레이어 (sibling)** | `create-proposal-document`, `create-winning-proposal` | **명시 호출만** (`$스킬명` / 사용자가 레이어만 지정). 암시 선택 금지 |

형제 스킬은 플래그십이 로드하는 콘텐츠·거버넌스 레이어입니다. 사용자가 형제를 이름으로
부르지 않으면 직접 열지 마십시오. Claude는 `disable-model-invocation: true`, Codex/ChatGPT는
`agents/openai.yaml`의 `policy.allow_implicit_invocation: false`로 형제의 암시 호출을 막습니다.
플래그십에는 이 제한을 두지 않습니다.

## 설치 위치

`--auto`는 홈 디렉터리에서 각 도구의 표시를 찾아 해당 스킬 경로에 설치합니다.

| 감지 대상 | 설치 경로 |
|---|---|
| `~/.claude/` 존재 | `~/.claude/skills/` |
| `~/.codex/` 존재 | `~/.agents/skills/` (**Codex 권장**, AGENTS.md 공용 규약) |
| `~/.grok/` 존재 | `~/.grok/skills/` |
| `~/.agents/` 존재 | `~/.agents/skills/` |
| 아무것도 없음 | `~/.agents/skills/` |

환경변수 `AI_SKILLS_DIR`이 있으면 그 경로도 대상에 포함됩니다. `CODEX_HOME`이 있으면
`$CODEX_HOME/skills`에도 설치하되 **레거시 호환 경고**를 냅니다 — Codex는 여전히 그 경로를
deprecated compat로 읽지만, 권장 설치 위치는 `~/.agents/skills`입니다. 기본 `--dest`로
`CODEX_HOME`을 쓰지 마십시오. 설치 전에 대상만 확인하려면
`python install_skill.py --list-targets`. 특정 경로에 넣으려면
`python install_skill.py --dest <경로> --all`.

세 스킬을 **모두** 설치하는 것이 기본값입니다. 플래그십(`create-best-proposal`)만 설치하면
통합 게이트가 형제 게이트를 찾지 못해 제출 판정 경로가 끊깁니다.

이미 설치돼 있으면 건너뜁니다(`Skip (exists)`). 최신본으로 교체하려면 `--force`를 붙입니다.

## 설치 후 확인

스크립트가 스킬별로 `SKILL.md`·`scripts/`·`references/`·라우팅 메타(openai.yaml /
`disable-model-invocation`)를 검증하고 결과를 출력합니다.
`Installed with problems`가 보이면 그 줄의 누락 파일을 사용자에게 알리십시오.

동작 확인이 필요하면:

```bash
python <설치경로>/create-best-proposal/scripts/unified_gate.py \
       <설치경로>/create-best-proposal/fixtures/audit_ready_financial.json --audit-only --no-explain
```

`STATUS: AUDIT-VALID`가 나오면 정상입니다.

## 설치 후 사용법

사용자가 제안서 작업을 요청하면 **`create-best-proposal`만** 진입점으로 사용하십시오.
나머지 둘은 내부 레이어이며, 사용자가 명시하거나 플래그십 워크플로가 가리킬 때만 엽니다.

## ChatGPT / Codex 웹·Work·Mobile

`install_skill.py`는 로컬 CLI용입니다. **프로젝트에 폴더를 업로드하는 것은 참고 자료일 뿐
Skill 등록이 아닙니다.**

- **로컬 CLI (Claude Code · Codex · Grok)**: 위 `--auto` 설치.
- **ChatGPT / Codex (Web · Work · Mobile)**: Plugin으로 등록합니다.
  저장소 루트의 [`.codex-plugin/plugin.json`](.codex-plugin/plugin.json) + `skills/` 레이아웃을
  사용하십시오. 자세한 안내는 README «ChatGPT·Codex Plugin» 절을 따릅니다.
- 게이트 스크립트 실행이 필요한 단계는 로컬 CLI에서 수행해야 합니다.

## 공개 저장소 — 커밋하면 안 되는 것

이 저장소는 **공개돼 있습니다.** 제안서 작업은 성격상 민감한 정보를 다루므로, 작업 중에 본
내용을 그대로 커밋하면 영구히 공개됩니다. 다음은 예제·픽스처·문서·커밋 메시지 어디에도
넣지 마십시오.

- **고객사·발주처·경쟁사의 실제 이름**, 사업명, 프로젝트 번호, 계약 정보
- **실제 금액·견적·단가**, 실적 수치, 인력 성명·연락처·소속
- 실제 RFP나 제안서의 **원문 발췌**, 페이지 이미지, 파일명
- 작업자의 **로컬 절대 경로**(윈도우 사용자 폴더, 유닉스 홈 디렉터리), 이메일, 사내 워크스페이스 링크
- 자격증명(API 키·토큰·비밀번호)

픽스처가 필요하면 가상 발주처(`○○공사`)와 가상 수치로 만듭니다. 실제 문서를 참고해 얻은
것은 **구조적 일반화**(예: "요구가 100건을 넘으면 조견표가 9장이 된다")까지만 옮기고,
그 문서를 특정할 수 있는 것은 옮기지 않습니다.

`test_repo_hygiene.py`가 로컬 경로·이메일·자격증명 형태·픽스처 발주처를 기계 검사합니다.
다만 "이 이름이 실제 고객사인가"는 기계가 판별할 수 없으므로, 그 판단은 이 규칙과 사람의
검토에 달려 있습니다.

## 이 저장소를 수정할 때

- 변경 후 `python -m unittest discover -s . -p "test_*.py" -q`가 통과해야 합니다.
- 게이트 동작을 바꾸면 `test_gate_integrity.py`에 재현 테스트를 추가하십시오.
- 위 «공개 저장소» 규칙을 지키십시오. 실제 제안 자료를 참고했다면 구조적 일반화만 남깁니다.
- 게이트 계약(제출 판정 규칙)은 `README.md`와
  `skills/create-winning-proposal/references/audit-schema.md`에 문서화돼 있습니다. 코드와
  문서를 함께 갱신하십시오.
- 스킬 라우팅 메타(암시/명시)를 바꿀 때는 `test_skill_schema.py`와 형제/플래그십 대칭을
  유지하십시오. 게이트·픽스처·워크플로를 약화하지 마십시오.
