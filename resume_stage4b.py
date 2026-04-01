"""
Resume from theme extraction - sentiment already done in run 20260327_155821_1b7bc9.
Loads saved sentiment, runs two-pass theme extraction, then Stages 5→6→7.
"""
import json
import logging
import os
import sys
import time
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("resume_stage4b")


def main():
    # Load API key
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
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
        logger.error("Usage: python resume_stage4b.py <source_run_id>")
        sys.exit(1)
    source_run = ROOT / "consumer_research" / "runs" / source_run_id
    filtered_path = source_run / "filtered" / "corpus.json"
    analysis_path = source_run / "analysis" / "results.json"

    if not filtered_path.exists():
        logger.error(f"Filtered corpus not found: {filtered_path}")
        sys.exit(1)

    # New run directory
    run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"
    run_dir = ROOT / "consumer_research" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"New run: {run_id}")

    import shutil
    for stage in ["raw", "normalized", "filtered"]:
        src = source_run / stage
        dst = run_dir / stage
        if src.exists():
            shutil.copytree(str(src), str(dst))
    shutil.copy(str(source_run / "config.json"), str(run_dir / "config.json"))

    # Load filtered corpus
    from consumer_research.models.schemas import (
        NormalizedItem, Sentiment, SentimentResult,
        ConfidenceTier, MatrixQuadrant, AnalysisResults, Theme, VerbatimQuote,
    )
    filtered = [NormalizedItem.model_validate(i) for i in json.loads(filtered_path.read_text(encoding="utf-8"))]
    logger.info(f"Loaded {len(filtered)} filtered items")

    # Load existing sentiment results if available
    sentiment_results = []
    if analysis_path.exists():
        saved = json.loads(analysis_path.read_text(encoding="utf-8"))
        for sr in saved.get("sentiment_results", []):
            try:
                sentiment_results.append(SentimentResult(
                    item_id=sr["item_id"],
                    sentiment=Sentiment(sr["sentiment"]),
                    sentiment_score=sr.get("sentiment_score", 0.5),
                    reasoning=sr.get("reasoning", ""),
                    key_phrases=sr.get("key_phrases", []),
                    aspects_mentioned=sr.get("aspects_mentioned", []),
                ))
            except Exception:
                pass
        logger.info(f"Loaded {len(sentiment_results)} saved sentiment results (skipping re-classification)")

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
        max_corpus_size=999_999,
        min_items_for_theme=5,
    )
    config = PipelineConfig(collection=collection, analysis=analysis_cfg, scoring=ScoringConfig())

    from consumer_research.utils.llm_client import create_llm_client
    llm_client = create_llm_client()

    # Stage 4: Theme extraction only (sentiment already done)
    logger.info(f"\n── STAGE 4: THEME EXTRACTION (two-pass, fixed) ──")
    from consumer_research.pipeline.analyze import _extract_themes
    t4 = time.time()

    sentiment_map = {r.item_id: r for r in sentiment_results}

    themes = _extract_themes(
        filtered, sentiment_map, collection.brand_name, collection.category,
        llm_client, min_items=analysis_cfg.min_items_for_theme
    )

    # Cross-source triangulation
    item_map = {item.item_id: item for item in filtered}
    for theme in themes:
        platforms = set()
        for iid in theme.supporting_item_ids:
            if iid in item_map:
                platforms.add(item_map[iid].source_platform)
        theme.platforms_present = list(platforms)
        theme.is_multi_source = len(platforms) >= 2

        if theme.is_multi_source:
            from collections import Counter
            platform_sents: dict[str, list[str]] = {}
            for iid in theme.supporting_item_ids:
                if iid in item_map and iid in sentiment_map:
                    p = item_map[iid].source_platform.value
                    s = sentiment_map[iid].sentiment.value
                    platform_sents.setdefault(p, []).append(s)
            dominant = {p: Counter(sents).most_common(1)[0][0] for p, sents in platform_sents.items()}
            theme.is_contested = len(set(dominant.values())) > 1

    # Representative quotes
    for theme in themes:
        quotes = []
        for qid in getattr(theme, "_quote_ids", []):
            if qid in item_map:
                item = item_map[qid]
                engagement = item.platform_metadata.score or item.platform_metadata.like_count or 0
                quotes.append(VerbatimQuote(
                    text=item.content_text[:300],
                    item_id=qid,
                    source_url=item.source_url,
                    source_platform=item.source_platform,
                    source_timestamp=item.source_timestamp,
                    engagement_score=engagement,
                    selection_reason="Highest engagement among theme members",
                ))
        if not quotes and theme.supporting_item_ids:
            first_id = theme.supporting_item_ids[0]
            if first_id in item_map:
                item = item_map[first_id]
                quotes.append(VerbatimQuote(
                    text=item.content_text[:300],
                    item_id=first_id,
                    source_url=item.source_url,
                    source_platform=item.source_platform,
                    source_timestamp=item.source_timestamp,
                    engagement_score=item.platform_metadata.score or 0,
                    selection_reason="First item in theme (fallback)",
                ))
        theme.representative_quotes = quotes

    overall = {"positive": 0, "negative": 0, "neutral": 0, "mixed": 0}
    for r in sentiment_results:
        overall[r.sentiment.value] = overall.get(r.sentiment.value, 0) + 1

    analysis_results = AnalysisResults(
        sentiment_results=sentiment_results,
        themes=themes,
        overall_sentiment=overall,
        total_items_analyzed=len(filtered),
        analysis_model=llm_client.model_name,
        analysis_prompts={},
    )

    # Save analysis
    analysis_dir = run_dir / "analysis"
    analysis_dir.mkdir(exist_ok=True)
    (analysis_dir / "results.json").write_text(
        json.dumps(analysis_results.model_dump(mode="json"), indent=2, default=str),
        encoding="utf-8"
    )

    logger.info(f"Stage 4: {time.time()-t4:.0f}s | {len(themes)} themes")
    for t in themes:
        logger.info(f"  {t.theme_id} {t.theme_label}: {t.item_count} items ({t.prevalence_pct:.1f}%) multi={t.is_multi_source}")

    if len(themes) == 0:
        logger.error("No themes extracted. Check logs above for errors.")
        sys.exit(1)

    # Stage 5
    logger.info(f"\n── STAGE 5: INSIGHT SYNTHESIS ──")
    from consumer_research.pipeline.synthesize import synthesize_insights
    t5 = time.time()
    insights = synthesize_insights(
        analysis_results, filtered, collection.brand_name, collection.category,
        collection.business_objectives, run_dir, llm_client,
    )
    logger.info(f"Stage 5: {time.time()-t5:.0f}s | {len(insights)} insights")

    # Stage 6
    logger.info(f"\n── STAGE 6: SCORING ──")
    from consumer_research.pipeline.scoring import score_insights
    t6 = time.time()
    scored = score_insights(insights, analysis_results, filtered, run_dir, config=config.scoring)
    logger.info(f"Stage 6: {time.time()-t6:.0f}s | {len(scored)} scored")

    # Stage 7
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

    # Summary
    platform_counts = {}
    for item in filtered:
        p = item.source_platform.value
        platform_counts[p] = platform_counts.get(p, 0) + 1

    logger.info("\n═══════════════════════════════════════")
    logger.info(f"Run ID:          {run_id}")
    logger.info(f"Items analyzed:  {len(filtered)}")
    logger.info(f"Platforms:       {platform_counts}")
    logger.info(f"Themes:          {len(themes)}")
    logger.info(f"Insights:        {len(insights)}")
    logger.info(f"High confidence: {sum(1 for s in scored if s.confidence_tier == ConfidenceTier.HIGH)}")
    logger.info(f"Key findings:    {sum(1 for s in scored if s.matrix_quadrant == MatrixQuadrant.KEY_FINDING)}")
    logger.info(f"Report:          {run_dir / 'report' / 'report.pptx'}")
    logger.info("═══════════════════════════════════════")


if __name__ == "__main__":
    main()
