# Running with Your Own Data

This pipeline accepts data from any source. You do not need to use the built-in collectors.

## Bring Your Own JSON

If you have pre-collected data from a scraper, vendor export, or manual collection, pass it directly to Stage 2. The ingester auto-detects the format.

```python
from pathlib import Path
from consumer_research.pipeline.ingest import ingest_external_data

items = ingest_external_data(
    Path("data/my_collected_data.json"),
    collection_query="brand study 2026",
)
# items is a list of NormalizedItem objects, ready for Stage 2 onward
```

## Supported Input Formats

### Format 1: Platform-scraped (Twitter/X, Instagram, Reddit, YouTube)

```json
[
  {
    "metadata_content": {
      "content": "Post text here",
      "created_at": "2026-01-15T10:30:00Z"
    },
    "engagements": {
      "likes": 42,
      "comments": 8,
      "shares": 3
    },
    "source": "instagram",
    "url": "https://instagram.com/p/abc123",
    "comments": [
      {
        "text": "Comment text",
        "username": "user123"
      }
    ]
  }
]
```

Field names are auto-detected. Use `text`, `content`, `caption`, or `title` for the main text. Use `twitter`, `reddit`, `youtube`, `instagram`, `news`, or `academic` for the source field.

### Format 2: Simple flat list

```json
[
  {
    "text": "Consumer opinion text here",
    "source": "reddit",
    "url": "https://reddit.com/r/example/...",
    "date": "2026-01-15"
  }
]
```

Any field name variant works: `text`/`content`/`body`, `source`/`platform`, `url`/`link`/`permalink`, `date`/`created_at`/`timestamp`.

### Format 3: Pre-normalized

If your data is already in `NormalizedItem` format (from a previous pipeline run), pass it directly - no transformation applied.

## How Analysis Works

All analysis runs inside your Claude Code session. The model running the session IS the analysis engine - no external API calls, no cost beyond your Claude Code or Claude Max subscription.

The workflow:

1. **Ingest and normalize** your data (code-based, free)
2. **Filter for relevance** - Claude Code reads items and classifies them (in-context)
3. **Analyze** - Claude Code classifies sentiment, emotion, aspects, and extracts themes (in-context)
4. **Synthesize insights** - Claude Code reads theme data and writes structured insights (in-context)
5. **Score** - data-driven confidence and signal strength math (code-based, free)
6. **Generate report** - charts and DOCX generation (code-based, free)

See [`examples/studies/weight_loss/run_weight_loss.py`](../examples/studies/weight_loss/run_weight_loss.py) for a complete working example, and the in-context analysis scripts in the same directory (`stage4_analysis.py`, `stage5_synthesis.py`).

## What Each Stage Costs

| Stage | How it runs | Cost |
|-------|------------|------|
| Ingest + Normalize | Code-based | Free |
| Filter | Claude Code session (in-context) | Included in subscription |
| Analyze | Claude Code session (in-context) | Included in subscription |
| Synthesize | Claude Code session (in-context) | Included in subscription |
| Score | Code-based (data-driven math) | Free |
| Report | Code-based (charts + DOCX) | Free |

No API keys required. No per-run cost.

## Scoring and Report Generation

Once analysis is complete, scoring and report generation are fully automated with no API calls:

```bash
# Score insights and generate DOCX report
consumer-research score-report <run_id>

# Regenerate report only (from existing scored data)
consumer-research regenerate <run_id>
```

Or use the scripts directly:

```bash
python scripts/stage6_7_score_report.py <run_id>
python scripts/regenerate_report.py <run_id>
```

## Resuming After a Failure

Every stage writes output to disk before the next stage starts. If anything fails, resume from the last completed stage:

```bash
# Resume from Stage 3 (filtering)
python scripts/resume_stage3.py <run_id>

# Resume from Stage 4 (analysis)
python scripts/resume_stage4.py <run_id>
```

All resume scripts accept the run ID as a CLI argument and load config from the run's `config.json`.
