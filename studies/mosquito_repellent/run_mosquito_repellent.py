"""
Run consumer research pipeline for Mosquito Repellent category using pre-collected
external data from 'data/data mosquit repellent.json'.

Data: 5,665 posts + 110,782 comments from Twitter, YouTube, Instagram, Reddit.
Skips Stage 1 (collection) - ingests external data directly, then runs
Stages 2-7 (normalize, filter, analyze, synthesize, score, report).

Usage:
    python studies/mosquito_repellent/run_mosquito_repellent.py
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

ROOT = Path(__file__).parent.parent.parent  # project root
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_mosquito_repellent")

# -- Constants --
DATA_FILE = ROOT / "data" / "data mosquit repellent.json"
BRAND_NAME = "Mosquito Repellent"
CATEGORY = "household insect protection / personal care"
MIN_CONTENT_LENGTH = 10
MIN_COMMENT_LENGTH = 5

BUSINESS_OBJECTIVES = [
    "Understand how mosquitoes disrupt sleep and what consumers do about it",
    "Map the product category landscape: coils, vaporizers, sprays, nets, electronic devices, natural remedies",
    "Identify which brands surface organically in consumer conversation",
    "Surface safety and health concerns around chemical repellents (DEET, transfluthrin, prallethrin), especially for children and babies",
    "Explore the natural vs chemical repellent tension and what drives consumer choice",
    "Identify unmet needs and product innovation opportunities",
    "Understand use context segmentation: indoor nighttime vs outdoor/hiking vs travel vs baby/child protection",
    "Assess how disease prevention (dengue, malaria) fear drives repellent purchase vs simple comfort/annoyance",
]

KEYWORDS = [
    "mosquito repellent", "mosquito killer", "bug spray", "insect repellent",
    "mosquito net", "mosquito coil", "Good Knight", "All Out", "Mortein",
    "Odomos", "Thermacell", "DEET", "citronella", "mosquito bite",
    "dengue prevention", "malaria prevention", "mosquito sleep",
    "electric mosquito killer", "mosquito vaporizer", "natural repellent",
]


def detect_platform(source: str) -> str:
    s = source.lower()
    if "reddit" in s:
        return "reddit"
    elif "instagram" in s:
        return "instagram"
    elif "youtube" in s:
        return "youtube"
    elif "twitter" in s:
        return "twitter"
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
        post_id = post.get("id", "")
        annotations = post.get("metadata_annotations", {})
        user_info = post.get("user_info", {})

        # -- Extract post text by platform --
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
            text = mc.get("caption", "") or mc.get("content", "")
        elif platform == "youtube":
            title = mc.get("title", "")
            desc = mc.get("description", "")
            text = f"{title}\n\n{desc}" if desc else title
        else:
            text = mc.get("content", "") or mc.get("caption", "") or mc.get("title", "")

        # -- Parse timestamp --
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

        # -- Build platform metadata --
        if platform == "twitter":
            meta = PlatformMetadata(
                score=eng.get("likes"),
                like_count=eng.get("likes"),
                view_count=eng.get("views"),
                num_comments=eng.get("comments"),
                share_count=eng.get("shares"),
                thread_id=post_id,
                region=annotations.get("region") if annotations else None,
            )
            source_platform = SourcePlatform.TWITTER
        elif platform == "reddit":
            meta = PlatformMetadata(
                score=eng.get("score"),
                subreddit=ps.get("subreddit"),
                num_comments=eng.get("comments"),
                thread_id=post_id,
                region=annotations.get("region") if annotations else None,
            )
            source_platform = SourcePlatform.REDDIT
        elif platform == "instagram":
            meta = PlatformMetadata(
                like_count=eng.get("likes"),
                view_count=eng.get("views"),
                num_comments=eng.get("comments"),
                share_count=eng.get("shares"),
                followers=ps.get("followers") if ps else None,
                engagement_rate=eng.get("engagement_rate") if isinstance(eng.get("engagement_rate"), (int, float)) and eng.get("engagement_rate") else None,
                media_type=mc.get("media_type"),
                thread_id=post_id,
                region=annotations.get("region") if annotations else None,
            )
            source_platform = SourcePlatform.INSTAGRAM
        elif platform == "youtube":
            meta = PlatformMetadata(
                like_count=int(eng.get("likes", 0) or 0) if eng.get("likes") else None,
                view_count=int(eng.get("views", 0) or 0) if eng.get("views") else None,
                video_id=post_id,
                video_title=mc.get("title"),
                num_comments=int(eng.get("comments", 0) or 0) if eng.get("comments") else None,
                thread_id=post_id,
                region=annotations.get("region") if annotations else None,
            )
            source_platform = SourcePlatform.YOUTUBE
        else:
            continue

        # -- Create post item --
        text = (text or "").strip()
        if not text:
            skipped_empty += 1
        elif len(text) < MIN_CONTENT_LENGTH:
            skipped_short += 1
        else:
            item = NormalizedItem(
                item_id=generate_item_id(url or post_id, text),
                source_platform=source_platform,
                source_url=url or f"https://{platform}.com/{post_id}",
                source_author=ps.get("username") or user_info.get("username") or "Unknown",
                source_timestamp=source_ts,
                collected_at=now,
                content_text=text,
                content_type=ContentType.POST,
                platform_metadata=meta,
                collection_query="mosquito repellent",
                collection_method="external_data_import",
            )
            items.append(item)

        # -- Process comments --
        for comment in post.get("comments", []):
            if platform == "twitter":
                # Twitter posts typically don't have nested comments in this format
                continue
            elif platform == "reddit":
                c_text = comment.get("content", "").strip()
                c_author = comment.get("author", "Unknown")
                c_url = f"{url}#comment_{comment.get('id', '')}"
                c_score = comment.get("score")
                c_region = comment.get("comment_annotations", {}).get("region") if comment.get("comment_annotations") else None
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
                c_meta = PlatformMetadata(
                    score=c_score,
                    subreddit=ps.get("subreddit"),
                    thread_id=post_id,
                    comment_depth=0,
                    region=c_region,
                )
                c_platform = SourcePlatform.REDDIT
            elif platform == "instagram":
                c_text = comment.get("text", "").strip()
                c_author = comment.get("username", "Unknown")
                user_id = comment.get("user_id", "")
                text_hash = hashlib.sha256(c_text.encode("utf-8")).hexdigest()[:8]
                c_url = f"{url}#comment_{user_id}_{text_hash}"
                c_ts = None
                c_region = comment.get("comment_annotations", {}).get("region") if comment.get("comment_annotations") else None
                c_meta = PlatformMetadata(
                    thread_id=post_id,
                    comment_depth=0,
                    region=c_region,
                )
                c_platform = SourcePlatform.INSTAGRAM
            elif platform == "youtube":
                c_text = comment.get("content", "").strip()
                c_author = comment.get("author_name", comment.get("author", "Unknown"))
                c_url = f"{url}#comment_{comment.get('id', '')}"
                c_ts = None
                c_ts_str = comment.get("time", comment.get("created_at", ""))
                if c_ts_str:
                    try:
                        c_ts = datetime.fromisoformat(c_ts_str.replace("Z", "+00:00"))
                        if c_ts.tzinfo is None:
                            c_ts = c_ts.replace(tzinfo=timezone.utc)
                    except (ValueError, TypeError):
                        pass
                c_votes = comment.get("votes")
                c_meta = PlatformMetadata(
                    thread_id=post_id,
                    video_id=post_id,
                    comment_depth=0,
                    score=c_votes if isinstance(c_votes, int) else None,
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
                source_author=c_author,
                source_timestamp=c_ts,
                collected_at=now,
                content_text=c_text,
                content_type=ContentType.COMMENT,
                platform_metadata=c_meta,
                collection_query="mosquito repellent",
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


def main():
    # -- Load .env --
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()

    if not DATA_FILE.exists():
        logger.error(f"Data file not found: {DATA_FILE}")
        sys.exit(1)

    # -- New run directory --
    run_id = f"mosquito_repellent_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"
    run_dir = ROOT / "consumer_research" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"New run: {run_id}")

    # -- Stage 0: Brief --
    brief_data = {
        "brand_name": BRAND_NAME,
        "category": CATEGORY,
        "business_questions": BUSINESS_OBJECTIVES,
        "aspects": ["sleep_disruption", "product_type", "brand_perception", "safety",
                     "natural_vs_chemical", "child_safety", "disease_prevention",
                     "efficacy", "cost", "innovation"],
        "target_audience": "Global consumers dealing with mosquito problems",
        "competitors": [],
        "geographic_focus": "",
        "time_period_months": 12,
        "additional_context": (
            "Category-level study on mosquito repellent consumer behaviour. "
            "Data from Dec 2024 - Dec 2025 across Twitter, YouTube, Instagram, Reddit. "
            "Heavy focus on sleep disruption use case from search queries."
        ),
    }
    (run_dir / "brief.json").write_text(json.dumps(brief_data, indent=2), encoding="utf-8")
    logger.info("Stage 0: Brief saved")

    # -- Save run config --
    from consumer_research.config import CollectionConfig, PipelineConfig, ScoringConfig
    from consumer_research.models.schemas import RunConfig

    collection = CollectionConfig(
        brand_name=BRAND_NAME,
        category=CATEGORY,
        time_period_days=365,
        business_objectives=BUSINESS_OBJECTIVES,
        keywords=KEYWORDS,
        competitors=[],
        trends_geo="",
        news_country="",
    )
    config = PipelineConfig(collection=collection, scoring=ScoringConfig())

    run_config = RunConfig(
        run_id=run_id,
        created_at=datetime.now(timezone.utc),
        brand_name=BRAND_NAME,
        category=CATEGORY,
        time_period_days=365,
        keywords=KEYWORDS,
        business_objectives=BUSINESS_OBJECTIVES,
        subreddits=[],
        trends_geo="",
        news_country="",
        claude_model="claude-sonnet-4-20250514",
        claude_temperature=0.0,
    )
    (run_dir / "config.json").write_text(run_config.model_dump_json(indent=2), encoding="utf-8")

    # -- Ingest external data --
    logger.info("\n== INGESTING EXTERNAL DATA ==")
    t_ingest = time.time()
    items = ingest_data(DATA_FILE)

    raw_dir = run_dir / "raw"
    raw_dir.mkdir(exist_ok=True)
    raw_items = [item.model_dump(mode="json") for item in items]
    (raw_dir / "external.json").write_text(
        json.dumps(raw_items, indent=None, default=str), encoding="utf-8"
    )
    logger.info(f"Ingestion done in {time.time()-t_ingest:.0f}s, saved {len(items)} items")

    # -- Stage 2: Normalize & dedup --
    logger.info("\n== STAGE 2: NORMALIZATION ==")
    from consumer_research.pipeline.normalize import normalize_and_deduplicate
    t2 = time.time()
    corpus = normalize_and_deduplicate({"external": items}, run_dir)
    logger.info(f"Stage 2 done in {time.time()-t2:.0f}s: {len(corpus)} items after dedup + thread cap")

    logger.info(f"\n== INGESTION COMPLETE ==")
    logger.info(f"Run directory: {run_dir}")
    logger.info(f"Corpus: {len(corpus)} items ready for Stage 3+")
    logger.info(f"Next: Run in-context analysis (Stages 3-7) in Claude Code session")

    return run_dir, corpus, config


if __name__ == "__main__":
    main()
