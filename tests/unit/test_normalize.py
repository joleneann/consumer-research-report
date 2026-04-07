"""Unit tests for pipeline/normalize.py — no API calls required."""
import json
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from consumer_research.models.schemas import (
    ContentType,
    NormalizedItem,
    PlatformMetadata,
    SourcePlatform,
)
from consumer_research.pipeline.normalize import normalize_and_deduplicate


def _make_item(
    item_id: str,
    content_text: str = "Sample text content",
    source_platform: SourcePlatform = SourcePlatform.REDDIT,
    content_type: ContentType = ContentType.COMMENT,
    thread_id: str | None = None,
    score: int | None = None,
    like_count: int | None = None,
    source_timestamp: datetime | None = None,
) -> NormalizedItem:
    meta = PlatformMetadata(
        thread_id=thread_id,
        score=score,
        like_count=like_count,
    )
    return NormalizedItem(
        item_id=item_id,
        source_platform=source_platform,
        source_url=f"https://example.com/{item_id}",
        collected_at=datetime.now(timezone.utc),
        content_text=content_text,
        content_type=content_type,
        platform_metadata=meta,
        collection_query="test",
        collection_method="test",
        source_timestamp=source_timestamp,
    )


# ── Deduplication ──────────────────────────────────────────────────────────────

class TestDeduplication:
    def test_exact_duplicate_removed(self, tmp_path):
        item = _make_item("aaa")
        result = normalize_and_deduplicate({"source_a": [item, item]}, tmp_path)
        assert len(result) == 1

    def test_different_ids_kept(self, tmp_path):
        items = [_make_item(f"id{i}") for i in range(5)]
        result = normalize_and_deduplicate({"source_a": items}, tmp_path)
        assert len(result) == 5

    def test_cross_source_duplicate_removed(self, tmp_path):
        item = _make_item("shared_id")
        result = normalize_and_deduplicate(
            {"source_a": [item], "source_b": [item]}, tmp_path
        )
        assert len(result) == 1

    def test_empty_sources_returns_empty(self, tmp_path):
        result = normalize_and_deduplicate({}, tmp_path)
        assert result == []

    def test_empty_source_list_returns_empty(self, tmp_path):
        result = normalize_and_deduplicate({"source_a": []}, tmp_path)
        assert result == []


# ── Thread-level cap ──────────────────────────────────────────────────────────

class TestThreadLevelCap:
    def test_max_5_comments_per_thread(self, tmp_path):
        items = [_make_item(f"id{i}", thread_id="thread1", score=i) for i in range(10)]
        result = normalize_and_deduplicate({"src": items}, tmp_path)
        # Only 5 of the 10 comments should remain
        assert len(result) == 5

    def test_thread_cap_uses_random_selection(self, tmp_path):
        """Thread cap should use random selection, NOT engagement-based."""
        items = [_make_item(f"id{i}", thread_id="thread1", score=i) for i in range(10)]
        result = normalize_and_deduplicate({"src": items}, tmp_path)
        kept_ids = sorted([i.item_id for i in result])
        # 5 kept
        assert len(kept_ids) == 5
        # Must NOT be the top-5-by-engagement set (id5-id9)
        engagement_sorted_top5 = sorted([f"id{i}" for i in range(5, 10)])
        assert kept_ids != engagement_sorted_top5, (
            "Thread cap kept the highest-engagement items - random selection is broken"
        )
        # Seeded (42) random selection produces this exact set
        assert kept_ids == ["id2", "id3", "id5", "id7", "id8"]

    def test_posts_not_capped(self, tmp_path):
        # Posts (not comments) should not be subject to thread cap
        items = [
            _make_item(
                f"post{i}",
                content_type=ContentType.POST,
                thread_id="thread1",
                score=i,
            )
            for i in range(10)
        ]
        result = normalize_and_deduplicate({"src": items}, tmp_path)
        assert len(result) == 10

    def test_different_threads_capped_independently(self, tmp_path):
        thread_a = [_make_item(f"a{i}", thread_id="threadA", score=i) for i in range(10)]
        thread_b = [_make_item(f"b{i}", thread_id="threadB", score=i) for i in range(10)]
        result = normalize_and_deduplicate({"src": thread_a + thread_b}, tmp_path)
        # 5 from each thread = 10 total
        assert len(result) == 10

    def test_youtube_comments_capped_randomly(self, tmp_path):
        """YouTube thread cap uses random selection, not like_count."""
        items = [
            _make_item(
                f"yt{i}",
                source_platform=SourcePlatform.YOUTUBE,
                content_type=ContentType.COMMENT,
                thread_id="video1",
                score=None,
                like_count=i,
            )
            for i in range(10)
        ]
        result = normalize_and_deduplicate({"src": items}, tmp_path)
        assert len(result) == 5
        kept_ids = sorted([i.item_id for i in result])
        # Must NOT be the top-5-by-like_count set (yt5-yt9)
        engagement_top5 = sorted([f"yt{i}" for i in range(5, 10)])
        assert kept_ids != engagement_top5, (
            "YouTube thread cap kept highest-engagement items - random selection is broken"
        )


# ── Output files ──────────────────────────────────────────────────────────────

class TestOutputFiles:
    def test_corpus_json_written(self, tmp_path):
        item = _make_item("abc")
        normalize_and_deduplicate({"src": [item]}, tmp_path)
        corpus_path = tmp_path / "normalized" / "corpus.json"
        assert corpus_path.exists()

    def test_stats_json_written(self, tmp_path):
        item = _make_item("abc")
        normalize_and_deduplicate({"src": [item]}, tmp_path)
        stats_path = tmp_path / "normalized" / "stats.json"
        assert stats_path.exists()

    def test_stats_counts_correct(self, tmp_path):
        items = [_make_item(f"id{i}") for i in range(5)]
        # Add a duplicate
        items.append(_make_item("id0"))
        normalize_and_deduplicate({"src": items}, tmp_path)
        stats = json.loads((tmp_path / "normalized" / "stats.json").read_text())
        assert stats["total_before_dedup"] == 6
        assert stats["duplicates_removed"] == 1
        assert stats["total_after_dedup"] == 5


# ── Timestamp sorting ─────────────────────────────────────────────────────────

class TestTimestampSorting:
    def test_newest_first(self, tmp_path):
        old = _make_item("old", source_timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc))
        new = _make_item("new", source_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc))
        result = normalize_and_deduplicate({"src": [old, new]}, tmp_path)
        assert result[0].item_id == "new"

    def test_naive_timestamps_handled(self, tmp_path):
        """Naive datetimes should not crash the sort."""
        item = _make_item("naive", source_timestamp=datetime(2025, 6, 1))  # no tzinfo
        result = normalize_and_deduplicate({"src": [item]}, tmp_path)
        assert len(result) == 1
