"""Approach A: Dual-Layer Corpus.

Splits the corpus into a primary layer (above engagement threshold) and a
silent majority layer (below threshold). Analyses both independently using
the same themes. Generates a comparison showing where the silent majority
agrees or diverges from the primary layer.

Usage: py -3 experiments/silent_majority/approach_a_dual_layer.py
"""
import json
import random
import sys
from pathlib import Path
from collections import Counter

# Add repo root to path for imports
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from shared import (
    load_run_data, split_corpus, compute_theme_sentiment,
    get_item_engagement, EXPERIMENT_DIR,
)
from consumer_research.models.schemas import compute_nss

OUTPUT_DIR = EXPERIMENT_DIR / "outputs" / "dual_layer"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    print("=" * 60)
    print("APPROACH A: DUAL-LAYER CORPUS")
    print("=" * 60)

    corpus, analysis, sentiment_map, config_data = load_run_data()
    print(f"\nTotal corpus: {len(corpus)} items")
    print(f"Themes: {len(analysis.themes)}")

    # Split corpus
    above, below = split_corpus(corpus)
    print(f"\nPrimary layer (above threshold): {len(above)} items ({len(above)/len(corpus)*100:.1f}%)")
    print(f"Silent majority (below threshold): {len(below)} items ({len(below)/len(corpus)*100:.1f}%)")

    # Platform breakdown
    above_plats = Counter(i.source_platform.value for i in above)
    below_plats = Counter(i.source_platform.value for i in below)
    print(f"\nPrimary layer by platform: {dict(above_plats)}")
    print(f"Silent majority by platform: {dict(below_plats)}")

    above_ids = {i.item_id for i in above}
    below_ids = {i.item_id for i in below}

    # Compute sentiment for each layer, per theme
    results = []
    print(f"\n{'Theme':<40} | {'Primary NSS':>12} | {'Silent NSS':>12} | {'Delta':>8} | {'Divergent?':>10}")
    print("-" * 95)

    # Deduplicate themes by theme_id
    seen_themes = {}
    for theme in analysis.themes:
        if theme.theme_id not in seen_themes:
            seen_themes[theme.theme_id] = theme
    unique_themes = list(seen_themes.values())

    for theme in unique_themes:
        p_count, p_dist, p_nss = compute_theme_sentiment(theme, above_ids, sentiment_map)
        s_count, s_dist, s_nss = compute_theme_sentiment(theme, below_ids, sentiment_map)

        delta = abs(p_nss - s_nss)
        divergent = delta > 0.15 and s_count >= 5  # Need minimum sample in silent layer

        label = theme.theme_label[:38]
        div_flag = "YES" if divergent else ""

        print(f"  {label:<38} | {p_nss:>+10.1%} (n={p_count:>4}) | {s_nss:>+10.1%} (n={s_count:>4}) | {delta:>6.1%} | {div_flag:>10}")

        results.append({
            "theme_id": theme.theme_id,
            "theme_label": theme.theme_label,
            "primary_count": p_count,
            "primary_sentiment": p_dist,
            "primary_nss": round(p_nss, 4),
            "silent_count": s_count,
            "silent_sentiment": s_dist,
            "silent_nss": round(s_nss, 4),
            "delta": round(delta, 4),
            "divergent": divergent,
        })

    # Overall corpus sentiment by layer
    above_overall = {"positive": 0, "negative": 0, "neutral": 0, "mixed": 0}
    below_overall = {"positive": 0, "negative": 0, "neutral": 0, "mixed": 0}
    for iid in above_ids:
        if iid in sentiment_map:
            s = sentiment_map[iid].sentiment.value
            above_overall[s] += 1
    for iid in below_ids:
        if iid in sentiment_map:
            s = sentiment_map[iid].sentiment.value
            below_overall[s] += 1

    above_nss = compute_nss(above_overall)
    below_nss = compute_nss(below_overall)

    print(f"\n{'Overall corpus':<40} | {above_nss:>+10.1%} (n={sum(above_overall.values()):>4}) | {below_nss:>+10.1%} (n={sum(below_overall.values()):>4}) | {abs(above_nss - below_nss):>6.1%}")

    divergent_count = sum(1 for r in results if r["divergent"])
    print(f"\nDivergent themes (delta > 15%, silent n >= 5): {divergent_count} of {len(results)}")

    # Save results
    output = {
        "approach": "dual_layer",
        "corpus_size": len(corpus),
        "primary_layer_size": len(above),
        "silent_layer_size": len(below),
        "primary_by_platform": dict(above_plats),
        "silent_by_platform": dict(below_plats),
        "overall_primary_nss": round(above_nss, 4),
        "overall_silent_nss": round(below_nss, 4),
        "overall_delta": round(abs(above_nss - below_nss), 4),
        "themes": results,
        "divergent_theme_count": divergent_count,
    }

    output_path = OUTPUT_DIR / "dual_layer_results.json"
    output_path.write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
