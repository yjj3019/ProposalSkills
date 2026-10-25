# Public Git repository research for proposal work

Checked: 2026-07-18
Scope: public GitHub repositories directly/indirectly useful for corporate/public proposals, RFP responses,
DOCX/PDF generation, automated style rules, and generic proposal structures.
This is not an exhaustive list of all GitHub repositories; it collects relevant searchable repositories.

## 1. Repositories to review first

| Repository | Purpose | Adoption assessment |
|---|---|---|
| [SalesforceLabs/ProposalForce](https://github.com/SalesforceLabs/ProposalForce) | RFP questions/answers/owners/status/knowledge base, CSV/DOCX export | Most direct reference for RFP response data models/workflows. BSD-3-Clause |
| [elapouya/python-docx-template](https://github.com/elapouya/python-docx-template) | Generate DOCX using Jinja-style tags in Word templates | Suitable for content filling while preserving company DOCX format. LGPL-2.1 |
| [python-openxml/python-docx](https://github.com/python-openxml/python-docx) | Read/generate/edit DOCX | Use for detailed table/heading/paragraph/image postprocessing |
| [jgm/pandoc](https://github.com/jgm/pandoc) | Markdown→DOCX/PDF, `reference.docx` | Reproducible pipeline separating text/styles |
| [quarto-dev/quarto-cli](https://github.com/quarto-dev/quarto-cli) | Pandoc-based technical publishing, cross-references/citations/code output | Useful for proposals rich in tables/charts/technical analysis. MIT |
| [vale-cli/vale](https://github.com/vale-cli/vale) | YAML style/terminology/spelling checks | Best fit for banned terms/approved terminology/overclaims. MIT |

Minimum implementation: `python-docx-template` + existing DOCX template.
Add Pandoc/Quarto only for Markdown source management; add Vale when style checking actually repeats.

## 2. RFP/response automation references

The GitHub [`rfp-automation` topic](https://github.com/topics/rfp-automation) showed 9 public repositories
as of 2026-07-18. Most are early projects with few stars/use records: treat them as feature-comparison/experiment
references rather than adopting code/architecture directly.

| Repository | Confirmed features | Caution |
|---|---|---|
| [AnshMNSoni/B2B-RFP-Agent](https://github.com/AnshMNSoni/B2B-RFP-Agent) | Manufacturing RFP processing/quotes | Industry-specific |
| [jabessouguie/consulting-tools](https://github.com/jabessouguie/consulting-tools) | Consulting proposals/Slides automation | Broad scope; reference only needed parts |
| [GideonLartey/wash-rfp-backend](https://github.com/GideonLartey/wash-rfp-backend) | PDF parsing/generative-AI NGO RFP backend | Explicitly a demo, unrelated to any specific NGO |
| [degerahmet/q-flow](https://github.com/degerahmet/q-flow) | RAG/security questionnaires/RFP answers/human review/Excel preservation | Valuable knowledge-search/review flow |
| [Parth-Gochhwal/RFP-IGNITE](https://github.com/Parth-Gochhwal/RFP-IGNITE) | Sales/technical/pricing agents + human-in-the-loop | Multiagent complexity unnecessary for this skill |
| [Satyapraveenv/ai-rfp-response-generator](https://github.com/Satyapraveenv/ai-rfp-response-generator) | Context extraction/scoring/narrative generation | Small early project |
| [Pankajkantghz/rfp-agent](https://github.com/Pankajkantghz/rfp-agent) | MERN RFP agent | Limited description/validation |
| [bhargavhari2001-cloud/BidCraft](https://github.com/bhargavhari2001-cloud/BidCraft) | Question extraction/knowledge matching/confidence scores | Recent early project |
| [sridivya9398/AutoProposal](https://github.com/sridivya9398/AutoProposal) | Agentic workflow/GraphRAG RFP-security responses | Recent early project |

Additional repositories:

- [VaultaFoundation/grant-framework](https://github.com/VaultaFoundation/grant-framework): proposal/maintenance-support/RFP-response types and review workflow.
- [open-agreements/open-agreements](https://github.com/open-agreements/open-agreements): not proposals, but a useful standard-document→DOCX and per-template source/license model.

## 3. Style and terminology automation

| Repository | Useful aspects |
|---|---|
| [vale-cli/Microsoft](https://github.com/vale-cli/Microsoft) | Microsoft Writing Style Guide as Vale rules; English technical proposal reference |
| [vale-cli/Google](https://github.com/vale-cli/Google) | Google developer-document style as Vale rules |
| [vale-cli/write-good](https://github.com/vale-cli/write-good) | English passive-voice/verbosity checks |
| [vale-cli/proselint](https://github.com/vale-cli/proselint) | Vale implementation of proselint rules |
| [redhat-documentation/vale-at-red-hat](https://github.com/redhat-documentation/vale-at-red-hat) | Organizational style-rule adoption/operations |
| [elastic/vale-rules](https://github.com/elastic/vale-rules) | Organizational rules/exceptions/GitHub Actions |
| [vale-cli/vale-action](https://github.com/vale-cli/vale-action) | Automated style checks in GitHub Actions |
| [testthedocs/awesome-docs](https://github.com/testthedocs/awesome-docs) | Accessibility/major technical style-guide links |

Do not apply English rules unchanged to Korean proposals. Reference structures/check types and independently
write company glossaries/banned terms/number-product notation rules.

## 4. DOCX/PDF generation and templates

| Repository | Purpose | Assessment |
|---|---|---|
| [mherkazandjian/docxsphinx](https://github.com/mherkazandjian/docxsphinx) | Sphinx→Word template styles | Only when substantial technical documents already use Sphinx |
| [JessicaTegner/pypandoc](https://github.com/JessicaTegner/pypandoc) | Call Pandoc from Python | Only when a Python pipeline needs Pandoc |
| [pandoc/lua-filters](https://github.com/pandoc/lua-filters) | Pandoc conversion filters | Reference for cross-references/tables/special transformations |
| [jvsteiner/pandoc-obsidian-templates](https://github.com/jvsteiner/pandoc-obsidian-templates) | Pandoc templates/DOCX examples | Style experiments |
| [TomBener/pandoc-templates](https://github.com/TomBener/pandoc-templates) | Markdown→DOCX/PDF templates | Archived; no direct dependency. MIT |
| [DonnC/docxtpl](https://github.com/DonnC/docxtpl) | Flutter DOCX tag substitution | Archived 2025-12-08; do not confuse with Python namesake |

## 5. Proposal structure/design templates

These differ from corporate RFP proposals; reference outlines/variables/visual composition only.

- [UBC-STAT/proposal-template](https://github.com/UBC-STAT/proposal-template): statistics research LaTeX proposal.
- [r02b/Latex-PhD_Proposal_Template](https://github.com/r02b/Latex-PhD_Proposal_Template): simple doctoral research class. MIT.
- [YimianDai/iNSFC](https://github.com/YimianDai/iNSFC): unofficial 2026 Chinese NSFC LaTeX template; verify official submission format.
- [hust-latex/hustproposal](https://github.com/hust-latex/hustproposal): university project-proposal LaTeX template.
- [donbr Discovery Phase & Project Proposal Template](https://gist.github.com/donbr/4571c74763f8fb55873e76381d937c17): short Markdown structure around customer understanding/current state/goals/approach.
- [dims TCE proposal template](https://gist.github.com/dims/b9cd0c191c785292a8efad34030faf48): goals/non-goals/requirements/security/risks/alternatives/transition strategy.
- [nelsonenzo Technical Spec Markdown Template](https://gist.github.com/nelsonenzo/070eadaa8babdf57f56c201525cda9f5): technical proposal/design structure.

Gist change management/releases/licenses can be less clear than repositories; verify author licensing before copying.

## 6. Recommended adoption scope

For the skill being designed, prioritize only:

1. `ProposalForce`: question/answer/evidence/status data model.
2. `python-docx-template`: company DOCX template filling.
3. `python-docx`: minimum necessary postprocessing/validation.
4. `Vale`: style/terminology checks once rules accumulate.

Pandoc/Quarto/RAG/multiagent systems are not current prerequisites.
Add only when Markdown source management is needed or a large answer library makes manual search a real bottleneck.

## 7. Pre-adoption checks

- License fits internal modification/distribution.
- Recent releases/maintenance state.
- Korean fonts/tables/headers-footers/sections/PDF conversion preserved.
- RFPs/previous proposals are not transmitted to external APIs.
- Each generated claim can retain source/as-of date/product version/reviewer.
- Generated output can be inspected through Word/PDF rendering.

## 7. 2026-09 proposal-skill repository benchmark

Checked: 2026-09-16. Public repositories implementing proposal/bid work as agent skills.
Referenced concepts only; no sentences/code/scoring models imported. Boundaries:
[external-method-boundaries.md](../skills/create-best-proposal/references/external-method-boundaries.md).

| Repository | Referenced concepts | Adoption | License |
|---|---|---|---|
| [danielkinneyspears/federal-proposal-skills](https://github.com/danielkinneyspears/federal-proposal-skills) | Preliminary capture, commitment audits, review discipline | Capture memo (Pink inputs), ambiguous-commitment warning | Apache-2.0 |
| [chakmarebel/federal-proposal-copilot](https://github.com/chakmarebel/federal-proposal-copilot) | Calibration corpus comparing AI draft/final submission, evidence-check stages | Deferred (below) | MIT |
| [yanhaoluo0/technical-proposal-expert-writing-skill](https://github.com/yanhaoluo0/technical-proposal-expert-writing-skill) | Mandatory prewriting technical questions | Six technical-depth questions (independently worded) | Unspecified; concepts only |
| [AIScientists-Dev/academic-humanizer](https://github.com/AIScientists-Dev/academic-humanizer) | AI-style categories/overcorrection prevention | Existing `AI_SLOP` rules suffice; no addition | Unclear; concepts only |
| [jackson-marcus/Bid-Craft](https://github.com/jackson-marcus/Bid-Craft) | Incremental amendments/clause-number change tracking | Deferred (below) | Unspecified; concepts only |

Not adopted:

- Splitting into 20+ skills conflicts with flagship entry routing.
- US federal procurement rules (FAR, Section L/M, CPARS), Price-to-Win, win-probability models.
- Blocking submission for ambiguous overcommitment: retain nonblocking warnings until false positives are validated.

Reviewed and deferred (next-stage candidates):

- Calibration corpus: classify AI draft/final differences into candidate rules. First prevent real data entering the public repository.
- Incremental amendment diff: retain clause IDs/change history. Current tools provide only source order/stale sweep.
- Working-folder git tracking check: bootstrap check for tracked user RFP/proposal files. Current coverage is repository hygiene tests only.
