"""
Run consumer research pipeline for Make in India using pre-collected
external data from 'data make in india.json'.

Data: 6,261 posts + 291,588 comments from Twitter, YouTube, Reddit, Instagram.
Skips Stage 1 (collection) - ingests external data directly, then runs
Stages 2-7 (normalize, filter, analyze, synthesize, score, report).

Usage:
    python run_make_in_india.py
"""
import hashlib
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_make_in_india")

# ── Constants ──
DATA_FILE = ROOT / "data make in india.json"
BRAND_NAME = "Make in India"
CATEGORY = "government initiative / economic policy / consumer nationalism"
MIN_CONTENT_LENGTH = 10
MIN_COMMENT_LENGTH = 5

BUSINESS_OBJECTIVES = [
    "Understand public sentiment toward the Make in India initiative - is it seen as succeeding or failing?",
    "Map consumer purchase behaviour - are people actually buying Indian over imported? What drives the choice?",
    "Assess Vocal for Local adoption - has it translated into sustained behaviour change or is it performative?",
    "Identify quality perception gaps - how do consumers perceive Made in India product quality vs. imports?",
    "Surface sector-specific perceptions - which sectors are seen as MII successes vs. failures?",
    "Understand how US-India tariff tensions and trade war have shaped the Make in India conversation in 2025",
    "Explore the nationalism vs. pragmatism tension - where does patriotic buying end and practical choice begin?",
    "Assess how Indian startups, D2C brands, and homegrown companies are perceived in this conversation",
]


def detect_platform(source: str) -> str:
    s = source.lower()
    if "twitter" in s:
        return "twitter"
    elif "reddit" in s:
        return "reddit"
    elif "instagram" in s:
        return "instagram"
    elif "youtube" in s:
        return "youtube"
    return "unknown"


def generate_item_id(source_url: str, content_text: str) -> str:
    raw = f"{source_url}|{content_text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def ingest_data(data_path: Path) -> list:
    """Transform external JSON into NormalizedItem dicts."""
    from consumer_research.models.schemas import (
        ContentType,
        NormalizedItem,
        PlatformMetadata,
        SourcePlatform,
    )

    logger.info(f"Loading {data_path.name}...")
    raw_data = json.loads(data_path.read_text(encoding="utf-8"))
    logger.info(f"Loaded {len(raw_data)} posts from external data")

    now = datetime.now(timezone.utc)
    items = []
    skipped_empty = 0
    skipped_short = 0

    for post in raw_data:
        platform = detect_platform(post.get("source", ""))
        mc = post.get("metadata_content", {})
        ps = post.get("profile_stats", {})
        eng = post.get("engagements", {})
        url = post.get("url", "")
        post_id = post.get("id", str(post.get("metadata_id", "")))
        annotations = post.get("metadata_annotations", {})
        if isinstance(annotations, str):
            try:
                annotations = json.loads(annotations.replace("'", '"'))
            except Exception:
                annotations = {}

        # ── Extract post text by platform ──
        if platform == "twitter":
            text = mc.get("content", "")
        elif platform == "reddit":
            text = mc.get("content", "")
            title = mc.get("title", "")
            if title and text:
                text = f"{title}\n\n{text}"
            elif title:
                text = title
        elif platform == "instagram":
            text = mc.get("caption", mc.get("content", ""))
        elif platform == "youtube":
            title = mc.get("title", "")
            desc = mc.get("description", "")
            text = f"{title}\n\n{desc}" if desc else title
        else:
            text = mc.get("content", "") or mc.get("caption", "") or mc.get("title", "")

        # ── Parse timestamp ──
        ts_str = mc.get("created_at", "")
        source_ts = None
        if ts_str:
            try:
                source_ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if source_ts.tzinfo is None:
                    source_ts = source_ts.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                try:
                    source_ts = datetime.strptime(ts_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    pass

        # ── Build platform metadata ──
        if platform == "twitter":
            meta = PlatformMetadata(
                like_count=_safe_int(eng.get("likes")),
                view_count=_safe_int(eng.get("views")),
                num_comments=_safe_int(eng.get("comments")),
                retweet_count=_safe_int(eng.get("shares")),
                quote_count=_safe_int(eng.get("quotes")),
                bookmark_count=_safe_int(eng.get("bookmarks")),
                engagement_rate=eng.get("engagement_rate") if isinstance(eng.get("engagement_rate"), (int, float)) else None,
                thread_id=str(post_id),
                region=annotations.get("region") if isinstance(annotations, dict) else None,
            )
            source_platform = SourcePlatform.TWITTER
        elif platform == "reddit":
            meta = PlatformMetadata(
                score=eng.get("score"),
                subreddit=ps.get("subreddit"),
                num_comments=eng.get("comments"),
                thread_id=str(post_id),
                region=annotations.get("region") if isinstance(annotations, dict) else None,
            )
            source_platform = SourcePlatform.REDDIT
        elif platform == "instagram":
            meta = PlatformMetadata(
                like_count=_safe_int(eng.get("likes")),
                view_count=_safe_int(eng.get("views")),
                num_comments=_safe_int(eng.get("comments")),
                share_count=_safe_int(eng.get("shares")),
                followers=_safe_int(ps.get("followers")),
                engagement_rate=eng.get("engagement_rate") if isinstance(eng.get("engagement_rate"), (int, float)) else None,
                media_type=mc.get("media_type"),
                thread_id=str(post_id),
                region=annotations.get("region") if isinstance(annotations, dict) else None,
            )
            source_platform = SourcePlatform.INSTAGRAM
        elif platform == "youtube":
            meta = PlatformMetadata(
                like_count=_safe_int(eng.get("likes")),
                view_count=_safe_int(eng.get("views")),
                video_id=str(post_id),
                video_title=mc.get("title"),
                num_comments=_safe_int(eng.get("comments")),
                thread_id=str(post_id),
                region=annotations.get("region") if isinstance(annotations, dict) else None,
            )
            source_platform = SourcePlatform.YOUTUBE
        else:
            continue

        # ── Create post item ──
        text = (text or "").strip()
        if not text:
            skipped_empty += 1
        elif len(text) < MIN_CONTENT_LENGTH:
            skipped_short += 1
        else:
            item = NormalizedItem(
                item_id=generate_item_id(url or str(post_id), text),
                source_platform=source_platform,
                source_url=url or f"https://{platform}.com/{post_id}",
                source_author=ps.get("username", "Unknown"),
                source_timestamp=source_ts,
                collected_at=now,
                content_text=text,
                content_type=ContentType.POST,
                platform_metadata=meta,
                collection_query=post.get("search_query", "Make in India"),
                collection_method="external_data_import",
            )
            items.append(item)

        # ── Process comments ──
        for idx, comment in enumerate(post.get("comments", [])):
            if platform == "twitter":
                c_text = comment.get("text", "").strip()
                c_author = comment.get("username", "Unknown")
                c_url = f"{url}#reply_{c_author}_{idx}"
                c_ts = None
                c_ts_str = comment.get("created_at", "")
                if c_ts_str:
                    try:
                        c_ts = datetime.fromisoformat(c_ts_str.replace("Z", "+00:00"))
                        if c_ts.tzinfo is None:
                            c_ts = c_ts.replace(tzinfo=timezone.utc)
                    except (ValueError, TypeError):
                        try:
                            c_ts = datetime.strptime(c_ts_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                        except (ValueError, TypeError):
                            pass
                c_ann = comment.get("comment_annotations", {})
                if isinstance(c_ann, str):
                    try:
                        c_ann = json.loads(c_ann.replace("'", '"'))
                    except Exception:
                        c_ann = {}
                c_meta = PlatformMetadata(
                    thread_id=str(post_id),
                    comment_depth=0,
                    region=c_ann.get("region") if isinstance(c_ann, dict) else None,
                )
                c_platform = SourcePlatform.TWITTER

            elif platform == "reddit":
                c_text = comment.get("content", "").strip()
                c_author = comment.get("author", "Unknown")
                c_url = f"{url}#comment_{comment.get('id', idx)}"
                c_ts = None
                c_ts_str = comment.get("created_at", "")
                if c_ts_str:
                    try:
                        c_ts = datetime.fromisoformat(c_ts_str.replace("Z", "+00:00"))
                        if c_ts.tzinfo is None:
                            c_ts = c_ts.replace(tzinfo=timezone.utc)
                    except (ValueError, TypeError):
                        try:
                            c_ts = datetime.strptime(c_ts_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                        except (ValueError, TypeError):
                            pass
                c_ann = comment.get("comment_annotations", {})
                if isinstance(c_ann, str):
                    try:
                        c_ann = json.loads(c_ann.replace("'", '"'))
                    except Exception:
                        c_ann = {}
                c_meta = PlatformMetadata(
                    score=comment.get("score"),
                    subreddit=ps.get("subreddit"),
                    thread_id=str(post_id),
                    comment_depth=0,
                    region=c_ann.get("region") if isinstance(c_ann, dict) else None,
                )
                c_platform = SourcePlatform.REDDIT

            elif platform == "instagram":
                c_text = comment.get("text", "").strip()
                c_author = comment.get("username", "Unknown")
                user_id = comment.get("user_id", "")
                text_hash = hashlib.sha256(c_text.encode("utf-8")).hexdigest()[:8]
                c_url = f"{url}#comment_{user_id}_{text_hash}"
                c_ts = None
                c_ann = comment.get("comment_annotations", {})
                if isinstance(c_ann, str):
                    try:
                        c_ann = json.loads(c_ann.replace("'", '"'))
                    except Exception:
                        c_ann = {}
                c_meta = PlatformMetadata(
                    thread_id=str(post_id),
                    comment_depth=0,
                    region=c_ann.get("region") if isinstance(c_ann, dict) else None,
                )
                c_platform = SourcePlatform.INSTAGRAM

            elif platform == "youtube":
                c_text = comment.get("content", "").strip()
                c_author = comment.get("author_name", comment.get("author", "Unknown"))
                c_url = f"{url}#comment_{comment.get('id', idx)}"
                c_ts = None
                c_ts_str = comment.get("time", comment.get("created_at", ""))
                if c_ts_str:
                    try:
                        c_ts = datetime.fromisoformat(c_ts_str.replace("Z", "+00:00"))
                        if c_ts.tzinfo is None:
                            c_ts = c_ts.replace(tzinfo=timezone.utc)
                    except (ValueError, TypeError):
                        try:
                            c_ts = datetime.strptime(c_ts_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                        except (ValueError, TypeError):
                            pass
                c_ann = comment.get("comment_annotations", {})
                if isinstance(c_ann, str):
                    try:
                        c_ann = json.loads(c_ann.replace("'", '"'))
                    except Exception:
                        c_ann = {}
                c_meta = PlatformMetadata(
                    thread_id=str(post_id),
                    video_id=str(post_id),
                    comment_depth=0,
                    region=c_ann.get("region") if isinstance(c_ann, dict) else None,
                )
                c_platform = SourcePlatform.YOUTUBE
            else:
                continue

            if not c_text:
                skipped_empty += 1
                continue
            if len(c_text) < MIN_COMMENT_LENGTH:
                skipped_short += 1
                continue

            c_item = NormalizedItem(
                item_id=generate_item_id(c_url, c_text),
                source_platform=c_platform,
                source_url=c_url,
                source_author=c_author or "Unknown",
                source_timestamp=c_ts,
                collected_at=now,
                content_text=c_text,
                content_type=ContentType.COMMENT,
                platform_metadata=c_meta,
                collection_query=post.get("search_query", "Make in India"),
                collection_method="external_data_import",
            )
            items.append(c_item)

    logger.info(f"Ingested {len(items)} items (skipped {skipped_empty} empty, {skipped_short} short)")

    from collections import Counter
    plat_counts = Counter(i.source_platform.value for i in items)
    type_counts = Counter(i.content_type.value for i in items)
    logger.info(f"By platform: {dict(plat_counts)}")
    logger.info(f"By type: {dict(type_counts)}")

    return items


def _safe_int(val) -> int | None:
    """Convert string/float to int safely, return None on failure."""
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def main():
    # ── Load .env ──
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()

    # ── Check API key ──
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        logger.error("ANTHROPIC_API_KEY is not set.")
        sys.exit(1)
    logger.info(f"API key: {api_key[:20]}...")

    if not DATA_FILE.exists():
        logger.error(f"Data file not found: {DATA_FILE}")
        sys.exit(1)

    # ── New run directory ──
    run_id = f"make_in_india_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"
    run_dir = ROOT / "consumer_research" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"New run: {run_id}")

    # ── Stage 0: Brief ──
    brief_data = {
        "brand_name": BRAND_NAME,
        "category": CATEGORY,
        "business_questions": BUSINESS_OBJECTIVES,
        "aspects": [
            "policy_effectiveness", "quality_perception", "price_competitiveness",
            "nationalism_patriotism", "sector_performance", "tariff_trade",
            "consumer_behaviour", "startup_ecosystem", "employment_impact",
        ],
        "target_audience": "Indian citizens, consumers, entrepreneurs, and policy observers",
        "competitors": ["China manufacturing", "Bangladesh exports", "Vietnam manufacturing",
                        "imported goods", "Chinese products"],
        "geographic_focus": "IN",
        "time_period_months": 12,
        "additional_context": (
            "Policy/movement-level study covering the Make in India initiative and Vocal for Local movement. "
            "Data from Jan-Dec 2025 across Twitter, YouTube, Reddit, Instagram. "
            "Covers policy perception, consumer nationalism, tariff tensions, sector analysis, D2C brands."
        ),
    }
    (run_dir / "brief.json").write_text(json.dumps(brief_data, indent=2), encoding="utf-8")
    logger.info("Stage 0: Brief saved")

    # ── Ingest external data ──
    logger.info("\n== INGESTING EXTERNAL DATA ==")
    t_ingest = time.time()
    items = ingest_data(DATA_FILE)

    raw_dir = run_dir / "raw"
    raw_dir.mkdir(exist_ok=True)
    raw_items = [item.model_dump(mode="json") for item in items]
    (raw_dir / "external.json").write_text(
        json.dumps(raw_items, indent=None, default=str), encoding="utf-8"
    )
    logger.info(f"Ingestion done in {time.time()-t_ingest:.0f}s, saved {len(items)} items to raw/external.json")

    # ── Stage 2: Normalize & dedup ──
    logger.info("\n== STAGE 2: NORMALIZATION ==")
    from consumer_research.pipeline.normalize import normalize_and_deduplicate
    t2 = time.time()
    corpus = normalize_and_deduplicate({"external": items}, run_dir)
    logger.info(f"Stage 2 done in {time.time()-t2:.0f}s: {len(corpus)} items after dedup + thread cap")

    # ── Save run config ──
    from consumer_research.config import (
        AnalysisConfig,
        CollectionConfig,
        PipelineConfig,
        ScoringConfig,
    )
    from consumer_research.models.schemas import RunConfig

    collection = CollectionConfig(
        brand_name=BRAND_NAME,
        category=CATEGORY,
        time_period_days=365,
        business_objectives=BUSINESS_OBJECTIVES,
        competitors=["China", "Bangladesh", "Vietnam", "imported goods"],
        subreddits=[],
        trends_geo="IN",
        news_country="in",
    )
    analysis_cfg = AnalysisConfig(
        claude_model="claude-sonnet-4-20250514",
        claude_temperature=0.0,
        batch_size=15,
        max_corpus_size=999_999,
        min_items_for_theme=5,
    )
    config = PipelineConfig(collection=collection, analysis=analysis_cfg, scoring=ScoringConfig())

    run_config = RunConfig(
        run_id=run_id,
        created_at=datetime.now(timezone.utc),
        brand_name=BRAND_NAME,
        category=CATEGORY,
        time_period_days=365,
        keywords=["Make in India", "Made in India", "Vocal for Local", "Atmanirbhar Bharat",
                   "Swadeshi", "Buy Indian", "Indian brands", "Indian manufacturing",
                   "PLI scheme", "tariff", "import vs Indian", "D2C India"],
        business_objectives=BUSINESS_OBJECTIVES,
        subreddits=[],
        trends_geo="IN",
        news_country="in",
        claude_model=analysis_cfg.claude_model,
        claude_temperature=analysis_cfg.claude_temperature,
    )
    (run_dir / "config.json").write_text(run_config.model_dump_json(indent=2), encoding="utf-8")

    # ── LLM client ──
    from consumer_research.utils.llm_client import create_llm_client
    llm_client = create_llm_client()

    # ── Stage 3: Relevance filtering ──
    logger.info(f"\n== STAGE 3: RELEVANCE FILTERING ({len(corpus)} items) ==")
    from consumer_research.pipeline.filter import filter_corpus
    t3 = time.time()
    filtered = filter_corpus(
        corpus,
        BRAND_NAME,
        CATEGORY,
        run_dir,
        llm_client,
        batch_size=analysis_cfg.batch_size,
    )
    logger.info(f"Stage 3 done in {time.time()-t3:.0f}s: {len(filtered)} relevant items")

    if len(filtered) < 5:
        logger.error("Too few items passed filter. Check filter logic.")
        sys.exit(1)

    # ── Stage 4: Analysis ──
    logger.info(f"\n== STAGE 4: ANALYSIS ({len(filtered)} items) ==")
    from consumer_research.pipeline.analyze import analyze_corpus
    t4 = time.time()
    analysis_results = analyze_corpus(
        filtered,
        BRAND_NAME,
        CATEGORY,
        run_dir,
        llm_client,
        batch_size=analysis_cfg.batch_size,
        min_items_for_theme=analysis_cfg.min_items_for_theme,
    )
    logger.info(f"Stage 4 done in {time.time()-t4:.0f}s: {len(analysis_results.themes)} themes")

    # ── Stage 5: Insight synthesis ──
    logger.info("\n== STAGE 5: INSIGHT SYNTHESIS ==")
    from consumer_research.pipeline.synthesize import synthesize_insights
    t5 = time.time()
    insights = synthesize_insights(
        analysis_results,
        filtered,
        BRAND_NAME,
        CATEGORY,
        BUSINESS_OBJECTIVES,
        run_dir,
        llm_client,
    )
    logger.info(f"Stage 5 done in {time.time()-t5:.0f}s: {len(insights)} insights")

    # ── Stage 6: Scoring ──
    logger.info("\n== STAGE 6: SCORING ==")
    from consumer_research.pipeline.scoring import score_insights, compute_brand_health
    t6 = time.time()
    scored = score_insights(insights, analysis_results, filtered, run_dir, config=config.scoring)
    brand_health = compute_brand_health(analysis_results, filtered)
    logger.info(f"Stage 6 done in {time.time()-t6:.0f}s: {len(scored)} scored insights")

    # Save brand health
    analysis_data = json.loads((run_dir / "analysis" / "results.json").read_text(encoding="utf-8"))
    analysis_data["brand_health"] = brand_health
    (run_dir / "analysis" / "results.json").write_text(
        json.dumps(analysis_data, indent=2, default=str), encoding="utf-8"
    )

    # ── Stage 7: Reports ──
    logger.info("\n== STAGE 7: REPORT GENERATION ==")
    report_dir = run_dir / "report"
    report_dir.mkdir(exist_ok=True)

    from consumer_research.report.charts import generate_all_charts
    charts = generate_all_charts(
        analysis=analysis_results,
        scored_insights=scored,
        items=filtered,
        output_dir=report_dir,
    )
    logger.info(f"Charts: {sum(1 for v in charts.values() if v)} generated")

    from consumer_research.report.docx_generator import generate_docx_report
    docx_path = generate_docx_report(
        scored_insights=scored,
        analysis=analysis_results,
        items=filtered,
        config=config,
        run_dir=run_dir,
        brand_health=brand_health,
    )
    logger.info(f"DOCX: {docx_path} ({docx_path.stat().st_size:,} bytes)")

    # ── Summary ──
    from consumer_research.models.schemas import ConfidenceTier, MatrixQuadrant
    platform_counts = {}
    for item in filtered:
        p = item.source_platform.value
        platform_counts[p] = platform_counts.get(p, 0) + 1

    logger.info("\n" + "=" * 50)
    logger.info(f"Run ID:          {run_id}")
    logger.info(f"Items filtered:  {len(filtered)} / {len(corpus)}")
    logger.info(f"Platforms:       {platform_counts}")
    logger.info(f"Themes:          {len(analysis_results.themes)}")
    logger.info(f"Insights:        {len(insights)}")
    logger.info(f"NSS:             {analysis_results.net_sentiment_score:+.2%}")
    logger.info(f"Brand Health:    {brand_health.get('overall_score', 'N/A')}/100")
    logger.info(f"High confidence: {sum(1 for s in scored if s.confidence_tier == ConfidenceTier.HIGH)}")
    logger.info(f"Key findings:    {sum(1 for s in scored if s.matrix_quadrant == MatrixQuadrant.KEY_FINDING)}")
    logger.info(f"Report:          {docx_path}")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
