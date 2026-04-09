"""Minimum text length filter experiment.

Analyzes what gets removed at different character thresholds,
and whether it's noise or signal.

Usage:
    py min_length_experiment.py
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
import json
import re
from pathlib import Path
from collections import Counter, defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from consumer_research.config import RUNS_DIR

# --- Config ---
RUN_ID = "20260407_173532_06e43d"  # Weight loss medication study
RUN_DIR = RUNS_DIR / RUN_ID
OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

THRESHOLDS = [5, 10, 15, 20, 30, 50]

# Patterns that indicate garbage content regardless of length
GARBAGE_PATTERNS = [
    re.compile(r"^\[deleted\]$", re.IGNORECASE),
    re.compile(r"^\[removed\]$", re.IGNORECASE),
]


def load_corpus():
    corpus_path = RUN_DIR / "normalized" / "corpus.json"
    items = json.loads(corpus_path.read_text(encoding="utf-8"))
    print(f"Loaded {len(items)} items from {corpus_path.name}")
    return items


def text_length(text: str) -> int:
    """Character count of the actual text."""
    return len(text.strip())


def alpha_ratio(text: str) -> float:
    """Fraction of characters that are alphanumeric (letters/digits)."""
    if not text.strip():
        return 0.0
    alpha = sum(1 for c in text if c.isalnum())
    return alpha / len(text.strip())


def is_garbage(text: str) -> bool:
    """Check if text matches known garbage patterns."""
    t = text.strip()
    return any(p.match(t) for p in GARBAGE_PATTERNS)


def is_emoji_only(text: str) -> bool:
    """Check if text is essentially emoji/symbols only (alpha ratio < 0.1)."""
    t = text.strip()
    if not t:
        return True
    return alpha_ratio(t) < 0.10


def classify_item(item: dict) -> str:
    """Classify an item into a quality category."""
    text = item.get("content_text", "").strip()
    if not text:
        return "empty"
    if is_garbage(text):
        return "deleted/removed"
    if is_emoji_only(text):
        return "emoji_only"
    if text_length(text) < 10:
        return "ultra_short"
    if text_length(text) < 20:
        return "very_short"
    if text_length(text) < 50:
        return "short"
    return "substantive"


def analyze_threshold(items: list[dict], min_chars: int) -> dict:
    """Analyze what a minimum character threshold would remove."""
    kept = []
    removed = []

    for item in items:
        text = item.get("content_text", "").strip()
        if text_length(text) < min_chars or is_garbage(text):
            removed.append(item)
        else:
            kept.append(item)

    # Classify removed items
    removed_categories = Counter(classify_item(i) for i in removed)

    # Platform breakdown of removed
    removed_by_platform = Counter(i.get("source_platform", "unknown") for i in removed)
    kept_by_platform = Counter(i.get("source_platform", "unknown") for i in kept)

    # Content type breakdown
    removed_by_type = Counter(i.get("content_type", "unknown") for i in removed)

    # Sample removed items (first 30, grouped by category)
    samples_by_category = defaultdict(list)
    for item in removed:
        cat = classify_item(item)
        if len(samples_by_category[cat]) < 10:
            samples_by_category[cat].append({
                "text": item["content_text"][:200],
                "platform": item.get("source_platform", "unknown"),
                "content_type": item.get("content_type", "unknown"),
                "engagement": (item.get("platform_metadata", {}).get("score")
                               or item.get("platform_metadata", {}).get("like_count")
                               or 0),
                "length": text_length(item["content_text"]),
            })

    # Check: are any removed items potentially valuable?
    # (high engagement items that would be lost)
    high_engagement_removed = []
    for item in removed:
        eng = (item.get("platform_metadata", {}).get("score")
               or item.get("platform_metadata", {}).get("like_count")
               or 0)
        if eng >= 10:
            high_engagement_removed.append({
                "text": item["content_text"][:200],
                "platform": item.get("source_platform", "unknown"),
                "engagement": eng,
                "length": text_length(item["content_text"]),
                "category": classify_item(item),
            })

    return {
        "min_chars": min_chars,
        "original_count": len(items),
        "kept_count": len(kept),
        "removed_count": len(removed),
        "pct_removed": round(100 * len(removed) / len(items), 2),
        "removed_categories": dict(removed_categories),
        "removed_by_platform": dict(removed_by_platform),
        "kept_by_platform": dict(kept_by_platform),
        "removed_by_content_type": dict(removed_by_type),
        "high_engagement_removed": high_engagement_removed,
        "samples_by_category": {k: v for k, v in samples_by_category.items()},
    }


def corpus_quality_profile(items: list[dict]) -> dict:
    """Full quality profile of the corpus before any filtering."""
    categories = Counter(classify_item(i) for i in items)
    lengths = [text_length(i["content_text"]) for i in items]

    # Length distribution
    brackets = [0, 5, 10, 20, 50, 100, 200, 500, 1000, float("inf")]
    length_dist = {}
    for lo, hi in zip(brackets, brackets[1:]):
        label = f"{lo}-{int(hi) if hi != float('inf') else '+'}"
        count = sum(1 for l in lengths if lo <= l < hi)
        length_dist[label] = count

    return {
        "total_items": len(items),
        "quality_categories": dict(categories),
        "length_distribution": length_dist,
        "mean_length": round(sum(lengths) / len(lengths), 1),
        "median_length": sorted(lengths)[len(lengths) // 2],
        "min_length": min(lengths),
        "max_length": max(lengths),
        "items_under_10_chars": sum(1 for l in lengths if l < 10),
        "items_under_20_chars": sum(1 for l in lengths if l < 20),
        "items_under_50_chars": sum(1 for l in lengths if l < 50),
    }


def main():
    print("=" * 70)
    print("MINIMUM TEXT LENGTH FILTER EXPERIMENT")
    print(f"Run: {RUN_ID} (Weight Loss Medication Study)")
    print("=" * 70)

    items = load_corpus()

    # Full quality profile
    print("\n--- CORPUS QUALITY PROFILE ---")
    profile = corpus_quality_profile(items)
    print(f"  Total items: {profile['total_items']}")
    print(f"  Mean length: {profile['mean_length']} chars")
    print(f"  Median length: {profile['median_length']} chars")
    print(f"\n  Quality categories:")
    for cat, count in sorted(profile["quality_categories"].items(), key=lambda x: -x[1]):
        pct = round(100 * count / profile["total_items"], 1)
        print(f"    {cat:<20} {count:>5} ({pct}%)")
    print(f"\n  Length distribution:")
    for bracket, count in profile["length_distribution"].items():
        pct = round(100 * count / profile["total_items"], 1)
        bar = "#" * int(pct)
        print(f"    {bracket:<10} {count:>5} ({pct:>5.1f}%) {bar}")

    (OUTPUT_DIR / "corpus_quality_profile.json").write_text(
        json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Analyze each threshold
    print("\n--- THRESHOLD ANALYSIS ---")
    all_results = {}
    for threshold in THRESHOLDS:
        result = analyze_threshold(items, threshold)
        all_results[str(threshold)] = result

        print(f"\n  Min {threshold} chars (+ garbage removal):")
        print(f"    Removed: {result['removed_count']} ({result['pct_removed']}%)")
        print(f"    Corpus: {result['original_count']} -> {result['kept_count']}")
        print(f"    Categories removed: {result['removed_categories']}")
        print(f"    By platform: {result['removed_by_platform']}")
        if result["high_engagement_removed"]:
            print(f"    WARNING: {len(result['high_engagement_removed'])} high-engagement items removed:")
            for he in result["high_engagement_removed"][:5]:
                print(f"      [{he['platform']}] eng={he['engagement']} len={he['length']} cat={he['category']}: {he['text'][:80]}")

    # Write all results
    (OUTPUT_DIR / "min_length_results.json").write_text(
        json.dumps(all_results, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Summary table
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"{'Threshold':<12} {'Removed':<10} {'% Removed':<12} {'After':<10} {'High-Eng Lost':<15}")
    for t in THRESHOLDS:
        r = all_results[str(t)]
        print(f"{t:<12} {r['removed_count']:<10} {r['pct_removed']:<12} {r['kept_count']:<10} {len(r['high_engagement_removed']):<15}")

    # Write summary
    summary = [
        {
            "threshold": t,
            "removed": all_results[str(t)]["removed_count"],
            "pct_removed": all_results[str(t)]["pct_removed"],
            "kept": all_results[str(t)]["kept_count"],
            "high_engagement_lost": len(all_results[str(t)]["high_engagement_removed"]),
        }
        for t in THRESHOLDS
    ]
    (OUTPUT_DIR / "min_length_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    print(f"\nResults written to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
