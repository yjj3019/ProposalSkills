# 제안서 관련 공개 저장소 정밀 분석

확인일: 2026-07-18
범위: `proposal-related-git-repositories.md`에 기록된 39개 저장소·Gist. README뿐 아니라 핵심 소스, 데이터 모델, 테스트, CI, 출력 로직, 라이선스와 최근 활동을 확인했다.

## 결론

가장 강한 조합은 다음과 같다.

1. ProposalForce의 요구사항·답변·담당·상태 모델
2. q-flow의 폐쇄형 근거, 검토 이벤트, 출력 봉쇄
3. RFP-IGNITE의 결정론적 누락·단위 검사와 승인본 분리
4. BidCraft의 추출/답변 평가 분리와 golden-set 평가
5. grant-framework의 단계별 승인과 변경 이력
6. open-agreements의 출처·라이선스 메타데이터와 산출물 검증
7. python-docx-template/python-docx의 기존 Word 템플릿 보존
8. Vale 조직 규칙 저장소의 규칙별 정상·오류 fixture와 점진적 게이트

GraphRAG, 다중 에이전트, 모델 자기점수, 검색 유사도를 사실 신뢰도로 표시하는 방식은 채택하지 않는다.

## RFP·자동화 저장소

| 저장소 | 코드 수준 확인 | 채택 | 제외·위험 |
|---|---|---|---|
| SalesforceLabs/ProposalForce | Salesforce 객체 `RFP → Question → Response`, Knowledge 연결, 상태·담당·CSV/DOCX export, CRUD/FLS 검사 | 단순 데이터 모델, 담당/상태/컴플라이언스 | archived, 근거 버전·출력 게이트 부재 |
| AnshMNSoni/B2B-RFP-Agent | Gemini JSON 추출, typed SKU 매칭, 결정론적 가격 계산 | 구조화 추출 경계, 파생값 재계산 | 근거·인증·검토 없음, 외부 전송 |
| jabessouguie/consulting-tools | 문서 파서, LLM 추출, Markdown/PPTX/DOCX, anonymizer, pytest | `[NEEDS INPUT]`, 익명화, 프로필/템플릿 어댑터 | 입력 잘림, 근거 매핑 없음, 저장소에 민감 파일 이력 |
| GideonLartey/wash-rfp-backend | PDF→Gemini JSON→PDF, 크기·형식 제한, HTML escape, 임시파일 정리 | 엄격한 업로드 경계, escape/cleanup | 출처 없는 추정값·중립 fallback, 인증 없음 |
| degerahmet/q-flow | Project/Question/Document/Embedding/Citation/ReviewEvent, 상태 전이, 409 export gate | 폐쇄형 근거, 검토 이벤트, 출력 차단 | 유사도=confidence 오용, 핵심 테스트 부족 |
| Parth-Gochhwal/RFP-IGNITE | 구조화 오케스트레이터, 누락/단위 검사, 승인 리뷰, 가격 override 재계산, audit JSON | 결정론적 검증, 질문 큐, 초안/승인본 분리 | 불필요한 agent 명명, 인증·불변 감사 부족 |
| Satyapraveenv/ai-rfp-response-generator | 프롬프트 기반 생성, Markdown/HTML, quality score 파싱 | 요구사항 우선 개요, 커스터마이즈 마커 | 모델 자기점수와 92점 fallback, 근거 없음 |
| Pankajkantghz/rfp-agent | RFP/Vendor/Proposal 모델, 이메일 식별자, Gemini 평가 | 정규화 데이터 옆 원문 ID 유지 | 무면허, 인증·근거·테스트 없음, 원문 로그 |
| bhargavhari2001-cloud/BidCraft | 다형식 추출, RAG+rerank, 편집/평가, DOCX/PDF, golden 평가 | 추출과 답변 평가 분리, edit-distance, golden set | 무면허, 약한 RLS, 제목 수준 citation, 출력 게이트 없음 |
| sridivya9398/AutoProposal | React mock UI와 setTimeout 시뮬레이션 | 질문 카드 아이디어만 | GraphRAG/FHE/ZK/BFT 등이 미구현, 무면허 |
| VaultaFoundation/grant-framework | Markdown+PR 검토, 규모별 승인 수, milestone 증빙 commit/tag | 버전 이력, 단계별 승인, 불변 증빙 링크 | 공개 workflow는 기밀 제안서에 부적합, 루트 라이선스 불명확 |
| open-agreements/open-agreements | source registry, metadata YAML, schema/postcondition, DOCX render, 100+ test/spec | 출처/라이선스 sidecar, 결정론적 검증, 렌더 QA | 법률 도메인 복잡성은 재사용하지 않음 |

## 문서 생성 저장소

| 저장소 | 판정 | 핵심 이유 |
|---|---|---|
| elapouya/python-docx-template | 기본 템플릿 엔진 | 기존 Word 본문·머리말·꼬리말을 두고 Jinja형 변수/반복/조건/이미지 적용. run 분할과 복합 필드는 렌더 검증 필요 |
| python-openxml/python-docx | 최소 후처리 | 문단·표·스타일·섹션 제어. TOC/SmartArt/추적 변경 등은 제한 |
| jgm/pandoc | Markdown 전용 선택지 | `reference.docx`는 본문 템플릿 채우기가 아니라 스타일 참조 |
| quarto-dev/quarto-cli | 데이터·인용 중심 기술 제안서만 | 코드·교차참조 강점. 외부 문서 실행 금지, DOCX 보존 한계 |
| mherkazandjian/docxsphinx | 기존 Sphinx 조직만 | 현재 main 기능과 배포 릴리스 차이, TOC/header/footer 제약 |
| JessicaTegner/pypandoc | 필요한 경우에만 | Pandoc CLI의 얇은 Python wrapper |
| pandoc/lua-filters | 검증한 필터만 고정 | 필터는 실행 코드이며 포맷별 품질이 다름 |
| pandoc-obsidian-templates | 디자인 참고 | 소설·학술·LaTeX 중심, DOCX 검증 약함 |
| TomBener/pandoc-templates | 의존 금지 | archived, 중국어 학술용, DOCX 표·그림 TODO |
| DonnC/docxtpl | 제외 | archived Flutter 구현, 표·이미지·rich text 미지원 |

## 문체 자동화 저장소

| 저장소 | 판정 | 핵심 이유 |
|---|---|---|
| vale-cli/vale | 검증된 객관 규칙에 사용 | markup-aware, 확장 가능. DOCX는 canonical text 추출 후 검사 |
| vale-cli/Microsoft | 규칙 구조 참고 | 40 YAML 규칙과 19 fixture 그룹. 미국 영문 정책을 한국어에 직접 적용 금지 |
| vale-cli/Google | 규칙 구조 참고 | 31 규칙, markup scope와 정확한 위치 테스트 |
| vale-cli/write-good | suggestion만 | 8개 영어 휴리스틱, 한국어 형태론 미지원 |
| vale-cli/proselint | 범주만 참고 | corporate speak/hedging/hyperbole 등, fixture 세분성 낮음 |
| redhat-documentation/vale-at-red-hat | 조직 운영 모델 채택 | 정상/오류 fixture, override, rule validation CI, 간단 YAML 우선 |
| elastic/vale-rules | 접근성 규칙 참고 | 의미 있는 링크, 방향 의존 표현 금지, Apache NOTICE 필요 |
| vale-cli/vale-action | 필요 시 점진 도입 | changed-line annotation부터 시작하고 객관적 error만 gate |
| testthedocs/awesome-docs | 링크 색인만 | CC BY-NC 4.0이므로 상업용 복제 위험 |

## 템플릿·Gist

| 항목 | 채택할 개념 | 라이선스·한계 |
|---|---|---|
| UBC-STAT/proposal-template | 메타데이터/내용/표현 분리, timeline, cross-reference | 무면허, 학술용, 코드·로고 복제 금지 |
| r02b/Latex-PhD_Proposal_Template | 선언형 표지 메타데이터 | MIT, 학술 의미 구조는 부족 |
| YimianDai/iNSFC | CJK font/spacing/numbering 중앙 설정, 연도별 양식 검증 | 무면허, 폰트·공식 양식 권리 위험 |
| hust-latex/hustproposal | documented source→generated class, CJK layout | LPPL 1.3c, 중국어·구형 폰트 |
| donbr proposal gist | discovery, scope, deliverable, milestone, dependency, acceptance | CC BY 4.0이나 혼합 출처·계약 조항 라이선스 복잡 |
| dims TCE gist | goals/non-goals, FR/NFR IDs, security, alternatives, test/upgrade/version history | 무면허, 개념만 독립 표현 |
| nelsonenzo technical spec gist | summary, background, goals, plan, impact, privacy | 무면허, 상업 RFP 단독 구조로는 부족 |

## 한국어 문체 자동화 원칙

영문 규칙 목록을 번역하지 않는다. 먼저 다음과 같은 결정론적 규칙만 자동화한다.

- 승인/금지 회사명·제품명·띄어쓰기 변형
- 날짜·통화·숫자·단위·버전 표기
- 미해결 placeholder와 충돌 표시
- 근거 없는 최고·유일·완벽·100%·무중단·보장 표현
- `상기`, `아래`, `좌측` 대신 명명된 절·표·그림 참조
- 의미 있는 링크 문구와 대체 텍스트

수동태, 장황함, 헤징, 가독성 점수는 한국어 제안서 말뭉치로 검증되기 전까지 제안 수준으로만 사용한다.

## 최종 아키텍처

1. 로컬 입력 inventory와 SHA-256
2. Bid/No-Bid 판정
3. 원문 위치를 가진 원자 요구사항 원장
4. 승인 근거 기반 초안과 `[NEEDS INPUT]`
5. 결정론적 상태 전이와 append-only 검토 이벤트
6. 의무·근거·약속·첨부·placeholder·렌더 제출 게이트
7. 기존 DOCX 템플릿 채우기와 최소 후처리
8. DOCX→PDF→페이지 이미지 렌더 검증
9. 제안서·컴플라이언스·근거·검토·게이트 보고서 묶음
