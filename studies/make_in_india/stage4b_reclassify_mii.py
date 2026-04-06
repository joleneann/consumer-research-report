"""
Stage 4b: Reclassify unthemed items with expanded keywords + second-pass noise removal.
Goal: get unthemed below 10%.
"""
import io, sys, json, re, random
from pathlib import Path
from collections import Counter, defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

RUN_DIR = ROOT / "consumer_research" / "runs" / "make_in_india_20260401_202927_95b158"

corpus = json.loads((RUN_DIR / "filtered" / "corpus.json").read_text(encoding="utf-8"))
results = json.loads((RUN_DIR / "analysis" / "results.json").read_text(encoding="utf-8"))
print(f"Loaded {len(corpus)} items, {len(results['themes'])} themes")

# Build item_id -> index map for sentiment_results
sr_map = {sr["item_id"]: i for i, sr in enumerate(results["sentiment_results"])}

# Find currently unthemed
themed_ids = set()
for theme in results["themes"]:
    themed_ids.update(theme["item_ids"])
unthemed_items = [item for item in corpus if item["item_id"] not in themed_ids]
print(f"Currently unthemed: {len(unthemed_items)} ({len(unthemed_items)/len(corpus)*100:.1f}%)")

# ── EXPANDED THEME KEYWORDS (only for reclassifying unthemed items) ──
EXPANDED_THEMES = {
    "THM_001": [  # MII Policy
        "make for india", "make for the world", "manufacturing policy",
        "national manufacturing", "manufacturing revolution",
    ],
    "THM_004": [  # Vocal for Local
        "indian product", "desi stuff", "indian shopping", "festival.*indian",
        "diwali.*indian", "independence day.*indian", "august.*swadeshi",
    ],
    "THM_006": [  # D2C/Startup
        "indian company", "indian brand", "desi brand", "boat ", "noise ",
        "lava ", "fire-boltt", "boAt", "titan", "tata.*brand",
        "reliance.*brand", "mahindra", "godrej", "amul", "dabur",
        "patanjali", "zomato", "swiggy", "ola ", "flipkart",
    ],
    "THM_008": [  # Defence
        "indian army", "indian navy", "indian air force", "iaf ",
        "ins ", "navy", "border", "wagah", "surgical strike",
        "rafale", "army", "soldier",
    ],
    "THM_009": [  # Political
        "bjp", "congress", "modi", "rahul", "nda ", "upa ",
        "pmo", "amit shah", "yogi", "piyush goyal", "gadkari",
        "mann ki baat", "election", "sarkar",
    ],
    "THM_010": [  # China dependency
        "china", "chinese",
    ],
    "THM_011": [  # PLI/FDI/Policy
        "gst", "tax reform", "budget", "customs", "fiscal",
        "investment", "ipo ", "market cap",
    ],
    "THM_012": [  # Employment
        "salary", "earning", "income", "job market", "career",
        "hiring", "it sector", "tech industry", "outsourc",
    ],
    "THM_014": [  # Sector success
        "apple.*india", "samsung.*india", "foxconn.*india",
        "tata.*semicond", "tata.*chip", "vedanta.*chip",
    ],
    "THM_015": [  # Atmanirbhar
        "self sufficient", "self-sufficient", "5 trillion",
        "superpower", "developed nation", "viksit",
    ],
}

# New theme for Indian economic growth narrative
NEW_THEME = {
    "theme_id": "THM_016",
    "label": "Indian Economic Growth & Global Standing",
    "description": "India's GDP growth, global ranking (4th/5th largest economy), infrastructure development, purchasing power, and economic transformation narrative.",
    "keywords": ["gdp", "economy", "economic growth", "trillion dollar",
                 "fastest growing", "4th largest", "5th largest",
                 "economic power", "purchasing power", "infrastructure",
                 "highway", "metro", "railway", "road", "airport",
                 "digital india", "upi", "fintech", "rupee",
                 "stock market", "sensex", "nifty",
                 "global ranking", "world bank", "imf",
                 "economic reform", "liberalis"],
}

# ── NOISE PATTERNS (remove from filtered corpus) ──
NOISE_KEYWORDS = [
    "cricket", "ipl ", "odi ", "test match", "wicket", "bowler", "batsman",
    "happy birthday", "rip ", "condolence",
    "movie review", "box office", "bollywood gossip",
    "recipe", "cooking tutorial",
    "astrology", "horoscope", "kundli",
    "bigg boss", "koffee with karan",
]

# Step 1: Remove noise items from corpus
noise_removed = 0
clean_corpus = []
removed_ids = set()
for item in corpus:
    text_l = item["content_text"].lower()
    is_noise = False
    # Very short comments with no MII relevance
    if len(text_l.strip()) < 25 and item["content_type"] == "comment":
        if item["item_id"] not in themed_ids:
            is_noise = True
    # Noise keyword match (only for unthemed)
    if not is_noise and item["item_id"] not in themed_ids:
        for kw in NOISE_KEYWORDS:
            if kw in text_l:
                is_noise = True
                break
    if is_noise:
        noise_removed += 1
        removed_ids.add(item["item_id"])
    else:
        clean_corpus.append(item)

print(f"Noise removal: {noise_removed} items removed, {len(clean_corpus)} remain")

# Step 2: Reclassify unthemed items with expanded keywords
reclassified = 0
for item in clean_corpus:
    if item["item_id"] in themed_ids:
        continue
    text_l = item["content_text"].lower()

    # Try expanded keywords first
    matched_theme = None
    for theme_id, keywords in EXPANDED_THEMES.items():
        for kw in keywords:
            if ".*" in kw:
                if re.search(kw, text_l):
                    matched_theme = theme_id
                    break
            elif kw in text_l:
                matched_theme = theme_id
                break
        if matched_theme:
            break

    # Try new theme
    if not matched_theme:
        for kw in NEW_THEME["keywords"]:
            if kw in text_l:
                matched_theme = "THM_016"
                break

    if matched_theme:
        # Add to theme
        for theme in results["themes"]:
            if theme["theme_id"] == matched_theme:
                theme["item_ids"].append(item["item_id"])
                theme["item_count"] = len(theme["item_ids"])
                break
        else:
            # It's THM_016, create new theme entry
            if matched_theme == "THM_016":
                results["themes"].append({
                    "theme_id": "THM_016",
                    "label": NEW_THEME["label"],
                    "description": NEW_THEME["description"],
                    "item_ids": [item["item_id"]],
                    "item_count": 1,
                    "prevalence": 0,
                    "sentiment_distribution": {"positive": 0, "negative": 0, "neutral": 0},
                    "net_sentiment_score": 0,
                })

        # Update sentiment_results
        idx = sr_map.get(item["item_id"])
        if idx is not None:
            results["sentiment_results"][idx]["themes"].append(matched_theme)

        reclassified += 1

print(f"Reclassified: {reclassified} items into themes")

# Step 3: Remove noise items from sentiment_results
results["sentiment_results"] = [
    sr for sr in results["sentiment_results"] if sr["item_id"] not in removed_ids
]

# Step 4: Recompute theme stats
new_total = len(clean_corpus)
for theme in results["themes"]:
    # Remove any noise item_ids
    theme["item_ids"] = [iid for iid in theme["item_ids"] if iid not in removed_ids]
    theme["item_count"] = len(theme["item_ids"])
    theme["prevalence"] = round(theme["item_count"] / new_total, 4) if new_total > 0 else 0

    # Recompute sentiment
    theme_pos = sum(1 for sr in results["sentiment_results"]
                    if theme["theme_id"] in sr.get("themes", []) and sr["sentiment"] == "positive")
    theme_neg = sum(1 for sr in results["sentiment_results"]
                    if theme["theme_id"] in sr.get("themes", []) and sr["sentiment"] == "negative")
    theme_total = theme["item_count"]
    theme["sentiment_distribution"] = {
        "positive": theme_pos,
        "negative": theme_neg,
        "neutral": theme_total - theme_pos - theme_neg,
    }
    theme["net_sentiment_score"] = round((theme_pos - theme_neg) / theme_total, 4) if theme_total > 0 else 0

# Remove themes with < 5 items
results["themes"] = [t for t in results["themes"] if t["item_count"] >= 5]

# Update overall counts
results["total_items_analyzed"] = new_total

# Recount overall sentiment
pos = sum(1 for sr in results["sentiment_results"] if sr["sentiment"] == "positive")
neg = sum(1 for sr in results["sentiment_results"] if sr["sentiment"] == "negative")
neu = sum(1 for sr in results["sentiment_results"] if sr["sentiment"] == "neutral")
mix = sum(1 for sr in results["sentiment_results"] if sr["sentiment"] == "mixed")
results["overall_sentiment"] = {"positive": pos, "negative": neg, "neutral": neu, "mixed": mix}
results["net_sentiment_score"] = round((pos - neg) / new_total, 4) if new_total > 0 else 0

# Check unthemed
all_themed_ids = set()
for theme in results["themes"]:
    all_themed_ids.update(theme["item_ids"])
all_ids = {item["item_id"] for item in clean_corpus}
still_unthemed = all_ids - all_themed_ids

print(f"\n== FINAL STATE ==")
print(f"Corpus: {new_total} items (was {len(corpus)})")
print(f"Themes: {len(results['themes'])}")
for t in sorted(results["themes"], key=lambda x: -x["item_count"]):
    print(f"  {t['theme_id']}: {t['label']}: {t['item_count']} ({t['prevalence']*100:.1f}%) NSS={t['net_sentiment_score']:+.3f}")
print(f"Unthemed: {len(still_unthemed)} ({len(still_unthemed)/new_total*100:.1f}%)")
print(f"NSS: {results['net_sentiment_score']:+.3f}")

# Save updated results
(RUN_DIR / "analysis" / "results.json").write_text(
    json.dumps(results, indent=2, default=str, ensure_ascii=False), encoding="utf-8"
)

# Save clean corpus
(RUN_DIR / "filtered" / "corpus.json").write_text(
    json.dumps([item for item in clean_corpus], indent=None, default=str, ensure_ascii=False), encoding="utf-8"
)
print(f"\nSaved updated analysis and filtered corpus")
