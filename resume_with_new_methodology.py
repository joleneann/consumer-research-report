"""Resume pipeline from Stage 4 with upgraded methodology.

Loads the existing filtered corpus (966 items) and re-runs:
- Stage 4: Sentiment + Emotion + ABSA + Theme extraction + NSS
- Stage 5: Insight synthesis
- Stage 6: Scoring + Brand Health Score
- Stage 7: Report generation (PPTX with new slides)

This avoids re-collecting and re-filtering data.
"""

from __future__ import annotations

import io
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("resume_v2")

# Load .env — force-set keys (setdefault won't override empty values)
env_path = ROOT / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

from consumer_research.config import CollectionConfig, PipelineConfig, ScoringConfig
from consumer_research.models.schemas import (
    AnalysisResults,
    NormalizedItem,
    compute_nss,
)
from consumer_research.pipeline.analyze import analyze_corpus
from consumer_research.pipeline.scoring import compute_brand_health, score_insights
from consumer_research.pipeline.synthesize import synthesize_insights
from consumer_research.report.pptx_generator import generate_pptx_report
from consumer_research.utils.llm_client import create_llm_client

# ── Config ──
RUN_ID = "20260327_162042_7d13c6"
run_dir = ROOT / "consumer_research" / "runs" / RUN_ID

# Load filtered corpus
corpus_path = run_dir / "filtered" / "corpus.json"
corpus_data = json.loads(corpus_path.read_text(encoding="utf-8"))
items = [NormalizedItem(**d) for d in corpus_data]
logger.info(f"Loaded {len(items)} items from filtered corpus")

# Load run config
config_path = run_dir / "config.json"
run_config = json.loads(config_path.read_text(encoding="utf-8"))
brand_name = run_config["brand_name"]
category = run_config["category"]
objectives = run_config.get("business_objectives", [])

# Pipeline config
collection = CollectionConfig(
    brand_name=brand_name,
    category=category,
    keywords=run_config.get("keywords", []),
    business_objectives=objectives,
    competitors=run_config.get("competitors", ["Coca-Cola", "Pepsi"]),
)
config = PipelineConfig(collection=collection)

# LLM client
llm = create_llm_client("claude")
logger.info(f"LLM client: {llm.model_name}")

# ── Stage 4: Analysis (with new emotion + ABSA + NSS methodology) ──
logger.info("=" * 60)
logger.info("STAGE 4: Analysis (upgraded methodology)")
logger.info("  - Plutchik emotion classification")
logger.info("  - Aspect-Based Sentiment Analysis (ABSA)")
logger.info("  - Net Sentiment Score (NSS)")
logger.info("=" * 60)

analysis = analyze_corpus(
    items=items,
    brand_name=brand_name,
    category=category,
    run_dir=run_dir,
    llm_client=llm,
    batch_size=15,
    min_items_for_theme=3,
)

logger.info(f"Sentiment: {analysis.overall_sentiment}")
logger.info(f"NSS: {analysis.net_sentiment_score:+.2%}")
logger.info(f"Emotions: {analysis.emotion_distribution}")
logger.info(f"Aspects tracked: {len(analysis.aspect_sentiment_summary)}")
logger.info(f"Themes: {len(analysis.themes)}")

# ── Stage 5: Insight Synthesis ──
logger.info("=" * 60)
logger.info("STAGE 5: Insight Synthesis")
logger.info("=" * 60)

insights = synthesize_insights(
    analysis=analysis,
    items=items,
    brand_name=brand_name,
    category=category,
    business_objectives=objectives,
    run_dir=run_dir,
    llm_client=llm,
)
logger.info(f"Insights: {len(insights)} generated, "
            f"{sum(1 for i in insights if i.passed_quality_gates)} passed quality gates")

# ── Stage 6: Scoring + Brand Health ──
logger.info("=" * 60)
logger.info("STAGE 6: Scoring + Brand Health Score")
logger.info("=" * 60)

scored_insights = score_insights(
    insights=insights,
    analysis=analysis,
    items=items,
    run_dir=run_dir,
    config=config.scoring if hasattr(config, "scoring") else None,
)

brand_health = compute_brand_health(analysis, items)

# Save brand health to analysis results
analysis_data = json.loads((run_dir / "analysis" / "results.json").read_text(encoding="utf-8"))
analysis_data["brand_health"] = brand_health
(run_dir / "analysis" / "results.json").write_text(
    json.dumps(analysis_data, indent=2, default=str), encoding="utf-8"
)

logger.info(f"Scored: {len(scored_insights)} insights")
for s in scored_insights:
    logger.info(f"  {s.insight.insight_id}: conf={s.confidence_score:.2f} "
                f"({s.confidence_tier.value}), sig={s.signal_strength_score:.2f} "
                f"({s.signal_strength_tier.value}) → {s.matrix_quadrant.value}")

# ── Stage 7: Report Generation ──
logger.info("=" * 60)
logger.info("STAGE 7: Report Generation")
logger.info("=" * 60)

report_dir = run_dir / "report"
report_dir.mkdir(parents=True, exist_ok=True)

# Generate PPTX (charts are generated internally by pptx_generator)
pptx_path = generate_pptx_report(
    scored_insights=scored_insights,
    analysis=analysis,
    items=items,
    config=config,
    run_dir=run_dir,
)
logger.info(f"PPTX: {pptx_path} ({pptx_path.stat().st_size:,} bytes)")

# ── Summary ──
logger.info("=" * 60)
logger.info("COMPLETE — New methodology results:")
logger.info(f"  Net Sentiment Score: {analysis.net_sentiment_score:+.2%}")
logger.info(f"  Brand Health Score: {brand_health['overall_score']}/100")
logger.info(f"  Emotions detected: {analysis.emotion_distribution}")
logger.info(f"  Aspects tracked: {len(analysis.aspect_sentiment_summary)}")
logger.info(f"  Themes: {len(analysis.themes)}")
logger.info(f"  Insights: {len(scored_insights)}")
key_findings = sum(1 for s in scored_insights if s.matrix_quadrant.value == "Key Finding")
logger.info(f"  Key Findings: {key_findings}")
logger.info(f"  Report: {pptx_path}")
logger.info("=" * 60)
