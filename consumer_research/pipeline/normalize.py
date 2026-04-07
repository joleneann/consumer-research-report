"""Stage 2: Data normalization and deduplication.

Takes raw items from multiple collectors, ensures they all conform to the
unified NormalizedItem schema, deduplicates by item_id, and writes the
result to normalized/corpus.json.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from consumer_research.models.schemas import NormalizedItem

logger = logging.getLogger(__name__)


def normalize_and_deduplicate(
    items_by_source: dict[str, list[NormalizedItem]],
    run_dir: Path,
) -> list[NormalizedItem]:
    """Normalize items from all sources and remove duplicates.

    Args:
        items_by_source: Dict mapping source name to list of NormalizedItems.
        run_dir: The run directory to write output files.

    Returns:
        Deduplicated list of NormalizedItems.
    """
    all_items: list[NormalizedItem] = []
    for source_name, items in items_by_source.items():
        logger.info(f"  {source_name}: {len(items)} items")
        all_items.extend(items)

    # Deduplicate by item_id
    seen: dict[str, NormalizedItem] = {}
    duplicates = 0
    for item in all_items:
        if item.item_id in seen:
            duplicates += 1
        else:
            seen[item.item_id] = item

    deduped = list(seen.values())

    # Thread-level cap: max 5 comments per thread to prevent single threads dominating
    # Selection is random (not engagement-sorted) to avoid privileging viral voices
    MAX_COMMENTS_PER_THREAD = 5
    import random
    random.seed(42)  # Reproducibility
    random.shuffle(deduped)

    thread_counts: dict[str, int] = {}
    thread_capped: list[NormalizedItem] = []
    thread_dropped = 0

    for item in deduped:
        tid = item.platform_metadata.thread_id
        if tid and item.content_type.value == "comment":
            count = thread_counts.get(tid, 0)
            if count >= MAX_COMMENTS_PER_THREAD:
                thread_dropped += 1
                continue
            thread_counts[tid] = count + 1
        thread_capped.append(item)

    if thread_dropped:
        logger.info(f"Thread-level cap: dropped {thread_dropped} excess comments (max {MAX_COMMENTS_PER_THREAD}/thread)")

    deduped = thread_capped

    # Sort by timestamp (newest first) - normalize all timestamps to UTC-aware
    def _sort_key(x):
        ts = x.source_timestamp
        if ts is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts

    deduped.sort(key=_sort_key, reverse=True)

    # Write output
    normalized_dir = run_dir / "normalized"
    normalized_dir.mkdir(parents=True, exist_ok=True)

    corpus_path = normalized_dir / "corpus.json"
    corpus_data = [item.model_dump(mode="json") for item in deduped]
    corpus_path.write_text(json.dumps(corpus_data, indent=2, default=str), encoding="utf-8")

    # Write stats
    platform_counts = {}
    for item in deduped:
        platform_counts[item.source_platform.value] = platform_counts.get(
            item.source_platform.value, 0
        ) + 1

    stats = {
        "total_before_dedup": len(all_items),
        "duplicates_removed": duplicates,
        "total_after_dedup": len(deduped),
        "items_by_platform": platform_counts,
        "date_range": {
            "earliest": str(min(
                (_sort_key(i) for i in deduped if i.source_timestamp),
                default="N/A",
            )),
            "latest": str(max(
                (_sort_key(i) for i in deduped if i.source_timestamp),
                default="N/A",
            )),
        },
    }
    stats_path = normalized_dir / "stats.json"
    stats_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")

    logger.info(
        f"Normalization complete: {len(all_items)} → {len(deduped)} items "
        f"({duplicates} duplicates removed)"
    )
    logger.info(f"Platform breakdown: {platform_counts}")

    return deduped


def load_corpus(run_dir: Path) -> list[NormalizedItem]:
    """Load a previously normalized corpus from disk."""
    corpus_path = run_dir / "normalized" / "corpus.json"
    data = json.loads(corpus_path.read_text(encoding="utf-8"))
    return [NormalizedItem(**item) for item in data]
