"""Regenerate DOCX report from existing analysis + scored data (no API calls)."""
from __future__ import annotations
import io, json, os, sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = Path(__file__).parent.parent  # scripts/ -> repo root

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("regen")

from consumer_research.config import CollectionConfig, PipelineConfig
from consumer_research.models.schemas import AnalysisResults, NormalizedItem, ScoredInsight, Insight
from consumer_research.report.docx_generator import generate_docx_report
from consumer_research.report.charts import generate_all_charts

# Accept run ID as CLI argument, default to most recent run
if len(sys.argv) > 1:
    RUN_ID = sys.argv[1]
else:
    runs = sorted((ROOT / "runs").iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    if not runs:
        print("ERROR: No run directories found"); sys.exit(1)
    RUN_ID = runs[0].name
    logger.info(f"No run ID provided, using most recent: {RUN_ID}")
run_dir = ROOT / "runs" / RUN_ID

# Load filtered corpus
corpus = [NormalizedItem(**d) for d in json.loads((run_dir / "filtered" / "corpus.json").read_text(encoding="utf-8"))]
logger.info(f"Corpus: {len(corpus)} items")

# Load analysis results
analysis_data = json.loads((run_dir / "analysis" / "results.json").read_text(encoding="utf-8"))
analysis = AnalysisResults(**analysis_data)
logger.info(f"Analysis: {len(analysis.sentiment_results)} sentiment, {len(analysis.themes)} themes, NSS={analysis.net_sentiment_score:+.2%}")

# Load scored insights
scored_data = json.loads((run_dir / "scored" / "scored_insights.json").read_text(encoding="utf-8"))
scored_insights = [ScoredInsight(**d) for d in scored_data]
logger.info(f"Scored: {len(scored_insights)} insights")

# Config
run_config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
config = PipelineConfig(collection=CollectionConfig(
    brand_name=run_config["brand_name"],
    category=run_config["category"],
    keywords=run_config.get("keywords", []),
    business_objectives=run_config.get("business_objectives", []),
    competitors=run_config.get("competitors", []),
    trends_geo=run_config.get("trends_geo", ""),
    news_country=run_config.get("news_country", ""),
))

# Brand health from raw JSON (not in Pydantic model)
brand_health = analysis_data.get("brand_health", {})

# Regenerate all charts (including radar for every insight)
charts = generate_all_charts(analysis=analysis, scored_insights=scored_insights, items=corpus, output_dir=run_dir / "report")
logger.info(f"Charts: {sum(1 for v in charts.values() if v)} generated")

# Generate DOCX
docx_path = generate_docx_report(scored_insights=scored_insights, analysis=analysis, items=corpus, config=config, run_dir=run_dir, brand_health=brand_health)
logger.info(f"DOCX: {docx_path} ({docx_path.stat().st_size:,} bytes)")
