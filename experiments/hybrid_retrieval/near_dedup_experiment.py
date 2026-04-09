"""Near-duplicate detection experiment using sentence embeddings.

Loads the weight loss medication study corpus, embeds all items,
identifies near-duplicate clusters at multiple similarity thresholds,
and reports how corpus composition would change.

Usage:
    py near_dedup_experiment.py
"""
import sys
import json
import time
from pathlib import Path
from collections import Counter, defaultdict

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from consumer_research.config import RUNS_DIR

# --- Config ---
RUN_ID = "20260407_173532_06e43d"  # Weight loss medication study
RUN_DIR = RUNS_DIR / RUN_ID
OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

THRESHOLDS = [0.80, 0.85, 0.90, 0.95]
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # 384-dim, fast, free, local


def load_corpus():
    """Load normalized corpus from the weight loss run."""
    corpus_path = RUN_DIR / "normalized" / "corpus.json"
    items = json.loads(corpus_path.read_text(encoding="utf-8"))
    print(f"Loaded {len(items)} items from {corpus_path.name}")
    return items


def get_engagement(item: dict) -> int:
    """Extract engagement score from an item."""
    meta = item.get("platform_metadata", {})
    return meta.get("score") or meta.get("like_count") or 0


def embed_corpus(items: list[dict], model: SentenceTransformer) -> np.ndarray:
    """Embed all item texts. Returns (n_items, embedding_dim) array."""
    texts = [item["content_text"] for item in items]
    print(f"Embedding {len(texts)} items with {EMBEDDING_MODEL}...")
    t0 = time.time()
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=64)
    elapsed = time.time() - t0
    print(f"Embedding complete: {elapsed:.1f}s, shape={embeddings.shape}")
    return embeddings


def find_clusters(sim_matrix: np.ndarray, threshold: float) -> list[list[int]]:
    """Find connected components of items with similarity >= threshold.

    Uses union-find for efficiency. Returns list of clusters (each a list of indices).
    Only returns clusters with 2+ items (actual duplicates).
    """
    n = sim_matrix.shape[0]
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    # Only check upper triangle (sim_matrix is symmetric)
    for i in range(n):
        for j in range(i + 1, n):
            if sim_matrix[i, j] >= threshold:
                union(i, j)

    # Group by root
    groups = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(i)

    # Only clusters with 2+ items
    clusters = [indices for indices in groups.values() if len(indices) >= 2]
    return clusters


def select_canonical(cluster_indices: list[int], items: list[dict]) -> int:
    """Select canonical item from a cluster: highest engagement, then longest text."""
    best = cluster_indices[0]
    best_eng = get_engagement(items[best])
    best_len = len(items[best]["content_text"])

    for idx in cluster_indices[1:]:
        eng = get_engagement(items[idx])
        tlen = len(items[idx]["content_text"])
        if eng > best_eng or (eng == best_eng and tlen > best_len):
            best = idx
            best_eng = eng
            best_len = tlen

    return best


def platform_distribution(items: list[dict]) -> dict[str, int]:
    """Count items by platform."""
    return dict(Counter(item.get("source_platform", "unknown") for item in items))


def content_type_distribution(items: list[dict]) -> dict[str, int]:
    """Count items by content type."""
    return dict(Counter(item.get("content_type", "unknown") for item in items))


def analyze_threshold(
    threshold: float,
    sim_matrix: np.ndarray,
    items: list[dict],
) -> dict:
    """Analyze near-duplicate clusters at a given threshold."""
    clusters = find_clusters(sim_matrix, threshold)

    # Flatten all clustered indices
    all_clustered = set()
    for c in clusters:
        all_clustered.update(c)

    # Select canonical items per cluster
    canonical_indices = set()
    removed_indices = set()
    for c in clusters:
        canon = select_canonical(c, items)
        canonical_indices.add(canon)
        for idx in c:
            if idx != canon:
                removed_indices.add(idx)

    # Build deduped index set: all items NOT in any cluster + canonical items
    unclustered = set(range(len(items))) - all_clustered
    deduped_indices = unclustered | canonical_indices

    # Stats
    n_original = len(items)
    n_deduped = len(deduped_indices)
    n_removed = len(removed_indices)

    # Platform shift
    platform_before = platform_distribution(items)
    platform_after = platform_distribution([items[i] for i in sorted(deduped_indices)])

    # Content type shift
    ctype_before = content_type_distribution(items)
    ctype_after = content_type_distribution([items[i] for i in sorted(deduped_indices)])

    # Removed items by platform
    removed_by_platform = platform_distribution([items[i] for i in removed_indices])

    # Build sample clusters for inspection (top 15 by size)
    cluster_details = []
    sorted_clusters = sorted(clusters, key=len, reverse=True)
    for c in sorted_clusters[:15]:
        canon = select_canonical(c, items)
        cluster_details.append({
            "size": len(c),
            "canonical_index": canon,
            "canonical_text": items[canon]["content_text"][:300],
            "canonical_platform": items[canon].get("source_platform", "unknown"),
            "canonical_engagement": get_engagement(items[canon]),
            "members": [
                {
                    "index": idx,
                    "text": items[idx]["content_text"][:300],
                    "platform": items[idx].get("source_platform", "unknown"),
                    "engagement": get_engagement(items[idx]),
                    "similarity_to_canonical": float(sim_matrix[idx, canon]),
                }
                for idx in c if idx != canon
            ],
        })

    return {
        "threshold": threshold,
        "n_clusters": len(clusters),
        "n_items_in_clusters": len(all_clustered),
        "n_removed": n_removed,
        "n_original": n_original,
        "n_deduped": n_deduped,
        "pct_removed": round(100 * n_removed / n_original, 2),
        "platform_before": platform_before,
        "platform_after": platform_after,
        "removed_by_platform": removed_by_platform,
        "content_type_before": ctype_before,
        "content_type_after": ctype_after,
        "largest_cluster_size": max(len(c) for c in clusters) if clusters else 0,
        "cluster_size_distribution": dict(Counter(len(c) for c in clusters)),
        "sample_clusters": cluster_details,
    }


def main():
    print("=" * 70)
    print("NEAR-DUPLICATE DETECTION EXPERIMENT")
    print(f"Run: {RUN_ID} (Weight Loss Medication Study)")
    print("=" * 70)

    # Load
    items = load_corpus()

    # Embed
    model = SentenceTransformer(EMBEDDING_MODEL)
    embeddings = embed_corpus(items, model)

    # Save embeddings for potential reuse
    np.save(OUTPUT_DIR / "embeddings.npy", embeddings)
    print(f"Saved embeddings to {OUTPUT_DIR / 'embeddings.npy'}")

    # Compute similarity matrix
    print("Computing cosine similarity matrix...")
    t0 = time.time()
    sim_matrix = cosine_similarity(embeddings)
    elapsed = time.time() - t0
    print(f"Similarity matrix computed: {elapsed:.1f}s, shape={sim_matrix.shape}")

    # Analyze at each threshold
    all_results = {}
    for threshold in THRESHOLDS:
        print(f"\n--- Threshold: {threshold} ---")
        result = analyze_threshold(threshold, sim_matrix, items)
        all_results[str(threshold)] = result

        print(f"  Clusters: {result['n_clusters']}")
        print(f"  Items in clusters: {result['n_items_in_clusters']}")
        print(f"  Would remove: {result['n_removed']} ({result['pct_removed']}%)")
        print(f"  Corpus: {result['n_original']} -> {result['n_deduped']}")
        print(f"  Largest cluster: {result['largest_cluster_size']} items")
        print(f"  Removed by platform: {result['removed_by_platform']}")

    # Write results
    (OUTPUT_DIR / "results_by_threshold.json").write_text(
        json.dumps(all_results, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Write sample clusters separately for easy inspection
    sample_clusters = {}
    for t in THRESHOLDS:
        sample_clusters[str(t)] = all_results[str(t)]["sample_clusters"]
    (OUTPUT_DIR / "sample_clusters.json").write_text(
        json.dumps(sample_clusters, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Summary comparison table
    comparison = []
    for t in THRESHOLDS:
        r = all_results[str(t)]
        comparison.append({
            "threshold": t,
            "clusters": r["n_clusters"],
            "items_removed": r["n_removed"],
            "pct_removed": r["pct_removed"],
            "corpus_after": r["n_deduped"],
            "largest_cluster": r["largest_cluster_size"],
        })
    (OUTPUT_DIR / "comparison_summary.json").write_text(
        json.dumps(comparison, indent=2), encoding="utf-8"
    )

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"{'Threshold':<12} {'Clusters':<10} {'Removed':<10} {'% Removed':<12} {'After':<10} {'Max Cluster':<12}")
    for c in comparison:
        print(f"{c['threshold']:<12} {c['clusters']:<10} {c['items_removed']:<10} {c['pct_removed']:<12} {c['corpus_after']:<10} {c['largest_cluster']:<12}")

    print(f"\nResults written to {OUTPUT_DIR}/")
    print("Inspect sample_clusters.json to validate cluster quality.")


if __name__ == "__main__":
    main()
