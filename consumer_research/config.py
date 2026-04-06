"""Global configuration for the consumer research pipeline."""

import os
from pathlib import Path
from dataclasses import dataclass, field


BASE_DIR = Path(__file__).parent.parent
RUNS_DIR = BASE_DIR / "consumer_research" / "runs"


@dataclass
class CollectionConfig:
    """Configuration for data collection."""
    brand_name: str
    category: str
    time_period_days: int = 180
    keywords: list[str] = field(default_factory=list)
    business_objectives: list[str] = field(default_factory=list)
    # Reddit — THESE ARE MINIMUMS, NOT TARGETS
    subreddits: list[str] = field(default_factory=list)
    reddit_max_posts: int = 500
    reddit_max_comments_per_post: int = 20
    reddit_min_score: int = 3  # Minimum upvotes to include a comment
    # YouTube — THESE ARE MINIMUMS, NOT TARGETS
    youtube_max_videos: int = 50
    youtube_max_comments_per_video: int = 100
    youtube_min_likes: int = 2  # Minimum likes to include a comment
    # Google Trends
    trends_geo: str = ""  # e.g., "IN" for India
    # NewsData.io
    news_language: str = "en"
    news_country: str = ""  # e.g., "in" for India
    news_max_articles: int = 200  # Use full daily allocation
    # Academic
    academic_max_papers: int = 50
    # Competitors (for comparative analysis)
    competitors: list[str] = field(default_factory=list)


@dataclass
class AnalysisConfig:
    """Configuration for analysis pipeline."""
    claude_model: str = "claude-sonnet-4-20250514"
    claude_temperature: float = 0.0
    batch_size: int = 15  # items per Claude API call
    max_corpus_size: int = 999_999  # No cap — always analyze everything collected
    min_items_for_theme: int = 3  # minimum supporting items for a theme
    min_items_for_insight: int = 3  # minimum items for insight quality gate
    # Methodology selection: "auto" picks based on corpus size
    # "in_context_full" = session LLM reads every item (small corpus)
    # "keyword_narrative" = keyword classification + mandatory narrative review (large corpus)
    # No external API calls in either mode — all analysis done by the Claude Code session
    methodology: str = "auto"
    # Threshold for auto methodology selection
    full_read_threshold: int = 1000  # Below this: session LLM reads every item. Above: keyword + narrative pass
    # Narrative review enforcement
    max_unthemed_pct: float = 0.10  # Pipeline refuses to proceed to Stage 5 if unthemed > this
    narrative_pass_required: bool = True  # ALWAYS True — never skip narrative review


@dataclass
class ScoringConfig:
    """Weights for confidence and signal strength scoring."""
    # Confidence weights (must sum to 1.0)
    confidence_sample_size: float = 0.25
    confidence_source_diversity: float = 0.25
    confidence_temporal_consistency: float = 0.15
    confidence_internal_agreement: float = 0.20
    confidence_data_recency: float = 0.15
    # Signal strength weights (must sum to 1.0)
    signal_prevalence: float = 0.35
    signal_engagement: float = 0.30
    signal_sentiment_intensity: float = 0.20
    signal_conversation_depth: float = 0.15


@dataclass
class ReportDesign:
    """Visual design specification for reports."""
    # Typography
    heading_font: str = "Inter"
    body_font: str = "Inter"
    heading_size_pt: int = 16
    body_size_pt: int = 11
    stat_callout_size_pt: int = 32
    # Colors
    bg_color: str = "#FFFFFF"
    primary_text: str = "#1B2A4A"
    secondary_text: str = "#4A5568"
    accent_blue: str = "#2B6CB0"
    accent_teal: str = "#4FD1C5"
    negative_red: str = "#E53E3E"
    positive_green: str = "#38A169"
    light_grey: str = "#EDF2F7"
    near_white: str = "#F7FAFC"
    border_grey: str = "#E2E8F0"


@dataclass
class PipelineConfig:
    """Top-level pipeline configuration."""
    collection: CollectionConfig
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    design: ReportDesign = field(default_factory=ReportDesign)

    # API keys (from environment)
    @property
    def anthropic_api_key(self) -> str:
        return os.environ.get("ANTHROPIC_API_KEY", "")

    @property
    def newsdata_api_key(self) -> str:
        return os.environ.get("NEWSDATA_API_KEY", "")

    @property
    def youtube_api_key(self) -> str:
        return os.environ.get("YOUTUBE_API_KEY", "")
