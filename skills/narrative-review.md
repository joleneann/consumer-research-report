# Stage 4c: Narrative Review

You are a senior consumer research analyst performing a narrative review pass. Your job is to read items that were NOT assigned to any theme during keyword-based theme extraction, and discover narrative patterns that keywords cannot detect.

**Parameter:** `run_id` - the run directory name (e.g., `20260407_184943_08eb92`). This will be provided when the skill is invoked.

## Step 1: Load Data

Read these files from the run directory:

```
runs/{run_id}/config.json           -> brand_name, category
runs/{run_id}/filtered/corpus.json  -> the filtered corpus (all items)
runs/{run_id}/analysis/results.json -> existing themes[] and sentiment_results[]
```

Extract:
- `brand_name` and `category` from config
- All items from filtered corpus
- All themes and their `supporting_item_ids` from results
- The `sentiment_results` array (you need this to compute sentiment for new themes)

## Step 2: Identify Unthemed Items

Build a set of all item_ids that appear in ANY theme's `supporting_item_ids`. Items NOT in this set are "unthemed." Calculate what percentage of the filtered corpus is unthemed.

## Step 3: Read and Analyse

**Read ALL unthemed items.** If the unthemed set is large, read in batches, but cover every item. Do not sample within the unthemed set.

**Also read a 10% random sample of themed items** to check for misclassification.

For each item, look for narrative patterns that keyword-based theme mapping cannot detect:

1. **Cultural references** - celebrity mentions, regional pride, festival/occasion contexts, Bollywood, cricket, pop culture connections to the brand/category
2. **Sarcasm, irony, memes** - items where the literal text contradicts the intended meaning, humorous commentary, viral formats
3. **Misinformation and conspiracy framing** - miracle claims, fear-based content, debunking, fact-checking responses, pseudoscience
4. **Moral and ethical debates** - "is it cheating?", stigma, shame, environmental concerns, labor conditions, fairness arguments
5. **Personal anecdotes** - first-person experience stories that don't use theme keywords but describe lived experience with the brand/category
6. **Cross-cutting emotional narratives** - pride, frustration, hope, cynicism, nostalgia that spans multiple existing themes
7. **Framing beyond existing themes** - any coherent perspective on the brand/category that existing themes don't capture

## Step 4: Build Narrative Themes

For each discovered pattern with 5+ items, create a Theme object. The output MUST match the `Theme` schema in `consumer_research/models/schemas.py`.

**Required fields for each narrative theme:**

```json
{
  "theme_id": "THM_NAR_01",
  "theme_label": "Descriptive Label",
  "theme_description": "Why this is a distinct narrative pattern and why keywords missed it",
  "supporting_item_ids": ["id1", "id2", ...],
  "item_count": 12,
  "prevalence_pct": 0.34,
  "sentiment_distribution": {"positive": 3, "negative": 5, "neutral": 2, "mixed": 2},
  "emotion_distribution": {"anger": 3, "sadness": 2, "trust": 1, ...},
  "net_sentiment_score": -0.167,
  "representative_quotes": [
    {
      "text": "The actual consumer quote text",
      "item_id": "abc123",
      "source_url": "https://...",
      "source_platform": "reddit",
      "source_timestamp": "2025-12-29T00:00:00Z",
      "engagement_score": null,
      "selection_reason": "High theme-relevance consumer voice"
    }
  ],
  "platforms_present": ["reddit", "twitter", "youtube"],
  "is_multi_source": true,
  "is_contested": false
}
```

**How to compute each field:**

- `prevalence_pct`: `item_count / len(filtered_corpus) * 100`
- `sentiment_distribution`: Look up each `supporting_item_id` in the `sentiment_results` array from `results.json`. Count sentiments. If an item has no sentiment result, skip it.
- `emotion_distribution`: Same lookup, count `primary_emotion` values.
- `net_sentiment_score`: `(positive - negative) / total` from the sentiment_distribution.
- `representative_quotes`: Select 2-3 quotes per theme. For each quote, look up the item in the filtered corpus to get `source_url`, `source_platform`, and `source_timestamp`. Read `platform_metadata.score` or `platform_metadata.like_count` for `engagement_score` (use null if unavailable). Prefer comments over posts, medium-length text (80-500 chars), and items with strong theme-keyword relevance.
- `platforms_present`: Distinct `source_platform` values from supporting items.
- `is_multi_source`: `len(platforms_present) >= 2`
- `is_contested`: True if the dominant sentiment differs between platforms (e.g., positive on Reddit, negative on Twitter).

## Step 5: Reassign Items to Existing Themes

If you find unthemed items that actually belong in an existing theme (keyword matching just missed them), add their `item_id` to that theme's `supporting_item_ids` and update `item_count` and `prevalence_pct`.

## Step 6: Write Output

**Update `runs/{run_id}/analysis/results.json`:**
- Read the existing file
- Append new narrative themes to the `themes` array
- Update any existing themes where you reassigned items (update `supporting_item_ids`, `item_count`, `prevalence_pct`)
- Preserve ALL other fields unchanged (`sentiment_results`, `overall_sentiment`, `net_sentiment_score`, `total_items_analyzed`, `analysis_model`, `analysis_prompts`)
- Write back to the same file

**Write `runs/{run_id}/analysis/narrative_review_summary.json`:**
```json
{
  "total_unthemed_reviewed": 205,
  "themed_sample_reviewed": 331,
  "narrative_themes_found": 5,
  "items_reassigned_to_existing_themes": 82,
  "remaining_unthemed_after_review": 85,
  "remaining_unthemed_pct": 2.4,
  "misclassified_items": [],
  "observations": "Free-text summary of patterns observed"
}
```

## Quality Standards

- Read EVERY unthemed item. Do not skip or sample within the unthemed set.
- A narrative theme needs at least 5 items to be worth reporting.
- Include 2-3 representative quotes per theme with full VerbatimQuote fields.
- In `theme_description`, explain WHY keyword matching failed to catch this pattern. This is the core value of narrative review.
- If all unthemed items are genuinely off-topic noise, say so. Do not manufacture themes.
- Completion criterion: unthemed items below 10% of corpus after your review. If still above 10%, keep reading and classifying.
- `source_platform` must use the enum values from the data: `reddit`, `youtube`, `twitter`, `instagram`, `amazon`, `news`, `academic`, `web`, `trends`.
