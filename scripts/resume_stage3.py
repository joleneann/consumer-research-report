"""
Resume pipeline from Stage 3 (Relevance Filtering) using normalized data
from run 20260327_033348_f00e82.

All 1,208 normalized items will go through filtering — no corpus cap.
Then Stages 4 → 5 → 6 → 7 run automatically.

Usage:
    set ANTHROPIC_API_KEY=sk-ant-...
    python resume_stage3.py
"""
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

# Project root
ROOT = Path(__file__).parent.parent  # scripts/ -> repo root

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("resume_stage3")


def main():
    # ── Check API key ──
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        logger.error("ANTHROPIC_API_KEY is not set. Run: set ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)
    logger.info(f"API key: {api_key[:20]}...")

    # ── Source run (has our normalized corpus) ──
    if len(sys.argv) > 1:
        source_run_id = sys.argv[1]
    else:
        logger.error("Usage: python resume_stage3.py <source_run_id>")
        sys.exit(1)
    source_run = ROOT / "runs" / source_run_id
    normalized_path = source_run / "normalized" / "corpus.json"
    if not normalized_path.exists():
        logger.error(f"Normalized corpus not found: {normalized_path}")
        sys.exit(1)

    # ── New run directory ──
    run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"
    run_dir = ROOT / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"New run: {run_id}")

    # Copy raw data to new run (for provenance)
    import shutil
    raw_src = source_run / "raw"
    raw_dst = run_dir / "raw"
    shutil.copytree(str(raw_src), str(raw_dst))
    logger.info(f"Copied raw data ({len(list(raw_dst.glob('*.json')))} files)")

    # Copy normalized data
    norm_dst = run_dir / "normalized"
    norm_dst.mkdir(exist_ok=True)
    shutil.copy(str(normalized_path), str(norm_dst / "corpus.json"))
    src_stats = source_run / "normalized" / "stats.json"
    if src_stats.exists():
        shutil.copy(str(src_stats), str(norm_dst / "stats.json"))

    # ── Load normalized corpus ──
    from consumer_research.models.schemas import NormalizedItem
    raw_corpus = json.loads(normalized_path.read_text(encoding="utf-8"))
    corpus = [NormalizedItem.model_validate(item) for item in raw_corpus]
    logger.info(f"Loaded {len(corpus)} normalized items — NO CAP, all going through filter")

    # ── Load config ──
    from consumer_research.config import (
        AnalysisConfig,
        CollectionConfig,
        PipelineConfig,
        ScoringConfig,
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
            subreddits=_rc.get("subreddits", []),
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
        min_items_for_theme=3,
    )
    config = PipelineConfig(collection=collection, analysis=analysis_cfg, scoring=ScoringConfig())

    # Save run config
    from consumer_research.models.schemas import RunConfig
    run_config = RunConfig(
        run_id=run_id,
        created_at=datetime.now(timezone.utc),
        brand_name=collection.brand_name,
        category=collection.category,
        time_period_days=collection.time_period_days,
        keywords=_rc.get("keywords", []),
        business_objectives=collection.business_objectives,
        subreddits=collection.subreddits,
        trends_geo=collection.trends_geo,
        news_country=collection.news_country,
        claude_model=analysis_cfg.claude_model,
        claude_temperature=analysis_cfg.claude_temperature,
    )
    (run_dir / "config.json").write_text(run_config.model_dump_json(indent=2), encoding="utf-8")

    # ── LLM client ──
    from consumer_research.utils.llm_client import create_llm_client
    llm_client = create_llm_client()

    # ── Stage 3: Filter ALL 1,208 items ──
    logger.info("\n── STAGE 3: RELEVANCE FILTERING (all 1,208 items) ──")
    from consumer_research.pipeline.filter import filter_corpus
    t3 = time.time()
    filtered = filter_corpus(
        corpus,
        collection.brand_name,
        collection.category,
        run_dir,
        llm_client,
        batch_size=analysis_cfg.batch_size,
    )
    logger.info(f"Stage 3 done in {time.time()-t3:.0f}s: {len(filtered)} relevant items")

    if len(filtered) < 5:
        logger.error("Too few items passed filter. Check filter logic and keywords.")
        sys.exit(1)

    # ── Stage 4: Analysis ──
    logger.info("\n── STAGE 4: ANALYSIS ──")
    from consumer_research.pipeline.analyze import analyze_corpus
    t4 = time.time()
    analysis_results = analyze_corpus(
        filtered,
        collection.brand_name,
        collection.category,
        run_dir,
        llm_client,
        batch_size=analysis_cfg.batch_size,
        min_items_for_theme=analysis.min_items_for_theme,
    )
    logger.info(f"Stage 4 done in {time.time()-t4:.0f}s: {len(analysis_results.themes)} themes")

    # ── Stage 5: Insight Synthesis ──
    logger.info("\n── STAGE 5: INSIGHT SYNTHESIS ──")
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
    logger.info(f"Stage 5 done in {time.time()-t5:.0f}s: {len(insights)} insights")

    # ── Stage 6: Scoring ──
    logger.info("\n── STAGE 6: SCORING ──")
    from consumer_research.pipeline.scoring import score_insights
    t6 = time.time()
    scored = score_insights(insights, analysis_results, filtered, run_dir, config=config.scoring)
    logger.info(f"Stage 6 done in {time.time()-t6:.0f}s: {len(scored)} scored insights")

    # ── Stage 7: Reports ──
    logger.info("\n── STAGE 7: REPORT GENERATION ──")
    report_dir = run_dir / "report"
    report_dir.mkdir(exist_ok=True)

    # PDF
    try:
        from consumer_research.report.pdf_generator import generate_pdf_report
        pdf_path = generate_pdf_report(scored, analysis_results, filtered, config, run_dir)
        logger.info(f"PDF: {pdf_path} ({pdf_path.stat().st_size:,} bytes)")
    except Exception as e:
        logger.warning(f"PDF failed (non-fatal): {e}")

    # PPTX
    try:
        from consumer_research.report.pptx_generator import generate_pptx_report
        pptx_path = generate_pptx_report(scored, analysis_results, filtered, config, run_dir)
        logger.info(f"PPTX: {pptx_path} ({pptx_path.stat().st_size:,} bytes)")
    except Exception as e:
        logger.error(f"PPTX failed: {e}")
        import traceback; traceback.print_exc()

    # ── Summary ──
    from consumer_research.models.schemas import ConfidenceTier, MatrixQuadrant, RunSummary
    platform_counts = {}
    for item in filtered:
        p = item.source_platform.value
        platform_counts[p] = platform_counts.get(p, 0) + 1

    logger.info("\n═══════════════════════════════════════")
    logger.info(f"Run ID:          {run_id}")
    logger.info(f"Items filtered:  {len(filtered)} / {len(corpus)}")
    logger.info(f"Platforms:       {platform_counts}")
    logger.info(f"Themes:          {len(analysis_results.themes)}")
    logger.info(f"Insights:        {len(insights)}")
    logger.info(f"High confidence: {sum(1 for s in scored if s.confidence_tier == ConfidenceTier.HIGH)}")
    logger.info(f"Key findings:    {sum(1 for s in scored if s.matrix_quadrant == MatrixQuadrant.KEY_FINDING)}")
    logger.info(f"Report dir:      {run_dir / 'report'}")
    logger.info("═══════════════════════════════════════")


if __name__ == "__main__":
    main()
