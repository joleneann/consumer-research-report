# Consumer Research Report Generator

Turn a research brief into a scored, client-ready consumer research report.

Given a brand, category, geography, and business questions, the pipeline collects evidence from online sources, normalizes it into a shared schema, filters for relevance, analyzes sentiment and themes, scores confidence from data, and generates a versioned DOCX deliverable.

## Evaluation

**This repo does not bundle commercial data, funded API credentials, or a free turnkey demo run.** Running it requires your own API keys and your own data.

There are two ways to evaluate it:

### Path A: Inspect the outcomes (no setup needed)

Go to [`examples/outcomes/`](examples/outcomes/). Four complete studies are there:

| Study | Items | Insights | NSS | Report |
|-------|-------|----------|-----|--------|
| [Weight Loss in India](examples/outcomes/weight_loss/) | 2,526 | 15 | +22.9% | DOCX |
| [Make in India](examples/outcomes/make_in_india/) | 5,814 | 16 | +15.9% | DOCX |
| [Thums Up (brand)](examples/outcomes/thums_up/) | 472 | 12 | +10.4% | DOCX |
| [Mosquito Repellent](examples/outcomes/mosquito_repellent/) | 5,391 | 18 | +29.5% | DOCX |

Each folder has the research brief, a study README, the final DOCX report, and a manifest of what the pipeline produced.

Open any DOCX to see the full deliverable: executive summary, theme landscape, per-insight deep dives with radar charts, brand health score, and methodology disclosure.

### Path B: Run it with your own data and credentials

See [What you need](#what-you-need-to-run-this) below, then [Quick Start](#quick-start).

---

## What This Does

- Accepts a brief: brand, category, geography, competitors, business questions
- Collects from Reddit, YouTube, NewsData.io, OpenAlex, Google Trends, Serper — or ingests any pre-collected JSON
- Normalizes all sources into a common schema with deterministic SHA-256 item IDs
- Filters irrelevant content using LLM classification (multilingual, handles Hindi/Hinglish)
- Extracts themes inductively from the corpus using a two-pass LLM approach — no predefined keyword lists
- Synthesizes one structured insight per theme (Observation / Insight / Implication / Recommendation)
- Scores each insight with data-driven confidence and signal metrics — no LLM judgment in scoring
- Generates charts and a versioned DOCX report

Themes emerge from the data. If consumers are discussing something the brief never anticipated — a cultural reference, a misinformation narrative, an untracked quality perception — it surfaces.

---

## What You Need to Run This

**Required:**

| Requirement | What it's for |
|-------------|---------------|
| `ANTHROPIC_API_KEY` | LLM analysis (filter, themes, synthesis). ~$1-2 per run. Key must be from the Default workspace at console.anthropic.com, not the Claude Code workspace. |
| Python 3.11+ | Runtime |
| Data | Either your own pre-collected JSON, or API keys for the built-in collectors |

**Optional collectors (all fail gracefully if absent):**

| Key | Source | Free tier |
|-----|--------|-----------|
| `YOUTUBE_API_KEY` | YouTube comments | 10K quota/day |
| `NEWSDATA_API_KEY` | News articles | 200 credits/day |
| `SERPER_API_KEY` | Web search results | 2,500 queries total |

Reddit, OpenAlex, and Google Trends are free with no key.

**Bring your own data:** If you have pre-collected data in any JSON format (Twitter exports, Instagram scrapes, vendor feeds), the pipeline ingests it directly. See [`docs/running_with_your_own_data.md`](docs/running_with_your_own_data.md).

---

## Quick Start

```bash
git clone https://github.com/joleneann/consumer-research-report.git
cd consumer-research-report
pip install -r requirements.txt
```

**Option 1: Run with pre-collected data**

```bash
# See examples/studies/weight_loss/run_weight_loss.py as a template
python examples/studies/weight_loss/run_weight_loss.py
```

**Option 2: Run the full pipeline with built-in collectors**

```bash
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

python -m consumer_research.run \
  --brand "Brand Name" \
  --category "Product Category" \
  --geo IN \
  --objectives "What do consumers think about quality?"
```

**Re-score and regenerate from an existing run (no API calls needed)**

```bash
python scripts/stage6_7_score_report.py [run_id]
python scripts/regenerate_report.py [run_id]
```

---

## Pipeline

```
Brief -> Collect -> Normalize -> Filter -> Analyze -> Synthesize -> Score -> Report
  [0]      [1]        [2]         [3]       [4]         [5]          [6]      [7]
```

Every stage writes artifacts to `consumer_research/runs/<run_id>/`. If the pipeline fails, resume from the last completed stage — no re-collection, no wasted API calls.

| Stage | What it does | Output |
|-------|-------------|--------|
| 0. Brief | Structure the research question | `brief.json` |
| 1. Collect | Pull from 6+ sources at max limits | `raw/*.json` |
| 2. Normalize | Deduplicate, engagement filter, common format | `normalized/corpus.json` |
| 3. Filter | LLM relevance classification (multilingual) | `filtered/corpus.json` |
| 4. Analyze | Sentiment, Plutchik emotion, ABSA, two-pass theme extraction | `analysis/results.json` |
| 5. Synthesize | One insight per theme | `insights/insights.json` |
| 6. Score | Confidence (5 factors) + Signal Strength (4 factors) + Brand Health | `scored/scored_insights.json` |
| 7. Report | Charts + DOCX report | `report/report_v###.docx` |

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

```
consumer_research/     Core package: collectors, pipeline stages, report generation
tests/                 Unit tests (no API calls required)
docs/                  Methodology, product documentation, running guide
examples/
  outcomes/            Four complete study outcomes with reports and briefs
  briefs/              Input brief JSONs for each study
  studies/             Study-specific runner scripts
scripts/               Utility scripts: resume, re-score, regenerate report
```

---

## Documentation

- [`CLAUDE.md`](CLAUDE.md) — Architecture, procedures, failure modes (developer reference)
- [`docs/methodology.docx`](docs/methodology.docx) — Research methodology (client-facing)
- [`docs/product_documentation.docx`](docs/product_documentation.docx) — Product guide
- [`docs/running_with_your_own_data.md`](docs/running_with_your_own_data.md) — Bring-your-own-data guide

---

## Known Limitations

Social listening methodology has structural limitations that cannot be fully eliminated:

- **Query framing bias**: Keywords presuppose contexts. You find what you search for.
- **Platform demographic bias**: Reddit skews male/urban. YouTube skews extreme reactions. No demographic weighting applied.
- **No sampling frame**: Prevalence is meaningful within the corpus only — never projectable to the general population.
- **Engagement filter**: Minimum upvote/like thresholds exclude moderate consumers and over-index on extreme sentiment.
- **No demographic data**: No platform provides verified age, gender, or location. Any demographic inference is speculative.
- **Language gaps**: English and Hindi/Hinglish supported. Tamil, Telugu, Bengali, Marathi, Kannada are not.

For the full list of 12 documented limitations with mitigation strategies, see the Methodology section in any generated report.

---

## License

MIT
