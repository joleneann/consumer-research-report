# Brand or Topic Sentiment Report Generator

Turn a research brief concerning a brand or a broad topic into a scored, client-ready consumer research report.

Given a brand or topic, category, geography, and business questions, the pipeline collects evidence from online sources, normalizes it into a shared schema, filters for relevance, analyzes sentiment and themes, scores confidence from data, and generates a versioned DOCX deliverable.

## Evaluation

**This repo does not bundle commercial data, funded API credentials, or a free turnkey demo run.** Running it requires your own API keys and your own data.

There are two ways to evaluate it:

### Path A: Inspect the outcomes (no setup needed)

Go to [`examples/outcomes/`](examples/outcomes/). Four complete studies are there.

**[UK Weight Loss Medication, 30-Day Conversation Study](examples/outcomes/uk_weight_loss/)**

30 days of UK conversation about weight loss medication: Reddit r/MounjaroUK and r/WegovyUK, Mumsnet, and UK news, collected 7 July to 6 August 2026. 12,450 items collected, 10,890 classified, 15 themes discovered inductively from the corpus, $9.70 in collection cost.

The 400 news articles sit in the corpus to be compared against, not counted with, so every theme carries two shares: how much of press output it takes, and how much of patient conversation.

| Theme | Patient conversation | Press output |
|---|---|---|
| The weekly weigh-in ritual | 21.7% | 0.2% |
| Dose titration and click-counting | 21.6% | 0.8% |
| Hair loss | 0.8% | 7.0% |
| Business and policy | 1.1% | 85.2% |

85.2% of press output is about companies, share prices, approvals and policy. That subject is 1.1% of patient conversation, and the two largest things in patients' lives get almost no coverage.

**The other three**

| Study | Type | Items | Insights | NSS |
|-------|------|-------|----------|-----|
| [India Hair Colour](examples/outcomes/hair_colour/) | Topic | 8,969 | 16 | +22.3% |
| [Make in India](examples/outcomes/make_in_india/) | Brand | 3,516 | 12 | +24.0% |
| [Weight Loss Medication in India](examples/outcomes/weight_loss/) | Topic | 2,484 | 12 | +16.8% |

Each folder has a study README, the final DOCX report, a manifest of what the pipeline produced, and the item-level workbook the report is built from, one tab per theme, so any figure can be traced back to the items behind it. The research brief sits either in the study folder or in [`examples/briefs/`](examples/briefs/), and each study README links its own.

Open any DOCX to see the full deliverable: executive summary, theme landscape, per-insight deep dives with radar charts, brand health score, and methodology disclosure.

### Path B: Run it with your own data and credentials

See [What you need](#what-you-need-to-run-this) below, then [Quick Start](#quick-start).

---

## What This Does

- Accepts a brief: brand, category, geography, competitors, business questions
- Collects from Reddit, YouTube, NewsData.io, OpenAlex, Google Trends, Serper - or ingests any pre-collected JSON
- Normalizes all sources into a common schema with deterministic SHA-256 item IDs
- Filters irrelevant content using LLM classification (multilingual, handles Hindi/Hinglish)
- Extracts themes inductively from the corpus using a two-pass LLM approach - no predefined keyword lists
- Synthesizes one structured insight per theme (Observation / Insight / Implication / Recommendation)
- Scores each insight with data-driven confidence and signal metrics - no LLM judgment in scoring
- Generates charts and a versioned DOCX report

Themes emerge from the data. If consumers are discussing something the brief never anticipated - a cultural reference, a misinformation narrative, an untracked quality perception - it surfaces.

---

## What You Need to Run This

**Required:**

| Requirement | What it's for |
|-------------|---------------|
| Python 3.11+ | Runtime |
| Data | Your own pre-collected JSON, or API keys for the built-in collectors |

**How analysis runs - two workflows:**

The codebase supports two workflows for Stages 3-5 (filter, analyze, synthesize). Both produce the same output.

| Workflow | What does the LLM work | Cost | When to use |
|----------|----------------------|------|-------------|
| **In-context** (Claude Code session) | The Claude Code session itself reads items and writes classifications directly to disk | Included in your Claude Code / Claude Max subscription | Primary workflow. All four published studies were produced this way. |
| **Automated pipeline** (`consumer-research run`) | External API calls via `ANTHROPIC_API_KEY` through `utils/llm_client.py` | ~$1-2 per run | Unattended batch runs without a Claude Code session open. |

Stages 0-2 (brief, collect, normalize) and 6-7 (score, report) are code-based and free in both workflows.

**Optional collector API keys (all fail gracefully if absent):**

| Key | Source | Free tier |
|-----|--------|-----------|
| `YOUTUBE_API_KEY` | YouTube comments | 10K quota/day |
| `NEWSDATA_API_KEY` | News articles | 200 credits/day |
| `SERPER_API_KEY` | Web search results | 2,500 queries total |

Reddit, OpenAlex, and Google Trends are free with no key.

**Bring your own data:** If you have pre-collected data in any JSON format (Twitter exports, Instagram scrapes, vendor feeds), the pipeline ingests it directly via `consumer-research ingest`. See [`docs/running_with_your_own_data.md`](docs/running_with_your_own_data.md).

---

## Quick Start

```bash
git clone https://github.com/joleneann/sentiment-research-report.git
cd sentiment-research-report
pip install -r requirements.txt
```

**Option 1: Bring your own data (no API keys needed)**

```bash
pip install -e .

# Ingest your JSON into a run directory (Stages 0-2)
consumer-research ingest \
  --data data/my_collected_data.json \
  --brand "Brand Name" \
  --category "Product Category"

# Stages 3-5 run in your Claude Code session (in-context analysis)
# Stage 6-7: score and generate the DOCX report
consumer-research score-report [run_id]
```

**Option 2: Run the full automated pipeline (requires ANTHROPIC_API_KEY)**

```bash
consumer-research run \
  --brand "Brand Name" \
  --category "Product Category" \
  --geo IN \
  --objectives "What do consumers think about quality?"
```

**Regenerate a report from an existing run**

```bash
consumer-research regenerate [run_id]
```

---

## Pipeline

Eight stages, each writing artifacts to `runs/<run_id>/`. If the pipeline fails, resume from the last completed stage.

0. **Brief** - structure the research question
1. **Collect** - pull from 6+ sources at max limits (or ingest your own JSON)
2. **Normalize** - deduplicate, engagement filter, common schema
3. **Filter** - LLM relevance classification (multilingual)
4. **Analyze** - sentiment, Plutchik emotion, ABSA, two-pass theme extraction, narrative review
5. **Synthesize** - one structured insight per theme (via dedicated skill with fresh context window)
6. **Score** - confidence (5 factors) + signal strength (4 factors) + brand health
7. **Report** - charts + versioned DOCX

---

## Scoring

Every insight receives two independent scores, both computed entirely from data:

**Confidence** (how sure we are this is real):
- Sample size (log-scaled relative to corpus)
- Source diversity (Herfindahl index with balance penalty)
- Temporal consistency (evenness across time quartiles)
- Internal agreement (sentiment consensus)
- Data recency (exponential decay)

**Signal Strength** (how loud this is in the data):
- Prevalence (% of corpus)
- Engagement level (percentile-ranked across insights)
- Sentiment intensity
- Conversation depth

Insights are ranked by confidence (primary) and signal strength (tiebreaker). Both scores shown as percentages in the report.

**Brand Health Score** (0-100): Sentiment (30%) + Engagement (25%) + Advocacy (20%) + Resilience (15%) + Conversation (10%).

---

## Project Structure

There are three layers. Each has a different purpose.

**Product interface** - the packaged CLI:

```
consumer-research ingest        Ingest external JSON data (Stages 0-2)
consumer-research run           Full automated pipeline (Stages 0-7, requires API key)
consumer-research score-report  Re-score + regenerate report (no API)
consumer-research regenerate    Regenerate DOCX only (no API)
```

This is the canonical way to use the system. Installed via `pip install -e .`.

**Analysis skills** - Claude Code skills for LLM-intensive stages:

```
skills/
  narrative-review.md             Stage 4c: discover narrative patterns keywords miss
  synthesize.md                   Stage 5: generate decision-grade insights per theme
```

These run as sub-agents with fresh context windows during in-context analysis. Each takes a `run_id` and reads config dynamically - works for any study. The synthesis skill produces measurably better insights than in-context synthesis (validated in a controlled experiment comparing output quality across 12 themes).

**Operator tools** - recovery and maintenance scripts:

```
scripts/resume_stage3.py        Resume pipeline from Stage 3
scripts/resume_stage4.py        Resume pipeline from Stage 4
scripts/rescore.py              Re-score insights from a specific run
scripts/resynthesize.py         Re-run synthesis + scoring
scripts/fix_quotes.py           Fix representative quotes per theme
scripts/add_narrative_themes.py Add narrative themes missed by keyword pass
scripts/export_to_excel.py      Export run data to Excel
```

These are for operators recovering from failures or re-running specific stages on existing data. They accept run IDs as arguments and load config from the run's own `config.json`.

**Example study workflows** - demonstrations of completed research:

```
examples/outcomes/              Four complete studies with DOCX reports
examples/briefs/                Research brief JSONs
examples/studies/weight_loss/   Study-specific analysis scripts
```

The study scripts (`run_weight_loss.py`, `stage4_analysis.py`, `stage5_synthesis.py`) are intentionally custom - they show how a specific study was conducted, not how to build a generic pipeline. Evaluate the product through the CLI and the outcomes, not through the study scripts.

**Source code:**

```
consumer_research/              Core package: collectors, pipeline, report generation
tests/                          Unit + smoke + integration tests (126 tests, no API calls)
docs/                           Methodology, product docs, running guide
```

---

## Documentation

- [`CLAUDE.md`](CLAUDE.md) - Architecture, procedures, failure modes (developer reference)
- [`docs/methodology.docx`](docs/methodology.docx) - Research methodology (client-facing)
- [`docs/product_documentation.docx`](docs/product_documentation.docx) - Product guide
- [`docs/running_with_your_own_data.md`](docs/running_with_your_own_data.md) - Bring-your-own-data guide

---

## Known Limitations

Social listening methodology has structural limitations that cannot be fully eliminated:

| # | Limitation | Severity | Fixable? | Status |
|---|-----------|----------|----------|--------|
| 1 | **Query framing bias** - You find what you search for. No adversarial queries. | CRITICAL | Partially | Not implemented |
| 2 | **Platform demographic bias** - No weighting for platform skew. | MEDIUM | Partially | Not implemented |
| 3 | **No sampling frame** - Prevalence is within-corpus only, never projectable. | HIGH | No | Inherent limitation |
| 4 | **Engagement filter excludes silent majority** - Hard thresholds removed. Collectors still fetch visibility-ranked content from platforms. | MEDIUM | Partially | **MITIGATED** |
| 5 | **No bot/astroturf detection** - Zero coordinated campaign detection. | MEDIUM | Yes | Not implemented |
| 6 | **Sarcasm/irony misclassification** - Keyword mode reads sarcasm as literal. | MEDIUM | Partially | Not implemented |
| 7 | **Influencer vs authentic voice conflated** - No sponsored content detection. | MEDIUM | Yes | Not implemented |
| 8 | **Near-duplicate inflation** - Paraphrases not caught by SHA-256 dedup. | LOW | Yes | Not implemented |
| 9 | **Language classification accuracy unvalidated** - LLM processes any language but accuracy only validated on English/Hindi. | LOW | Yes | Not implemented |
| 10 | **No temporal weighting in theme extraction** - Old viral threads count equally. | LOW | Yes | Not implemented |
| 11 | **Cross-theme interactions not surfaced** - Multi-coded items split, never analysed jointly. | MEDIUM | Yes | Not implemented |
| 12 | **No reliable demographic data** - No verified age, gender, or location from any platform. | CRITICAL | No | Inherent limitation |
| 13 | **LLM non-determinism in theme extraction** - Same corpus can produce slightly different themes across runs due to model inference variance. | MEDIUM | Partially | **MITIGATED** |
| 14 | **Geographic relevance not verified** - No verified geolocation; 2-3% of corpus from non-target markets. | LOW | Partially | Not implemented |

Full details with "How to Fix" column in [`CLAUDE.md`](CLAUDE.md).

---

## License

MIT
