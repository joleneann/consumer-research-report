"""Unit tests for models/schemas.py — validation, NSS, computed fields."""
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from consumer_research.models.schemas import (
    AspectSentiment,
    ContentType,
    Emotion,
    Insight,
    NormalizedItem,
    PlatformMetadata,
    Sentiment,
    SentimentResult,
    SourcePlatform,
    VerbatimQuote,
    compute_nss,
)


# ── compute_nss ───────────────────────────────────────────────────────────────

class TestComputeNss:
    def test_all_positive(self):
        assert compute_nss({"positive": 10, "negative": 0, "neutral": 0}) == 1.0

    def test_all_negative(self):
        assert compute_nss({"positive": 0, "negative": 10, "neutral": 0}) == -1.0

    def test_neutral_stays_in_denominator(self):
        # 5 pos, 0 neg, 5 neutral = (5-0)/10 = 0.5
        assert compute_nss({"positive": 5, "negative": 0, "neutral": 5}) == 0.5

    def test_balanced(self):
        # 5 pos, 5 neg = 0.0
        assert compute_nss({"positive": 5, "negative": 5}) == 0.0

    def test_empty_distribution(self):
        assert compute_nss({}) == 0.0

    def test_zero_total(self):
        assert compute_nss({"positive": 0, "negative": 0}) == 0.0

    def test_mixed_included(self):
        # 4 pos, 2 neg, 2 neutral, 2 mixed = (4-2)/10 = 0.2
        result = compute_nss({"positive": 4, "negative": 2, "neutral": 2, "mixed": 2})
        assert result == 0.2


# ── NormalizedItem validation ─────────────────────────────────────────────────

class TestNormalizedItemValidation:
    def _minimal(self, **overrides):
        defaults = dict(
            item_id="abc123def456abcd",
            source_platform=SourcePlatform.REDDIT,
            source_url="https://reddit.com/r/test/1",
            collected_at=datetime.now(timezone.utc),
            content_text="Some text here",
            content_type=ContentType.POST,
            collection_query="test query",
            collection_method="reddit_search",
        )
        defaults.update(overrides)
        return NormalizedItem(**defaults)

    def test_minimal_valid_item(self):
        item = self._minimal()
        assert item.item_id == "abc123def456abcd"

    def test_platform_metadata_defaults(self):
        item = self._minimal()
        assert item.platform_metadata is not None
        assert item.platform_metadata.score is None
        assert item.platform_metadata.thread_id is None

    def test_source_timestamp_optional(self):
        item = self._minimal(source_timestamp=None)
        assert item.source_timestamp is None

    def test_content_type_enum(self):
        item = self._minimal(content_type=ContentType.COMMENT)
        assert item.content_type == ContentType.COMMENT


# ── SentimentResult ───────────────────────────────────────────────────────────

class TestSentimentResult:
    def test_aspect_names_property(self):
        result = SentimentResult(
            item_id="abc",
            sentiment=Sentiment.POSITIVE,
            sentiment_score=0.8,
            reasoning="Clear positive tone",
            aspects=[
                AspectSentiment(aspect="taste", sentiment=Sentiment.POSITIVE, sentiment_score=0.9),
                AspectSentiment(aspect="price", sentiment=Sentiment.NEGATIVE, sentiment_score=0.3),
            ],
            primary_emotion=Emotion.JOY,
            emotion_intensity=0.7,
        )
        assert result.aspect_names == ["taste", "price"]

    def test_empty_aspects(self):
        result = SentimentResult(
            item_id="abc",
            sentiment=Sentiment.NEUTRAL,
            sentiment_score=0.5,
            reasoning="Neutral",
            primary_emotion=Emotion.NONE,
            emotion_intensity=0.0,
        )
        assert result.aspect_names == []

    def test_sentiment_score_range(self):
        with pytest.raises(ValidationError):
            SentimentResult(
                item_id="abc",
                sentiment=Sentiment.POSITIVE,
                sentiment_score=1.5,  # out of range
                reasoning="test",
                primary_emotion=Emotion.NONE,
                emotion_intensity=0.0,
            )


# ── VerbatimQuote ─────────────────────────────────────────────────────────────

class TestVerbatimQuote:
    def test_selection_reason_required(self):
        with pytest.raises(ValidationError):
            VerbatimQuote(
                text="Some quote",
                item_id="abc",
                source_url="https://example.com",
                source_platform=SourcePlatform.REDDIT,
                # missing selection_reason
            )

    def test_valid_quote(self):
        q = VerbatimQuote(
            text="This product is amazing",
            item_id="abc123",
            source_url="https://reddit.com/r/test/1",
            source_platform=SourcePlatform.REDDIT,
            selection_reason="Highest engagement in theme",
        )
        assert q.text == "This product is amazing"
        assert q.engagement_score is None


# ── Insight ───────────────────────────────────────────────────────────────────

class TestInsight:
    def _make_insight(self, **overrides):
        defaults = dict(
            insight_id="INS_001",
            observation="33% of posts mention quality issues",
            insight="Consumers associate the brand with premium ingredients but question consistency",
            implication="Quality inconsistency erodes trust in repeat purchasers",
            recommendation="Implement batch-level quality tracking and publish transparency reports",
            further_validation="Structured survey on quality expectations across SKUs",
            supporting_theme_ids=["THM_001"],
            supporting_item_count=45,
            source_urls=["https://example.com/1"],
            is_grounded=True,
            is_non_obvious=True,
            is_actionable=True,
            is_specific=True,
            is_falsifiable=True,
            passed_quality_gates=True,
        )
        defaults.update(overrides)
        return Insight(**defaults)

    def test_fully_passed_insight(self):
        ins = self._make_insight()
        assert ins.passed_quality_gates is True

    def test_failed_gate_reflected(self):
        ins = self._make_insight(is_grounded=False, passed_quality_gates=False)
        assert ins.passed_quality_gates is False

    def test_insight_id_stored(self):
        ins = self._make_insight(insight_id="INS_042")
        assert ins.insight_id == "INS_042"


# ── SourcePlatform enum ───────────────────────────────────────────────────────

class TestSourcePlatformEnum:
    def test_all_expected_platforms_present(self):
        expected = ["reddit", "youtube", "twitter", "instagram", "news", "web", "academic", "trends"]
        actual_values = [p.value for p in SourcePlatform]
        for platform in expected:
            assert platform in actual_values, f"Missing platform: {platform}"

    def test_instagram_present(self):
        # Instagram was added in a bug fix — ensure it's not dropped
        assert SourcePlatform.INSTAGRAM.value == "instagram"

    def test_web_present(self):
        # WEB was added as a distinct source from NEWS
        assert SourcePlatform.WEB.value == "web"
