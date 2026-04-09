"""Side-by-side comparison of Approach A (Dual-Layer) vs Approach B (Weighted).

Loads results from both approaches and generates a comparison table.
Run this AFTER running both approach scripts.

Usage: py -3 experiments/silent_majority/comparison.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

EXPERIMENT_DIR = Path(__file__).parent
DUAL_LAYER_PATH = EXPERIMENT_DIR / "outputs" / "dual_layer" / "dual_layer_results.json"
WEIGHTED_PATH = EXPERIMENT_DIR / "outputs" / "weighted" / "weighted_results.json"


def main():
    if not DUAL_LAYER_PATH.exists():
        print("ERROR: Run approach_a_dual_layer.py first")
        return
    if not WEIGHTED_PATH.exists():
        print("ERROR: Run approach_b_weighted.py first")
        return

    dl = json.loads(DUAL_LAYER_PATH.read_text(encoding="utf-8"))
    wt = json.loads(WEIGHTED_PATH.read_text(encoding="utf-8"))

    print("=" * 120)
    print("SILENT MAJORITY EXPERIMENT: SIDE-BY-SIDE COMPARISON")
    print("=" * 120)

    # Corpus overview
    print(f"\n## Corpus Split (Approach A)")
    print(f"  Primary layer (above threshold): {dl['primary_layer_size']:,} items ({dl['primary_layer_size']/dl['corpus_size']*100:.1f}%)")
    print(f"  Silent majority (below threshold): {dl['silent_layer_size']:,} items ({dl['silent_layer_size']/dl['corpus_size']*100:.1f}%)")
    print(f"\n## Weight Distribution (Approach B)")
    print(f"  Items at floor weight: {wt['floor_weight_items']:,} ({wt['floor_weight_items']/wt['corpus_size']*100:.1f}%)")
    print(f"  Weight range: {wt['weight_range'][0]} to {wt['weight_range'][1]}")

    # Overall NSS comparison
    print(f"\n## Overall NSS")
    print(f"  {'Metric':<35} | {'Value':>10}")
    print(f"  {'-'*35}-+-{'-'*10}")
    print(f"  {'A: Primary layer NSS':<35} | {dl['overall_primary_nss']:>+9.1%}")
    print(f"  {'A: Silent majority NSS':<35} | {dl['overall_silent_nss']:>+9.1%}")
    print(f"  {'A: Delta':<35} | {dl['overall_delta']:>9.1%}")
    print(f"  {'B: Unweighted NSS (all items)':<35} | {wt['overall_unweighted_nss']:>+9.1%}")
    print(f"  {'B: Weighted NSS':<35} | {wt['overall_weighted_nss']:>+9.1%}")
    print(f"  {'B: Delta':<35} | {wt['overall_delta']:>9.1%}")

    # Per-theme comparison
    dl_themes = {t["theme_id"]: t for t in dl["themes"]}
    wt_themes = {t["theme_id"]: t for t in wt["themes"]}

    all_theme_ids = list(dict.fromkeys(
        [t["theme_id"] for t in dl["themes"]] + [t["theme_id"] for t in wt["themes"]]
    ))

    print(f"\n## Per-Theme Comparison")
    print(f"  {'Theme':<35} | {'A:Primary':>10} | {'A:Silent':>10} | {'A:Delta':>8} | {'B:Unwtd':>10} | {'B:Wtd':>10} | {'B:Delta':>8} | {'Diverges?':>9}")
    print(f"  {'-'*35}-+-{'-'*10}-+-{'-'*10}-+-{'-'*8}-+-{'-'*10}-+-{'-'*10}-+-{'-'*8}-+-{'-'*9}")

    for tid in all_theme_ids:
        d = dl_themes.get(tid, {})
        w = wt_themes.get(tid, {})
        label = (d.get("theme_label") or w.get("theme_label", tid))[:33]

        a_primary = d.get("primary_nss", 0)
        a_silent = d.get("silent_nss", 0)
        a_delta = d.get("delta", 0)
        b_unwtd = w.get("unweighted_nss", 0)
        b_wtd = w.get("weighted_nss", 0)
        b_delta = w.get("delta", 0)

        diverges = d.get("divergent", False)
        div_flag = "YES" if diverges else ""

        print(f"  {label:<35} | {a_primary:>+9.1%} | {a_silent:>+9.1%} | {a_delta:>6.1%} | {b_unwtd:>+9.1%} | {b_wtd:>+9.1%} | {b_delta:>6.1%} | {div_flag:>9}")

    # Summary
    print(f"\n## Summary")
    print(f"  Approach A divergent themes: {dl['divergent_theme_count']} of {len(dl['themes'])}")
    print(f"  Approach B avg rank change: {wt['avg_rank_change']:.1f} positions")

    # Recommendation
    a_overall_delta = dl["overall_delta"]
    b_overall_delta = wt["overall_delta"]

    print(f"\n## Key Finding")
    if a_overall_delta < 0.05:
        print(f"  The silent majority largely AGREES with the primary layer (overall delta: {a_overall_delta:.1%}).")
        print(f"  Engagement filtering does not significantly bias overall sentiment in this corpus.")
    elif a_overall_delta < 0.15:
        print(f"  The silent majority shows MODERATE divergence from the primary layer (overall delta: {a_overall_delta:.1%}).")
        print(f"  Some themes may be affected. Check per-theme divergences.")
    else:
        print(f"  The silent majority SIGNIFICANTLY DIVERGES from the primary layer (overall delta: {a_overall_delta:.1%}).")
        print(f"  Engagement filtering materially biases the analysis. Consider weighted or dual-layer approach.")

    if b_overall_delta < 0.05:
        print(f"  Weighting has MINIMAL impact on overall NSS (delta: {b_overall_delta:.1%}).")
    else:
        print(f"  Weighting CHANGES overall NSS by {b_overall_delta:.1%} - engagement correlates with sentiment direction.")

    # Save comparison
    comparison = {
        "overall": {
            "a_primary_nss": dl["overall_primary_nss"],
            "a_silent_nss": dl["overall_silent_nss"],
            "a_delta": a_overall_delta,
            "b_unweighted_nss": wt["overall_unweighted_nss"],
            "b_weighted_nss": wt["overall_weighted_nss"],
            "b_delta": b_overall_delta,
        },
        "a_divergent_themes": dl["divergent_theme_count"],
        "b_avg_rank_change": wt["avg_rank_change"],
    }
    out_path = EXPERIMENT_DIR / "outputs" / "comparison.json"
    out_path.write_text(json.dumps(comparison, indent=2), encoding="utf-8")
    print(f"\nComparison saved to {out_path}")


if __name__ == "__main__":
    main()
