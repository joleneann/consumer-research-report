"""Stage 4: Analysis engine - sentiment, theme extraction, cross-source triangulation.

Uses Claude API to perform:
1. Per-item sentiment classification with aspect extraction
2. Theme extraction across the corpus
3. Cross-source triangulation (do themes appear on multiple platforms?)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from consumer_research.models.schemas import (
    AnalysisResults,
    AspectSentiment,
    Emotion,
    NormalizedItem,
    Sentiment,
    SentimentResult,
    SourcePlatform,
    Theme,
    VerbatimQuote,
    compute_nss,
)

logger = logging.getLogger(__name__)

SENTIMENT_PROMPT = """You are a consumer sentiment and emotion analyst.

Brand: {brand_name}
Category: {category}

For each item below, classify:
1. SENTIMENT toward {brand_name} (positive/negative/neutral/mixed)
2. PRIMARY EMOTION using Plutchik's model (joy/trust/fear/surprise/sadness/disgust/anger/anticipation/none)
3. ASPECT-LEVEL SENTIMENT — for each product/brand aspect mentioned, score sentiment separately

Respond with a JSON array:
[
  {{
    "item_id": "<id>",
    "sentiment": "positive|negative|neutral|mixed",
    "sentiment_score": 0.0-1.0,
    "reasoning": "Brief explanation",
    "key_phrases": ["phrase1", "phrase2"],
    "primary_emotion": "joy|trust|fear|surprise|sadness|disgust|anger|anticipation|none",
    "emotion_intensity": 0.0-1.0,
    "secondary_emotion": "joy|trust|fear|surprise|sadness|disgust|anger|anticipation|none",
    "aspects": [
      {{"aspect": "taste", "sentiment": "positive", "score": 0.85}},
      {{"aspect": "price", "sentiment": "negative", "score": 0.3}}
    ]
  }}
]

Guidelines:
- Emotion intensity: 0.0 = barely detectable, 1.0 = extremely strong
- Aspects: extract specific product/brand attributes (taste, price, packaging, availability, quality, health, occasions, etc.) and score sentiment for EACH independently
- secondary_emotion: the second strongest emotion, or "none" if only one is detectable
- Content may be in English, Hindi, or Hinglish — treat all languages equally

Items:
{items_json}

Respond ONLY with the JSON array."""

THEME_DISCOVERY_PROMPT = """You are a consumer research thematic analyst.

Brand: {brand_name}
Category: {category}

Analyze the following consumer discussions and identify recurring THEMES.
A theme is a pattern of consumer perception that appears across multiple items.

Each theme must:
- Have a clear, specific label (not generic like "positive feedback")
- Have a short keyword list that would identify similar items

The four perception dimensions to consider:
1. Cognitive Associations (what consumers think - attributes, quality, features)
2. Emotional Resonance (how they feel - trust, excitement, frustration)
3. Behavioral Signals (how they act - occasions, triggers, loyalty)
4. Competitive Position (vs alternatives - preference drivers, switching)

Respond with a JSON array of themes (aim for 8-15 themes):
[
  {{
    "theme_id": "THM_001",
    "theme_label": "Specific theme name",
    "theme_description": "What this theme captures in 1-2 sentences",
    "perception_dimension": "cognitive|emotional|behavioral|competitive",
    "keywords": ["keyword1", "keyword2", "keyword3"],
    "supporting_item_ids": ["id1", "id2", "id3"],
    "representative_quote_ids": ["id_of_best_quote1", "id_of_best_quote2"]
  }}
]

Consumer data (item_id, platform, text, sentiment):
{items_json}

Respond ONLY with the JSON array."""

THEME_MAPPING_PROMPT = """You are a consumer research analyst.

Brand: {brand_name}

For each item below, determine which of the following themes it belongs to (if any).
An item can belong to MULTIPLE themes. If it doesn't match any theme clearly, return an empty list.

THEMES:
{themes_json}

ITEMS TO CLASSIFY:
{items_json}

Respond with a JSON array:
[
  {{
    "item_id": "<id>",
    "matching_theme_ids": ["THM_001", "THM_003"]
  }}
]

Respond ONLY with the JSON array. Every item_id must appear exactly once."""


def analyze_corpus(
    items: list[NormalizedItem],
    brand_name: str,
    category: str,
    run_dir: Path,
    llm_client,
    batch_size: int = 15,
    min_items_for_theme: int = 3,
) -> AnalysisResults:
    """Run sentiment analysis and theme extraction on the filtered corpus.

    Args:
        items: Filtered corpus items.
        brand_name: Brand being analyzed.
        category: Product category.
        run_dir: Run directory for output.
        llm_client: LLMClient instance (Claude or Gemini).
        batch_size: Items per sentiment batch.
        min_items_for_theme: Minimum items to form a theme.

    Returns:
        AnalysisResults with sentiment data, themes, and triangulation.
    """
    analysis_dir = run_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    # ── Step 1: Sentiment Classification ──
    logger.info(f"Analyzing sentiment for {len(items)} items...")
    sentiment_results = _classify_sentiment(
        items, brand_name, category, llm_client, batch_size
    )

    # ── Step 2: Theme Extraction ──
    logger.info("Extracting themes...")
    sentiment_map = {r.item_id: r for r in sentiment_results}
    themes = _extract_themes(
        items, sentiment_map, brand_name, category, llm_client, min_items_for_theme
    )

    # ── Step 3: Cross-Source Triangulation ──
    logger.info("Triangulating across sources...")
    item_map = {item.item_id: item for item in items}
    for theme in themes:
        platforms_in_theme = set()
        for item_id in theme.supporting_item_ids:
            if item_id in item_map:
                platforms_in_theme.add(item_map[item_id].source_platform)
        theme.platforms_present = list(platforms_in_theme)
        theme.is_multi_source = len(platforms_in_theme) >= 2

        # Check for contested themes (different platforms disagree on sentiment)
        if theme.is_multi_source:
            platform_sentiments: dict[str, list[str]] = {}
            for item_id in theme.supporting_item_ids:
                if item_id in item_map and item_id in sentiment_map:
                    platform = item_map[item_id].source_platform.value
                    sent = sentiment_map[item_id].sentiment.value
                    platform_sentiments.setdefault(platform, []).append(sent)

            dominant_sentiments = {}
            for platform, sents in platform_sentiments.items():
                from collections import Counter
                dominant_sentiments[platform] = Counter(sents).most_common(1)[0][0]

            theme.is_contested = len(set(dominant_sentiments.values())) > 1

    # Build representative quotes with full provenance
    for theme in themes:
        quotes = []
        for qid in getattr(theme, "_quote_ids", []):
            if qid in item_map:
                item = item_map[qid]
                engagement = item.platform_metadata.score or item.platform_metadata.like_count or 0
                quotes.append(VerbatimQuote(
                    text=item.content_text[:300],
                    item_id=qid,
                    source_url=item.source_url,
                    source_platform=item.source_platform,
                    source_timestamp=item.source_timestamp,
                    engagement_score=engagement,
                    selection_reason="Highest engagement among theme members",
                ))
        if not quotes and theme.supporting_item_ids:
            # Fallback: pick first item as quote
            first_id = theme.supporting_item_ids[0]
            if first_id in item_map:
                item = item_map[first_id]
                quotes.append(VerbatimQuote(
                    text=item.content_text[:300],
                    item_id=first_id,
                    source_url=item.source_url,
                    source_platform=item.source_platform,
                    source_timestamp=item.source_timestamp,
                    engagement_score=item.platform_metadata.score or 0,
                    selection_reason="First item in theme (fallback)",
                ))
        theme.representative_quotes = quotes

    # Compute overall sentiment
    overall = {"positive": 0, "negative": 0, "neutral": 0, "mixed": 0}
    for r in sentiment_results:
        overall[r.sentiment.value] = overall.get(r.sentiment.value, 0) + 1

    # Compute Net Sentiment Score (industry standard: Brandwatch, Sprinklr, YouGov)
    nss = compute_nss(overall)
    logger.info(f"  Net Sentiment Score: {nss:+.2%}")

    # Compute corpus-wide emotion distribution (Plutchik's 8 emotions)
    emotion_dist: dict[str, int] = {}
    for r in sentiment_results:
        if r.primary_emotion != Emotion.NONE:
            e = r.primary_emotion.value
            emotion_dist[e] = emotion_dist.get(e, 0) + 1
    logger.info(f"  Emotion distribution: {emotion_dist}")

    # Compute aspect sentiment summary (ABSA aggregation)
    aspect_summary: dict[str, dict[str, int]] = {}
    for r in sentiment_results:
        for asp in r.aspects:
            if asp.aspect not in aspect_summary:
                aspect_summary[asp.aspect] = {"positive": 0, "negative": 0, "neutral": 0, "mixed": 0}
            aspect_summary[asp.aspect][asp.sentiment.value] += 1
    logger.info(f"  Aspects tracked: {len(aspect_summary)} unique aspects")

    # Compute per-theme emotion distribution and NSS
    for theme in themes:
        theme_emotion_dist: dict[str, int] = {}
        for iid in theme.supporting_item_ids:
            if iid in sentiment_map:
                sr = sentiment_map[iid]
                if sr.primary_emotion != Emotion.NONE:
                    e = sr.primary_emotion.value
                    theme_emotion_dist[e] = theme_emotion_dist.get(e, 0) + 1
        theme.emotion_distribution = theme_emotion_dist
        theme.net_sentiment_score = compute_nss(theme.sentiment_distribution)

    results = AnalysisResults(
        sentiment_results=sentiment_results,
        themes=themes,
        overall_sentiment=overall,
        net_sentiment_score=nss,
        emotion_distribution=emotion_dist,
        aspect_sentiment_summary=aspect_summary,
        total_items_analyzed=len(items),
        analysis_model=llm_client.model_name,
        analysis_prompts={
            "sentiment": SENTIMENT_PROMPT.format(
                brand_name=brand_name, category=category, items_json="[...]"
            ),
            "theme_discovery": THEME_DISCOVERY_PROMPT.format(
                brand_name=brand_name,
                category=category,
                items_json="[...]",
            ),
        },
    )

    # Write outputs
    results_data = results.model_dump(mode="json")
    (analysis_dir / "results.json").write_text(
        json.dumps(results_data, indent=2, default=str), encoding="utf-8"
    )

    logger.info(
        f"Analysis complete: {len(sentiment_results)} sentiment results, "
        f"{len(themes)} themes ({sum(1 for t in themes if t.is_multi_source)} multi-source)"
    )

    return results


def _classify_sentiment(
    items: list[NormalizedItem],
    brand_name: str,
    category: str,
    llm_client,
    batch_size: int,
) -> list[SentimentResult]:
    """Classify sentiment for each item in batches."""
    results: list[SentimentResult] = []
    degraded_count = 0

    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        batch_json = json.dumps(
            [
                {
                    "item_id": item.item_id,
                    "platform": item.source_platform.value,
                    "text": item.content_text[:500],
                }
                for item in batch
            ],
            indent=2,
        )

        prompt = SENTIMENT_PROMPT.format(
            brand_name=brand_name, category=category, items_json=batch_json
        )

        try:
            text = llm_client.generate(prompt, max_tokens=4096, temperature=0.0)
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]

            parsed = json.loads(text)
            for item_data in parsed:
                # Parse aspect-based sentiment (ABSA)
                raw_aspects = item_data.get("aspects", [])
                aspects: list[AspectSentiment] = []
                for a in raw_aspects:
                    if isinstance(a, dict):
                        try:
                            aspects.append(AspectSentiment(
                                aspect=a.get("aspect", "unknown"),
                                sentiment=Sentiment(a.get("sentiment", "neutral")),
                                sentiment_score=a.get("score", 0.5),
                            ))
                        except (ValueError, KeyError):
                            pass
                    elif isinstance(a, str):
                        # Backward compat: flat string → neutral aspect
                        aspects.append(AspectSentiment(
                            aspect=a, sentiment=Sentiment.NEUTRAL, sentiment_score=0.5
                        ))

                # Parse Plutchik emotions
                try:
                    primary_emotion = Emotion(item_data.get("primary_emotion", "none"))
                except ValueError:
                    primary_emotion = Emotion.NONE
                try:
                    secondary_emotion = Emotion(item_data.get("secondary_emotion", "none"))
                except ValueError:
                    secondary_emotion = None

                results.append(SentimentResult(
                    item_id=item_data["item_id"],
                    sentiment=Sentiment(item_data["sentiment"]),
                    sentiment_score=item_data.get("sentiment_score", 0.5),
                    reasoning=item_data.get("reasoning", ""),
                    key_phrases=item_data.get("key_phrases", []),
                    aspects=aspects,
                    primary_emotion=primary_emotion,
                    emotion_intensity=item_data.get("emotion_intensity", 0.0),
                    secondary_emotion=secondary_emotion,
                ))

            # Check for incomplete LLM response — assign neutral defaults so corpus totals stay consistent
            returned_ids = {d["item_id"] for d in parsed if "item_id" in d}
            sent_ids = {item.item_id for item in batch}
            missing_ids = sent_ids - returned_ids
            if missing_ids:
                logger.warning(
                    f"  Sentiment batch {i // batch_size + 1}: LLM returned {len(parsed)}/{len(batch)} items. "
                    f"Assigning neutral defaults to {len(missing_ids)} missing item(s): {list(missing_ids)[:5]}"
                )
                for mid in missing_ids:
                    results.append(SentimentResult(
                        item_id=mid,
                        sentiment=Sentiment.NEUTRAL,
                        sentiment_score=0.5,
                        reasoning="LLM did not return classification for this item",
                        key_phrases=[],
                        aspects=[],
                        primary_emotion=Emotion.NONE,
                        emotion_intensity=0.0,
                    ))

            logger.info(f"  Sentiment batch {i // batch_size + 1}: {len(parsed)} classified")

        except Exception as e:
            logger.error(f"  Sentiment batch error: {e}. Assigning neutral defaults to {len(batch)} items.")
            degraded_count += len(batch)
            for item in batch:
                results.append(SentimentResult(
                    item_id=item.item_id,
                    sentiment=Sentiment.NEUTRAL,
                    sentiment_score=0.5,
                    reasoning=f"Batch error: {e}",
                    key_phrases=[],
                    aspects=[],
                    primary_emotion=Emotion.NONE,
                    emotion_intensity=0.0,
                ))

    if degraded_count > 0:
        pct = degraded_count / len(items) * 100
        logger.warning(
            f"DEGRADED ANALYSIS: {degraded_count} of {len(items)} items ({pct:.1f}%) "
            f"received default neutral classification due to batch errors. "
            f"NSS and brand health scores may be flattened. Review batch error logs above."
        )

    return results


def _extract_themes(
    items: list[NormalizedItem],
    sentiment_map: dict[str, SentimentResult],
    brand_name: str,
    category: str,
    llm_client,
    min_items: int,
) -> list[Theme]:
    """Extract themes using a two-pass approach:
    Pass 1: Discover themes from a representative sample.
    Pass 2: Map ALL items to the discovered themes in batches.
    """
    import random

    # ── Pass 1: Theme Discovery (stratified sample) ──
    # Sample up to 300 items, stratified by platform for diversity
    by_platform: dict[str, list[NormalizedItem]] = {}
    for item in items:
        p = item.source_platform.value
        by_platform.setdefault(p, []).append(item)

    # Sort each platform group by item_id for deterministic sampling
    for platform in by_platform:
        by_platform[platform].sort(key=lambda x: x.item_id)

    sample: list[NormalizedItem] = []
    sample_target = min(300, len(items))
    for platform_items in by_platform.values():
        quota = max(1, int(len(platform_items) / len(items) * sample_target))
        sample.extend(platform_items[:quota])
    # Top up to sample_target if needed
    sample_ids = {i.item_id for i in sample}
    remaining = [i for i in items if i.item_id not in sample_ids]
    random.seed(42)
    random.shuffle(remaining)
    sample.extend(remaining[: sample_target - len(sample)])
    sample = sample[:sample_target]

    logger.info(f"  Theme discovery: sampling {len(sample)}/{len(items)} items (stratified by platform)")

    discovery_items = []
    for item in sample:
        sent = sentiment_map.get(item.item_id)
        discovery_items.append({
            "item_id": item.item_id,
            "platform": item.source_platform.value,
            "text": item.content_text[:300],
            "sentiment": sent.sentiment.value if sent else "unknown",
        })

    discovery_prompt = THEME_DISCOVERY_PROMPT.format(
        brand_name=brand_name,
        category=category,
        items_json=json.dumps(discovery_items, indent=2),
    )

    try:
        text = llm_client.generate(discovery_prompt, max_tokens=8192, temperature=0.0)
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        candidate_themes = json.loads(text)
        logger.info(f"  Theme discovery: {len(candidate_themes)} themes found")
    except Exception as e:
        logger.error(f"Theme discovery error: {e}")
        return []

    if not candidate_themes:
        return []

    # Build initial theme→item mapping from discovery items
    theme_item_map: dict[str, set[str]] = {t["theme_id"]: set(t.get("supporting_item_ids", [])) for t in candidate_themes}
    theme_quote_ids: dict[str, list[str]] = {t["theme_id"]: t.get("representative_quote_ids", []) for t in candidate_themes}

    # ── Pass 2: Map ALL remaining items to themes in batches ──
    mapped_ids = {iid for ids in theme_item_map.values() for iid in ids}
    unmapped_items = sorted(
        [i for i in items if i.item_id not in mapped_ids],
        key=lambda x: x.item_id,
    )
    logger.info(f"  Theme mapping: classifying {len(unmapped_items)} remaining items in batches...")

    themes_summary = json.dumps([
        {"theme_id": t["theme_id"], "theme_label": t["theme_label"], "theme_description": t["theme_description"]}
        for t in candidate_themes
    ], indent=2)

    batch_size = 30
    for batch_start in range(0, len(unmapped_items), batch_size):
        batch = unmapped_items[batch_start: batch_start + batch_size]
        batch_json = json.dumps([
            {
                "item_id": item.item_id,
                "platform": item.source_platform.value,
                "text": item.content_text[:200],
                "sentiment": sentiment_map.get(item.item_id, None) and sentiment_map[item.item_id].sentiment.value or "unknown",
            }
            for item in batch
        ], indent=2)

        mapping_prompt = THEME_MAPPING_PROMPT.format(
            brand_name=brand_name,
            themes_json=themes_summary,
            items_json=batch_json,
        )

        try:
            text = llm_client.generate(mapping_prompt, max_tokens=4096, temperature=0.0)
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            mappings = json.loads(text)
            for m in mappings:
                iid = m["item_id"]
                for tid in m.get("matching_theme_ids", []):
                    if tid in theme_item_map:
                        theme_item_map[tid].add(iid)
        except Exception as e:
            logger.error(f"  Theme mapping batch error (non-fatal): {e}")

        logger.info(f"  Theme mapping: batch {batch_start // batch_size + 1}/{(len(unmapped_items) + batch_size - 1) // batch_size} done")

    # ── Build Theme objects ──
    themes: list[Theme] = []
    for t in candidate_themes:
        tid = t["theme_id"]
        supporting_ids = list(theme_item_map[tid])

        if len(supporting_ids) < min_items:
            logger.info(f"  Dropping theme {tid} ({t['theme_label']}) — only {len(supporting_ids)} items (min {min_items})")
            continue

        # Compute sentiment distribution from mapped items
        sent_dist = {"positive": 0, "negative": 0, "neutral": 0, "mixed": 0}
        for iid in supporting_ids:
            if iid in sentiment_map:
                s = sentiment_map[iid].sentiment.value
                sent_dist[s] = sent_dist.get(s, 0) + 1

        theme = Theme(
            theme_id=tid,
            theme_label=t["theme_label"],
            theme_description=t["theme_description"],
            supporting_item_ids=supporting_ids,
            item_count=len(supporting_ids),
            prevalence_pct=round(len(supporting_ids) / len(items) * 100, 1),
            sentiment_distribution=sent_dist,
            representative_quotes=[],
            platforms_present=[],
            is_multi_source=False,
        )
        theme._quote_ids = theme_quote_ids.get(tid, [])  # type: ignore
        themes.append(theme)

    themes.sort(key=lambda t: t.item_count, reverse=True)
    logger.info(f"  Final themes: {len(themes)} (after min_items={min_items} filter)")
    return themes
