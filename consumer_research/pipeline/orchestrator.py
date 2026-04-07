"""Pipeline orchestrator - runs all 8 stages in sequence.

Stage 0: User Brief → brief.json
Stage 1: Data Collection → raw/ (ALL collectors at MAX limits)
Stage 2: Normalization + Thread-level Dedup → normalized/corpus.json
Stage 3: Relevance Filtering → filtered/corpus.json + rejected.json
Stage 4: Analysis → analysis/results.json (sentiment, themes, triangulation)
Stage 5: Insight Synthesis → insights/insights.json
Stage 6: Scoring → scored/scored_insights.json (confidence + signal strength)
Stage 7: Report Generation → report/report.docx + report.pdf + report.pptx

Google Trends data is separated from the opinion pipeline and used as a
quantitative validation layer in the report.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from consumer_research.collectors.academic import AcademicCollector
from consumer_research.collectors.web_search import WebSearchCollector
from consumer_research.collectors.news import NewsCollector
from consumer_research.collectors.reddit_mcp import RedditCollector
from consumer_research.collectors.trends import TrendsCollector
from consumer_research.collectors.youtube import YouTubeCollector
from consumer_research.config import RUNS_DIR, PipelineConfig
from consumer_research.models.schemas import (
    ConfidenceTier,
    RunConfig,
    RunSummary,
)
from consumer_research.pipeline.analyze import analyze_corpus
from consumer_research.pipeline.brief import ResearchBrief, create_brief_from_args
from consumer_research.pipeline.filter import filter_corpus
from consumer_research.pipeline.normalize import normalize_and_deduplicate
from consumer_research.pipeline.scoring import score_insights
from consumer_research.pipeline.synthesize import synthesize_insights
from consumer_research.utils.keywords import get_flat_keywords
from consumer_research.utils.llm_client import create_llm_client

logger = logging.getLogger(__name__)


def run_pipeline(config: PipelineConfig, brief: ResearchBrief | None = None) -> Path:
    """Execute the full 8-stage pipeline.

    Args:
        config: Complete pipeline configuration.
        brief: Optional pre-built research brief. If None, created from config.

    Returns:
        Path to the run directory containing all outputs.
    """
    start_time = time.time()

    # Create run directory
    run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # ── Stage 0: Brief ──
    logger.info("── STAGE 0: BRIEF ──")
    if brief is None:
        brief = create_brief_from_args(
            brand_name=config.collection.brand_name,
            category=config.collection.category,
            keywords=config.collection.keywords,
            objectives=config.collection.business_objectives,
            competitors=config.collection.competitors,
            geo=config.collection.trends_geo,
        )
    brief.save(run_dir)

    # Expand keywords from brief
    keywords = get_flat_keywords(brief)
    logger.info(f"Keywords expanded: {len(keywords)} total")

    # Save run config for reproducibility
    run_config = RunConfig(
        run_id=run_id,
        created_at=datetime.now(timezone.utc),
        brand_name=config.collection.brand_name,
        category=config.collection.category,
        time_period_days=config.collection.time_period_days,
        keywords=keywords,
        business_objectives=config.collection.business_objectives,
        subreddits=config.collection.subreddits,
        trends_geo=config.collection.trends_geo,
        news_country=config.collection.news_country,
        claude_model=config.analysis.claude_model,
        claude_temperature=config.analysis.claude_temperature,
    )
    (run_dir / "config.json").write_text(
        run_config.model_dump_json(indent=2), encoding="utf-8"
    )

    logger.info(f"\n=== Pipeline run {run_id} for '{config.collection.brand_name}' ===")

    # ── Stage 1: Data Collection (ALL at MAX limits) ──
    logger.info("\n── STAGE 1: DATA COLLECTION (MAX LIMITS) ──")
    opinion_items, trends_items = _collect_data(config, keywords, run_dir)

    # ── Stage 2: Normalization (opinion data only — trends separated) ──
    logger.info("\n── STAGE 2: NORMALIZATION ──")
    corpus = normalize_and_deduplicate(opinion_items, run_dir)

    # ── Stage 3: Relevance Filtering ──
    logger.info("\n── STAGE 3: RELEVANCE FILTERING ──")
    llm_client = create_llm_client(model=config.analysis.claude_model)

    filtered = filter_corpus(
        corpus,
        config.collection.brand_name,
        config.collection.category,
        run_dir,
        llm_client,
        batch_size=config.analysis.batch_size,
    )

    # ── Stage 4: Analysis ──
    # Note: the automated pipeline always uses LLM-backed analysis regardless of corpus size.
    # "In-context" vs "keyword_narrative" is a workflow-level distinction, not a code branch:
    # - Automated pipeline (this path): always calls analyze_corpus() via the LLM API
    # - Manual in-context workflow: a human reads items directly inside a Claude Code session
    logger.info("\n── STAGE 4: ANALYSIS ──")
    analysis = analyze_corpus(
        filtered,
        config.collection.brand_name,
        config.collection.category,
        run_dir,
        llm_client,
        batch_size=config.analysis.batch_size,
        min_items_for_theme=config.analysis.min_items_for_theme,
    )

    # ── Theme coverage validation gate (Procedure 15 enforcement) ──
    from consumer_research.pipeline.validate import validate_theme_coverage
    coverage = validate_theme_coverage(
        analysis, filtered, max_unthemed_pct=config.analysis.max_unthemed_pct
    )
    if not coverage["passed"] and config.analysis.narrative_pass_required:
        logger.error(
            "Refusing to proceed to Stage 5 with >10% unthemed items. "
            "Run narrative review pass first, then resume from Stage 5."
        )
        return run_dir

    # ── Stage 5: Insight Synthesis ──
    logger.info("\n── STAGE 5: INSIGHT SYNTHESIS ──")
    insights = synthesize_insights(
        analysis,
        filtered,
        config.collection.brand_name,
        config.collection.category,
        config.collection.business_objectives,
        run_dir,
        llm_client,
    )

    # ── Stage 6: Scoring (fully data-driven — no LLM needed) ──
    logger.info("\n── STAGE 6: SCORING ──")
    scored = score_insights(
        insights,
        analysis,
        filtered,
        run_dir,
        config=config.scoring,
    )

    # ── Stage 7: Report Generation ──
    logger.info("\n── STAGE 7: REPORT GENERATION ──")
    report_dir = run_dir / "report"
    report_dir.mkdir(parents=True, exist_ok=True)

    # Save trends data separately for the report's quantitative layer
    if trends_items.get("trends"):
        trends_report_path = report_dir / "trends_data.json"
        trends_data = [item.model_dump(mode="json") for item in trends_items["trends"]]
        trends_report_path.write_text(
            json.dumps(trends_data, indent=2, default=str), encoding="utf-8"
        )
        logger.info(f"Trends data saved for report ({len(trends_items['trends'])} data points)")

    try:
        from consumer_research.report.pdf_generator import generate_pdf_report
        generate_pdf_report(scored, analysis, filtered, config, run_dir)
        logger.info("PDF report generated.")
    except ImportError:
        logger.warning("PDF generator not yet implemented. Skipping PDF.")

    try:
        from consumer_research.report.pptx_generator import generate_pptx_report
        generate_pptx_report(scored, analysis, filtered, config, run_dir)
        logger.info("PPTX report generated.")
    except ImportError:
        logger.warning("PPTX generator not yet implemented. Skipping PPTX.")

    try:
        from consumer_research.report.charts import generate_all_charts
        from consumer_research.report.docx_generator import generate_docx_report
        generate_all_charts(analysis, scored, filtered, report_dir)
        generate_docx_report(scored, analysis, filtered, config, run_dir)
        logger.info("DOCX report generated.")
    except ImportError:
        logger.warning("DOCX generator not available. Skipping DOCX.")
    except Exception as e:
        logger.error(f"DOCX generation failed: {e}")

    # ── Write Summary ──
    duration = time.time() - start_time
    platform_counts = {}
    for item in filtered:
        platform_counts[item.source_platform.value] = (
            platform_counts.get(item.source_platform.value, 0) + 1
        )

    summary = RunSummary(
        run_id=run_id,
        brand_name=config.collection.brand_name,
        total_collected=sum(len(v) for v in opinion_items.values()) + sum(len(v) for v in trends_items.values()),
        total_after_filter=len(filtered),
        total_rejected=len(corpus) - len(filtered),
        items_by_platform=platform_counts,
        themes_extracted=len(analysis.themes),
        insights_generated=len(insights),
        insights_passed_quality_gates=sum(1 for i in insights if i.passed_quality_gates),
        high_confidence_insights=sum(
            1 for s in scored if s.confidence_tier == ConfidenceTier.HIGH
        ),
        duration_seconds=round(duration, 1),
    )
    (run_dir / "summary.json").write_text(
        summary.model_dump_json(indent=2), encoding="utf-8"
    )

    logger.info(f"\n=== Pipeline complete in {duration:.1f}s ===")
    logger.info(f"Run directory: {run_dir}")
    logger.info(f"Items: {summary.total_collected} collected → {summary.total_after_filter} filtered")
    logger.info(f"Themes: {summary.themes_extracted}")
    logger.info(f"Insights: {summary.insights_generated} ({summary.insights_passed_quality_gates} passed gates)")
    logger.info(f"High confidence: {summary.high_confidence_insights}")

    return run_dir


def _collect_data(
    config: PipelineConfig,
    keywords: list[str],
    run_dir: Path,
) -> tuple[dict[str, list], dict[str, list]]:
    """Run all collectors. Returns (opinion_items, trends_items) separately.

    Google Trends data is NOT mixed into the opinion pipeline.
    It goes to the report as a quantitative validation layer.
    """
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    cc = config.collection

    opinion_items: dict[str, list] = {}
    trends_items: dict[str, list] = {}

    def _safe_collect(name: str, collector, brand: str, kws: list, save_path, target_dict: dict, key: str):
        """Wrapper: no single collector failure crashes the pipeline."""
        try:
            items = collector.collect(brand, kws)
            target_dict[key] = items
            _save_raw(save_path, items)
            logger.info(f"  {name}: {len(items)} items collected")
        except Exception as e:
            logger.error(f"  {name} FAILED (non-fatal): {e}")
            target_dict[key] = []
            _save_raw(save_path, [])

    # Reddit (OPINION — max limits)
    logger.info("Collecting from Reddit (max limits)...")
    _safe_collect("Reddit", RedditCollector(
        subreddits=cc.subreddits,
        max_posts=cc.reddit_max_posts,
        max_comments_per_post=cc.reddit_max_comments_per_post,
    ), cc.brand_name, keywords, raw_dir / "reddit.json", opinion_items, "reddit")

    # YouTube (OPINION — max limits)
    logger.info("Collecting from YouTube (max limits)...")
    _safe_collect("YouTube", YouTubeCollector(
        max_videos=cc.youtube_max_videos,
        max_comments_per_video=cc.youtube_max_comments_per_video,
        region_code=cc.trends_geo,
    ), cc.brand_name, keywords, raw_dir / "youtube.json", opinion_items, "youtube")

    # News (OPINION — max limits)
    logger.info("Collecting from NewsData.io (max limits)...")
    _safe_collect("NewsData", NewsCollector(
        language=cc.news_language,
        country=cc.news_country,
        max_articles=cc.news_max_articles,
    ), cc.brand_name, keywords, raw_dir / "news.json", opinion_items, "news")

    # Academic (EVIDENCE — max limits)
    logger.info("Collecting from OpenAlex (max limits)...")
    _safe_collect("Academic", AcademicCollector(
        max_papers=cc.academic_max_papers,
    ), cc.brand_name, keywords, raw_dir / "academic.json", opinion_items, "academic")

    # Web Search via Serper (WEB — broader coverage)
    logger.info("Collecting from Serper/Google Search (web-wide)...")
    _safe_collect("Serper", WebSearchCollector(
        max_results=100,
    ), cc.brand_name, keywords[:8], raw_dir / "web_search.json", opinion_items, "web")

    # Google Trends (QUANTITATIVE — separated from opinion pipeline)
    logger.info("Collecting from Google Trends (quantitative layer)...")
    _safe_collect("Google Trends", TrendsCollector(
        geo=cc.trends_geo,
    ), cc.brand_name, keywords[:4], raw_dir / "trends.json", trends_items, "trends")

    opinion_total = sum(len(v) for v in opinion_items.values())
    trends_total = sum(len(v) for v in trends_items.values())
    logger.info(f"Total: {opinion_total} opinion items + {trends_total} trends data points")

    # ── POST-COLLECTION QUALITY AUDIT ──
    # Sample 50 items per collector and check brand-mention rate.
    # Warns if a collector has <50% brand-relevant content.
    import random as _rand
    brand_lower = cc.brand_name.lower()
    brand_check_terms = {brand_lower, brand_lower.replace(" ", "")}
    if "thums" in brand_lower:
        brand_check_terms.update(["thumbs up", "thumsup", "thumbsup"])

    logger.info("Post-collection quality audit:")
    for source_name, items in opinion_items.items():
        if not items:
            continue
        sample = _rand.sample(items, min(50, len(items)))
        brand_hits = sum(
            1 for i in sample
            if any(bt in i.content_text.lower() for bt in brand_check_terms)
        )
        rate = brand_hits / len(sample) * 100
        status = "OK" if rate >= 50 else "LOW - consider tighter queries"
        logger.info(f"  {source_name}: {brand_hits}/{len(sample)} sampled items mention brand ({rate:.0f}%) [{status}]")

    return opinion_items, trends_items


def _save_raw(path: Path, items: list) -> None:
    """Save raw collector output to disk."""
    data = [item.model_dump(mode="json") for item in items]
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
