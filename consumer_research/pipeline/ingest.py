"""Generic data ingestion — converts any JSON data into NormalizedItems.

Supports two input modes:
1. Scraper output: Data from built-in collectors (Reddit, YouTube, etc.)
2. External JSON: Pre-collected data in any of these formats:
   - Platform-scraped format (Twitter/YouTube/Reddit/Instagram with metadata_content, engagements, comments)
   - Simple format: list of {"text": "...", "source": "...", "url": "...", "date": "..."}
   - CSV-exported format: flat records with text, platform, date columns

The ingester auto-detects the format and normalizes everything into NormalizedItem objects.

Usage:
    from consumer_research.pipeline.ingest import ingest_external_data
    items = ingest_external_data(Path("data/my_data.json"), collection_query="brand study")
"""
from __future__ import annotations

import hashlib
import json
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from consumer_research.models.schemas import (
    ContentType,
    NormalizedItem,
    PlatformMetadata,
    SourcePlatform,
)

logger = logging.getLogger(__name__)

# Platform detection from source field
PLATFORM_PATTERNS = {
    "twitter": SourcePlatform.TWITTER,
    "tweet": SourcePlatform.TWITTER,
    "x.com": SourcePlatform.TWITTER,
    "reddit": SourcePlatform.REDDIT,
    "youtube": SourcePlatform.YOUTUBE,
    "yt": SourcePlatform.YOUTUBE,
    "instagram": SourcePlatform.INSTAGRAM,
    "ig": SourcePlatform.INSTAGRAM,
    "news": SourcePlatform.NEWS,
    "academic": SourcePlatform.ACADEMIC,
    "amazon": SourcePlatform.AMAZON,
    "flipkart": SourcePlatform.FLIPKART,
}


def _detect_platform(source: str) -> SourcePlatform | None:
    """Detect platform from source field, URL, or platform name."""
    s = source.lower()
    for pattern, platform in PLATFORM_PATTERNS.items():
        if pattern in s:
            return platform
    return None


def _generate_item_id(source_url: str, content_text: str) -> str:
    """Deterministic SHA-256 ID."""
    raw = f"{source_url}|{content_text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _parse_timestamp(ts_str: str | None) -> datetime | None:
    """Parse timestamp from various formats."""
    if not ts_str:
        return None
    try:
        dt = datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        pass
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(str(ts_str), fmt).replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
    return None


def _detect_format(data: list[dict]) -> str:
    """Auto-detect the JSON format by scanning a sample of records."""
    if not data:
        return "empty"

    # Scan first 20 items to detect mixed formats
    sample_size = min(20, len(data))
    has_platform_scraped = False
    has_ecommerce = False
    has_simple = False
    has_normalized = False

    for item in data[:sample_size]:
        keys = set(item.keys())
        if "metadata_content" in keys and "engagements" in keys:
            has_platform_scraped = True
        elif "reviews" in keys and "product_details" in keys:
            has_ecommerce = True
        elif "item_id" in keys and "source_platform" in keys and "content_text" in keys:
            has_normalized = True
        elif "text" in keys or "content" in keys:
            has_simple = True

    # If first sample didn't catch all formats, do a broader check
    if sample_size < len(data) and not (has_platform_scraped and has_ecommerce):
        for item in data[sample_size::max(1, len(data) // 100)]:
            keys = set(item.keys())
            if not has_platform_scraped and "metadata_content" in keys:
                has_platform_scraped = True
            if not has_ecommerce and "reviews" in keys and "product_details" in keys:
                has_ecommerce = True
            if has_platform_scraped and has_ecommerce:
                break

    format_count = sum([has_platform_scraped, has_ecommerce, has_simple, has_normalized])
    if format_count > 1:
        return "mixed"
    if has_platform_scraped:
        return "platform_scraped"
    if has_ecommerce:
        return "ecommerce"
    if has_normalized:
        return "normalized"
    if has_simple:
        return "simple"
    return "unknown"


def _apply_engagement_thresholds(
    items: list[NormalizedItem],
    config=None,
) -> list[NormalizedItem]:
    """Apply platform-specific engagement thresholds to filter low-engagement items.

    Thresholds by platform type:
    - Social (Reddit, YouTube, Twitter, Instagram): min likes/upvotes (default 2)
    - Review (Amazon, Flipkart): min helpful votes (default 1)
    - Editorial (News, Academic, Web, Trends): no threshold

    Posts are never filtered - only comments/replies. This preserves discussion
    context while filtering noise from low-engagement responses.
    """
    if config is None:
        from consumer_research.config import CollectionConfig
        config = CollectionConfig(brand_name="", category="")

    # Platform -> (engagement field, threshold)
    thresholds = {
        SourcePlatform.REDDIT: config.reddit_min_score,
        SourcePlatform.YOUTUBE: config.youtube_min_likes,
        SourcePlatform.TWITTER: config.twitter_min_likes,
        SourcePlatform.INSTAGRAM: config.instagram_min_likes,
    }
    review_threshold = config.review_min_helpful_votes
    # No threshold for: NEWS, ACADEMIC, TRENDS, WEB

    filtered = []
    dropped_counts: dict[str, int] = {}

    for item in items:
        platform = item.source_platform

        # Posts are never engagement-filtered (they frame discussions)
        if item.content_type == ContentType.POST:
            # But review posts (Amazon/Flipkart) ARE filtered since every item is a review
            if platform.value in ("amazon", "flipkart"):
                score = item.platform_metadata.score or 0
                if score < review_threshold:
                    dropped_counts[platform.value] = dropped_counts.get(platform.value, 0) + 1
                    continue
            filtered.append(item)
            continue

        # Comments: apply social platform thresholds
        if platform in thresholds:
            engagement = item.platform_metadata.score or item.platform_metadata.like_count or 0
            if engagement < thresholds[platform]:
                dropped_counts[platform.value] = dropped_counts.get(platform.value, 0) + 1
                continue

        # Review platform comments (if any)
        if platform.value in ("amazon", "flipkart"):
            score = item.platform_metadata.score or 0
            if score < review_threshold:
                dropped_counts[platform.value] = dropped_counts.get(platform.value, 0) + 1
                continue

        filtered.append(item)

    if dropped_counts:
        total_dropped = sum(dropped_counts.values())
        logger.info(
            f"Engagement filter: dropped {total_dropped} low-engagement items "
            f"({', '.join(f'{p}: {n}' for p, n in sorted(dropped_counts.items()))})"
        )

    return filtered


def ingest_external_data(
    data_path: Path,
    collection_query: str = "external",
    min_content_length: int = 10,
    min_comment_length: int = 5,
    config=None,
) -> list[NormalizedItem]:
    """Ingest external JSON data into NormalizedItems.

    Auto-detects the format and handles:
    - Platform-scraped format (Twitter/YouTube/Reddit/Instagram with nested comments)
    - Simple format (flat list of text + source + url + date)
    - Pre-normalized format (already NormalizedItem dicts)

    Applies platform-specific engagement thresholds after ingestion.

    Args:
        data_path: Path to JSON file
        collection_query: Query string to record in items
        min_content_length: Skip posts shorter than this
        min_comment_length: Skip comments shorter than this
        config: Optional CollectionConfig with engagement thresholds

    Returns:
        List of NormalizedItem objects ready for normalization pipeline
    """
    logger.info(f"Loading {data_path.name}...")
    raw_data = json.loads(data_path.read_text(encoding="utf-8-sig"))  # utf-8-sig handles BOM-encoded files

    if not isinstance(raw_data, list):
        if isinstance(raw_data, dict) and "items" in raw_data:
            raw_data = raw_data["items"]
        elif isinstance(raw_data, dict) and "data" in raw_data:
            raw_data = raw_data["data"]
        else:
            logger.error(f"Expected a JSON array or dict with 'items'/'data' key, got {type(raw_data)}")
            return []

    logger.info(f"Loaded {len(raw_data)} records")
    fmt = _detect_format(raw_data)
    logger.info(f"Detected format: {fmt}")

    if fmt == "normalized":
        items = [NormalizedItem(**d) for d in raw_data]
    elif fmt == "platform_scraped":
        items = _ingest_platform_scraped(raw_data, collection_query, min_content_length, min_comment_length)
    elif fmt == "ecommerce":
        items = _ingest_ecommerce_reviews(raw_data, collection_query, min_content_length)
    elif fmt == "mixed":
        items = _ingest_mixed(raw_data, collection_query, min_content_length, min_comment_length)
    elif fmt == "simple":
        items = _ingest_simple(raw_data, collection_query, min_content_length)
    else:
        logger.warning(f"Unknown format, attempting simple ingestion")
        items = _ingest_simple(raw_data, collection_query, min_content_length)

    # Apply engagement thresholds (social >= 2 likes/upvotes, review >= 1 helpful vote)
    return _apply_engagement_thresholds(items, config)


def _ingest_platform_scraped(
    raw_data: list[dict],
    collection_query: str,
    min_content_length: int,
    min_comment_length: int,
) -> list[NormalizedItem]:
    """Ingest platform-scraped format with metadata_content, engagements, comments."""
    now = datetime.now(timezone.utc)
    items = []
    skipped_empty = 0
    skipped_short = 0

    for post in raw_data:
        platform_enum = _detect_platform(post.get("source", ""))
        if not platform_enum:
            continue
        platform = platform_enum.value

        mc = post.get("metadata_content", {})
        ps = post.get("profile_stats", {})
        eng = post.get("engagements", {})
        url = post.get("url", "")
        post_id = post.get("id", "")
        annotations = post.get("metadata_annotations", {})
        user_info = post.get("user_info", {})

        # Extract post text by platform
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

        # Parse timestamp
        source_ts = _parse_timestamp(mc.get("created_at", mc.get("date", mc.get("published_at"))))

        # Build platform metadata
        def _safe_int(val):
            if val is None:
                return None
            try:
                return int(val)
            except (ValueError, TypeError):
                return None

        meta = PlatformMetadata(
            score=_safe_int(eng.get("score", eng.get("likes"))),
            like_count=_safe_int(eng.get("likes")),
            view_count=_safe_int(eng.get("views")),
            num_comments=_safe_int(eng.get("comments")),
            share_count=_safe_int(eng.get("shares")),
            subreddit=ps.get("subreddit") if platform == "reddit" else None,
            video_id=post_id if platform == "youtube" else None,
            video_title=mc.get("title") if platform == "youtube" else None,
            followers=_safe_int(ps.get("followers")) if ps else None,
            thread_id=post_id,
            region=annotations.get("region") if isinstance(annotations, dict) else None,
        )

        # Create post item
        text = (text or "").strip()
        if not text:
            skipped_empty += 1
        elif len(text) < min_content_length:
            skipped_short += 1
        else:
            item = NormalizedItem(
                item_id=_generate_item_id(url or post_id, text),
                source_platform=platform_enum,
                source_url=url or f"https://{platform}.com/{post_id}",
                source_author=ps.get("username") or (user_info.get("username") if isinstance(user_info, dict) else None) or "Unknown",
                source_timestamp=source_ts,
                collected_at=now,
                content_text=text,
                content_type=ContentType.POST,
                platform_metadata=meta,
                collection_query=collection_query,
                collection_method="external_data_import",
            )
            items.append(item)

        # Process comments
        for comment in post.get("comments", []):
            c_text, c_author, c_url, c_ts, c_score = _extract_comment(comment, platform, url, post_id)

            if not c_text:
                skipped_empty += 1
                continue
            if len(c_text) < min_comment_length:
                skipped_short += 1
                continue

            c_meta = PlatformMetadata(
                score=c_score,
                thread_id=post_id,
                comment_depth=0,
                subreddit=ps.get("subreddit") if platform == "reddit" else None,
                video_id=post_id if platform == "youtube" else None,
                region=comment.get("comment_annotations", {}).get("region") if isinstance(comment.get("comment_annotations"), dict) else None,
            )

            c_item = NormalizedItem(
                item_id=_generate_item_id(c_url, c_text),
                source_platform=platform_enum,
                source_url=c_url,
                source_author=c_author,
                source_timestamp=c_ts,
                collected_at=now,
                content_text=c_text,
                content_type=ContentType.COMMENT,
                platform_metadata=c_meta,
                collection_query=collection_query,
                collection_method="external_data_import",
            )
            items.append(c_item)

    logger.info(f"Ingested {len(items)} items (skipped {skipped_empty} empty, {skipped_short} short)")
    plat_counts = Counter(i.source_platform.value for i in items)
    type_counts = Counter(i.content_type.value for i in items)
    logger.info(f"By platform: {dict(plat_counts)}")
    logger.info(f"By type: {dict(type_counts)}")
    return items


def _extract_comment(comment: dict, platform: str, parent_url: str, post_id: str):
    """Extract comment fields by platform. Returns (text, author, url, timestamp, score)."""
    if platform == "reddit":
        text = comment.get("content", "").strip()
        author = comment.get("author", "Unknown")
        url = f"{parent_url}#comment_{comment.get('id', '')}"
        ts = _parse_timestamp(comment.get("created_at"))
        score = comment.get("score")
        return text, author, url, ts, score

    elif platform == "instagram":
        text = comment.get("text", "").strip()
        author = comment.get("username", "Unknown")
        user_id = comment.get("user_id", "")
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:8] if text else "empty"
        url = f"{parent_url}#comment_{user_id}_{text_hash}"
        score = comment.get("likes", comment.get("score"))
        return text, author, url, None, score

    elif platform == "youtube":
        text = comment.get("content", "").strip()
        author = comment.get("author_name", comment.get("author", "Unknown"))
        url = f"{parent_url}#comment_{comment.get('id', '')}"
        ts = _parse_timestamp(comment.get("time", comment.get("created_at")))
        votes = comment.get("votes")
        score = int(votes) if isinstance(votes, (int, float)) else None
        return text, author, url, ts, score

    elif platform == "twitter":
        text = comment.get("content", comment.get("text", "")).strip()
        author = comment.get("username", comment.get("author", "Unknown"))
        url = f"{parent_url}#reply_{comment.get('id', '')}"
        ts = _parse_timestamp(comment.get("created_at"))
        score = comment.get("likes", comment.get("score"))
        return text, author, url, ts, score

    return "", "Unknown", "", None, None


def _ingest_ecommerce_reviews(
    raw_data: list[dict],
    collection_query: str,
    min_content_length: int,
) -> list[NormalizedItem]:
    """Ingest e-commerce review format: products with asin, reviews[], product_details."""
    import re

    now = datetime.now(timezone.utc)
    items = []
    skipped = 0

    for product in raw_data:
        reviews = product.get("reviews", [])
        if not reviews:
            continue
        pd = product.get("product_details", {})
        title = pd.get("title", "")
        if not title or title == "Unknown Product":
            continue

        platform_enum = _detect_platform(product.get("source", ""))
        if not platform_enum:
            platform_enum = SourcePlatform.AMAZON

        product_url = pd.get("url", "")
        asin = product.get("asin", "")

        for review in reviews:
            text = (review.get("content") or "").strip()
            review_title = (review.get("review_title") or "").strip()
            if review_title and text:
                text = f"{review_title}: {text}"
            elif review_title:
                text = review_title

            if not text or len(text) < min_content_length:
                skipped += 1
                continue

            # Parse star rating
            star_str = review.get("review_star_rating", "")
            try:
                star_rating = int(float(star_str)) if star_str else None
            except (ValueError, TypeError):
                star_rating = None

            # Parse review date: "Reviewed in India on 28 December 2025"
            review_ts = None
            date_str = review.get("review_date", "")
            if date_str:
                m = re.search(r"(\d{1,2})\s+(\w+)\s+(\d{4})", date_str)
                if m:
                    try:
                        review_ts = datetime.strptime(
                            f"{m.group(1)} {m.group(2)} {m.group(3)}", "%d %B %Y"
                        ).replace(tzinfo=timezone.utc)
                    except ValueError:
                        pass

            author = review.get("review_author", "Unknown")
            review_url = f"{product_url}#review_{hashlib.sha256(text.encode('utf-8')).hexdigest()[:8]}"

            meta = PlatformMetadata(
                score=star_rating,
                thread_id=asin,
            )

            item = NormalizedItem(
                item_id=_generate_item_id(review_url, text),
                source_platform=platform_enum,
                source_url=review_url,
                source_author=author,
                source_timestamp=review_ts,
                collected_at=now,
                content_text=text,
                content_type=ContentType.REVIEW,
                platform_metadata=meta,
                collection_query=collection_query,
                collection_method="external_data_import",
            )
            items.append(item)

    logger.info(f"Ingested {len(items)} e-commerce reviews (skipped {skipped} short)")
    plat_counts = Counter(i.source_platform.value for i in items)
    logger.info(f"By platform: {dict(plat_counts)}")
    return items


def _ingest_mixed(
    raw_data: list[dict],
    collection_query: str,
    min_content_length: int,
    min_comment_length: int,
) -> list[NormalizedItem]:
    """Ingest mixed-format data by routing each item to the right sub-ingester."""
    platform_scraped = []
    ecommerce = []
    simple = []

    for item in raw_data:
        keys = set(item.keys())
        if "metadata_content" in keys and "engagements" in keys:
            platform_scraped.append(item)
        elif "reviews" in keys and "product_details" in keys:
            ecommerce.append(item)
        else:
            simple.append(item)

    items = []
    if platform_scraped:
        logger.info(f"Mixed format: {len(platform_scraped)} platform-scraped records")
        items.extend(_ingest_platform_scraped(platform_scraped, collection_query, min_content_length, min_comment_length))
    if ecommerce:
        logger.info(f"Mixed format: {len(ecommerce)} e-commerce records")
        items.extend(_ingest_ecommerce_reviews(ecommerce, collection_query, min_content_length))
    if simple:
        logger.info(f"Mixed format: {len(simple)} simple records")
        items.extend(_ingest_simple(simple, collection_query, min_content_length))

    logger.info(f"Mixed format total: {len(items)} items")
    plat_counts = Counter(i.source_platform.value for i in items)
    type_counts = Counter(i.content_type.value for i in items)
    logger.info(f"By platform: {dict(plat_counts)}")
    logger.info(f"By type: {dict(type_counts)}")
    return items


def _ingest_simple(
    raw_data: list[dict],
    collection_query: str,
    min_content_length: int,
) -> list[NormalizedItem]:
    """Ingest simple flat format: [{"text": "...", "source": "reddit", "url": "...", "date": "..."}]."""
    now = datetime.now(timezone.utc)
    items = []

    # Auto-detect field names from first record
    sample = raw_data[0] if raw_data else {}
    text_field = next((k for k in ["text", "content", "content_text", "body", "message", "caption", "title"] if k in sample), None)
    source_field = next((k for k in ["source", "platform", "source_platform", "channel"] if k in sample), None)
    url_field = next((k for k in ["url", "source_url", "link", "permalink"] if k in sample), None)
    date_field = next((k for k in ["date", "created_at", "timestamp", "published_at", "time"] if k in sample), None)
    author_field = next((k for k in ["author", "username", "user", "source_author", "screen_name"] if k in sample), None)

    if not text_field:
        logger.error(f"Cannot find text field in data. Available keys: {list(sample.keys())}")
        return []

    logger.info(f"Field mapping: text={text_field}, source={source_field}, url={url_field}, date={date_field}, author={author_field}")

    for record in raw_data:
        text = str(record.get(text_field, "")).strip()
        if not text or len(text) < min_content_length:
            continue

        platform_enum = _detect_platform(str(record.get(source_field, ""))) if source_field else None
        if not platform_enum:
            platform_enum = SourcePlatform.REDDIT  # default fallback

        url = str(record.get(url_field, "")) if url_field else ""
        source_ts = _parse_timestamp(record.get(date_field)) if date_field else None
        author = str(record.get(author_field, "Unknown")) if author_field else "Unknown"

        item = NormalizedItem(
            item_id=_generate_item_id(url or text[:50], text),
            source_platform=platform_enum,
            source_url=url,
            source_author=author,
            source_timestamp=source_ts,
            collected_at=now,
            content_text=text,
            content_type=ContentType.POST,
            platform_metadata=PlatformMetadata(thread_id=url or _generate_item_id(url, text)),
            collection_query=collection_query,
            collection_method="external_data_import",
        )
        items.append(item)

    logger.info(f"Ingested {len(items)} items from simple format")
    plat_counts = Counter(i.source_platform.value for i in items)
    logger.info(f"By platform: {dict(plat_counts)}")
    return items
