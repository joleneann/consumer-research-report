"""
Stage 6 (Scoring) + Stage 7 (Report Generation).
Both are code-based - no LLM API calls needed.
"""
import io, sys, json
from pathlib import Path
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = Path(__file__).parent.parent  # scripts/ -> repo root

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("stage6_7")

# Accept run ID as CLI argument, default to latest weight loss run
if len(sys.argv) > 1:
    RUN_DIR = RUNS_DIR / sys.argv[1]
else:
    # Find the most recent run directory
    runs = sorted(Path(RUNS_DIR).iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    if not runs:
        print("ERROR: No run directories found in runs/")
        sys.exit(1)
    RUN_DIR = runs[0]
logger.info(f"Run directory: {RUN_DIR.name}")

# Load all data
from consumer_research.config import RUNS_DIR
from consumer_research.models.schemas import (
    AnalysisResults, Insight, NormalizedItem, ScoredInsight,
)
from consumer_research.config import CollectionConfig, PipelineConfig, ScoringConfig

corpus_data = json.loads((RUN_DIR / "filtered" / "corpus.json").read_text(encoding="utf-8"))
corpus = [NormalizedItem(**d) for d in corpus_data]
logger.info(f"Corpus: {len(corpus)} items")

analysis_data = json.loads((RUN_DIR / "analysis" / "results.json").read_text(encoding="utf-8"))
analysis = AnalysisResults(**analysis_data)
logger.info(f"Analysis: {len(analysis.themes)} themes, NSS={analysis.net_sentiment_score:+.2%}")

insights_data = json.loads((RUN_DIR / "insights" / "insights.json").read_text(encoding="utf-8"))
insights = [Insight(**d) for d in insights_data]
logger.info(f"Insights: {len(insights)}")

# Config — load from run's config.json (saved during pipeline execution)
_config_path = RUN_DIR / "config.json"
if _config_path.exists():
    _rc = json.loads(_config_path.read_text(encoding="utf-8"))
    config = PipelineConfig(
        collection=CollectionConfig(
            brand_name=_rc.get("brand_name", "Unknown"),
            category=_rc.get("category", "general"),
            time_period_days=_rc.get("time_period_days", 180),
            business_objectives=_rc.get("business_objectives", []),
            competitors=_rc.get("competitors", []),
            trends_geo=_rc.get("trends_geo", ""),
            news_country=_rc.get("news_country", ""),
        ),
        scoring=ScoringConfig(),
    )
    logger.info(f"Config loaded: {_rc.get('brand_name')} / {_rc.get('category')}")
else:
    logger.error(f"No config.json found in {RUN_DIR}. Pass a run directory that has one.")
    sys.exit(1)

# ── Stage 6: Scoring ──
logger.info("\n== STAGE 6: SCORING ==")
from consumer_research.pipeline.scoring import score_insights, compute_brand_health

scored = score_insights(insights, analysis, corpus, RUN_DIR, config=config.scoring)
brand_health = compute_brand_health(analysis, corpus)
logger.info(f"Scored: {len(scored)} insights")
logger.info(f"Brand Health Score: {brand_health.get('overall_score', 'N/A')}/100")

# Save brand_health into analysis results
analysis_data["brand_health"] = brand_health
(RUN_DIR / "analysis" / "results.json").write_text(
    json.dumps(analysis_data, indent=2, default=str), encoding="utf-8"
)

# ── Stage 7: Charts + DOCX ──
logger.info("\n== STAGE 7: REPORT GENERATION ==")
report_dir = RUN_DIR / "report"
report_dir.mkdir(exist_ok=True)

# Charts
from consumer_research.report.charts import generate_all_charts
charts = generate_all_charts(
    analysis=analysis,
    scored_insights=scored,
    items=corpus,
    output_dir=report_dir,
)
logger.info(f"Charts: {sum(1 for v in charts.values() if v)} generated")

# DOCX
from consumer_research.report.docx_generator import generate_docx_report
docx_path = generate_docx_report(
    scored_insights=scored,
    analysis=analysis,
    items=corpus,
    config=config,
    run_dir=RUN_DIR,
    brand_health=brand_health,
)
logger.info(f"DOCX: {docx_path} ({docx_path.stat().st_size:,} bytes)")

# ── Summary ──
from consumer_research.models.schemas import ConfidenceTier, MatrixQuadrant
platform_counts = {}
for item in corpus:
    p = item.source_platform.value
    platform_counts[p] = platform_counts.get(p, 0) + 1

logger.info(f"\n{'='*50}")
logger.info(f"Items:           {len(corpus)}")
logger.info(f"Platforms:       {platform_counts}")
logger.info(f"Themes:          {len(analysis.themes)}")
logger.info(f"Insights:        {len(insights)}")
logger.info(f"NSS:             {analysis.net_sentiment_score:+.2%}")
logger.info(f"Brand Health:    {brand_health.get('overall_score', 'N/A')}/100")
logger.info(f"High confidence: {sum(1 for s in scored if s.confidence_tier == ConfidenceTier.HIGH)}")
logger.info(f"Key findings:    {sum(1 for s in scored if s.matrix_quadrant == MatrixQuadrant.KEY_FINDING)}")
logger.info(f"Report:          {docx_path}")
logger.info(f"{'='*50}")
