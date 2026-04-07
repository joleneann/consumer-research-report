"""Re-score insights from insights.json (no API calls needed — scoring is data-driven)."""
from __future__ import annotations
import io, json, os, sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = Path(__file__).parent.parent  # scripts/ -> repo root

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("rescore")

from consumer_research.config import CollectionConfig, PipelineConfig, RUNS_DIR
from consumer_research.models.schemas import AnalysisResults, NormalizedItem, Insight
from consumer_research.pipeline.scoring import score_insights

RUN_ID = "20260327_162042_7d13c6"
run_dir = RUNS_DIR / RUN_ID

# Load filtered corpus
corpus = [NormalizedItem(**d) for d in json.loads((run_dir / "filtered" / "corpus.json").read_text(encoding="utf-8"))]
logger.info(f"Corpus: {len(corpus)} items")

# Load analysis results
analysis_data = json.loads((run_dir / "analysis" / "results.json").read_text(encoding="utf-8"))
analysis = AnalysisResults(**analysis_data)
logger.info(f"Analysis: {len(analysis.themes)} themes")

# Load insights (the 11 we just wrote)
insights_data = json.loads((run_dir / "insights" / "insights.json").read_text(encoding="utf-8"))

# Build Insight objects
insights = []
for ins_data in insights_data:
    source_theme = next((t for t in analysis.themes if t.theme_id == ins_data.get("source_theme_id")), None)
    theme_id = ins_data.get("source_theme_id", "")
    item_count = source_theme.item_count if source_theme else 0
    insight = Insight(
        insight_id=ins_data["insight_id"],
        observation=ins_data["observation"],
        insight=ins_data["insight"],
        implication=ins_data.get("implication", ""),
        recommendation=ins_data.get("recommendation", ""),
        further_validation=ins_data.get("further_validation", ""),
        supporting_theme_ids=[theme_id],
        supporting_item_count=item_count,
        source_urls=[],
        is_grounded=ins_data.get("is_grounded", True),
        is_non_obvious=ins_data.get("is_non_obvious", True),
        is_actionable=ins_data.get("is_actionable", True),
        is_specific=ins_data.get("is_specific", True),
        is_falsifiable=ins_data.get("is_falsifiable", True),
        passed_quality_gates=True,
    )
    insights.append(insight)

logger.info(f"Insights loaded: {len(insights)}")

# Config
run_config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
config = PipelineConfig(collection=CollectionConfig(
    brand_name=run_config["brand_name"],
    category=run_config["category"],
    keywords=run_config.get("keywords", []),
    business_objectives=run_config.get("business_objectives", []),
))

# Score
scored = score_insights(insights, analysis, corpus, run_dir, config=config.scoring)
logger.info(f"Scored: {len(scored)} insights")
for s in scored:
    logger.info(f"  {s.insight.insight_id}: conf={s.confidence_score:.2f} ({s.confidence_tier.value}) | signal={s.signal_strength_score:.2f} ({s.signal_strength_tier.value})")
