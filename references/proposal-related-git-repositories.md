# 제안서 작업 관련 공개 Git 저장소 조사

확인일: 2026-07-18
범위: 기업·공공 제안서, RFP 응답, DOCX/PDF 생성, 문체 규칙 자동검사, 범용 제안 구조에 직접 또는 간접 활용할 수 있는 공개 GitHub 저장소. GitHub 전체의 모든 저장소를 완전 열거한 목록은 아니며, 검색 가능한 저장소 중 관련성이 확인된 항목을 정리했다.

## 1. 우선 검토할 저장소

| 저장소 | 용도 | 적용 판단 |
|---|---|---|
| [SalesforceLabs/ProposalForce](https://github.com/SalesforceLabs/ProposalForce) | RFP 질문·답변·담당·상태·지식베이스 관리, CSV와 DOCX 출력 | RFP 응답 데이터 모델과 워크플로 참고에 가장 직접적. BSD-3-Clause |
| [elapouya/python-docx-template](https://github.com/elapouya/python-docx-template) | Word 템플릿에 Jinja형 태그를 넣어 DOCX 생성 | 회사 DOCX 서식을 보존하면서 내용만 채우는 방식에 적합. LGPL-2.1 |
| [python-openxml/python-docx](https://github.com/python-openxml/python-docx) | DOCX 읽기·생성·수정 | 표, 제목, 문단, 이미지 등 세밀한 후처리가 필요할 때 사용 |
| [jgm/pandoc](https://github.com/jgm/pandoc) | Markdown을 DOCX/PDF 등으로 변환, `reference.docx` 지원 | 텍스트와 스타일을 분리하는 재현 가능한 생성 파이프라인에 적합 |
| [quarto-dev/quarto-cli](https://github.com/quarto-dev/quarto-cli) | Pandoc 기반 기술 문서 출판, 교차참조·인용·코드 결과 지원 | 표·차트·기술 분석이 많은 제안서에 유용. MIT |
| [vale-cli/vale](https://github.com/vale-cli/vale) | 문체·용어·맞춤법 규칙을 YAML로 자동 검사 | 제안서 금지어, 승인 용어, 과장 표현 검출에 가장 적합. MIT |

최소 구현은 `python-docx-template`과 기존 DOCX 템플릿 조합이다. Markdown 중심으로 원본을 관리해야 할 때만 Pandoc 또는 Quarto를 추가하고, 문체 검사가 실제로 반복될 때 Vale을 추가한다.

## 2. RFP·제안 응답 자동화 참고

GitHub의 [`rfp-automation` 토픽](https://github.com/topics/rfp-automation)에 2026-07-18 기준 공개 저장소 9개가 노출된다. 대부분 별과 사용 이력이 적은 초기 프로젝트이므로 코드나 아키텍처를 그대로 채택하기보다 기능 비교와 실험 참고용으로 취급한다.

| 저장소 | 확인된 기능 | 주의 |
|---|---|---|
| [AnshMNSoni/B2B-RFP-Agent](https://github.com/AnshMNSoni/B2B-RFP-Agent) | 제조업 RFP 처리와 견적 생성 | 특정 산업용 |
| [jabessouguie/consulting-tools](https://github.com/jabessouguie/consulting-tools) | 컨설팅 제안서와 Slides 자동화 | 범위가 넓어 필요한 부분만 참고 |
| [GideonLartey/wash-rfp-backend](https://github.com/GideonLartey/wash-rfp-backend) | PDF 파싱과 생성형 AI 기반 NGO RFP 백엔드 | 데모이며 특정 NGO와 무관하다고 명시 |
| [degerahmet/q-flow](https://github.com/degerahmet/q-flow) | RAG, 보안 질의서·RFP 답변, 사람 검토, Excel 형식 보존 | 지식검색·검토 흐름 참고 가치 높음 |
| [Parth-Gochhwal/RFP-IGNITE](https://github.com/Parth-Gochhwal/RFP-IGNITE) | 영업·기술·가격 에이전트와 human-in-the-loop | 다중 에이전트 복잡성은 현재 스킬에 불필요 |
| [Satyapraveenv/ai-rfp-response-generator](https://github.com/Satyapraveenv/ai-rfp-response-generator) | 컨텍스트 추출, 점수화, 서술 생성 | 작은 초기 프로젝트 |
| [Pankajkantghz/rfp-agent](https://github.com/Pankajkantghz/rfp-agent) | MERN 기반 RFP 에이전트 | 설명과 검증 자료가 제한적 |
| [bhargavhari2001-cloud/BidCraft](https://github.com/bhargavhari2001-cloud/BidCraft) | 질문 추출, 지식베이스 매칭, 신뢰도 점수 | 최근 초기 프로젝트 |
| [sridivya9398/AutoProposal](https://github.com/sridivya9398/AutoProposal) | Agentic workflow와 GraphRAG 기반 RFP·보안질의 응답 | 최근 초기 프로젝트 |

별도 저장소:

- [VaultaFoundation/grant-framework](https://github.com/VaultaFoundation/grant-framework): 제안, 유지보수 지원, RFP 응답 유형과 심사 흐름 참고.
- [open-agreements/open-agreements](https://github.com/open-agreements/open-agreements): 제안서 자체는 아니지만 표준 문서→DOCX 생성, 템플릿별 출처·라이선스 관리 구조가 좋은 참고 사례.

## 3. 문체·용어 규격 자동화

| 저장소 | 활용 가능 부분 |
|---|---|
| [vale-cli/Microsoft](https://github.com/vale-cli/Microsoft) | Microsoft Writing Style Guide를 Vale 규칙으로 구현. 영문 기술 제안서 기준 참고 |
| [vale-cli/Google](https://github.com/vale-cli/Google) | Google 개발자 문서 스타일의 Vale 규칙 구현 |
| [vale-cli/write-good](https://github.com/vale-cli/write-good) | 수동태·장황한 표현 등 영문 문체 검사 참고 |
| [vale-cli/proselint](https://github.com/vale-cli/proselint) | proselint 규칙의 Vale 구현 |
| [redhat-documentation/vale-at-red-hat](https://github.com/redhat-documentation/vale-at-red-hat) | 조직 내부 문체 규칙을 도입·운영하는 구성 참고 |
| [elastic/vale-rules](https://github.com/elastic/vale-rules) | 조직별 Vale 규칙, 예외, GitHub Actions 연계 사례 |
| [vale-cli/vale-action](https://github.com/vale-cli/vale-action) | GitHub Actions에서 문체 검사 자동 실행 |
| [testthedocs/awesome-docs](https://github.com/testthedocs/awesome-docs) | 접근성 및 주요 기술 문서 스타일 가이드 링크 모음 |

한국어 제안서에는 위 영문 규칙을 그대로 적용하지 않는다. 저장소 구조와 검사 유형만 참고해 회사 용어집, 금지어, 숫자·제품명 표기 규칙을 자체 작성하는 편이 안전하다.

## 4. DOCX·PDF 생성과 템플릿

| 저장소 | 용도 | 판단 |
|---|---|---|
| [mherkazandjian/docxsphinx](https://github.com/mherkazandjian/docxsphinx) | Sphinx 문서를 Word 템플릿 스타일로 출력 | 대규모 기술 문서가 Sphinx에 이미 있을 때만 고려 |
| [JessicaTegner/pypandoc](https://github.com/JessicaTegner/pypandoc) | Python에서 Pandoc 변환 호출 | Python 파이프라인에서 Pandoc이 필요할 때만 사용 |
| [pandoc/lua-filters](https://github.com/pandoc/lua-filters) | Pandoc 문서 변환 필터 모음 | 교차참조·표·특수 변환이 필요할 때 참고 |
| [jvsteiner/pandoc-obsidian-templates](https://github.com/jvsteiner/pandoc-obsidian-templates) | 여러 Pandoc 문서 템플릿과 DOCX 예시 | 스타일 실험 참고용 |
| [TomBener/pandoc-templates](https://github.com/TomBener/pandoc-templates) | Markdown→DOCX/PDF 템플릿 | 보관(archived) 상태이므로 직접 의존하지 않음. MIT |
| [DonnC/docxtpl](https://github.com/DonnC/docxtpl) | Flutter에서 DOCX 태그 치환 | 2025-12-08 보관됨. Python용 동명 도구와 혼동 주의 |

## 5. 제안서 구조·디자인 참고용 템플릿

아래는 기업 RFP 제안서와 목적이 다르므로 목차·변수·시각 구성만 참고한다.

- [UBC-STAT/proposal-template](https://github.com/UBC-STAT/proposal-template): 통계학 연구 제안서 LaTeX 템플릿.
- [r02b/Latex-PhD_Proposal_Template](https://github.com/r02b/Latex-PhD_Proposal_Template): 간단한 박사 연구계획서 클래스. MIT.
- [YimianDai/iNSFC](https://github.com/YimianDai/iNSFC): 중국 국가자연과학기금 비공식 2026 LaTeX 템플릿. 공식 제출 형식 확인 필수.
- [hust-latex/hustproposal](https://github.com/hust-latex/hustproposal): 대학 프로젝트 제안서 LaTeX 템플릿.
- [donbr Discovery Phase & Project Proposal Template](https://gist.github.com/donbr/4571c74763f8fb55873e76381d937c17): 고객 이해, 현재 상태, 목표, 접근법 중심의 짧은 Markdown 구조.
- [dims TCE proposal template](https://gist.github.com/dims/b9cd0c191c785292a8efad34030faf48): 목표·비목표, 요구사항, 보안, 위험, 대안, 전환 전략이 포함된 기술 제안 구조.
- [nelsonenzo Technical Spec Markdown Template](https://gist.github.com/nelsonenzo/070eadaa8babdf57f56c201525cda9f5): 기술 제안/설계 문서 구조 참고.

Gist는 저장소보다 변경 관리·릴리스·라이선스가 불명확할 수 있으므로 내용을 복제하기 전에 원저작자의 라이선스를 별도로 확인한다.

## 6. 추천 채택 범위

현재 만들려는 스킬에는 다음만 우선 채택하면 충분하다.

1. `ProposalForce`: 질문·응답·근거·상태 데이터 모델 참고
2. `python-docx-template`: 회사 DOCX 템플릿 채우기
3. `python-docx`: 필요한 최소 후처리와 검증
4. `Vale`: 규칙이 누적된 뒤 문체·용어 자동검사

Pandoc·Quarto·RAG·다중 에이전트는 현재 필수 요건이 아니다. 원본을 Markdown으로 관리해야 하거나, 답변 지식베이스가 커져 수동 검색이 실제 병목이 될 때 추가한다.

## 7. 도입 전 확인 항목

- 저장소 라이선스가 사내 수정·배포 방식과 맞는지
- 최근 릴리스와 유지보수 상태
- DOCX의 한글 글꼴, 표, 머리말·꼬리말, 섹션, PDF 변환 보존 여부
- RFP와 과거 제안서가 외부 API로 전송되지 않는지
- 생성 문구마다 출처, 기준일, 제품 버전, 검토자를 남길 수 있는지
- 자동 생성 결과를 Word와 PDF로 렌더링해 검수할 수 있는지
