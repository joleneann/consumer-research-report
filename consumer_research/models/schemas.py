"""Pydantic models for all pipeline data schemas.

Every stage of the pipeline produces data conforming to these schemas.
This ensures type safety, validation, and consistent serialization across
the entire system.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


# ─── Enums ───────────────────────────────────────────────────────────────────

class SourcePlatform(str, Enum):
    REDDIT = "reddit"
    YOUTUBE = "youtube"
    NEWS = "news"
    ACADEMIC = "academic"
    TRENDS = "trends"
    WEB = "web"
    AMAZON = "amazon"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    FLIPKART = "flipkart"


class ContentType(str, Enum):
    POST = "post"
    COMMENT = "comment"
    REVIEW = "review"
    ARTICLE = "article"
    PAPER = "paper"
    TREND_DATA = "trend_data"


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class Emotion(str, Enum):
    """Plutchik's 8 primary emotions — industry standard for brand perception."""
    JOY = "joy"
    TRUST = "trust"
    FEAR = "fear"
    SURPRISE = "surprise"
    SADNESS = "sadness"
    DISGUST = "disgust"
    ANGER = "anger"
    ANTICIPATION = "anticipation"
    NONE = "none"


class ConfidenceTier(str, Enum):
    HIGH = "high"            # 0.75-1.0
    MEDIUM = "medium"        # 0.50-0.74
    DIRECTIONAL = "directional"  # 0.25-0.49
    INSUFFICIENT = "insufficient"  # 0.00-0.24


class SignalStrengthTier(str, Enum):
    STRONG = "strong"        # 0.75-1.0
    MODERATE = "moderate"    # 0.50-0.74
    WEAK = "weak"            # 0.25-0.49
    TRACE = "trace"          # 0.00-0.24


class MatrixQuadrant(str, Enum):
    KEY_FINDING = "Key Finding"          # High confidence + Strong signal
    EMERGING_TREND = "Emerging Trend"    # High confidence + Weak signal
    WATCH_CLOSELY = "Watch Closely"      # Low confidence + Strong signal
    NOISE = "Noise"                      # Low confidence + Weak signal


# ─── Stage 1: Raw Collection ────────────────────────────────────────────────

class PlatformMetadata(BaseModel):
    """Platform-specific metadata preserved as-is from the source."""
    score: Optional[int] = None          # Reddit upvotes
    subreddit: Optional[str] = None
    num_comments: Optional[int] = None
    star_rating: Optional[float] = None  # Amazon/review ratings
    verified_purchase: Optional[bool] = None
    video_id: Optional[str] = None       # YouTube
    video_title: Optional[str] = None
    like_count: Optional[int] = None
    view_count: Optional[int] = None
    citation_count: Optional[int] = None  # Academic
    doi: Optional[str] = None
    journal: Optional[str] = None
    search_interest: Optional[int] = None  # Google Trends (0-100)
    region: Optional[str] = None
    thread_id: Optional[str] = None  # Reddit post ID / YouTube video ID — for thread-level dedup
    comment_depth: Optional[int] = None  # Reply depth (0=top-level, 1=reply, 2=reply-to-reply)
    # Instagram-specific
    followers: Optional[int] = None          # Creator's follower count
    share_count: Optional[int] = None        # Instagram shares
    engagement_rate: Optional[float] = None  # Pre-computed engagement rate
    media_type: Optional[str] = None         # "reel", "carousel", "image", "text"
    # Twitter-specific
    retweet_count: Optional[int] = None       # Twitter shares/retweets
    quote_count: Optional[int] = None         # Twitter quotes
    bookmark_count: Optional[int] = None      # Twitter bookmarks


# ─── Stage 2: Normalized Corpus ──────────────────────────────────────────────

class NormalizedItem(BaseModel):
    """Unified schema for every item in the corpus, regardless of source.

    This is the single source of truth for all downstream analysis.
    The item_id is a deterministic SHA-256 hash of source_url + content_text,
    ensuring the same content always gets the same ID (reproducibility).
    """
    item_id: str = Field(description="SHA-256 hash of source_url + content_text")
    source_platform: SourcePlatform
    source_url: str = Field(description="Permalink to original content - MANDATORY")
    source_author: str = Field(default="Unknown")
    source_timestamp: Optional[datetime] = None
    collected_at: datetime
    content_text: str
    content_type: ContentType
    platform_metadata: PlatformMetadata = Field(default_factory=PlatformMetadata)
    collection_query: str = Field(description="The search query used to find this item")
    collection_method: str = Field(description="e.g., reddit_mcp_search, pytrends_interest_over_time")


# ─── Stage 3: Relevance Filtering ───────────────────────────────────────────

class RelevanceClassification(BaseModel):
    """Result of Claude's relevance classification for a single item."""
    item_id: str
    relevant: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(description="One sentence explaining relevance decision")
    relevance_type: str = Field(description="direct_mention|comparison|category_discussion|unrelated")


class FilteredCorpus(BaseModel):
    """Output of Stage 3: items that passed relevance filtering."""
    items: list[NormalizedItem]
    rejected_count: int
    filter_prompt: str = Field(description="Exact prompt used for classification (reproducibility)")
    filter_model: str = Field(description="Model version used")


# ─── Stage 4: Analysis ──────────────────────────────────────────────────────

class AspectSentiment(BaseModel):
    """Sentiment for a specific product/brand aspect (ABSA).

    Industry standard: Brandwatch, Sprinklr, Thematic all score sentiment
    PER aspect rather than per item. E.g., taste: positive, price: negative.
    """
    aspect: str
    sentiment: Sentiment
    sentiment_score: float = Field(ge=0.0, le=1.0)


class SentimentResult(BaseModel):
    """Sentiment classification for a single item.

    Includes Plutchik emotion classification and aspect-based sentiment (ABSA)
    alongside the traditional positive/negative/neutral/mixed classification.
    """
    item_id: str
    sentiment: Sentiment
    sentiment_score: float = Field(ge=0.0, le=1.0, description="Strength of sentiment")
    reasoning: str
    key_phrases: list[str] = Field(default_factory=list)
    # Aspect-Based Sentiment Analysis (ABSA)
    aspects: list[AspectSentiment] = Field(default_factory=list)
    # Plutchik emotion classification
    primary_emotion: Emotion = Field(default=Emotion.NONE)
    emotion_intensity: float = Field(default=0.0, ge=0.0, le=1.0)
    secondary_emotion: Optional[Emotion] = None

    @property
    def aspect_names(self) -> list[str]:
        """Backward-compatible flat list of aspect names."""
        return [a.aspect for a in self.aspects]


class VerbatimQuote(BaseModel):
    """A selected consumer quote with full provenance."""
    text: str
    item_id: str
    source_url: str
    source_platform: SourcePlatform
    source_timestamp: Optional[datetime] = None
    engagement_score: Optional[int] = None
    selection_reason: str = Field(description="Why this quote was selected (e.g., highest engagement)")


class Theme(BaseModel):
    """A recurring theme extracted from the corpus."""
    theme_id: str
    theme_label: str
    theme_description: str
    supporting_item_ids: list[str]
    item_count: int
    prevalence_pct: float
    sentiment_distribution: dict[str, int] = Field(
        description="e.g., {'positive': 8, 'negative': 12, 'neutral': 3}"
    )
    emotion_distribution: dict[str, int] = Field(
        default_factory=dict,
        description="Plutchik emotion counts, e.g., {'joy': 5, 'anger': 2, 'trust': 8}"
    )
    net_sentiment_score: float = Field(
        default=0.0,
        description="(positive - negative) / total, range -1.0 to +1.0"
    )
    representative_quotes: list[VerbatimQuote]
    platforms_present: list[SourcePlatform]
    is_multi_source: bool = Field(description="Theme appears across 2+ platforms")
    is_contested: bool = Field(default=False, description="Platforms disagree on sentiment")


def compute_nss(distribution: dict[str, int]) -> float:
    """Compute Net Sentiment Score: (positive - negative) / total.

    Industry standard metric (Brandwatch, Sprinklr, YouGov).
    Returns value in range [-1.0, +1.0].
    """
    total = sum(distribution.values())
    if total == 0:
        return 0.0
    pos = distribution.get("positive", 0)
    neg = distribution.get("negative", 0)
    return round((pos - neg) / total, 4)


class AnalysisResults(BaseModel):
    """Output of Stage 4: full analysis of the filtered corpus."""
    sentiment_results: list[SentimentResult]
    themes: list[Theme]
    overall_sentiment: dict[str, int]  # {"positive": N, "negative": N, ...}
    net_sentiment_score: float = Field(
        default=0.0,
        description="(positive - negative) / total, range -1.0 to +1.0"
    )
    emotion_distribution: dict[str, int] = Field(
        default_factory=dict,
        description="Corpus-wide Plutchik emotion counts"
    )
    aspect_sentiment_summary: dict[str, dict[str, int]] = Field(
        default_factory=dict,
        description="Aspect → sentiment counts, e.g., {'taste': {'positive': 20, 'negative': 3, ...}}"
    )
    total_items_analyzed: int
    analysis_model: str
    analysis_prompts: dict[str, str] = Field(description="All prompts used, keyed by purpose")


# ─── Stage 5: Insight Synthesis ──────────────────────────────────────────────

class Insight(BaseModel):
    """A synthesized, decision-grade insight.

    Follows the framework:
    Observation → Insight → Implication → Recommendation → Further Validation
    """
    insight_id: str
    observation: str = Field(description="What the data shows (theme + evidence)")
    insight: str = Field(description="What it means for the consumer (the 'why')")
    implication: str = Field(description="What it means for the business ('So What')")
    recommendation: str = Field(description="What the client should do ('Now What')")
    further_validation: str = Field(description="What additional research would strengthen this")
    supporting_theme_ids: list[str]
    supporting_item_count: int
    source_urls: list[str] = Field(description="Key source URLs backing this insight")
    # Quality gate results
    is_grounded: bool = Field(description="Links to >=3 source items")
    is_non_obvious: bool = Field(description="Would a brand manager not already know this?")
    is_actionable: bool = Field(description="There is a concrete action the client can take")
    is_specific: bool = Field(description="Names specific occasions, segments, attributes")
    is_falsifiable: bool = Field(description="The claim could be proven wrong with more data")
    passed_quality_gates: bool = Field(description="All 5 quality gates passed")


# ─── Stage 6: Scoring ────────────────────────────────────────────────────────

class ConfidenceBreakdown(BaseModel):
    """Breakdown of how each factor contributed to the confidence score."""
    sample_size_score: float
    source_diversity_score: float
    temporal_consistency_score: float
    internal_agreement_score: float
    data_recency_score: float


class SignalStrengthBreakdown(BaseModel):
    """Breakdown of signal strength factors — all computed from data, no LLM opinion."""
    prevalence_score: float  # % of corpus supporting this theme (thread-weighted)
    engagement_level_score: float  # Avg engagement vs. corpus median
    sentiment_intensity_score: float  # How extreme the sentiment (strong vs. mild)
    conversation_depth_score: float  # Avg reply depth — deeper = more engagement


class ScoredInsight(BaseModel):
    """An insight with full confidence and signal strength scoring — both data-driven."""
    insight: Insight
    confidence_score: float = Field(ge=0.0, le=1.0)
    confidence_tier: ConfidenceTier
    confidence_breakdown: ConfidenceBreakdown
    signal_strength_score: float = Field(ge=0.0, le=1.0)
    signal_strength_tier: SignalStrengthTier
    signal_strength_breakdown: SignalStrengthBreakdown
    matrix_quadrant: MatrixQuadrant
    # Statistical context for any reported percentage
    sample_size: int
    confidence_interval_95: Optional[tuple[float, float]] = None


# ─── Run Metadata ────────────────────────────────────────────────────────────

class RunConfig(BaseModel):
    """Complete configuration for a single pipeline run. Stored for reproducibility."""
    run_id: str
    created_at: datetime
    brand_name: str
    category: str
    time_period_days: int
    keywords: list[str]
    business_objectives: list[str]
    subreddits: list[str]
    trends_geo: str
    news_country: str
    claude_model: str
    claude_temperature: float
    filter_prompt: Optional[str] = None
    analysis_prompts: Optional[dict[str, str]] = None


class RunSummary(BaseModel):
    """Summary statistics for a completed run."""
    run_id: str
    brand_name: str
    total_collected: int
    total_after_filter: int
    total_rejected: int
    items_by_platform: dict[str, int]
    themes_extracted: int
    insights_generated: int
    insights_passed_quality_gates: int
    high_confidence_insights: int
    key_finding_insights: int
    duration_seconds: float
