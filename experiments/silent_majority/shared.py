"""Shared data loading and utilities for the silent majority experiment.

Loads the hair colour run data once. Both approach scripts import from here.
"""
import json
import math
from pathlib import Path
from collections import Counter
from consumer_research.config import RUNS_DIR
from consumer_research.models.schemas import (
    AnalysisResults, NormalizedItem, SentimentResult, Sentiment,
    SourcePlatform, ContentType, compute_nss,
)

RUN_ID = "20260407_143544_98a8c6"
RUN_DIR = RUNS_DIR / RUN_ID
EXPERIMENT_DIR = Path(__file__).parent

# Engagement threshold (aligned with config.py)
SOCIAL_THRESHOLD = 2   # Reddit, YouTube, Twitter, Instagram
REVIEW_THRESHOLD = 1   # Amazon, Flipkart
NO_THRESHOLD_PLATFORMS = {"news", "academic", "trends", "web"}


def load_run_data():
    """Load all run artifacts. Returns (corpus, analysis, sentiment_map, config)."""
    corpus = [
        NormalizedItem(**d)
        for d in json.loads((RUN_DIR / "normalized" / "corpus.json").read_text(encoding="utf-8"))
    ]
    analysis_data = json.loads((RUN_DIR / "analysis" / "results.json").read_text(encoding="utf-8"))
    analysis = AnalysisResults(**analysis_data)
    config_data = json.loads((RUN_DIR / "config.json").read_text(encoding="utf-8"))

    sentiment_map = {s.item_id: s for s in analysis.sentiment_results}

    return corpus, analysis, sentiment_map, config_data


def get_item_engagement(item: NormalizedItem) -> int:
    """Get the engagement score for an item (score or like_count, whichever is set)."""
    return item.platform_metadata.score or item.platform_metadata.like_count or 0


def is_above_threshold(item: NormalizedItem) -> bool:
    """Check if an item passes the engagement threshold for its platform."""
    platform = item.source_platform.value

    if platform in NO_THRESHOLD_PLATFORMS:
        return True  # No threshold for editorial/quantitative content

    engagement = get_item_engagement(item)

    if platform in ("amazon", "flipkart"):
        return engagement >= REVIEW_THRESHOLD

    # Social platforms
    return engagement >= SOCIAL_THRESHOLD


def split_corpus(corpus: list[NormalizedItem]):
    """Split corpus into above-threshold and below-threshold items."""
    above = [item for item in corpus if is_above_threshold(item)]
    below = [item for item in corpus if not is_above_threshold(item)]
    return above, below


def compute_theme_sentiment(theme, item_ids_subset: set, sentiment_map: dict):
    """Compute sentiment distribution and NSS for a theme within a subset of items."""
    theme_items_in_subset = [
        iid for iid in theme.supporting_item_ids if iid in item_ids_subset
    ]
    dist = {"positive": 0, "negative": 0, "neutral": 0, "mixed": 0}
    for iid in theme_items_in_subset:
        if iid in sentiment_map:
            s = sentiment_map[iid].sentiment.value
            dist[s] = dist.get(s, 0) + 1

    nss = compute_nss(dist)
    return len(theme_items_in_subset), dist, nss


def compute_weighted_theme_sentiment(theme, corpus_map: dict, sentiment_map: dict):
    """Compute engagement-weighted sentiment for a theme.

    Weight = max(0.1, log(1 + engagement)). Zero-engagement items still
    contribute at floor weight (0.1) rather than being excluded.
    """
    weighted_dist = {"positive": 0.0, "negative": 0.0, "neutral": 0.0, "mixed": 0.0}
    total_weight = 0.0
    item_count = 0

    for iid in theme.supporting_item_ids:
        if iid not in corpus_map or iid not in sentiment_map:
            continue

        item = corpus_map[iid]
        engagement = get_item_engagement(item)
        weight = max(0.1, math.log(1 + engagement))

        sentiment = sentiment_map[iid].sentiment.value
        weighted_dist[sentiment] = weighted_dist.get(sentiment, 0.0) + weight
        total_weight += weight
        item_count += 1

    # Weighted NSS
    if total_weight > 0:
        weighted_nss = (weighted_dist["positive"] - weighted_dist["negative"]) / total_weight
    else:
        weighted_nss = 0.0

    return item_count, weighted_dist, round(weighted_nss, 4), total_weight
