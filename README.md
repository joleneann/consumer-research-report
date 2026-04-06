# Brand Sentiment Report Generator

Consumer Research Report Generator is a production-style decision-support system that turns a brand brief into a scored, client-ready consumer research report.

Given a brand, category, geography, and business questions, the pipeline collects evidence from noisy online sources, normalizes it into a shared schema, filters for relevance, analyzes sentiment and themes, scores confidence from data, and generates a versioned DOCX deliverable.

This repo is best understood as a workflow engine, not a dashboard and not just an "LLM project". The hard part is surviving messy inputs, partial failures, mixed data formats, and still producing a structured output with provenance.

## What It Does

- Accepts a research brief: brand, category, geography, competitors, and business questions
- Collects from Reddit, YouTube, NewsData.io, OpenAlex, Google Trends, Serper, or ingests external JSON
- Normalizes all sources into a common item schema
- Filters irrelevant or low-signal content
- Analyzes sentiment, emotion, aspect-level sentiment, and themes
- Synthesizes one insight per theme
- Scores each insight with data-driven confidence and signal metrics
- Generates charts and a versioned DOCX report

## Why This Project Exists

Traditional consumer research is expensive and slow. Social listening dashboards are fast but usually stop at keyword tracking and charts. This project sits in between: it is designed to turn messy online conversation into something a client or operator could actually use to make decisions.

The engineering goal is not just "analyze text." It is to build a workflow that can handle unreliable collectors, ambiguous input data, multiple source types, and client-facing output requirements without collapsing into one-off scripts.

## Current Status

- Main reusable product code lives in [`consumer_research/`](consumer_research/)
- Primary entry point is [`consumer_research/run.py`](consumer_research/run.py)
- Generated artifacts are written to `consumer_research/runs/<run_id>/`
- Final reports are versioned as `report_v###.docx`
- Study-specific scripts in [`studies/`](studies/) are examples and historical analyses, not the main interface

## Happy Path

### 1. Install dependencies

```bash
git clone https://github.com/joleneann/consumer-research-report.git
cd consumer-research-report
pip install -r requirements.txt
```

### 2. Set environment variables

Current pipeline runs use external APIs for collection and LLM analysis.

Required for analysis:

```bash
ANTHROPIC_API_KEY=...
```

Optional, depending on which collectors you want to enable:

```bash
YOUTUBE_API_KEY=...
NEWSDATA_API_KEY=...
SERPER_API_KEY=...
```

Collectors fail gracefully. Missing keys do not crash the full pipeline; those sources are skipped and the run continues.

### 3. Run a study

```bash
python -m consumer_research.run \
  --brand "Thums Up" \
  --category "Carbonated beverages" \
  --geo IN \
  --competitors "Coca-Cola" "Pepsi" \
  --objectives \
    "What are consumers saying about taste and quality?" \
    "How is the brand discussed relative to competitors?"
```

### 4. Inspect the output

Each run writes stage-by-stage artifacts under:

```text
consumer_research/runs/<run_id>/
  brief.json
  config.json
  raw/
  normalized/
  filtered/
  analysis/
  insights/
  scored/
  report/report_v###.docx
```

## Quick Review Path

If you are reviewing this repo for engineering quality, start here:

1. Open the sample deliverable: [`sample-reports/Weight_Loss_India_Consumer_Sentiment.docx`](sample-reports/Weight_Loss_India_Consumer_Sentiment.docx)
2. Read the primary workflow entry point: [`consumer_research/run.py`](consumer_research/run.py)
3. Read the orchestration layer: [`consumer_research/pipeline/orchestrator.py`](consumer_research/pipeline/orchestrator.py)
4. Read the shared schema definitions: [`consumer_research/models/schemas.py`](consumer_research/models/schemas.py)
5. Read the report generator: [`consumer_research/report/docx_generator.py`](consumer_research/report/docx_generator.py)

The repo also includes lightweight reference artifacts in [`sample-runs/`](sample-runs/), but it does not yet ship a full deterministic offline fixture run. That is still a gap.

## Pipeline

```text
Brief -> Collect -> Normalize -> Filter -> Analyze -> Synthesize -> Score -> Report
  [0]      [1]        [2]         [3]       [4]         [5]          [6]      [7]
```

| Stage | Purpose | Primary output |
| --- | --- | --- |
| 0. Brief | Structure the research question | `brief.json` |
| 1. Collect | Gather raw evidence from supported sources | `raw/*.json` |
| 2. Normalize | Deduplicate, cap thread dominance, unify schema | `normalized/corpus.json` |
| 3. Filter | LLM relevance classification | `filtered/corpus.json` |
| 4. Analyze | Sentiment, emotion, aspect sentiment, theme extraction | `analysis/results.json` |
| 5. Synthesize | One decision-grade insight per theme | `insights/insights.json` |
| 6. Score | Confidence, signal strength, brand health | `scored/scored_insights.json` |
| 7. Report | Charts plus DOCX output | `report/report_v###.docx` |

Every stage writes artifacts to disk so partial runs can be resumed without recollecting everything.

## Data Sources

| Source | Role in the pipeline | Notes |
| --- | --- | --- |
| Reddit | Long-form opinion, complaints, comparisons | Public JSON API, rate limited |
| YouTube | Comment-driven reactions to brand content | Requires `YOUTUBE_API_KEY` |
| NewsData.io | Media coverage and narrative context | Requires `NEWSDATA_API_KEY` |
| OpenAlex | Academic and evidence layer | No key required |
| Google Trends | Search interest over time | Quantitative validation layer |
| Serper | Web-wide mentions from blogs, forums, review sites | Requires `SERPER_API_KEY` |
| External JSON | Pre-collected Twitter/X, Instagram, vendor exports, or custom scrapes | Supported via flexible ingestion |

## Reliability Features

- Collector fault isolation: one failing source should not kill the run
- Stage-by-stage artifacting: every stage writes output to disk
- Resumability: later-stage utilities can regenerate or rescore existing runs
- Provenance: normalized items retain source URLs, timestamps, and platform metadata
- Deterministic IDs: item identity is derived from source URL and content
- Versioned outputs: report generation increments `report_v###.docx` instead of overwriting
- Flexible ingestion: external JSON can be normalized without rewriting the pipeline

## Main Operational Scripts

Primary interface:

- [`consumer_research/run.py`](consumer_research/run.py): run the end-to-end pipeline

Regeneration and rescoring:

- [`stage6_7_score_report.py`](stage6_7_score_report.py): rescore insights and regenerate report assets from an existing run
- [`regenerate_report.py`](regenerate_report.py): regenerate charts and DOCX from existing scored output

Recovery and utility scripts:

- [`scripts/resume_stage3.py`](scripts/resume_stage3.py)
- [`scripts/resume_stage4.py`](scripts/resume_stage4.py)
- [`scripts/rescore.py`](scripts/rescore.py)
- [`scripts/resynthesize.py`](scripts/resynthesize.py)
- [`scripts/fix_quotes.py`](scripts/fix_quotes.py)
- [`scripts/export_to_excel.py`](scripts/export_to_excel.py)

## Repo Guide

```text
consumer_research/
  collectors/         Source-specific collectors
  models/             Shared schemas and scoring models
  pipeline/           Core workflow stages
  report/             Charts and DOCX generation
  utils/              Keyword expansion, hashing, rate limiting, LLM client
  tests/              Test package scaffold

scripts/              Recovery and operational helpers
studies/              Study-specific scripts and older one-off analyses
sample-reports/       Example client-facing deliverable
sample-runs/          Small reference artifacts for review
docs/                 Methodology and product documentation
```

If the structure feels busy, start with `consumer_research/` first. That is the reusable product code. The rest of the repo is mostly operator support, examples, and historical study-specific work.

## Scoring Model

Each insight receives two independent scores, both derived from data rather than LLM judgment.

Confidence score:

- Sample size
- Source diversity
- Temporal consistency
- Internal agreement
- Data recency

Signal strength score:

- Prevalence in the corpus
- Engagement level
- Sentiment intensity
- Conversation depth

The pipeline also computes a composite Brand Health Score from sentiment, engagement, advocacy, resilience, and conversation volume/depth.

## Known Limitations

This project tries to be honest about both methodological limits and engineering maturity.

Methodological limits:

- Query framing affects what the system is likely to find
- Platform composition introduces demographic and behavioral bias
- Online conversation has no clean sampling frame, so prevalence is corpus-relative
- Engagement filters suppress quieter voices
- There is no bot or astroturf detection layer yet
- Verified demographic segmentation is not supported

Current engineering gaps:

- Test coverage is still minimal
- The repo still mixes reusable product code with study-specific scripts
- A fully reproducible offline demo dataset is not packaged yet
- Some implementation and documentation cleanup is still in progress

## What This Demonstrates

This project is intended to show production-style engineering on top of messy, ambiguous, real-world inputs:

- building a decision-support system instead of a toy text-analysis demo
- designing for provenance, resumability, and fault tolerance
- turning unstructured conversation into structured, client-facing output
- balancing product requirements, data quality, and operational workflow

## Documentation

- [`CLAUDE.md`](CLAUDE.md): detailed project reference and working notes
- [`docs/methodology.docx`](docs/methodology.docx): client-facing methodology document
- [`docs/product_documentation.docx`](docs/product_documentation.docx): product overview

## License

MIT
