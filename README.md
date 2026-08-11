# ProposalSkills

모델에 종속되지 않는 제안서 문서 제작 스킬과 조사 자료를 관리합니다. 핵심 `SKILL.md`, 참조자료, 검증 스크립트는 ChatGPT, Claude, Gemini, Grok 등에서 동일하게 사용할 수 있습니다.

## 수록 스킬

| 스킬 | 성격 | 이런 작업에 사용 |
|---|---|---|
| **[`create-best-proposal`](skills/create-best-proposal/SKILL.md)** ★ 권장 | **통합 플래그십** — 콘텐츠+거버넌스 오케스트레이션, meta→audit, 통합 게이트, 대량 조견표 | 실전 제안서 작성부터 bid 판정·제출 게이트까지 **한 경로**로 끝낼 때 |
| [`create-proposal-document`](skills/create-proposal-document/SKILL.md) | 한국어 · PPTX 장표형 중심(DOCX 지원) · 수주 패턴 뱅크 | 한국어 IT 제안서 본문·문체·조견표·시각 레이어만 깊게 다룰 때 |
| [`create-winning-proposal`](skills/create-winning-proposal/SKILL.md) | 한/영 · 프로세스 통제 · audit JSON | bid/no-bid, 승인 체인, 결정론적 제출 게이트만 필요할 때 |

세 스킬은 충돌하지 않습니다. `create-best-proposal`이 나머지 둘을 오케스트레이션하며, 상세 문체·스키마 원문은 형제 스킬 `references/`를 참조합니다.

시뮬 근거 요약: 문서 스킬 작성 품질 ≈93 / readiness ≈31, 거버넌스 프로세스 ≈99 → **통합 스킬이 작성+제출 두 축을 동시에 강제**합니다.

## AI에게 전달했을 때 설치

AI에게 이 저장소와 함께 **“README의 설치 지침에 따라 스킬을 설치해줘”**라고 요청합니다.

```bash
# 권장: 세 스킬 모두
python install_skill.py --dest <AI의 스킬 상위 디렉터리> --all

# 플래그십 + sibling 게이트(권장)
python install_skill.py --dest <AI의 스킬 상위 디렉터리> --with-deps

# 개별
python install_skill.py --dest <AI의 스킬 상위 디렉터리> --name create-proposal-document
python install_skill.py --dest <AI의 스킬 상위 디렉터리> --name create-winning-proposal
```

`--name` 기본값은 `create-best-proposal`입니다. `--with-deps`는 document·winning 게이트를
함께 설치합니다(이미 있으면 Skip). `AI_SKILLS_DIR` 또는 `CODEX_HOME`이 있으면 `--dest`를
생략할 수 있습니다. 기존 설치는 덮어쓰지 않습니다.

비판적 선정·반영 기록: [critical-selection-2026-08.md](references/critical-selection-2026-08.md)

Grok 사용자 스킬 예:
```bash
python install_skill.py --dest "%USERPROFILE%\.grok\skills" --all
```

`agents/openai.yaml`은 OpenAI 계열 UI용 선택 메타데이터입니다.

## create-best-proposal 빠른 명령

```bash
# 작성 메타 → audit JSON
python skills/create-best-proposal/scripts/build_audit_from_meta.py meta.json -o audit.json

# 유형 C 대량 조견표
python skills/create-best-proposal/scripts/bulk_matrix.py requirements.json -o matrix.md

# 통합 게이트 (audit + 선택 문서)
python skills/create-best-proposal/scripts/unified_gate.py audit.json
python skills/create-best-proposal/scripts/unified_gate.py audit.json --doc 제안서.pptx --stage submission

# 완성도 2축
python score_completeness.py audit.json
```

## 테스트

```bash
cd ProposalSkills
python -m unittest discover -s . -p "test_*.py" -q
python skills/create-winning-proposal/scripts/test_proposal_gate.py -q
python skills/create-best-proposal/scripts/test_best_proposal.py -q
```

## 자료

- [스킬 대조 분석과 상호 개선 반영](references/skill-comparison-and-improvements.md)
- [스킬 자료 수집 노트](references/proposal-skill-materials-research.md)
- [관련 공개 Git 저장소](references/proposal-related-git-repositories.md)
- [39개 저장소·Gist 정밀 분석](references/repository-deep-audit.md)
- [10회 시뮬레이션과 개선 결과](references/simulation-report-10-runs.md)
- [종류별 시뮬레이션 리포트](simulation/output/SIMULATION_REPORT.md)
