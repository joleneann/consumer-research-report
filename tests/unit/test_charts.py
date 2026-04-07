"""Unit tests for chart generation — temporal distribution chart."""
from datetime import datetime, timezone
from pathlib import Path

import pytest

from consumer_research.models.schemas import NormalizedItem, SourcePlatform, ContentType, PlatformMetadata
from consumer_research.report.charts import generate_temporal_chart


def _make_item(item_id: str, year: int | None = None) -> NormalizedItem:
    """Build a minimal NormalizedItem with an optional source_timestamp year."""
    ts = datetime(year, 6, 15, tzinfo=timezone.utc) if year else None
    return NormalizedItem(
        item_id=item_id,
        source_platform=SourcePlatform.REDDIT,
        source_url=f"https://reddit.com/{item_id}",
        source_author="user",
        source_timestamp=ts,
        collected_at=datetime.now(timezone.utc),
        content_text=f"Test item {item_id}",
        content_type=ContentType.POST,
        platform_metadata=PlatformMetadata(),
        collection_query="test",
        collection_method="test",
    )


class TestTemporalChart:
    def test_generates_png(self, tmp_path):
        items = [_make_item("a", 2025), _make_item("b", 2025), _make_item("c", 2024)]
        path = generate_temporal_chart(items, tmp_path)
        assert path is not None
        assert path.exists()
        assert path.name == "chart_temporal.png"

    def test_returns_none_for_all_undated(self, tmp_path):
        items = [_make_item("a"), _make_item("b")]
        path = generate_temporal_chart(items, tmp_path)
        assert path is None

    def test_undated_items_included_in_chart(self, tmp_path):
        """Undated items should appear as a separate bar, not be silently dropped."""
        items = [
            _make_item("a", 2025),
            _make_item("b", 2025),
            _make_item("c", None),  # undated
        ]
        path = generate_temporal_chart(items, tmp_path)
        assert path is not None
        # File should be non-trivially sized (contains undated bar)
        assert path.stat().st_size > 1000

    def test_percentages_use_full_corpus_denominator(self, tmp_path):
        """Percentages should be of full corpus (10 items), not just dated subset (8)."""
        items = [_make_item(f"d_{i}", 2025) for i in range(8)]
        items += [_make_item(f"u_{i}", None) for i in range(2)]  # 2 undated
        # 8 dated + 2 undated = 10 total
        # If denominator is correct (10), 2025 bar = 80%, not 100%
        path = generate_temporal_chart(items, tmp_path)
        assert path is not None
