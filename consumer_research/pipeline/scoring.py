"""Stage 6: Confidence and signal strength scoring - fully data-driven.

Every insight receives two independent scores, both computed entirely from data:
- Confidence Score: How sure are we? (sample size, source diversity, temporal, agreement, recency)
- Signal Strength: How loudly are consumers saying it? (prevalence, engagement, intensity, depth)

Insights ranked by confidence (primary) then signal strength (tiebreaker).
No LLM judgment involved in scoring.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from consumer_research.config import ScoringConfig
from consumer_research.models.schemas import (
    AnalysisResults,
    ConfidenceBreakdown,
    ConfidenceTier,
    Insight,
    NormalizedItem,
    ScoredInsight,
    SignalStrengthBreakdown,
    SignalStrengthTier,
)

logger = logging.getLogger(__name__)


def score_insights(
    insights: list[Insight],
    analysis: AnalysisResults,
    items: list[NormalizedItem],
    run_dir: Path,
    config: ScoringConfig | None = None,
) -> list[ScoredInsight]:
    """Score each insight for confidence and signal strength.

    Both scores are computed entirely from data — no LLM calls needed.
    Scoring uses continuous functions and corpus-relative percentiles so that
    insights differentiate even in large, multi-platform corpora.
    """
    if config is None:
        config = ScoringConfig()

    scored_dir = run_dir / "scored"
    scored_dir.mkdir(parents=True, exist_ok=True)

    item_map = {item.item_id: item for item in items}
    theme_map = {t.theme_id: t for t in analysis.themes}
    sentiment_map = {s.item_id: s for s in analysis.sentiment_results}

    # Compute corpus-level stats for relative scoring.
    # Use p75 of non-zero engagement as baseline (median is often 0 for comment-heavy corpora).
    all_scores = [
        item.platform_metadata.score or item.platform_metadata.like_count or 0
        for item in items
    ]
    nonzero_scores = sorted([s for s in all_scores if s > 0])
    if nonzero_scores:
        corpus_p75_engagement = nonzero_scores[min(len(nonzero_scores) - 1, 3 * len(nonzero_scores) // 4)]
    else:
        corpus_p75_engagement = 1

    # Pre-compute per-insight item lists for percentile-based scoring
    insight_item_lists: list[tuple[Insight, list[NormalizedItem]]] = []
    for insight in insights:
        supporting_themes = [
            theme_map[tid] for tid in insight.supporting_theme_ids if tid in theme_map
        ]
        supporting_items = []
        for theme in supporting_themes:
            supporting_items.extend(
                item_map[iid] for iid in theme.supporting_item_ids if iid in item_map
            )
        insight_item_lists.append((insight, supporting_items))

    # Corpus-level platform count for diversity scoring
    total_platforms = len(set(item.source_platform for item in items))

    # Pre-compute per-insight avg engagement for percentile ranking across insights
    insight_engagements = []
    for _, sup_items in insight_item_lists:
        eng_vals = [
            i.platform_metadata.score or i.platform_metadata.like_count or 0
            for i in sup_items
        ]
        insight_engagements.append(sum(eng_vals) / len(eng_vals) if eng_vals else 0)
    sorted_engagements = sorted(insight_engagements)

    scored: list[ScoredInsight] = []

    for idx, (insight, supporting_items) in enumerate(insight_item_lists):
        # ── Confidence Score ──
        conf_breakdown = _compute_confidence(
            supporting_items, sentiment_map, config, len(items), total_platforms
        )
        confidence_score = (
            config.confidence_sample_size * conf_breakdown.sample_size_score
            + config.confidence_source_diversity * conf_breakdown.source_diversity_score
            + config.confidence_temporal_consistency * conf_breakdown.temporal_consistency_score
            + config.confidence_internal_agreement * conf_breakdown.internal_agreement_score
            + config.confidence_data_recency * conf_breakdown.data_recency_score
        )

        # ── Signal Strength Score ──
        # Compute percentile rank of this insight's engagement among all insights
        eng_val = insight_engagements[idx]
        eng_rank = sorted_engagements.index(eng_val) / max(1, len(sorted_engagements) - 1) if sorted_engagements else 0.5
        sig_breakdown = _compute_signal_strength(
            supporting_items, sentiment_map, items, corpus_p75_engagement, eng_rank
        )
        signal_score = (
            config.signal_prevalence * sig_breakdown.prevalence_score
            + config.signal_engagement * sig_breakdown.engagement_level_score
            + config.signal_sentiment_intensity * sig_breakdown.sentiment_intensity_score
            + config.signal_conversation_depth * sig_breakdown.conversation_depth_score
        )

        # ── Tiers ──
        conf_tier = _confidence_tier(confidence_score)
        sig_tier = _signal_tier(signal_score)

        # ── Wilson CI ──
        n = insight.supporting_item_count
        total = len(items)
        ci = _wilson_ci(n, total) if total > 0 else None

        scored_insight = ScoredInsight(
            insight=insight,
            confidence_score=round(confidence_score, 3),
            confidence_tier=conf_tier,
            confidence_breakdown=conf_breakdown,
            signal_strength_score=round(signal_score, 3),
            signal_strength_tier=sig_tier,
            signal_strength_breakdown=sig_breakdown,
            sample_size=n,
            confidence_interval_95=ci,
        )
        scored.append(scored_insight)

    # Sort by confidence (primary) then signal strength (tiebreaker)
    scored.sort(key=lambda s: (s.confidence_score, s.signal_strength_score), reverse=True)

    # Write output
    scored_data = [s.model_dump(mode="json") for s in scored]
    (scored_dir / "scored_insights.json").write_text(
        json.dumps(scored_data, indent=2, default=str), encoding="utf-8"
    )

    high_conf = sum(1 for s in scored if s.confidence_tier == ConfidenceTier.HIGH)
    logger.info(
        f"Scoring complete: {len(scored)} insights scored. "
        f"{high_conf} high confidence."
    )

    return scored


def _compute_confidence(
    items: list[NormalizedItem],
    sentiment_map: dict,
    config: ScoringConfig,
    corpus_size: int = 0,
    total_platforms: int = 1,
) -> ConfidenceBreakdown:
    """Compute confidence factor scores — all from data.

    Uses continuous logarithmic scoring and corpus-relative metrics so that
    insights differentiate even in large corpora. Every factor produces a
    value between 0 and 1 with meaningful spread across themes.
    """
    import math
    n = len(items)

    # Sample size — log-scaled relative to corpus size.
    # A theme with 1% of corpus gets ~0.3, 5% gets ~0.55, 20% gets ~0.80, 50%+ gets ~0.95.
    if n == 0 or corpus_size == 0:
        sample = 0.1
    else:
        share = n / corpus_size
        # Log curve: f(x) = ln(1 + share * k) / ln(1 + k), k controls curvature
        sample = min(1.0, math.log(1 + share * 50) / math.log(1 + 50))
        sample = max(0.1, sample)

    # Source diversity — ratio of platforms this insight covers vs total available,
    # with a Herfindahl concentration penalty for unbalanced representation.
    insight_platforms = Counter(item.source_platform for item in items)
    n_plat = len(insight_platforms)
    if n_plat == 0 or total_platforms == 0:
        diversity = 0.1
    else:
        # Base: fraction of available platforms represented
        coverage = n_plat / total_platforms
        # Herfindahl-Hirschman concentration: 1/n for perfect balance, 1.0 for single-source
        total_items = sum(insight_platforms.values())
        hhi = sum((c / total_items) ** 2 for c in insight_platforms.values()) if total_items else 1.0
        # Ideal HHI for n_plat platforms is 1/n_plat; penalty increases as HHI rises
        balance = (1.0 / n_plat) / hhi if hhi > 0 else 0.0  # 1.0 = perfectly balanced
        balance = min(1.0, balance)
        diversity = 0.6 * coverage + 0.4 * balance
        diversity = max(0.1, min(1.0, diversity))

    # Temporal consistency — measures how evenly items are spread across time.
    # A theme concentrated in one week scores lower than one spread across months.
    def _to_utc(ts):
        return ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts

    timestamps = [_to_utc(item.source_timestamp) for item in items if item.source_timestamp]
    if len(timestamps) >= 2:
        ts_sorted = sorted(timestamps)
        span_days = max(1, (ts_sorted[-1] - ts_sorted[0]).days)
        # Divide span into 4 quartile periods and measure evenness of item distribution
        bucket_size = span_days / 4.0
        if bucket_size > 0:
            buckets = [0, 0, 0, 0]
            t0 = ts_sorted[0]
            for ts in ts_sorted:
                idx = min(3, int((ts - t0).days / bucket_size))
                buckets[idx] += 1
            total_ts = sum(buckets)
            if total_ts > 0:
                # Evenness: 1 - normalized std deviation (0 = all in one bucket, 1 = perfectly even)
                mean_b = total_ts / 4.0
                variance = sum((b - mean_b) ** 2 for b in buckets) / 4.0
                std_dev = variance ** 0.5
                max_std = mean_b * (3 ** 0.5 / 2)  # max possible std for 4 buckets
                evenness = 1.0 - (std_dev / max_std) if max_std > 0 else 0.5
            else:
                evenness = 0.3
        else:
            evenness = 0.3
        # Combine span breadth (how long) and evenness (how spread)
        span_score = min(1.0, math.log(1 + span_days) / math.log(1 + 365))
        temporal = 0.4 * span_score + 0.6 * evenness
        temporal = max(0.1, min(1.0, temporal))
    else:
        temporal = 0.1 if len(timestamps) == 0 else 0.3

    # Internal agreement — sentiment concentration.
    # High agreement (80%+ same sentiment) = high score. Mixed = low score.
    sentiments = [
        sentiment_map[item.item_id].sentiment.value
        for item in items
        if item.item_id in sentiment_map
    ]
    if sentiments:
        counts = Counter(sentiments)
        most_common_count = counts.most_common(1)[0][1]
        agreement = most_common_count / len(sentiments)
        # Also consider how many distinct sentiments appear — 4 is max fragmentation
        n_sentiments = len(counts)
        # Penalise fragmentation: 1 sentiment = full agreement, 4 = more mixed
        frag_penalty = 1.0 - (n_sentiments - 1) * 0.1  # mild penalty
        agreement = agreement * max(0.7, frag_penalty)
    else:
        agreement = 0.5

    # Data recency — continuous decay based on how old the newest item is.
    # Smooth exponential decay: 0 days = 1.0, 90 days = ~0.7, 180 = ~0.5, 365 = ~0.3
    now = datetime.now(timezone.utc)
    if timestamps:
        newest = max(timestamps)
        if newest.tzinfo is None:
            newest = newest.replace(tzinfo=timezone.utc)
        days_old = max(0, (now - newest).days)
        # Exponential decay with half-life of ~120 days
        recency = max(0.1, math.exp(-0.005 * days_old))
    else:
        recency = 0.1

    return ConfidenceBreakdown(
        sample_size_score=round(sample, 2),
        source_diversity_score=round(diversity, 2),
        temporal_consistency_score=round(temporal, 2),
        internal_agreement_score=round(agreement, 2),
        data_recency_score=round(recency, 2),
    )


def _compute_signal_strength(
    supporting_items: list[NormalizedItem],
    sentiment_map: dict,
    all_items: list[NormalizedItem],
    corpus_p75_engagement: int,
    engagement_percentile_rank: float = 0.5,
) -> SignalStrengthBreakdown:
    """Compute signal strength factors — all from data, no LLM.

    Uses continuous scoring with logarithmic scales and corpus-relative
    percentiles so insights differentiate on the radar chart.
    """
    import math

    # Prevalence: % of corpus this theme covers (thread-weighted).
    # Log-scaled so small differences at the top end still show variation.
    if all_items:
        supporting_threads = set()
        for item in supporting_items:
            tid = item.platform_metadata.thread_id
            supporting_threads.add(tid or item.item_id)

        total_threads = set()
        for item in all_items:
            tid = item.platform_metadata.thread_id
            total_threads.add(tid or item.item_id)

        prevalence = len(supporting_threads) / len(total_threads) if total_threads else 0
        # Log-scaled: 0.5% -> ~0.15, 2% -> ~0.35, 5% -> ~0.50, 15% -> ~0.72, 30%+ -> ~0.90
        prevalence_score = min(1.0, math.log(1 + prevalence * 100) / math.log(1 + 100))
        prevalence_score = max(0.05, prevalence_score)
    else:
        prevalence_score = 0.0

    # Engagement level: percentile rank of this insight's avg engagement
    # relative to all other insights. This guarantees differentiation.
    # Blend with absolute log-ratio for anchoring to corpus baseline.
    scores = [
        item.platform_metadata.score or item.platform_metadata.like_count or 0
        for item in supporting_items
    ]
    if scores and corpus_p75_engagement > 0:
        avg_engagement = sum(scores) / len(scores)
        ratio = avg_engagement / corpus_p75_engagement
        # Absolute component: log-scaled ratio against corpus p75
        abs_score = min(1.0, math.log(1 + ratio * 3) / math.log(1 + 30))
        # Relative component: percentile rank among all insights (guaranteed spread)
        rel_score = 0.15 + 0.70 * engagement_percentile_rank  # maps [0,1] to [0.15, 0.85]
        # Blend: 40% absolute + 60% relative (relative ensures differentiation)
        engagement_score = 0.4 * abs_score + 0.6 * rel_score
        engagement_score = max(0.05, min(1.0, engagement_score))
    else:
        engagement_score = 0.15 + 0.70 * engagement_percentile_rank

    # Sentiment intensity: how extreme (not just direction).
    # Uses standard deviation of sentiment scores for richer signal.
    intensities = [
        sentiment_map[item.item_id].sentiment_score
        for item in supporting_items
        if item.item_id in sentiment_map
    ]
    if intensities:
        # Average distance from neutral (0.5)
        avg_intensity = sum(abs(i - 0.5) for i in intensities) / len(intensities)
        # Also factor in variance — high variance = polarised = strong signal
        mean_s = sum(intensities) / len(intensities)
        variance = sum((i - mean_s) ** 2 for i in intensities) / len(intensities) if len(intensities) > 1 else 0
        std_dev = variance ** 0.5
        # Combine: intensity (how far from neutral) + polarisation (how spread)
        intensity_score = min(1.0, avg_intensity * 2.5 + std_dev * 1.5)
        intensity_score = max(0.05, intensity_score)
    else:
        intensity_score = 0.1

    # Conversation depth: proportion of comments (vs posts) + actual reply depth.
    # More comments relative to posts = deeper conversation.
    comments = [item for item in supporting_items if item.content_type.value == "comment"]
    posts = [item for item in supporting_items if item.content_type.value == "post"]
    n_total = len(supporting_items)

    if n_total > 0:
        comment_ratio = len(comments) / n_total
        # Depth from comment_depth field
        depths = [
            item.platform_metadata.comment_depth or 0
            for item in comments
        ]
        if depths:
            avg_depth = sum(depths) / len(depths)
            # Log-scaled depth: 0 -> 0, 1 -> ~0.5, 3 -> ~0.8, 5+ -> ~0.9
            depth_component = min(1.0, math.log(1 + avg_depth * 2) / math.log(1 + 10))
        else:
            depth_component = 0.1
        # Combine: comment density (60%) + actual reply depth (40%)
        depth_score = 0.6 * comment_ratio + 0.4 * depth_component
        depth_score = max(0.05, min(1.0, depth_score))
    else:
        depth_score = 0.1

    return SignalStrengthBreakdown(
        prevalence_score=round(prevalence_score, 2),
        engagement_level_score=round(engagement_score, 2),
        sentiment_intensity_score=round(intensity_score, 2),
        conversation_depth_score=round(depth_score, 2),
    )


def _confidence_tier(score: float) -> ConfidenceTier:
    if score >= 0.75:
        return ConfidenceTier.HIGH
    elif score >= 0.50:
        return ConfidenceTier.MEDIUM
    elif score >= 0.25:
        return ConfidenceTier.DIRECTIONAL
    return ConfidenceTier.INSUFFICIENT


def _signal_tier(score: float) -> SignalStrengthTier:
    if score >= 0.75:
        return SignalStrengthTier.STRONG
    elif score >= 0.50:
        return SignalStrengthTier.MODERATE
    elif score >= 0.25:
        return SignalStrengthTier.WEAK
    return SignalStrengthTier.TRACE


def _wilson_ci(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score confidence interval for a proportion."""
    if total == 0:
        return (0.0, 0.0)
    p = successes / total
    denominator = 1 + z**2 / total
    centre = (p + z**2 / (2 * total)) / denominator
    spread = z * ((p * (1 - p) / total + z**2 / (4 * total**2)) ** 0.5) / denominator
    lower = max(0.0, round(centre - spread, 4))
    upper = min(1.0, round(centre + spread, 4))
    return (lower, upper)


# ─── Brand Health Score ─────────────────────────────────────────────────────

def compute_brand_health(
    analysis: AnalysisResults,
    items: list[NormalizedItem],
) -> dict:
    """Compute a composite Brand Health Score (0-100) from data we already have.

    Five components, all data-driven (no LLM opinion):
    1. Sentiment (0.30): NSS rescaled from [-1,+1] to [0,100]
    2. Engagement (0.25): median engagement relative to corpus baseline
    3. Advocacy (0.20): % of items with strongly positive sentiment (score >= 0.8)
    4. Resilience (0.15): consistency of sentiment across platforms
    5. Conversation (0.10): log-scaled volume + avg depth

    Returns dict with overall_score and component scores (all 0-100).
    """
    import math

    sentiment_map = {s.item_id: s for s in analysis.sentiment_results}

    # 1. Sentiment component: NSS [-1,+1] → [0, 100]
    nss = getattr(analysis, "net_sentiment_score", 0.0)
    sentiment_component = round((nss + 1) / 2 * 100, 1)

    # 2. Engagement component: ratio of above-median items
    scores_list = [
        item.platform_metadata.score or item.platform_metadata.like_count or 0
        for item in items
    ]
    if scores_list:
        sorted_scores = sorted(scores_list)
        median = sorted_scores[len(sorted_scores) // 2]
        if median > 0:
            above_median_ratio = sum(1 for s in scores_list if s > median) / len(scores_list)
            engagement_component = round(min(100, above_median_ratio * 200), 1)  # 50% above median = 100
        else:
            engagement_component = 50.0  # No meaningful engagement data
    else:
        engagement_component = 50.0

    # 3. Advocacy component: % of items with sentiment_score >= 0.8
    total_with_sentiment = len(analysis.sentiment_results)
    strongly_positive = sum(
        1 for r in analysis.sentiment_results
        if r.sentiment_score >= 0.8 and r.sentiment.value == "positive"
    )
    if total_with_sentiment > 0:
        advocacy_ratio = strongly_positive / total_with_sentiment
        advocacy_component = round(min(100, advocacy_ratio * 500), 1)  # 20% strongly positive = 100
    else:
        advocacy_ratio = None
        advocacy_component = 50.0

    # 4. Resilience component: sentiment consistency across platforms
    platform_sentiments: dict[str, list[float]] = {}
    for item in items:
        if item.item_id in sentiment_map:
            p = item.source_platform.value
            platform_sentiments.setdefault(p, []).append(
                sentiment_map[item.item_id].sentiment_score
            )

    if len(platform_sentiments) >= 2:
        platform_means = [sum(v) / len(v) for v in platform_sentiments.values()]
        mean_of_means = sum(platform_means) / len(platform_means)
        variance = sum((m - mean_of_means) ** 2 for m in platform_means) / len(platform_means)
        std_dev = math.sqrt(variance)
        # Low std_dev = high resilience (consistent across platforms)
        resilience_component = round(max(0, min(100, (1 - std_dev * 4) * 100)), 1)
    else:
        resilience_component = 50.0  # Single platform — neutral

    # 5. Conversation component: log(volume) + depth
    volume = len(items)
    log_volume = math.log10(max(1, volume))
    # Normalize: 100 items (log=2) → 40, 1000 items (log=3) → 60, 10000 (log=4) → 80
    volume_score = min(100, log_volume * 20)

    depths = [
        item.platform_metadata.comment_depth or 0
        for item in items
        if item.content_type.value == "comment"
    ]
    avg_depth = sum(depths) / len(depths) if depths else 0
    depth_score = min(100, avg_depth * 40)  # depth 2.5 = 100

    conversation_component = round((volume_score + depth_score) / 2, 1)

    # Weighted composite
    overall = round(
        0.30 * sentiment_component
        + 0.25 * engagement_component
        + 0.20 * advocacy_component
        + 0.15 * resilience_component
        + 0.10 * conversation_component,
        1,
    )

    result = {
        "overall_score": overall,
        "sentiment_component": sentiment_component,
        "engagement_component": engagement_component,
        "advocacy_component": advocacy_component,
        "resilience_component": resilience_component,
        "conversation_component": conversation_component,
        # The component saturates at a 20% share, so it cannot report how far past the bar a
        # corpus sits. Carry the underlying share so the report can print it alongside.
        "advocacy_ratio_pct": (round(advocacy_ratio * 100, 1)
                               if advocacy_ratio is not None else None),
    }

    logger.info(f"Brand Health Score: {overall}/100 "
                f"(Sent={sentiment_component}, Eng={engagement_component}, "
                f"Adv={advocacy_component}, Res={resilience_component}, "
                f"Conv={conversation_component})")

    return result
