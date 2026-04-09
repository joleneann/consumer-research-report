"""Approach C: Equal Inclusion.

Includes ALL items regardless of engagement, counts every item equally.
No weighting, no threshold. The simplest approach.

Usage: py -3 experiments/silent_majority/approach_c_equal.py
"""
import json
import sys
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from shared import (
    load_run_data, compute_theme_sentiment, EXPERIMENT_DIR,
)
from consumer_research.models.schemas import compute_nss

OUTPUT_DIR = EXPERIMENT_DIR / "outputs" / "equal"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    print("=" * 60)
    print("APPROACH C: EQUAL INCLUSION (no threshold, no weighting)")
    print("=" * 60)

    corpus, analysis, sentiment_map, config_data = load_run_data()
    all_ids = {item.item_id for item in corpus}

    print(f"\nTotal corpus: {len(corpus)} items (ALL included, all equal)")

    # Deduplicate themes
    seen_themes = {}
    for theme in analysis.themes:
        if theme.theme_id not in seen_themes:
            seen_themes[theme.theme_id] = theme
    unique_themes = list(seen_themes.values())

    # Load Approach A and B results for comparison
    dl_path = EXPERIMENT_DIR / "outputs" / "dual_layer" / "dual_layer_results.json"
    wt_path = EXPERIMENT_DIR / "outputs" / "weighted" / "weighted_results.json"
    dl = json.loads(dl_path.read_text(encoding="utf-8")) if dl_path.exists() else None
    wt = json.loads(wt_path.read_text(encoding="utf-8")) if wt_path.exists() else None

    dl_themes = {t["theme_id"]: t for t in dl["themes"]} if dl else {}
    wt_themes = {t["theme_id"]: t for t in wt["themes"]} if wt else {}

    # Per-theme analysis
    results = []
    print(f"\n{'Theme':<35} | {'C:Equal NSS':>12} | {'A:Primary':>10} | {'B:Weighted':>10} | {'C vs A':>8} | {'C vs B':>8}")
    print("-" * 100)

    for theme in unique_themes:
        c_count, c_dist, c_nss = compute_theme_sentiment(theme, all_ids, sentiment_map)

        a_primary_nss = dl_themes.get(theme.theme_id, {}).get("primary_nss", 0)
        b_weighted_nss = wt_themes.get(theme.theme_id, {}).get("weighted_nss", 0)

        delta_vs_a = abs(c_nss - a_primary_nss)
        delta_vs_b = abs(c_nss - b_weighted_nss)

        label = theme.theme_label[:33]
        print(f"  {label:<33} | {c_nss:>+10.1%} (n={c_count:>4}) | {a_primary_nss:>+9.1%} | {b_weighted_nss:>+9.1%} | {delta_vs_a:>6.1%} | {delta_vs_b:>6.1%}")

        results.append({
            "theme_id": theme.theme_id,
            "theme_label": theme.theme_label,
            "equal_count": c_count,
            "equal_sentiment": c_dist,
            "equal_nss": round(c_nss, 4),
            "delta_vs_primary": round(delta_vs_a, 4),
            "delta_vs_weighted": round(delta_vs_b, 4),
        })

    # Overall
    overall_dist = {"positive": 0, "negative": 0, "neutral": 0, "mixed": 0}
    for iid in all_ids:
        if iid in sentiment_map:
            s = sentiment_map[iid].sentiment.value
            overall_dist[s] += 1
    c_overall_nss = compute_nss(overall_dist)

    a_overall = dl["overall_primary_nss"] if dl else 0
    b_overall = wt["overall_weighted_nss"] if wt else 0

    print(f"\n{'Overall':<35} | {c_overall_nss:>+10.1%} (n={sum(overall_dist.values()):>4}) | {a_overall:>+9.1%} | {b_overall:>+9.1%} | {abs(c_overall_nss - a_overall):>6.1%} | {abs(c_overall_nss - b_overall):>6.1%}")

    # Rank comparison across all three
    c_ranked = sorted(results, key=lambda r: r["equal_nss"], reverse=True)
    c_ranks = {r["theme_id"]: i + 1 for i, r in enumerate(c_ranked)}

    # Get A ranks (by primary NSS)
    if dl:
        a_sorted = sorted(dl["themes"], key=lambda t: t["primary_nss"], reverse=True)
        a_ranks = {t["theme_id"]: i + 1 for i, t in enumerate(a_sorted)}
    else:
        a_ranks = {}

    # Get B ranks (by weighted NSS)
    if wt:
        b_sorted = sorted(wt["themes"], key=lambda t: t["weighted_nss"], reverse=True)
        b_ranks = {t["theme_id"]: i + 1 for i, t in enumerate(b_sorted)}
    else:
        b_ranks = {}

    print(f"\n\n{'Theme':<35} | {'A:Primary':>10} | {'B:Weighted':>10} | {'C:Equal':>10}")
    print("-" * 75)
    for r in results:
        tid = r["theme_id"]
        label = r["theme_label"][:33]
        a_r = a_ranks.get(tid, "-")
        b_r = b_ranks.get(tid, "-")
        c_r = c_ranks.get(tid, "-")
        print(f"  {label:<33} | {str(a_r):>10} | {str(b_r):>10} | {str(c_r):>10}")

    # Summary
    print(f"\n## Summary")
    print(f"  C (Equal) overall NSS: {c_overall_nss:+.1%}")
    print(f"  A (Primary layer) overall NSS: {a_overall:+.1%}")
    print(f"  B (Weighted) overall NSS: {b_overall:+.1%}")
    print(f"  A (Silent majority) overall NSS: {dl['overall_silent_nss']:+.1%}" if dl else "")
    print(f"\n  C sits between A:Primary ({a_overall:+.1%}) and A:Silent ({dl['overall_silent_nss']:+.1%})" if dl else "")
    print(f"  C is {abs(c_overall_nss - b_overall):.1%} lower than B:Weighted - weighting amplifies high-engagement positivity")

    # Save
    output = {
        "approach": "equal_inclusion",
        "corpus_size": len(corpus),
        "overall_equal_nss": round(c_overall_nss, 4),
        "overall_primary_nss": round(a_overall, 4) if dl else None,
        "overall_weighted_nss": round(b_overall, 4) if wt else None,
        "overall_silent_nss": round(dl["overall_silent_nss"], 4) if dl else None,
        "themes": results,
    }
    output_path = OUTPUT_DIR / "equal_results.json"
    output_path.write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
