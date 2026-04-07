"""
Resume from Stage 4 using the filtered corpus from run 20260327_152744_d03e06.
Theme extraction was broken (capped at 200 items). Fixed. Re-running analysis → score → report.

Usage: python resume_stage4.py
"""
import json
import logging
import os
import sys
import time
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone

ROOT = Path(__file__).parent.parent  # scripts/ -> repo root

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("resume_stage4")


def main():
    from consumer_research.config import RUNS_DIR

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        # Try .env
        env_path = ROOT / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("ANTHROPIC_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
                    os.environ["ANTHROPIC_API_KEY"] = api_key
                    break
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set")
        sys.exit(1)
    logger.info(f"API key: {api_key[:20]}...")

    # Source run (CLI arg required)
    if len(sys.argv) > 1:
        source_run_id = sys.argv[1]
    else:
        logger.error("Usage: python resume_stage4.py <source_run_id>")
        sys.exit(1)
    source_run = RUNS_DIR / source_run_id
    filtered_path = source_run / "filtered" / "corpus.json"
    if not filtered_path.exists():
        logger.error(f"Filtered corpus not found: {filtered_path}")
        sys.exit(1)

    # New run directory
    run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"New run: {run_id}")

    # Copy artifacts from source run
    import shutil
    for stage in ["raw", "normalized", "filtered"]:
        src = source_run / stage
        dst = run_dir / stage
        if src.exists():
            shutil.copytree(str(src), str(dst))
    shutil.copy(str(source_run / "config.json"), str(run_dir / "config.json"))
    logger.info("Copied raw/normalized/filtered from source run")

    # Load filtered corpus
    from consumer_research.models.schemas import NormalizedItem
    raw_data = json.loads(filtered_path.read_text(encoding="utf-8"))
    filtered = [NormalizedItem.model_validate(item) for item in raw_data]
    logger.info(f"Loaded {len(filtered)} filtered items")

    # Config
    from consumer_research.config import (
        AnalysisConfig, CollectionConfig, PipelineConfig, ScoringConfig
    )
    # Load config from source run's config.json
    _config_path = source_run / "config.json"
    if _config_path.exists():
        _rc = json.loads(_config_path.read_text(encoding="utf-8"))
        collection = CollectionConfig(
            brand_name=_rc.get("brand_name", "Unknown"),
            category=_rc.get("category", "general"),
            time_period_days=_rc.get("time_period_days", 180),
            business_objectives=_rc.get("business_objectives", []),
            competitors=_rc.get("competitors", []),
            trends_geo=_rc.get("trends_geo", ""),
            news_country=_rc.get("news_country", ""),
        )
        logger.info(f"Config loaded from source run: {collection.brand_name}")
    else:
        logger.error(f"No config.json in source run {source_run}. Cannot proceed.")
        sys.exit(1)
    analysis_cfg = AnalysisConfig(
        claude_model=_rc.get("claude_model", "claude-sonnet-4-20250514"),
        claude_temperature=0.0,
        batch_size=15,
        min_items_for_theme=5,
    )
    config = PipelineConfig(collection=collection, analysis=analysis_cfg, scoring=ScoringConfig())

    from consumer_research.utils.llm_client import create_llm_client
    llm_client = create_llm_client()

    # Stage 4: Analysis (with fixed theme extraction)
    logger.info(f"\n── STAGE 4: ANALYSIS (two-pass theme extraction) ──")
    from consumer_research.pipeline.analyze import analyze_corpus
    t4 = time.time()
    analysis_results = analyze_corpus(
        filtered,
        collection.brand_name,
        collection.category,
        run_dir,
        llm_client,
        batch_size=analysis_cfg.batch_size,
        min_items_for_theme=analysis_cfg.min_items_for_theme,
    )
    logger.info(f"Stage 4: {time.time()-t4:.0f}s | {len(analysis_results.themes)} themes")

    for t in analysis_results.themes:
        logger.info(f"  {t.theme_id} {t.theme_label}: {t.item_count} items ({t.prevalence_pct:.1f}%) multi={t.is_multi_source}")

    # Stage 5: Insight Synthesis
    logger.info(f"\n── STAGE 5: INSIGHT SYNTHESIS ──")
    from consumer_research.pipeline.synthesize import synthesize_insights
    t5 = time.time()
    insights = synthesize_insights(
        analysis_results,
        filtered,
        collection.brand_name,
        collection.category,
        collection.business_objectives,
        run_dir,
        llm_client,
    )
    logger.info(f"Stage 5: {time.time()-t5:.0f}s | {len(insights)} insights")

    # Stage 6: Scoring
    logger.info(f"\n── STAGE 6: SCORING ──")
    from consumer_research.pipeline.scoring import score_insights
    t6 = time.time()
    scored = score_insights(insights, analysis_results, filtered, run_dir, config=config.scoring)
    logger.info(f"Stage 6: {time.time()-t6:.0f}s | {len(scored)} scored")

    # Stage 7: Reports
    logger.info(f"\n── STAGE 7: REPORT GENERATION ──")
    report_dir = run_dir / "report"
    report_dir.mkdir(exist_ok=True)

    try:
        from consumer_research.report.pdf_generator import generate_pdf_report
        pdf_path = generate_pdf_report(scored, analysis_results, filtered, config, run_dir)
        logger.info(f"PDF/HTML: {pdf_path} ({pdf_path.stat().st_size:,} bytes)")
    except Exception as e:
        logger.warning(f"PDF failed: {e}")

    try:
        from consumer_research.report.pptx_generator import generate_pptx_report
        pptx_path = generate_pptx_report(scored, analysis_results, filtered, config, run_dir)
        logger.info(f"PPTX: {pptx_path} ({pptx_path.stat().st_size:,} bytes)")
    except Exception as e:
        logger.error(f"PPTX failed: {e}")
        import traceback; traceback.print_exc()

    from consumer_research.models.schemas import ConfidenceTier
    platform_counts = {}
    for item in filtered:
        p = item.source_platform.value
        platform_counts[p] = platform_counts.get(p, 0) + 1

    logger.info("\n═══════════════════════════════════════")
    logger.info(f"Run ID:          {run_id}")
    logger.info(f"Items analyzed:  {len(filtered)}")
    logger.info(f"Platforms:       {platform_counts}")
    logger.info(f"Themes:          {len(analysis_results.themes)}")
    logger.info(f"Insights:        {len(insights)}")
    logger.info(f"High confidence: {sum(1 for s in scored if s.confidence_tier == ConfidenceTier.HIGH)}")
    logger.info(f"Report:          {run_dir / 'report' / 'report.pptx'}")
    logger.info("═══════════════════════════════════════")


if __name__ == "__main__":
    main()
