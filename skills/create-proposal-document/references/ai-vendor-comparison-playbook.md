# Comparing AI vendors and models for a decision-maker (playbook and 2026-11-12 snapshot)

Use when a proposal, briefing or sample deck compares AI model families or vendors (for example OpenAI GPT and
Anthropic Claude): what each pursues, price, rules, strengths and caveats. Model names, prices and rules here change
within weeks. Treat section 6 as a dated snapshot and rerun section 2 before quoting any number.

## 1. Rules that held up

1. **Only the vendors' own documentation supplies numbers.** Third-party blogs disagreed with each other on version
   names and prices in the same week. Do not mix them in; list them as excluded.
2. **Date every figure.** Put the as-of date in the lead or footer of each slide that carries a number.
3. **Say when a page was read through a summarizing tool**, or when the primary page was blocked (HTTP 403). A search
   snippet is a pointer, not a source.
4. **Do not pair models and claim parity.** Pair by rank only if you say so, and chart price on one axis sorted by
   price. Tier names across vendors are not equivalent.
5. **Disclose the author's interest** when the author is a model from one of the vendors, and balance the item set so
   each side leads on several items.
6. **No benchmark scores** unless the source, date and method are on the slide and the test is reproducible.
7. **Absence of evidence is not a "no".** Write "not verified in this research" and list it on the limits slide.

## 2. Verification workflow

For each vendor, read in this order and record the URL and date:

1. Models overview: names, one-line positioning, context window, maximum output, base price, retirement commitments.
2. Pricing page: cache read/write multipliers, batch discount, long-context rule (threshold and what is multiplied,
   or "not stated"), speed tiers, data-residency multiplier.
3. One flagship model page: supported tools and features, rate-limit tiers, cloud availability, deprecation info.
4. Data handling page: retention default, training default, zero data retention eligibility, region table.
5. Company page for mission and legal structure (paraphrase; never quote marketing text).

Write what you could not read in the limits slide: blocked pages, plans pages without an official price, unstated rules.

## 3. What to compare (ten items that were decision-relevant)

Flagship input price; light-tier input price; long-context price rule; cloud routes; model lifetime disclosure; the
shared tool set (search, code, computer use); speed options; image-generation tool; voice and transcription models;
in-country data storage. Choose items so each vendor leads on about as many as the other, and show ties as ties.

## 4. Cost model on one slide

`cost = uncached_input x input_price + cached_input x cache_read_price + output x output_price`, per million tokens.
State the scenario (for example 100 M input of which 80% hits the cache, 10 M output), list-price basis and what is
excluded (cache writes, batch, speed tier, residency surcharge). In the snapshot scenario output was 64 to 69 percent
of the total for all eight models, so the actionable line was "check output length before switching model".

## 5. Korea checklist (data location)

- Separate **storage at rest** from **inference location**; vendors differ on each and may offer one without the other.
- Name the endpoint or parameter that sets the region, the models it covers and any surcharge.
- Retention default, training default and zero-data-retention eligibility each get a row.
- Cloud-marketplace routes (Bedrock, Google Cloud, Foundry) follow the cloud's region rules, not the vendor's own
  API rules; mark them "not verified" unless read.
- Add: "이 자료는 법률 자문이 아닙니다. 개인정보 국외 이전 해당 여부는 법무 검토가 필요합니다."

## 6. Snapshot as of 2026-11-12 (re-verify before use)

Sources: platform.claude.com/docs (models overview, pricing, data residency, choosing a model),
developers.openai.com/api/docs (models, pricing, GPT-6 Astra page, your-data), anthropic.com/company.
Prices are USD per million tokens, input / output.

| Family | Model | Price | Positioning (vendor wording, paraphrased) |
|---|---|---|---|
| OpenAI | GPT-6 Astra | 10 / 50 | hardest work, flagship |
| OpenAI | GPT-6.1 Sol | 2 / 10 | near Astra at lower cost |
| OpenAI | GPT-6.1 Terra | 1 / 5 | fast and efficient; visual reasoning, computer use, natural writing |
| OpenAI | GPT-6 Luna | 0.1 / 0.5 | economical, focused high-volume tasks |
| Anthropic | Claude Fable 5.2 | 8 / 40 | demanding reasoning and long-horizon agent work; most capable generally available |
| Anthropic | Claude Opus 5.5 | 4 / 20 | long-running agentic coding and knowledge work; start here for most workloads |
| Anthropic | Claude Sonnet 5.5 | 2 / 10 | speed and intelligence together |
| Anthropic | Claude Haiku 5.5 | 0.10 / 0.50 up to a 100K prompt, higher above (input 0.50) | high-volume, low-latency tasks |

Common: context about 1M tokens (OpenAI 1.05M with 922K maximum input; Claude 1M), maximum output 128K.
Claude Mythos 5.2 is limited to verified organizations and was left out.

Rules that differed:

- **Long context.** OpenAI: above 272K input tokens, input is 2x and output 1.5x (whether the whole request or only
  the excess is not stated). Claude: the full 1M window at the standard rate, except Haiku 5.5 above 100K.
- **Batch.** 50% on both. **Cache reads.** OpenAI 5 to 10% of input price; Claude 2.5% (Fable 5.2), 5% (Opus 5.5,
  Sonnet 5.5), 10% (others).
- **Speed.** OpenAI Fast 2x (all four) and Ultrafast 6x (Astra, Sol). Claude fast mode 2x on Fable 5.2 and
  Opus 5.5, not available with batch.
- **Tools.** Both: web search, code execution, computer use, text and image input, text output. OpenAI also lists an
  image-generation tool and dedicated voice and transcription models; Claude's lineup lists neither.
- **Cloud routes.** OpenAI: Bedrock, Google Cloud (private preview for Astra); Azure not verified. Claude: Claude API,
  Bedrock, Google Cloud, Microsoft Foundry, Claude Platform on AWS.
- **Lifetime.** Claude publishes minimum availability dates (Fable 5.2 not before 2027-11-09, Opus 5.5 2027-09-22,
  Sonnet 5.5 2027-09-28, Haiku 5.5 2027-10-07). The OpenAI Astra page lists none.
- **Data location.** OpenAI: regional storage in ten regions including South Korea (`kr.api.openai.com`); regional
  processing in the US, Europe and UAE, and for some models in Australia, Japan and India; South Korea stores
  in-region but does not process in-region. Claude (own API): `inference_geo` is `us` or `global`, workspace geo is
  `us` only, US-only inference costs 1.1x. OpenAI regional endpoints add about 10% (applicability to these models not
  verified). Retention: OpenAI abuse-monitoring logs up to 30 days, no training on API data by default, zero data
  retention by approval; Claude is eligible for zero data retention (covered models excluded) and HIPAA readiness.
- **Mission and structure.** OpenAI: nonprofit OpenAI Foundation and for-profit OpenAI Group share the mission that AGI
  benefits all of humanity. Anthropic: public benefit corporation with a Long-Term Benefit Trust; mission is the
  responsible development of advanced AI for long-term human benefit.

Not verified and therefore left out: ChatGPT subscription prices (official page blocked; secondary sources conflict),
OpenAI on Azure, the scope of OpenAI's long-context surcharge, Claude's MCP support scope.

## 7. Reference implementation

`assets/examples/ai-model-comparison/make_deck.py` renders this comparison as 17 slides with the patterns in
`editorial-deck-design.md`. Its figures are the section 6 snapshot; update both together.
