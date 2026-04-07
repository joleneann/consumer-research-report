"""Write complete analysis/results.json from Stage 4 outputs."""
import json
import sys
import random
import pathlib

sys.stdout.reconfigure(encoding="utf-8")

RUN_DIR = pathlib.Path("runs/20260407_173532_06e43d")

# Load all Stage 4 artifacts
filtered = json.loads((RUN_DIR / "filtered" / "corpus.json").read_text(encoding="utf-8"))
sentiment_results = json.loads((RUN_DIR / "analysis" / "sentiment_results.json").read_text(encoding="utf-8"))
themes_final = json.loads((RUN_DIR / "analysis" / "themes_final.json").read_text(encoding="utf-8"))
item_themes_map = json.loads((RUN_DIR / "analysis" / "item_themes.json").read_text(encoding="utf-8"))

# Build lookups
filtered_map = {i["item_id"]: i for i in filtered}
sentiment_map = {sr["item_id"]: sr for sr in sentiment_results}

# Compute overall sentiment
overall_sentiment = {"positive": 0, "negative": 0, "neutral": 0, "mixed": 0}
for sr in sentiment_results:
    if sr["item_id"] in item_themes_map:  # only count themed items
        s = sr["sentiment"]
        overall_sentiment[s] = overall_sentiment.get(s, 0) + 1

# Compute NSS
total = sum(overall_sentiment.values())
nss = (overall_sentiment["positive"] - overall_sentiment["negative"]) / total if total > 0 else 0

# Compute emotion distribution
emotion_dist = {}
for sr in sentiment_results:
    if sr["item_id"] in item_themes_map:
        e = sr["primary_emotion"]
        emotion_dist[e] = emotion_dist.get(e, 0) + 1

# Compute aspect sentiment summary
aspect_summary = {}
for sr in sentiment_results:
    if sr["item_id"] in item_themes_map:
        for asp in sr.get("aspects", []):
            name = asp["aspect"]
            sent = asp["sentiment"]
            if name not in aspect_summary:
                aspect_summary[name] = {"positive": 0, "negative": 0, "neutral": 0, "mixed": 0}
            aspect_summary[name][sent] = aspect_summary[name].get(sent, 0) + 1

# Build Theme objects with sentiment distributions and quotes
random.seed(42)
themes_output = []
for theme in themes_final:
    tid = theme["theme_id"]
    theme_item_ids = theme["item_ids"]

    # Compute per-theme sentiment
    theme_sent = {"positive": 0, "negative": 0, "neutral": 0, "mixed": 0}
    theme_emo = {}
    for iid in theme_item_ids:
        sr = sentiment_map.get(iid)
        if sr:
            theme_sent[sr["sentiment"]] = theme_sent.get(sr["sentiment"], 0) + 1
            e = sr["primary_emotion"]
            theme_emo[e] = theme_emo.get(e, 0) + 1

    # Compute theme NSS
    t_total = sum(theme_sent.values())
    theme_nss = (theme_sent["positive"] - theme_sent["negative"]) / t_total if t_total > 0 else 0

    # Select representative quotes (2-3 per theme)
    # Prefer comments over posts, medium length (80-500 chars), from different platforms
    candidates = []
    for iid in theme_item_ids:
        item = filtered_map.get(iid)
        if not item:
            continue
        text = item.get("content_text", "")
        if 80 <= len(text) <= 500 and item.get("content_type") == "comment":
            candidates.append(item)

    # If not enough comments, include posts
    if len(candidates) < 3:
        for iid in theme_item_ids:
            item = filtered_map.get(iid)
            if not item:
                continue
            text = item.get("content_text", "")
            if 80 <= len(text) <= 500 and item.get("content_type") == "post":
                candidates.append(item)

    # Pick from different platforms
    used_platforms = set()
    quotes = []
    random.shuffle(candidates)
    for item in candidates:
        plat = item.get("source_platform", "unknown")
        if plat not in used_platforms or len(quotes) < 2:
            quotes.append({
                "text": item["content_text"][:400],
                "item_id": item["item_id"],
                "source_url": item.get("source_url", ""),
                "source_platform": item.get("source_platform", "reddit"),
                "source_timestamp": item.get("source_timestamp"),
                "engagement_score": item.get("platform_metadata", {}).get("score"),
                "selection_reason": f"Representative consumer voice for {theme['label']}",
            })
            used_platforms.add(plat)
        if len(quotes) >= 3:
            break

    # Platforms present
    platforms = list(set(
        filtered_map[iid].get("source_platform", "unknown")
        for iid in theme_item_ids
        if iid in filtered_map
    ))

    themes_output.append({
        "theme_id": tid,
        "theme_label": theme["label"],
        "theme_description": theme["description"],
        "supporting_item_ids": theme_item_ids,
        "item_count": len(theme_item_ids),
        "prevalence_pct": round(theme["prevalence"] * 100, 2),
        "sentiment_distribution": theme_sent,
        "emotion_distribution": theme_emo,
        "net_sentiment_score": round(theme_nss, 4),
        "representative_quotes": quotes,
        "platforms_present": platforms,
        "is_multi_source": len(platforms) >= 2,
        "is_contested": False,  # Would need per-platform sentiment comparison
    })

# Assemble full AnalysisResults
analysis_results = {
    "sentiment_results": sentiment_results,
    "themes": themes_output,
    "overall_sentiment": overall_sentiment,
    "net_sentiment_score": round(nss, 4),
    "emotion_distribution": emotion_dist,
    "aspect_sentiment_summary": aspect_summary,
    "total_items_analyzed": len(item_themes_map),
    "analysis_model": "claude-code-in-context",
    "analysis_prompts": {
        "method": "in-context analysis by Claude Code session",
        "sentiment": "Keyword-pattern + contextual classification with Plutchik emotions and ABSA",
        "themes": "Two-pass: discovery from 300-item stratified sample + full-corpus keyword mapping + narrative review",
    },
}

# Write
output_path = RUN_DIR / "analysis" / "results.json"
output_path.write_text(
    json.dumps(analysis_results, indent=2, default=str, ensure_ascii=False),
    encoding="utf-8",
)

print(f"Written analysis/results.json")
print(f"  Total items analyzed: {analysis_results['total_items_analyzed']}")
print(f"  Overall sentiment: {overall_sentiment}")
print(f"  NSS: {nss:.4f} ({nss*100:+.1f}%)")
print(f"  Themes: {len(themes_output)}")
print(f"  Emotions: {emotion_dist}")
print(f"  Aspects: {list(aspect_summary.keys())}")
