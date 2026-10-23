# ProposalSkills 마켓플레이스 관리

한 저장소에서 두 호스트의 카탈로그를 제공하고 동일한 세 스킬을 한 플러그인으로 배포한다.
플러그인을 별도 폴더로 복제하지 않는다. 두 카탈로그의 source는 저장소 루트 `./`를 가리킨다.

| 항목 | 값 |
|---|---|
| 저장소 | `yjj3019/ProposalSkills` |
| 마켓플레이스 ID | `proposal-skills-marketplace` |
| 플러그인 ID | `proposal-skills` |
| 설치 식별자 | `proposal-skills@proposal-skills-marketplace` |
| Claude 카탈로그 | `.claude-plugin/marketplace.json` |
| Codex 카탈로그 | `.agents/plugins/marketplace.json` |
| 공통 매니페스트 / 호스트 호환 매니페스트 | `plugin.json` / `.codex-plugin/plugin.json` / `.claude-plugin/plugin.json` |

`@` 뒤의 이름은 GitHub 소유자가 아니라 카탈로그의 `name`이다.
기존 `yjj3019`·`fef-marketplace`와는 다른 마켓플레이스다. 기존 ID를 바꾸면 설치 식별자도
바뀌므로, 이름을 유지하고 플러그인 버전을 올리는 방식으로 관리한다.

## 등록·설치

Claude Code 세션:

```text
/plugin marketplace add yjj3019/ProposalSkills
/plugin install proposal-skills@proposal-skills-marketplace
```

Codex CLI (`plugin add`를 지원하는 버전):

```bash
codex plugin marketplace add yjj3019/ProposalSkills --ref main
codex plugin add proposal-skills@proposal-skills-marketplace
```

Codex 설치 선택자는 이 문서 작성 환경의 `codex plugin add --help`로 확인했다.
구버전에서 명령이 없으면 지원되는 데스크톱 플러그인 설치 화면을 사용한다.
로컬 작업본을 고쳤다고 GitHub의 설치 내용이 바뀌지는 않는다. 원하는 버전이 원격에 반영돼
있어야 위 명령으로 그 버전을 받을 수 있다. 이 문서의 명령을 제시하는 것과 실제 등록·설치는 별개다.

등록 후 Claude는 `/proposal-skills:create-best-proposal`, Codex는 `$create-best-proposal`로 시작한다.
ChatGPT의 지원되는 선택기에서는 설치된 스킬을 선택한다.
수동 스킬 설치와 플러그인 설치는 대안이다. 중복 설치하면 같은 이름의 스킬이 중복 노출될 수 있다.

## 업데이트

Claude의 카탈로그 갱신과 설치본 업데이트(CLI):

```bash
claude plugin marketplace update proposal-skills-marketplace
claude plugin update proposal-skills@proposal-skills-marketplace
```

Codex의 카탈로그 갱신과 가용 플러그인 확인:

```bash
codex plugin marketplace upgrade proposal-skills-marketplace
codex plugin list
```

카탈로그 갱신만으로 설치본의 업데이트 완료를 단정하지 않는다.
호스트의 설치/업데이트 결과와 실제 설치 버전을 확인하고 필요하면 새 채팅이나 재시작으로 반영한다.
설치 캐시에 직접 파일을 덮어써 업데이트하지 않는다. 사용자 자료는 별도 작업 폴더에 둔다.

## 릴리스 준비와 검증

현재 로컬 후보 버전은 `1.2.2`다. GitHub 릴리스·태그·공식 디렉터리 게시를 의미하지 않는다.

1. 세 매니페스트의 이름·버전·설명·작성자를 일치시킨다. 버전 변경 시 세 파일을 함께 갱신한다.
2. 양쪽 카탈로그에 `proposal-skills` 항목이 각각 한 번 존재하고 같은 루트를 가리키는지 확인한다.
3. 아래 검사를 실행하고 결과를 확인한다. 실제 호스트의 설치·호출도 배포 환경에서 별도로 확인한다.

```bash
python -m unittest test_skill_schema -q
python -m unittest discover -s . -p "test_*.py" -q
claude plugin validate .
python package_plugin.py -o dist/proposal-skills-1.2.2.zip
```

패키징은 JSON 파싱, 세 매니페스트의 식별 정보, Codex 스킬 경로, 카탈로그 이름,
해당 플러그인의 누락·중복·source를 검사한다. 이 저장소의 자체 연결 검사이며 모든 외부
카탈로그·원격 플러그인의 범용 스키마 검사기가 아니다.
오류가 있으면 ZIP을 만들지 않고 실패한다. 기존 ZIP은 덮어쓰지 않는다.
정상 ZIP에는 두 카탈로그·공통/호환 매니페스트·세 스킬·Python 의존성 목록이 함께 들어간다.

## 저장소 마켓플레이스와 공식 디렉터리의 차이

저장소 등록은 사용자가 지정한 카탈로그를 받는 경로다. 공식 공개 디렉터리에 게시하는 작업은
별도 절차다. 로컬 Claude 검증은 통과하더라도 디렉터리 게시 기준의 추가 지적이 있을 수 있다.
현재 저장소에는 라이선스가 지정돼 있지 않고 디렉터리용 아이콘도 없어 관련 지적이 있다.
권리자의 라이선스 선택이나 공개 게시를 이 작업에서 임의로 수행하지 않는다.

루트 CLAUDE.md는 저장소를 수정하는 사람/에이전트의 안내다. 설치 시 프로젝트 컨텍스트로
자동 로드된다고 가정하지 않는다. 플러그인 실행 지침은 배포되는 세 SKILL.md와 reference에 있다.

형식과 등록 근거(2026-10-24 확인):
[Claude marketplace](https://code.claude.com/docs/en/plugin-marketplaces),
[OpenAI plugin packaging](https://developers.openai.com/plugins/build/plugins).
