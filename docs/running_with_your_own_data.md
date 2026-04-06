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

If your data is already in `NormalizedItem` format (from a previous pipeline run), pass it directly — no transformation applied.

## Running Stages 2-7 on Your Data

```python
import json
import logging
from pathlib import Path
from uuid import uuid4
from datetime import datetime

from consumer_research.pipeline.ingest import ingest_external_data
from consumer_research.pipeline.normalize import normalize_and_deduplicate
from consumer_research.config import PipelineConfig, CollectionConfig, AnalysisConfig, ScoringConfig
from consumer_research.utils.llm_client import create_llm_client

# Setup
logging.basicConfig(level=logging.INFO)
run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid4().hex[:6]
run_dir = Path("consumer_research/runs") / run_id
run_dir.mkdir(parents=True, exist_ok=True)

config = PipelineConfig(
    collection=CollectionConfig(
        brand_name="Your Brand",
        category="Your Category",
        business_objectives=["What do consumers think about quality?"],
        trends_geo="IN",
    )
)

# Stage 2: Ingest and normalize your data
items = ingest_external_data(Path("data/your_data.json"), collection_query="your brand study")
corpus = normalize_and_deduplicate({"external": items}, run_dir)

# Stages 3-7: Filter, analyze, synthesize, score, report
from consumer_research.pipeline.filter import filter_corpus
from consumer_research.pipeline.analyze import analyze_corpus
from consumer_research.pipeline.synthesize import synthesize_insights
from consumer_research.pipeline.scoring import score_insights, compute_brand_health
from consumer_research.report.charts import generate_all_charts
from consumer_research.report.docx_generator import generate_docx_report

llm = create_llm_client()

filtered = filter_corpus(corpus, config.collection.brand_name, config.collection.category, run_dir, llm)
analysis = analyze_corpus(filtered, config.collection.brand_name, config.collection.category, run_dir, llm)
insights = synthesize_insights(analysis, filtered, config.collection.brand_name, config.collection.category, config.collection.business_objectives, run_dir, llm)
scored = score_insights(insights, analysis, filtered, run_dir)
brand_health = compute_brand_health(analysis, filtered)

generate_all_charts(analysis, scored, filtered, run_dir / "report")
generate_docx_report(scored, analysis, filtered, config, run_dir, brand_health)
```

See [`examples/studies/weight_loss/run_weight_loss.py`](../examples/studies/weight_loss/run_weight_loss.py) for a complete working example.

## API Key Setup

Write API keys to a `.env` file in the project root:

```bash
ANTHROPIC_API_KEY=sk-ant-...
YOUTUBE_API_KEY=...      # Optional
NEWSDATA_API_KEY=...     # Optional
SERPER_API_KEY=...       # Optional
```

The pipeline loads `.env` automatically. The Anthropic key must be from the **Default workspace** at `console.anthropic.com/settings/keys` — keys from the "Claude Code" workspace will not work for API calls.

## What Each Stage Costs

| Stage | API calls | Cost |
|-------|-----------|------|
| Normalize | None | Free |
| Filter | Claude API — ~0.1-0.3 tokens/item | ~$0.20-0.50 per 1,000 items |
| Analyze | Claude API — theme discovery + mapping | ~$0.50-1.00 per run |
| Synthesize | Claude API — one call per study | ~$0.20-0.50 |
| Score | None (data-driven) | Free |
| Report | None | Free |

Total: ~$1-2 per run for a corpus of 1,000-6,000 items.

## Resuming After a Failure

Every stage writes output to disk before the next stage starts. If anything fails, resume from the last completed stage:

```bash
# Resume from Stage 3 (filtering)
python scripts/resume_stage3.py <run_id>

# Resume from Stage 4 (analysis)
python scripts/resume_stage4.py <run_id>

# Re-score and regenerate report from existing insights
python scripts/stage6_7_score_report.py <run_id>

# Regenerate report only (no scoring)
python scripts/regenerate_report.py <run_id>
```

All resume scripts accept the run ID as a CLI argument and load config from the run's `config.json`. No hardcoded paths.
