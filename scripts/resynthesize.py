"""Re-run Stage 5 (synthesis) + Stage 6 (scoring) using existing analysis data.
No data collection or re-analysis — only re-generates insights from existing themes.
"""
from __future__ import annotations
import io, json, os, sys
from pathlib import Path
from pathlib import Path as _P

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = Path(__file__).parent.parent  # scripts/ -> repo root

# Load API key from .env
env_file = ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("resynth")

from consumer_research.config import CollectionConfig, PipelineConfig, ScoringConfig, RUNS_DIR
from consumer_research.models.schemas import AnalysisResults, NormalizedItem
from consumer_research.pipeline.synthesize import synthesize_insights
from consumer_research.pipeline.scoring import score_insights
from consumer_research.utils.llm_client import create_llm_client

RUN_ID = "20260327_162042_7d13c6"
run_dir = RUNS_DIR / RUN_ID

# Load filtered corpus
corpus = [NormalizedItem(**d) for d in json.loads((run_dir / "filtered" / "corpus.json").read_text(encoding="utf-8"))]
logger.info(f"Corpus: {len(corpus)} items")

# Load analysis results
analysis_data = json.loads((run_dir / "analysis" / "results.json").read_text(encoding="utf-8"))
analysis = AnalysisResults(**analysis_data)
logger.info(f"Analysis: {len(analysis.themes)} themes")

# Config
run_config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
config = PipelineConfig(collection=CollectionConfig(
    brand_name=run_config["brand_name"],
    category=run_config["category"],
    keywords=run_config.get("keywords", []),
    business_objectives=run_config.get("business_objectives", []),
))

# Initialize LLM client
llm_client = create_llm_client()

# Stage 5: Re-synthesize insights
logger.info("── STAGE 5: RE-SYNTHESIS ──")
insights = synthesize_insights(
    analysis,
    corpus,
    config.collection.brand_name,
    config.collection.category,
    config.collection.business_objectives,
    run_dir,
    llm_client,
)
logger.info(f"Insights generated: {len(insights)} (from {len(analysis.themes)} themes)")

# Stage 6: Re-score
logger.info("── STAGE 6: RE-SCORING ──")
scored = score_insights(
    insights,
    analysis,
    corpus,
    run_dir,
    config=config.scoring,
)
logger.info(f"Scored: {len(scored)} insights")
for s in scored:
    logger.info(f"  {s.insight.insight_id}: conf={s.confidence_score:.2f} ({s.confidence_tier.value}) | signal={s.signal_strength_score:.2f} ({s.signal_strength_tier.value})")

logger.info("Done. Now run: python regenerate_report.py")
