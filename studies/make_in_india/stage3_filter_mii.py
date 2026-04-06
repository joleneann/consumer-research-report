"""
Stage 3: In-context keyword-based relevance filtering for Make in India.
No API calls - uses keyword matching to separate signal from noise.
"""
import json, sys, re
from pathlib import Path
from collections import Counter

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

RUN_DIR = ROOT / "consumer_research" / "runs" / "make_in_india_20260401_202927_95b158"
print(f"Run directory: {RUN_DIR.name}")

corpus = json.loads((RUN_DIR / "normalized" / "corpus.json").read_text(encoding="utf-8"))
print(f"Loaded {len(corpus)} normalized items")

# ── Relevance keywords ──
# Tier 1: High-confidence keywords (direct MII reference)
TIER1_KEYWORDS = [
    'make in india', 'made in india', 'vocal for local', 'atmanirbhar',
    'swadeshi', 'मेक इन इंडिया', 'मेड इन इंडिया', 'आत्मनिर्भर',
    'pli scheme', 'production linked incentive',
    'boycott china', 'ban china', 'boycott bangladesh',
    'buy indian', 'indian brand', 'desi brand',
    'स्वदेशी', 'भारत में बना',
]

# Tier 2: Contextual keywords (need India/Indian mention nearby)
TIER2_KEYWORDS = [
    'manufactur', 'tariff', 'import duty', 'trade war', 'trade deficit',
    'fdi', 'foreign direct invest', 'export', 'industrial policy',
    'semiconductor', 'electronics', 'textile', 'pharma', 'defence',
    'automobile', 'ev ', 'electric vehicle',
    'startup', 'entrepreneur', 'd2c', 'direct to consumer',
    'quality', 'world class', 'global standard',
    'nationalism', 'patriotism', 'patriotic', 'national pride',
    'homegrown', 'local brand', 'support local', 'shop local',
]

# India context words (required for Tier 2)
INDIA_CONTEXT = [
    'india', 'indian', 'bharat', 'desi', 'swadeshi', 'modi',
    'भारत', 'इंडिया', 'देसी', 'हिंदुस्तान',
]

# Negative patterns (reject even if keywords match)
NOISE_PATTERNS = [
    r'^(lol|haha|nice|great|wow|omg|love|😂|❤|🔥|👍)',  # pure reactions
    r'^.{0,15}$',  # very short (under 15 chars)
]

relevant = []
rejected = []

for item in corpus:
    text = item.get('content_text', '').lower()

    # Skip very short content
    if len(text.strip()) < 20:
        rejected.append(item)
        continue

    # Skip noise patterns
    is_noise = False
    for pat in NOISE_PATTERNS:
        if re.match(pat, text.strip()):
            is_noise = True
            break
    if is_noise:
        rejected.append(item)
        continue

    # Tier 1: Direct match = relevant
    tier1_match = any(kw in text for kw in TIER1_KEYWORDS)
    if tier1_match:
        relevant.append(item)
        continue

    # Tier 2: Contextual keyword + India context
    has_india = any(ctx in text for ctx in INDIA_CONTEXT)
    if has_india:
        tier2_match = any(kw in text for kw in TIER2_KEYWORDS)
        if tier2_match:
            relevant.append(item)
            continue

    # Tier 3: Search query was directly relevant + content mentions India
    query = item.get('collection_query', '').lower()
    if query != 'unknown' and has_india:
        query_relevant = any(t in query for t in [
            'make in india', 'vocal for local', 'indian brand', 'desi brand',
            'supporting indian', 'nationalism', 'patriotism', 'buy indian',
            'imports', 'consumer perspective', 'pros and cons', 'ground reality',
            'success or failure',
        ])
        if query_relevant:
            relevant.append(item)
            continue

    rejected.append(item)

print(f"\nRelevance filter results:")
print(f"  Relevant: {len(relevant)} ({len(relevant)/len(corpus)*100:.1f}%)")
print(f"  Rejected: {len(rejected)} ({len(rejected)/len(corpus)*100:.1f}%)")

# Platform breakdown
plats = Counter(i['source_platform'] for i in relevant)
types = Counter(i['content_type'] for i in relevant)
print(f"\nRelevant by platform: {dict(plats)}")
print(f"Relevant by type: {dict(types)}")

# Save filtered corpus
filtered_dir = RUN_DIR / "filtered"
filtered_dir.mkdir(exist_ok=True)
(filtered_dir / "corpus.json").write_text(
    json.dumps(relevant, indent=None, default=str, ensure_ascii=False), encoding="utf-8"
)
(filtered_dir / "rejected.json").write_text(
    json.dumps(rejected, indent=None, default=str, ensure_ascii=False), encoding="utf-8"
)
print(f"\nSaved {len(relevant)} items to filtered/corpus.json")
print(f"Saved {len(rejected)} items to filtered/rejected.json")

# Sample relevant items for quality check
print("\nRelevant samples (15 random):")
import random
random.seed(42)
for item in random.sample(relevant, min(15, len(relevant))):
    print(f"  [{item['source_platform']}] {item['content_text'][:140]}")
