"""Language and geographic relevance audit.

Detects:
1. Non-English/Hindi languages via Unicode script analysis
2. Geographic noise via keyword heuristics (non-India market content)

Usage:
    py language_geo_audit.py
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
import json
import re
import unicodedata
from pathlib import Path
from collections import Counter, defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from consumer_research.config import RUNS_DIR

# ── Runs to audit ───────────────────────────────────────────────────────────
RUNS = {
    "Hair Colour": "20260407_143544_98a8c6",
    "Weight Loss": "20260407_173532_06e43d",
}

# ── Unicode script detection ────────────────────────────────────────────────
# Map Unicode script names to language labels
SCRIPT_TO_LANG = {
    "LATIN": "latin",
    "DEVANAGARI": "hindi",
    "TAMIL": "tamil",
    "TELUGU": "telugu",
    "BENGALI": "bengali",
    "KANNADA": "kannada",
    "MALAYALAM": "malayalam",
    "GUJARATI": "gujarati",
    "GURMUKHI": "punjabi",
    "ODIA": "odia",
    "HANGUL": "korean",
    "CJK": "chinese",
    "HIRAGANA": "japanese",
    "KATAKANA": "japanese",
    "ARABIC": "arabic",
    "THAI": "thai",
    "CYRILLIC": "russian",
}


def detect_scripts(text: str) -> dict[str, int]:
    """Count characters by Unicode script."""
    scripts: dict[str, int] = Counter()
    for ch in text:
        if ch.isspace() or ch in '.,!?;:()[]{}"\'-/@#$%^&*+=<>~`|\\':
            continue
        try:
            name = unicodedata.name(ch, "")
        except ValueError:
            continue
        if not name:
            # Emoji or unknown
            scripts["emoji/symbol"] += 1
            continue
        matched = False
        for script_prefix, lang in SCRIPT_TO_LANG.items():
            if script_prefix in name:
                scripts[lang] += 1
                matched = True
                break
        if not matched:
            if ch.isalpha():
                scripts["latin"] += 1  # Default for unmatched alphabetic
            else:
                scripts["emoji/symbol"] += 1
    return dict(scripts)


def primary_language(text: str) -> str:
    """Detect the primary language/script of a text."""
    scripts = detect_scripts(text)
    if not scripts:
        return "empty"
    # Remove emoji/symbol from consideration for primary language
    lang_scripts = {k: v for k, v in scripts.items() if k != "emoji/symbol"}
    if not lang_scripts:
        return "emoji_only"
    return max(lang_scripts, key=lang_scripts.get)


# ── Geographic relevance heuristics ─────────────────────────────────────────
# Signals that content is likely NOT from the Indian market
NON_INDIA_SIGNALS = [
    # Hair-specific non-India signals
    (re.compile(r'\bnatural blonde\b', re.I), "blonde_hair"),
    (re.compile(r'\bmy blonde\b', re.I), "blonde_hair"),
    (re.compile(r'\bborn blonde\b', re.I), "blonde_hair"),
    (re.compile(r'\blight blonde\b', re.I), "blonde_hair"),
    (re.compile(r'\bdirty blonde\b', re.I), "blonde_hair"),
    (re.compile(r'\bstrawberry blonde\b', re.I), "blonde_hair"),
    (re.compile(r'\bplatinum blonde\b', re.I), "blonde_hair"),
    # US/UK/Western market references
    (re.compile(r'\bWalgreens\b', re.I), "us_retailer"),
    (re.compile(r'\bCVS\b'), "us_retailer"),
    (re.compile(r'\bTarget\b'), "us_retailer"),
    (re.compile(r'\bWalmart\b', re.I), "us_retailer"),
    (re.compile(r'\bBoots\b'), "uk_retailer"),
    (re.compile(r'\bSuperdrug\b', re.I), "uk_retailer"),
    (re.compile(r'\bSally Beauty\b', re.I), "us_retailer"),
    (re.compile(r'\bUlta\b'), "us_retailer"),
    (re.compile(r'\bSephora\b', re.I), "western_retailer"),
    # Currency
    (re.compile(r'\$\d+'), "usd_price"),
    (re.compile(r'\b\d+\s*dollars?\b', re.I), "usd_price"),
    (re.compile(r'£\d+'), "gbp_price"),
    (re.compile(r'\b\d+\s*pounds?\b', re.I), "gbp_price"),
    (re.compile(r'€\d+'), "eur_price"),
    # US-specific health/pharma
    (re.compile(r'\bFDA approved\b', re.I), "us_regulatory"),
    (re.compile(r'\binsurance covers?\b', re.I), "us_healthcare"),
    (re.compile(r'\bmy insurance\b', re.I), "us_healthcare"),
    (re.compile(r'\bco-?pay\b', re.I), "us_healthcare"),
    (re.compile(r'\bdeductible\b', re.I), "us_healthcare"),
    (re.compile(r'\bout of pocket\b', re.I), "us_healthcare"),
    (re.compile(r'\bGoodRx\b', re.I), "us_healthcare"),
    (re.compile(r'\bMedicare\b', re.I), "us_healthcare"),
    (re.compile(r'\bMedicaid\b', re.I), "us_healthcare"),
]

# India-positive signals (if present, item is likely India-relevant even with other signals)
INDIA_SIGNALS = [
    re.compile(r'\b(?:Rs\.?|₹|INR)\s*\d+', re.I),
    re.compile(r'\b(?:India|Indian|Mumbai|Delhi|Bangalore|Bengaluru|Chennai|Kolkata|Hyderabad|Pune)\b', re.I),
    re.compile(r'\b(?:Ayurved|ayurvedic|patanjali|meesho|flipkart|nykaa|baba ramdev)\b', re.I),
    re.compile(r'\b(?:crore|lakh|bhai|yaar|behen|ji|arre|accha)\b', re.I),
]


def check_geographic_relevance(text: str) -> dict:
    """Check if text has non-India market signals."""
    non_india_hits = []
    for pattern, label in NON_INDIA_SIGNALS:
        if pattern.search(text):
            non_india_hits.append(label)

    india_hits = []
    for pattern in INDIA_SIGNALS:
        if pattern.search(text):
            india_hits.append(pattern.pattern[:30])

    return {
        "non_india_signals": non_india_hits,
        "india_signals": india_hits,
        "likely_non_india": len(non_india_hits) > 0 and len(india_hits) == 0,
    }


# ── Main ────────────────────────────────────────────────────────────────────
OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

all_results = {}

for study_name, run_id in RUNS.items():
    print(f"\n{'='*70}")
    print(f"AUDIT: {study_name} (run {run_id})")
    print(f"{'='*70}")

    run_dir = RUNS_DIR / run_id
    corpus_path = run_dir / "filtered" / "corpus.json"
    if not corpus_path.exists():
        corpus_path = run_dir / "normalized" / "corpus.json"
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    print(f"Corpus: {len(corpus)} items (from {corpus_path.parent.name}/)")

    # ── Language audit ──────────────────────────────────────────────────────
    lang_counts = Counter()
    lang_samples = defaultdict(list)

    for item in corpus:
        text = item.get("content_text", "")
        lang = primary_language(text)
        lang_counts[lang] += 1
        if len(lang_samples[lang]) < 5:
            lang_samples[lang].append({
                "text": text[:200],
                "platform": item.get("source_platform", ""),
                "item_id": item.get("item_id", ""),
            })

    print(f"\n  LANGUAGE DISTRIBUTION:")
    for lang, count in lang_counts.most_common():
        pct = 100 * count / len(corpus)
        print(f"    {lang:<20} {count:>5} ({pct:>5.1f}%)")

    # ── Geographic audit ────────────────────────────────────────────────────
    non_india_items = []
    non_india_signal_counts = Counter()

    for item in corpus:
        text = item.get("content_text", "")
        geo = check_geographic_relevance(text)
        if geo["likely_non_india"]:
            non_india_items.append({
                "text": text[:300],
                "platform": item.get("source_platform", ""),
                "item_id": item.get("item_id", ""),
                "signals": geo["non_india_signals"],
            })
            for sig in geo["non_india_signals"]:
                non_india_signal_counts[sig] += 1

    print(f"\n  GEOGRAPHIC RELEVANCE:")
    print(f"    Likely non-India items: {len(non_india_items)} ({100*len(non_india_items)/len(corpus):.1f}%)")
    if non_india_signal_counts:
        print(f"    Signal breakdown:")
        for sig, count in non_india_signal_counts.most_common():
            print(f"      {sig:<25} {count:>5}")

    # Sample non-India items
    if non_india_items:
        print(f"\n    Sample non-India items (first 10):")
        for ni in non_india_items[:10]:
            print(f"      [{ni['platform']}] {ni['signals']}: {ni['text'][:100]}")

    # ── Combined risk ───────────────────────────────────────────────────────
    non_english_hindi = sum(c for l, c in lang_counts.items()
                           if l not in ("latin", "hindi", "emoji_only", "empty"))
    print(f"\n  SUMMARY:")
    print(f"    Non-English/Hindi items: {non_english_hindi} ({100*non_english_hindi/len(corpus):.1f}%)")
    print(f"    Likely non-India items: {len(non_india_items)} ({100*len(non_india_items)/len(corpus):.1f}%)")
    print(f"    Combined noise estimate: {non_english_hindi + len(non_india_items)} ({100*(non_english_hindi + len(non_india_items))/len(corpus):.1f}%) [upper bound, may overlap]")

    all_results[study_name] = {
        "run_id": run_id,
        "corpus_size": len(corpus),
        "language_distribution": dict(lang_counts),
        "language_samples": {k: v for k, v in lang_samples.items()},
        "non_india_count": len(non_india_items),
        "non_india_pct": round(100 * len(non_india_items) / len(corpus), 2),
        "non_india_signal_breakdown": dict(non_india_signal_counts),
        "non_india_samples": non_india_items[:20],
        "non_english_hindi_count": non_english_hindi,
        "non_english_hindi_pct": round(100 * non_english_hindi / len(corpus), 2),
    }

# ── Save ────────────────────────────────────────────────────────────────────
(OUTPUT_DIR / "language_geo_audit.json").write_text(
    json.dumps(all_results, indent=2, ensure_ascii=False), encoding="utf-8"
)
print(f"\nFull results: {OUTPUT_DIR / 'language_geo_audit.json'}")
