"""Unit tests for pipeline/ingest.py — no API calls required."""
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from consumer_research.pipeline.ingest import (
    _detect_format,
    _detect_platform,
    _generate_item_id,
    _parse_timestamp,
    ingest_external_data,
)
from consumer_research.models.schemas import SourcePlatform


# ── Format detection ──────────────────────────────────────────────────────────

class TestDetectFormat:
    def test_platform_scraped_format(self):
        data = [{"metadata_content": {"content": "hello"}, "engagements": {"likes": 5}}]
        assert _detect_format(data) == "platform_scraped"

    def test_simple_format_text_field(self):
        data = [{"text": "hello world", "source": "reddit"}]
        assert _detect_format(data) == "simple"

    def test_simple_format_content_field(self):
        data = [{"content": "some text", "url": "https://example.com"}]
        assert _detect_format(data) == "simple"

    def test_normalized_format(self):
        data = [{"item_id": "abc123", "source_platform": "reddit", "content_text": "hello"}]
        assert _detect_format(data) == "normalized"

    def test_empty_data(self):
        assert _detect_format([]) == "empty"

    def test_unknown_format(self):
        data = [{"foo": "bar", "baz": 42}]
        assert _detect_format(data) == "unknown"


# ── Platform detection ────────────────────────────────────────────────────────

class TestDetectPlatform:
    def test_reddit(self):
        assert _detect_platform("reddit") == SourcePlatform.REDDIT
        assert _detect_platform("https://reddit.com/r/test") == SourcePlatform.REDDIT

    def test_youtube(self):
        assert _detect_platform("youtube") == SourcePlatform.YOUTUBE
        assert _detect_platform("https://youtube.com/watch?v=abc") == SourcePlatform.YOUTUBE
        assert _detect_platform("yt") == SourcePlatform.YOUTUBE

    def test_instagram(self):
        assert _detect_platform("instagram") == SourcePlatform.INSTAGRAM
        assert _detect_platform("ig") == SourcePlatform.INSTAGRAM

    def test_twitter(self):
        assert _detect_platform("twitter") == SourcePlatform.TWITTER
        assert _detect_platform("x.com") == SourcePlatform.TWITTER

    def test_unknown_returns_none(self):
        assert _detect_platform("unknown_source") is None
        assert _detect_platform("") is None


# ── Item ID generation ────────────────────────────────────────────────────────

class TestGenerateItemId:
    def test_deterministic(self):
        id1 = _generate_item_id("https://example.com/post/1", "some text")
        id2 = _generate_item_id("https://example.com/post/1", "some text")
        assert id1 == id2

    def test_different_url_different_id(self):
        id1 = _generate_item_id("https://example.com/post/1", "same text")
        id2 = _generate_item_id("https://example.com/post/2", "same text")
        assert id1 != id2

    def test_different_text_different_id(self):
        id1 = _generate_item_id("same_url", "text one")
        id2 = _generate_item_id("same_url", "text two")
        assert id1 != id2

    def test_id_is_16_chars(self):
        item_id = _generate_item_id("url", "text")
        assert len(item_id) == 16


# ── Timestamp parsing ─────────────────────────────────────────────────────────

class TestParseTimestamp:
    def test_iso_format(self):
        ts = _parse_timestamp("2026-01-15T10:30:00Z")
        assert ts is not None
        assert ts.year == 2026
        assert ts.tzinfo is not None

    def test_date_only(self):
        ts = _parse_timestamp("2026-01-15")
        assert ts is not None
        assert ts.year == 2026
        assert ts.month == 1

    def test_none_input(self):
        assert _parse_timestamp(None) is None

    def test_empty_string(self):
        assert _parse_timestamp("") is None

    def test_timezone_aware_result(self):
        ts = _parse_timestamp("2026-03-01T12:00:00+05:30")
        assert ts is not None
        assert ts.tzinfo is not None


# ── Full ingestion ────────────────────────────────────────────────────────────

class TestIngestExternalData:
    def test_simple_format_ingestion(self, tmp_path):
        data = [
            {"text": "This is a great product", "source": "reddit", "url": "https://reddit.com/r/test/1"},
            {"text": "I love this brand", "source": "instagram", "url": "https://instagram.com/p/abc"},
            {"text": "x", "source": "reddit", "url": "https://reddit.com/r/test/2"},  # too short, skipped
        ]
        f = tmp_path / "test.json"
        f.write_text(json.dumps(data))
        items = ingest_external_data(f, collection_query="test")
        assert len(items) == 2
        assert all(i.content_text for i in items)

    def test_platform_detected_correctly(self, tmp_path):
        data = [{"text": "Reddit post text here", "source": "reddit", "url": "https://reddit.com/r/test/1"}]
        f = tmp_path / "test.json"
        f.write_text(json.dumps(data))
        items = ingest_external_data(f)
        assert len(items) == 1
        assert items[0].source_platform == SourcePlatform.REDDIT

    def test_platform_scraped_ingestion(self, tmp_path):
        data = [
            {
                "metadata_content": {"content": "Post text here", "created_at": "2026-01-01"},
                "engagements": {"likes": 10, "comments": 2},
                "source": "instagram",
                "url": "https://instagram.com/p/test123",
                "comments": [
                    {"text": "Great comment with enough length", "username": "user1", "likes": 5},
                ],
            }
        ]
        f = tmp_path / "test.json"
        f.write_text(json.dumps(data))
        items = ingest_external_data(f)
        # 1 post + 1 comment (comment has 5 likes, above threshold of 2)
        assert len(items) == 2
        platforms = {i.source_platform for i in items}
        assert SourcePlatform.INSTAGRAM in platforms

    def test_pre_normalized_passthrough(self, tmp_path):
        data = [
            {
                "item_id": "abc123def456abcd",
                "source_platform": "reddit",
                "source_url": "https://reddit.com/r/test/1",
                "source_author": "user1",
                "collected_at": "2026-01-01T00:00:00Z",
                "content_text": "Some normalized text content here",
                "content_type": "post",
                "platform_metadata": {},
                "collection_query": "test query",
                "collection_method": "external",
            }
        ]
        f = tmp_path / "test.json"
        f.write_text(json.dumps(data))
        items = ingest_external_data(f)
        assert len(items) == 1
        assert items[0].item_id == "abc123def456abcd"

    def test_empty_file_returns_empty_list(self, tmp_path):
        f = tmp_path / "test.json"
        f.write_text("[]")
        items = ingest_external_data(f)
        assert items == []

    def test_bom_encoded_json(self, tmp_path):
        """Windows apps (Excel, Notepad) often save JSON with a UTF-8 BOM."""
        data = [{"text": "BOM test - this product is excellent quality", "source": "reddit", "url": "https://reddit.com/1"}]
        f = tmp_path / "bom_test.json"
        f.write_bytes(b"\xef\xbb\xbf" + json.dumps(data).encode("utf-8"))
        items = ingest_external_data(f)
        assert len(items) == 1
        assert "BOM test" in items[0].content_text


class TestNoEngagementGating:
    """Verify that engagement is NOT used as a corpus admission gate.

    All items enter regardless of likes/upvotes. Engagement is metadata only.
    """

    def _make_platform_scraped(self, platform, likes=0, comments_data=None):
        item = {
            "metadata_content": {"content": f"This is a sufficiently long {platform} post for testing"},
            "engagements": {"likes": likes},
            "source": platform,
            "url": f"https://{platform}.com/post/123",
            "id": "post_123",
            "comments": comments_data or [],
        }
        return item

    def _make_comment(self, text="This is a sufficiently long comment for testing", likes=0):
        return {"content": text, "text": text, "username": "user1", "score": likes, "likes": likes}

    def test_zero_engagement_comment_included(self, tmp_path):
        """Zero-engagement comments must NOT be filtered out."""
        data = [self._make_platform_scraped("twitter", likes=10, comments_data=[
            self._make_comment("High engagement comment for testing", likes=50),
            self._make_comment("Zero engagement comment for testing", likes=0),
        ])]
        f = tmp_path / "test.json"
        f.write_text(json.dumps(data))
        items = ingest_external_data(f)
        comments = [i for i in items if i.content_type.value == "comment"]
        assert len(comments) == 2  # Both kept - no threshold

    def test_zero_likes_post_included(self, tmp_path):
        """Posts with zero likes must be included."""
        data = [self._make_platform_scraped("instagram", likes=0)]
        f = tmp_path / "test.json"
        f.write_text(json.dumps(data))
        items = ingest_external_data(f)
        assert len(items) == 1

    def test_engagement_metadata_preserved(self, tmp_path):
        """Engagement values must be preserved on items for scoring."""
        data = [self._make_platform_scraped("reddit", likes=42, comments_data=[
            self._make_comment("A comment with known engagement", likes=7),
        ])]
        f = tmp_path / "test.json"
        f.write_text(json.dumps(data))
        items = ingest_external_data(f)
        post = [i for i in items if i.content_type.value == "post"][0]
        assert post.platform_metadata.score == 42 or post.platform_metadata.like_count == 42

    def test_no_engagement_config_fields(self):
        """CollectionConfig should NOT have engagement threshold fields."""
        from consumer_research.config import CollectionConfig
        cfg = CollectionConfig(brand_name="test", category="test")
        assert not hasattr(cfg, "reddit_min_score")
        assert not hasattr(cfg, "youtube_min_likes")
        assert not hasattr(cfg, "twitter_min_likes")
        assert not hasattr(cfg, "instagram_min_likes")
        assert not hasattr(cfg, "review_min_helpful_votes")
