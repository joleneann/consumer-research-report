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
                    {"text": "Great comment", "username": "user1"},
                ],
            }
        ]
        f = tmp_path / "test.json"
        f.write_text(json.dumps(data))
        items = ingest_external_data(f)
        assert len(items) == 2  # 1 post + 1 comment
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
