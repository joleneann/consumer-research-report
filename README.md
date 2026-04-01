# Consumer Research Pipeline

An automated consumer insights engine that turns a research brief into a scored, structured report. Brief in, report out.

**This is a discovery engine, not a validation tool.** Themes are extracted inductively from the corpus — the brief defines what to collect, not what to find. If consumers are talking about something the brand never anticipated, it surfaces.

## What It Produces

Input: A research brief (brand, category, geography, 3-5 questions).

Output: A DOCX report containing:
- **Collection funnel** — raw volume, deduplication stats, relevance filter pass rates
- **Sentiment analysis** — Net Sentiment Score (NSS) per insight, overall, and per aspect
- **Emotion profiling** — Plutchik 8-emotion model across the full corpus
- **Aspect-Based Sentiment Analysis (ABSA)** — per-aspect sentiment (e.g., efficacy +33%, safety -8%)
- **Insight landscape** — every theme ranked by Confidence x Signal Strength
- **Deep dives** — per-insight breakdown: What the Data Shows, What it Means, Business Implication, Recommendation, Further Validation, Representative Voices
- **Brand Health Score** — 0-100 composite (sentiment, engagement, advocacy, resilience, conversation)
- **Data provenance** — full methodology, scoring weights, source breakdown

## Pipeline Architecture

```
[0] BRIEF       → brief.json              Research scope, approved before collection
[1] COLLECT     → raw/*.json              Reddit, YouTube, News, Academic, Web Search, Trends, External
[2] NORMALIZE   → normalized/corpus.json  Thread-level dedup + engagement filter
[3] FILTER      → filtered/corpus.json    LLM relevance classification (multilingual)
[4] ANALYZE     → analysis/results.json   Sentiment, Plutchik emotions, ABSA, theme extraction
[5] SYNTHESIZE  → insights/insights.json  One insight per theme, mandatory coverage
[6] SCORE       → scored/scored.json      Confidence (5 factors) + Signal Strength (4 factors)
[7] REPORT      → report_v###.docx        DOCX + 6 standard charts + per-insight radar charts
```

### Data Sources

| Source | Method | What It Adds |
|--------|--------|-------------|
| Reddit | Public JSON API | Long-form unfiltered consumer opinion, complaints, comparisons |
| YouTube | YouTube Data API | Real-time reactions to campaigns, product launches, celebrity content |
| Twitter/X | External ingestion | Breaking sentiment, political context, influencer reach |
| Instagram | External ingestion | Visual brand engagement, influencer content, younger demographics |
| NewsData.io | API | Media narrative, regulatory context, analyst commentary |
| Google Trends | PyTrends | Search interest quantification, seasonal patterns |
| OpenAlex | API | Academic research, clinical evidence, peer-reviewed context |
| Web Search | Serper API | Broader web context, blog posts, forum threads |

### Quality Gates

**3-layer brand validation:**
1. Brand-anchored keywords — brand name present in every search query
2. Collector-level validation — title/content must reference the brand
3. Post-collection audit — sample 50 items per source, warn if <50% mention brand

**Engagement filtering:**
- Reddit: minimum 3 upvotes
- YouTube: minimum 2 likes
- Thread dedup: max 5 comments per Reddit thread (prevents vocal-minority over-indexing)

**Insight scoring (data-driven, no LLM opinion):**
- Confidence: sample size (0.25) + source diversity (0.25) + temporal spread (0.15) + internal agreement (0.20) + recency (0.15)
- Signal Strength: prevalence (0.35) + engagement (0.30) + sentiment intensity (0.20) + depth (0.15)

## Sample Reports

Two complete reports are included in `sample-reports/`, both generated from external datasets:

### Weight Loss in India — Consumer Sentiment & Brand Perception
- **Corpus:** 2,526 items from 43,698 raw (5.8% pass rate)
- **Sources:** Reddit, Instagram, YouTube
- **Insights discovered:** 15 (inductively, from data — not pre-defined)
- **NSS range:** -11% (GLP-1 side effects) to +48% (weight loss transformations)
- **Key findings:** PCOS affects 16.5% of the conversation (underserved medical segment); "food noise" concept emerging as paradigm shift; Bollywood celebrity speculation driving GLP-1 awareness through suspicion, not endorsement

### Make in India — Consumer Sentiment & Brand Perception
- **Corpus:** 5,814 items from 282,355 raw (2.1% pass rate)
- **Sources:** Twitter, YouTube, Reddit, Instagram
- **Insights discovered:** 16 (inductively)
- **NSS range:** +10% (China dependency) to +41% (Atmanirbhar self-reliance)
- **Key findings:** China dependency paradox (trade deficit doubled from $43B to $99B during "Boycott China" sentiment); political polarisation consumes 34.8% of the conversation; "conditional patriotism" — consumers want to buy Indian but refuse inferior quality wrapped in a flag

## Discovery vs. Confirmation

Traditional social listening tools define themes upfront and filter data to match — a confirmation engine. This pipeline runs the opposite direction:

1. Collect everything within the brief's aperture
2. Let themes emerge from a stratified discovery sample
3. Map the full corpus against discovered themes
4. Score each theme's confidence and signal strength from data alone

The practical consequence: this pipeline finds what's actually in the data, including themes the brief never anticipated. Both sample reports contain insights that a keyword-filtered approach would structurally miss.

## Documentation

- `docs/methodology.docx` — Full research methodology: how a brief becomes a report, stage-by-stage
- `docs/product_documentation.docx` — Product documentation: what it does, how to use it, when to trust it

## Tech Stack

- **Language:** Python 3.11+
- **Analysis LLM:** Claude (Anthropic) — deterministic (temperature 0.0)
- **Report generation:** python-docx, matplotlib (Tufte-inspired charts, Inter font)
- **Data models:** Pydantic v2
- **Collection:** httpx, PyTrends, Crawl4AI

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file:
```
ANTHROPIC_API_KEY=your_key
YOUTUBE_API_KEY=your_key        # optional
NEWSDATA_API_KEY=your_key       # optional
SERPER_API_KEY=your_key         # optional
```

Run:
```bash
python -m consumer_research.run --brand "Brand" --category "Category" --geo "IN"
```

## Author

**Jolene Fernandes** — Growth engineer. Builds systems, not campaigns.

- [Amplify PLG Prototype](https://github.com/joleneann/amplify-plg) — Healthcare marketing website + 5-screen interactive signup flow
- [Growth Content Essays](https://github.com/joleneann/growth-content-essays) — AI pipeline: raw content to structured practitioner-grade essays
