"""Approach B: Weighted Inclusion.

Includes ALL items regardless of engagement but weights each item by
log(1 + engagement). Zero-engagement items contribute at floor weight (0.1).
High-engagement items contribute proportionally more.

Usage: py -3 experiments/silent_majority/approach_b_weighted.py
"""
import json
import math
import sys
from pathlib import Path
from collections import Counter

# Add repo root to path for imports
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from shared import (
    load_run_data, compute_weighted_theme_sentiment,
    get_item_engagement, compute_theme_sentiment, EXPERIMENT_DIR,
)
from consumer_research.models.schemas import compute_nss

OUTPUT_DIR = EXPERIMENT_DIR / "outputs" / "weighted"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    print("=" * 60)
    print("APPROACH B: WEIGHTED INCLUSION")
    print("=" * 60)

    corpus, analysis, sentiment_map, config_data = load_run_data()
    corpus_map = {item.item_id: item for item in corpus}
    all_ids = set(corpus_map.keys())

    print(f"\nTotal corpus: {len(corpus)} items (ALL included, no threshold)")

    # Engagement weight distribution
    weights = []
    for item in corpus:
        eng = get_item_engagement(item)
        w = max(0.1, math.log(1 + eng))
        weights.append(w)

    print(f"Weight range: {min(weights):.2f} to {max(weights):.2f}")
    print(f"Median weight: {sorted(weights)[len(weights)//2]:.2f}")
    print(f"Items at floor weight (0.1): {sum(1 for w in weights if w <= 0.11)}")

    # Deduplicate themes
    seen_themes = {}
    for theme in analysis.themes:
        if theme.theme_id not in seen_themes:
            seen_themes[theme.theme_id] = theme
    unique_themes = list(seen_themes.values())

    # Per-theme comparison: unweighted vs weighted
    results = []
    print(f"\n{'Theme':<40} | {'Unweighted NSS':>14} | {'Weighted NSS':>14} | {'Delta':>8} | {'Rank Change':>11}")
    print("-" * 100)

    for theme in unique_themes:
        # Unweighted (original - all items, equal weight)
        u_count, u_dist, u_nss = compute_theme_sentiment(theme, all_ids, sentiment_map)

        # Weighted
        w_count, w_dist, w_nss, w_total = compute_weighted_theme_sentiment(
            theme, corpus_map, sentiment_map
        )

        delta = abs(u_nss - w_nss)
        label = theme.theme_label[:38]

        print(f"  {label:<38} | {u_nss:>+12.1%} (n={u_count:>4}) | {w_nss:>+12.1%}        | {delta:>6.1%} |")

        results.append({
            "theme_id": theme.theme_id,
            "theme_label": theme.theme_label,
            "unweighted_count": u_count,
            "unweighted_sentiment": u_dist,
            "unweighted_nss": round(u_nss, 4),
            "weighted_count": w_count,
            "weighted_sentiment": {k: round(v, 2) for k, v in w_dist.items()},
            "weighted_nss": round(w_nss, 4),
            "total_weight": round(w_total, 2),
            "delta": round(delta, 4),
        })

    # Rank comparison
    unweighted_ranked = sorted(results, key=lambda r: r["unweighted_nss"], reverse=True)
    weighted_ranked = sorted(results, key=lambda r: r["weighted_nss"], reverse=True)

    u_ranks = {r["theme_id"]: i + 1 for i, r in enumerate(unweighted_ranked)}
    w_ranks = {r["theme_id"]: i + 1 for i, r in enumerate(weighted_ranked)}

    print(f"\n\n{'Theme':<40} | {'Unweighted Rank':>15} | {'Weighted Rank':>14} | {'Change':>8}")
    print("-" * 85)
    rank_changes = []
    for r in results:
        tid = r["theme_id"]
        u_rank = u_ranks[tid]
        w_rank = w_ranks[tid]
        change = u_rank - w_rank  # positive = moved up with weighting
        rank_changes.append(abs(change))
        arrow = ""
        if change > 0:
            arrow = f"+{change}"
        elif change < 0:
            arrow = str(change)

        label = r["theme_label"][:38]
        print(f"  {label:<38} | {u_rank:>15} | {w_rank:>14} | {arrow:>8}")

    # Overall weighted NSS
    total_w_pos = 0.0
    total_w_neg = 0.0
    total_w_all = 0.0
    for item in corpus:
        iid = item.item_id
        if iid not in sentiment_map:
            continue
        eng = get_item_engagement(item)
        weight = max(0.1, math.log(1 + eng))
        s = sentiment_map[iid].sentiment.value
        if s == "positive":
            total_w_pos += weight
        elif s == "negative":
            total_w_neg += weight
        total_w_all += weight

    weighted_overall_nss = (total_w_pos - total_w_neg) / total_w_all if total_w_all > 0 else 0

    # Unweighted overall (all items, equal weight)
    overall_dist = {"positive": 0, "negative": 0, "neutral": 0, "mixed": 0}
    for iid in all_ids:
        if iid in sentiment_map:
            s = sentiment_map[iid].sentiment.value
            overall_dist[s] += 1
    unweighted_overall_nss = compute_nss(overall_dist)

    print(f"\nOverall corpus NSS:")
    print(f"  Unweighted (all items, equal): {unweighted_overall_nss:+.1%}")
    print(f"  Weighted (log engagement):     {weighted_overall_nss:+.1%}")
    print(f"  Delta:                         {abs(unweighted_overall_nss - weighted_overall_nss):.1%}")
    print(f"\nAverage rank change per theme: {sum(rank_changes)/len(rank_changes):.1f} positions")

    # Save results
    output = {
        "approach": "weighted_inclusion",
        "corpus_size": len(corpus),
        "weight_function": "max(0.1, log(1 + engagement))",
        "floor_weight_items": sum(1 for w in weights if w <= 0.11),
        "weight_range": [round(min(weights), 2), round(max(weights), 2)],
        "overall_unweighted_nss": round(unweighted_overall_nss, 4),
        "overall_weighted_nss": round(weighted_overall_nss, 4),
        "overall_delta": round(abs(unweighted_overall_nss - weighted_overall_nss), 4),
        "avg_rank_change": round(sum(rank_changes) / len(rank_changes), 2),
        "themes": results,
    }

    output_path = OUTPUT_DIR / "weighted_results.json"
    output_path.write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
