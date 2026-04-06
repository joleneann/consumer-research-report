# Consumer Research Report Generator

**Enterprise-grade brand perception analysis from social listening data.**

Turn a research brief into a comprehensive DOCX report in hours, not weeks. Collects data from Reddit, YouTube, News, Academic sources, Google Trends, and web search. Discovers themes inductively from the corpus — no predefined hypotheses, no keyword dashboards. The pipeline finds what consumers are actually talking about.

## Why This Matters

Traditional consumer research costs $50-200K per study and takes 6-8 weeks. Social listening dashboards track keywords but don't generate insights. This pipeline bridges the gap: it collects real consumer voices at scale, applies rigorous analytical methodology, and produces a report that reads like it came from a research agency.

**What makes it different from a social listening dashboard:**
- Themes emerge from the data, not from predefined keyword lists
- Every insight includes observation, consumer meaning, business implication, and recommendation
- Scoring is fully data-driven — confidence and signal strength computed from 9 statistical factors
- The report is a flowing DOCX document, not a dashboard screenshot

## Sample Output

See [`sample-reports/Weight_Loss_India_Consumer_Sentiment.docx`](sample-reports/Weight_Loss_India_Consumer_Sentiment.docx) — a full report analyzing 2,526 consumer conversations about weight loss products in India across Reddit, Instagram, and YouTube. 15 insights, radar charts per theme, Brand Health Score, and methodology disclosure.

## Pipeline

```
Brief -> Collect -> Normalize -> Filter -> Analyze -> Synthesize -> Score -> Report
  [0]      [1]        [2]         [3]       [4]         [5]          [6]      [7]
```

| Stage | What it does | Output |
|-------|-------------|--------|
| 0. Brief | Structure the research question | `brief.json` |
| 1. Collect | Pull from 6+ sources at max limits | `raw/*.json` |
| 2. Normalize | Deduplicate, engagement filter, common format | `normalized/corpus.json` |
| 3. Filter | LLM relevance classification (multilingual) | `filtered/corpus.json` |
| 4. Analyze | Sentiment, Plutchik emotion, ABSA, two-pass theme extraction | `analysis/results.json` |
| 5. Synthesize | One insight per theme (Observation/Insight/Implication/Recommendation) | `insights/insights.json` |
| 6. Score | Confidence (5 factors) + Signal Strength (4 factors) + Brand Health | `scored/scored_insights.json` |
| 7. Report | Charts + DOCX report | `report/report_v###.docx` |

Every stage writes artifacts to disk. If the pipeline crashes, resume from the last completed stage — no re-collection, no wasted API calls.

## Data Sources

| Source | What it captures | Cost |
|--------|-----------------|------|
| Reddit | Long-form consumer opinion, complaints, comparisons | Free (rate limited) |
| YouTube | Reactions to brand content, ad responses | Free (10K quota/day) |
| NewsData.io | Media narrative, regulatory coverage | Free (200 credits/day) |
| OpenAlex | Academic research, peer-reviewed context | Free (100K+/day) |
| Google Trends | Search interest over time (quantitative layer) | Free |
| Serper (Google) | Web-wide review sites, forums, articles | Free (2,500 queries) |
| Twitter/X, Instagram | External data ingestion (any JSON format) | Bring your own data |

## Quick Start

```bash
# Clone and install
git clone https://github.com/yourusername/consumer-research.git
cd consumer-research
pip install -r requirements.txt

# Set API keys (only needed for automated pipeline runs)
# Analysis runs at zero cost inside Claude Code / Claude Max
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

# Run the pipeline
python -m consumer_research.run \
  --brand "Brand Name" \
  --category "Product Category" \
  --geo IN \
  --objectives "What do consumers think about quality?" "How does pricing compare to competitors?"

# Or re-score and regenerate from existing data (no API needed)
python stage6_7_score_report.py [run_id]
python regenerate_report.py [run_id]
```

## Zero-API Architecture

All analysis is designed to run inside a Claude Code session at zero marginal cost. The model running the session IS the analysis engine — it reads the data, classifies sentiment, extracts themes, and synthesizes insights directly. No external API calls for analysis.

For automated pipeline runs without Claude Code, the Anthropic API handles filtering and classification at ~$1-2 per run.

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
- Engagement level (percentile-ranked)
- Sentiment intensity
- Conversation depth

Insights are ranked by confidence (primary) and signal strength (tiebreaker). Both scores shown as percentages — no categorical labels, no artificial quadrants.

**Brand Health Score** (0-100): Sentiment (30%) + Engagement (25%) + Advocacy (20%) + Resilience (15%) + Conversation (10%).

## Report Structure

1. **Cover** — brand name, key metrics table (items analysed, insights, NSS, Brand Health, platforms)
2. **Executive Summary** — top insights by confidence, "Top Insights at a Glance" table
3. **Data Universe** — collection funnel, platform breakdown chart
4. **Sentiment & Emotion** — NSS, Plutchik emotion distribution, ABSA heatmap
5. **Insight Landscape** — all insights with prevalence, confidence, signal, NSS
6. **Insight Deep Dives** — one per theme: data line, radar chart, observation, insight, implication, recommendation, verbatims
7. **Brand Health Score** — component breakdown with conditional callouts
8. **Methodology** — derived from run config (never hardcoded)
9. **Data Provenance** — platform table, date range, known biases

## Known Limitations

These are structural limitations of social listening methodology. The pipeline cannot eliminate them — only mitigate and disclose.

- **Query framing bias**: Keywords presuppose contexts. You find what you search for. The keyword expansion follows the brief's framing — it doesn't generate adversarial queries.
- **Platform demographic bias**: Reddit skews male/urban/18-34. YouTube skews toward extreme reactions. Instagram skews female/influencer. No demographic weighting applied.
- **No sampling frame**: Prevalence is meaningful within the corpus only — never projectable to the general population. "33% of items" does not mean "33% of consumers."
- **Engagement filter excludes quiet voices**: Minimum upvote/like thresholds systematically exclude moderate consumers. The corpus over-indexes on extreme sentiment.
- **No bot/astroturf detection**: Engagement thresholds filter some bots but zero detection of coordinated campaigns or paid reviews.
- **No reliable demographics**: No platform in this pipeline provides verified age, gender, or location. Any demographic inference is speculative.
- **Language gaps**: English and Hindi/Hinglish supported. Tamil, Telugu, Bengali, Marathi, Kannada — representing hundreds of millions of consumers — are not.

For the full list of 12 documented limitations with mitigation strategies, see the Methodology section in any generated report.

## Project Structure

```
consumer_research/
  config.py                  — All defaults, scoring weights, collection limits
  run.py                     — CLI entry point
  models/schemas.py          — Pydantic models (NormalizedItem, ScoredInsight, etc.)
  utils/llm_client.py        — Unified LLM client (Claude -> Gemini fallback)
  utils/keywords.py          — Brief -> 50+ search keywords
  pipeline/orchestrator.py   — Wires all 8 stages
  pipeline/filter.py         — Stage 3: relevance classification
  pipeline/analyze.py        — Stage 4: sentiment, emotion, ABSA, themes
  pipeline/synthesize.py     — Stage 5: one insight per theme
  pipeline/scoring.py        — Stage 6: data-driven confidence + signal
  pipeline/validate.py       — Theme coverage gate, methodology selector
  pipeline/ingest.py         — Generic data ingestion (any JSON format)
  report/docx_generator.py   — DOCX report (primary output)
  report/charts.py           — 11 chart types (Tufte-inspired, Inter font)
scripts/                     — Utility scripts (resume, re-score, fix quotes)
studies/                     — Per-study analysis scripts
docs/                        — Methodology and product documentation
sample-reports/              — Showcase report
sample-runs/                 — Sample run artifacts (config, brief, scored insights)
```

## Documentation

- [`CLAUDE.md`](CLAUDE.md) — Complete technical reference (architecture, procedures, failure modes)
- [`docs/methodology.docx`](docs/methodology.docx) — Full research methodology (client-facing)
- [`docs/product_documentation.docx`](docs/product_documentation.docx) — Product guide for non-technical users

## License

MIT
