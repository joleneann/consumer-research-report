"""Unit tests for pipeline/scoring.py — data-driven math, no API calls."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from consumer_research.config import ScoringConfig
from consumer_research.models.schemas import (
    AnalysisResults,
    ContentType,
    Emotion,
    Insight,
    NormalizedItem,
    PlatformMetadata,
    Sentiment,
    SentimentResult,
    SourcePlatform,
    Theme,
    compute_nss,
)
from consumer_research.pipeline.scoring import compute_brand_health, score_insights


def _ts(days_ago: int = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days_ago)


def _make_item(
    item_id: str,
    platform: SourcePlatform = SourcePlatform.REDDIT,
    score: int | None = 10,
    like_count: int | None = None,
    timestamp: datetime | None = None,
    content_type: ContentType = ContentType.POST,
) -> NormalizedItem:
    return NormalizedItem(
        item_id=item_id,
        source_platform=platform,
        source_url=f"https://example.com/{item_id}",
        collected_at=datetime.now(timezone.utc),
        content_text=f"Text for {item_id}",
        content_type=content_type,
        platform_metadata=PlatformMetadata(score=score, like_count=like_count),
        collection_query="test",
        collection_method="test",
        source_timestamp=timestamp or _ts(30),
    )


def _make_sentiment(item_id: str, sentiment: Sentiment = Sentiment.POSITIVE, score: float = 0.8) -> SentimentResult:
    return SentimentResult(
        item_id=item_id,
        sentiment=sentiment,
        sentiment_score=score,
        reasoning="test",
        primary_emotion=Emotion.JOY if sentiment == Sentiment.POSITIVE else Emotion.NONE,
        emotion_intensity=0.7 if sentiment == Sentiment.POSITIVE else 0.0,
    )


def _make_theme(
    theme_id: str,
    item_ids: list[str],
    sentiment_dist: dict | None = None,
    platforms: list[SourcePlatform] | None = None,
) -> Theme:
    return Theme(
        theme_id=theme_id,
        theme_label=f"Theme {theme_id}",
        theme_description=f"Description for {theme_id}",
        supporting_item_ids=item_ids,
        item_count=len(item_ids),
        prevalence_pct=round(len(item_ids) / 100 * 100, 1),
        sentiment_distribution=sentiment_dist or {"positive": 5, "negative": 1, "neutral": 4},
        is_multi_source=bool(platforms and len(platforms) > 1),
        platforms_present=platforms or [SourcePlatform.REDDIT],
        representative_quotes=[],
    )


def _make_insight(
    insight_id: str,
    theme_ids: list[str],
    supporting_item_count: int = 10,
) -> Insight:
    return Insight(
        insight_id=insight_id,
        observation="Observation text",
        insight="Insight text",
        implication="Implication text",
        recommendation="Recommendation text",
        further_validation="Validation text",
        supporting_theme_ids=theme_ids,
        supporting_item_count=supporting_item_count,
        source_urls=["https://example.com"],
        is_grounded=True,
        is_non_obvious=True,
        is_actionable=True,
        is_specific=True,
        is_falsifiable=True,
        passed_quality_gates=True,
    )


def _make_analysis(
    themes: list[Theme],
    sentiment_results: list[SentimentResult],
) -> AnalysisResults:
    total = len(sentiment_results)
    pos = sum(1 for s in sentiment_results if s.sentiment == Sentiment.POSITIVE)
    neg = sum(1 for s in sentiment_results if s.sentiment == Sentiment.NEGATIVE)
    return AnalysisResults(
        sentiment_results=sentiment_results,
        themes=themes,
        overall_sentiment={"positive": pos, "negative": neg, "neutral": total - pos - neg},
        net_sentiment_score=compute_nss({"positive": pos, "negative": neg, "neutral": total - pos - neg}),
        total_items_analyzed=total,
        analysis_model="test",
        analysis_prompts={"sentiment": "test"},
    )


# ── score_insights ────────────────────────────────────────────────────────────

class TestScoreInsights:
    def test_returns_scored_insights(self, tmp_path):
        item_ids = [f"i{j}" for j in range(20)]
        items = [_make_item(iid) for iid in item_ids]
        sentiments = [_make_sentiment(iid) for iid in item_ids]
        theme = _make_theme("THM_001", item_ids)
        insight = _make_insight("INS_001", ["THM_001"])
        analysis = _make_analysis([theme], sentiments)

        result = score_insights([insight], analysis, items, tmp_path)
        assert len(result) == 1
        assert result[0].insight.insight_id == "INS_001"

    def test_confidence_score_in_range(self, tmp_path):
        item_ids = [f"i{j}" for j in range(20)]
        items = [_make_item(iid) for iid in item_ids]
        sentiments = [_make_sentiment(iid) for iid in item_ids]
        theme = _make_theme("THM_001", item_ids)
        insight = _make_insight("INS_001", ["THM_001"])
        analysis = _make_analysis([theme], sentiments)

        result = score_insights([insight], analysis, items, tmp_path)
        score = result[0].confidence_score
        assert 0.0 <= score <= 1.0

    def test_signal_score_in_range(self, tmp_path):
        item_ids = [f"i{j}" for j in range(20)]
        items = [_make_item(iid) for iid in item_ids]
        sentiments = [_make_sentiment(iid) for iid in item_ids]
        theme = _make_theme("THM_001", item_ids)
        insight = _make_insight("INS_001", ["THM_001"])
        analysis = _make_analysis([theme], sentiments)

        result = score_insights([insight], analysis, items, tmp_path)
        score = result[0].signal_strength_score
        assert 0.0 <= score <= 1.0

    def test_larger_sample_higher_confidence(self, tmp_path):
        """An insight backed by more items should score higher confidence."""
        small_ids = [f"s{j}" for j in range(5)]
        large_ids = [f"l{j}" for j in range(50)]
        all_ids = small_ids + large_ids
        items = [_make_item(iid) for iid in all_ids]
        sentiments = [_make_sentiment(iid) for iid in all_ids]

        small_theme = _make_theme("THM_001", small_ids)
        large_theme = _make_theme("THM_002", large_ids)
        small_ins = _make_insight("INS_001", ["THM_001"])
        large_ins = _make_insight("INS_002", ["THM_002"])

        analysis = _make_analysis([small_theme, large_theme], sentiments)
        result = score_insights([small_ins, large_ins], analysis, items, tmp_path)

        by_id = {r.insight.insight_id: r for r in result}
        assert by_id["INS_002"].confidence_score > by_id["INS_001"].confidence_score

    def test_output_file_written(self, tmp_path):
        item_ids = [f"i{j}" for j in range(10)]
        items = [_make_item(iid) for iid in item_ids]
        sentiments = [_make_sentiment(iid) for iid in item_ids]
        theme = _make_theme("THM_001", item_ids)
        insight = _make_insight("INS_001", ["THM_001"])
        analysis = _make_analysis([theme], sentiments)

        score_insights([insight], analysis, items, tmp_path)
        assert (tmp_path / "scored" / "scored_insights.json").exists()

    def test_empty_insights_returns_empty(self, tmp_path):
        items = [_make_item(f"i{j}") for j in range(5)]
        sentiments = [_make_sentiment(f"i{j}") for j in range(5)]
        analysis = _make_analysis([], sentiments)
        result = score_insights([], analysis, items, tmp_path)
        assert result == []

    def test_multi_platform_higher_confidence(self, tmp_path):
        """Multi-platform support should boost source diversity confidence factor."""
        reddit_ids = [f"r{j}" for j in range(10)]
        yt_ids = [f"y{j}" for j in range(10)]
        single_ids = [f"s{j}" for j in range(10)]

        reddit_items = [_make_item(iid, platform=SourcePlatform.REDDIT) for iid in reddit_ids]
        yt_items = [_make_item(iid, platform=SourcePlatform.YOUTUBE) for iid in yt_ids]
        single_items = [_make_item(iid, platform=SourcePlatform.REDDIT) for iid in single_ids]

        all_items = reddit_items + yt_items + single_items
        all_sentiments = [_make_sentiment(i.item_id) for i in all_items]

        multi_theme = _make_theme(
            "THM_001", reddit_ids + yt_ids,
            platforms=[SourcePlatform.REDDIT, SourcePlatform.YOUTUBE]
        )
        single_theme = _make_theme("THM_002", single_ids, platforms=[SourcePlatform.REDDIT])

        multi_ins = _make_insight("INS_001", ["THM_001"])
        single_ins = _make_insight("INS_002", ["THM_002"])

        analysis = _make_analysis([multi_theme, single_theme], all_sentiments)
        result = score_insights([multi_ins, single_ins], analysis, all_items, tmp_path)

        by_id = {r.insight.insight_id: r for r in result}
        assert by_id["INS_001"].confidence_score > by_id["INS_002"].confidence_score


# ── compute_brand_health ──────────────────────────────────────────────────────

class TestComputeBrandHealth:
    def test_score_in_range(self):
        item_ids = [f"i{j}" for j in range(20)]
        items = [_make_item(iid) for iid in item_ids]
        sentiments = [_make_sentiment(iid) for iid in item_ids]
        theme = _make_theme("THM_001", item_ids)
        analysis = _make_analysis([theme], sentiments)

        bhs = compute_brand_health(analysis, items)
        assert 0 <= bhs["overall_score"] <= 100

    def test_all_positive_high_score(self):
        item_ids = [f"i{j}" for j in range(20)]
        items = [_make_item(iid, score=100) for iid in item_ids]
        sentiments = [_make_sentiment(iid, Sentiment.POSITIVE, 1.0) for iid in item_ids]
        theme = _make_theme("THM_001", item_ids, {"positive": 20, "negative": 0, "neutral": 0})
        analysis = _make_analysis([theme], sentiments)

        bhs = compute_brand_health(analysis, items)
        assert bhs["overall_score"] > 50  # should be above neutral — conversation component limits small corpora

    def test_all_negative_lower_score(self):
        item_ids = [f"i{j}" for j in range(20)]
        items = [_make_item(iid, score=0) for iid in item_ids]
        sentiments = [_make_sentiment(iid, Sentiment.NEGATIVE, 0.1) for iid in item_ids]
        theme = _make_theme("THM_001", item_ids, {"positive": 0, "negative": 20, "neutral": 0})
        analysis = _make_analysis([theme], sentiments)

        bhs_neg = compute_brand_health(analysis, items)

        # Compare: all-positive should score higher than all-negative
        pos_items = [_make_item(f"p{j}", score=100) for j in range(20)]
        pos_sentiments = [_make_sentiment(f"p{j}", Sentiment.POSITIVE, 1.0) for j in range(20)]
        pos_theme = _make_theme("THM_002", [f"p{j}" for j in range(20)], {"positive": 20, "negative": 0, "neutral": 0})
        pos_analysis = _make_analysis([pos_theme], pos_sentiments)

        bhs_pos = compute_brand_health(pos_analysis, pos_items)
        assert bhs_pos["overall_score"] > bhs_neg["overall_score"]

    def test_has_all_components(self):
        item_ids = [f"i{j}" for j in range(10)]
        items = [_make_item(iid) for iid in item_ids]
        sentiments = [_make_sentiment(iid) for iid in item_ids]
        theme = _make_theme("THM_001", item_ids)
        analysis = _make_analysis([theme], sentiments)

        bhs = compute_brand_health(analysis, items)
        for key in ["overall_score", "sentiment_component", "engagement_component",
                    "advocacy_component", "resilience_component", "conversation_component"]:
            assert key in bhs, f"Missing key: {key}"
