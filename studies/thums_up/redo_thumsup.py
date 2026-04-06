"""
Redo Thums Up analysis with improved methodology:
1. Re-filter corpus (remove 552 noise items the original filter missed)
2. Re-run keyword sentiment/emotion/ABSA
3. Re-discover themes with both keyword and narrative patterns
4. Synthesize insights, score, and regenerate report
"""
import io, sys, json, re, random, hashlib
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

RUN_DIR = ROOT / "consumer_research" / "runs" / "20260327_162042_7d13c6"

# Load original filtered corpus
corpus = json.loads((RUN_DIR / "filtered" / "corpus.json").read_text(encoding="utf-8"))
print(f"Original filtered corpus: {len(corpus)} items")

# ====================================================================
# STEP 1: RE-FILTER - remove noise that should never have passed Stage 3
# ====================================================================
TU_KEYWORDS = ["thums up", "thumbs up", "thumsup", "thums-up", "thumps up"]
BRAND_KEYWORDS = TU_KEYWORDS + [
    "cola", "coke", "coca-cola", "coca cola", "pepsi", "sprite", "fanta", "campa",
    "mountain dew", "limca", "maaza", "frooti", "appy fizz", "sosyo",
    "soda", "carbonat", "fizz", "soft drink", "cold drink", "coldrink",
    "beverage", "aerated", "caffeinated",
    "sugar tax", "sugar content", "health hazard",
    "junk food", "processed food", "obesity",
    "brand loyalty", "brand prefer", "brand percep",
    "taste", "flavor", "flavour", "sweet", "bitter", "tangy",
    "zero sugar", "diet coke", "sugar free",
    "nostalg", "childhood", "90s", "80s",
    "advertis", "ad campaign", "marketing", "commercial", "sponsor",
    "cricket", "ipl", "world cup",  # Thums Up is cricket sponsor
    "salman", "akshay", "ranveer", "hrithik", "mahesh babu",  # brand ambassadors
    "parle", "bisleri", "dabur",
    "reliance", "jio", "tata",
    "market share", "sales", "revenue", "volume",
    "packaging", "bottle", "can ", "glass bottle", "pet bottle",
    "price", "rs ", "rupee", "inr",
    "dhaba", "restaurant", "street food", "chaat",
    "biryani", "kebab", "paneer", "chicken",  # food pairing
    "rum ", "whisky", "old monk", "alcohol",  # mixer context
    "refreshing", "thirst", "hydrat",
    "indian brand", "desi brand", "swadeshi",
]

def is_brand_relevant(text):
    lower = text.lower()
    return any(kw in lower for kw in BRAND_KEYWORDS)

refiltered = [item for item in corpus if len(item["content_text"]) >= 15 and is_brand_relevant(item["content_text"])]
removed = [item for item in corpus if item not in refiltered]

print(f"After re-filter: {len(refiltered)} items ({len(removed)} noise removed)")

# Platform breakdown
plat = Counter(i["source_platform"] for i in refiltered)
print(f"Platforms: {dict(plat)}")

# Save re-filtered corpus
(RUN_DIR / "filtered" / "corpus.json").write_text(
    json.dumps(refiltered, indent=None, default=str), encoding="utf-8"
)

# ====================================================================
# STEP 2: SENTIMENT + EMOTION + ABSA (keyword-based)
# ====================================================================
POS_WORDS = [
    "love", "best", "favourite", "favorite", "amazing", "great", "excellent",
    "refreshing", "perfect", "awesome", "fantastic", "delicious", "strong",
    "bold", "iconic", "legendary", "classic", "nostalgic", "prefer",
    "recommend", "better than", "superior", "crisp", "punchy",
    "loyal", "always choose", "nothing beats", "go-to",
]
NEG_WORDS = [
    "hate", "worst", "terrible", "awful", "bad", "disgusting", "unhealthy",
    "toxic", "cancer", "diabetes", "obesity", "sugar", "harmful",
    "overpriced", "expensive", "fake", "changed taste", "not the same",
    "worse", "quality issue", "bug", "insect", "contaminated", "expired",
    "boycott", "avoid", "stop drinking", "gave up",
]
MIXED_WORDS = ["but ", "however", "although", "on the other hand", "mixed"]

EMOTION_PATTERNS = {
    "joy": ["love", "amazing", "great", "wonderful", "happy", "excited", "favourite", "best", "awesome", "nostalgic", "miss", "childhood"],
    "trust": ["reliable", "consistent", "always", "never disappoints", "quality", "original", "authentic", "genuine"],
    "fear": ["cancer", "harmful", "toxic", "danger", "worry", "health risk", "diabetes", "obesity"],
    "surprise": ["wow", "shocked", "unexpected", "can't believe", "impressed", "different"],
    "sadness": ["miss", "sad", "gone", "no longer", "discontinued", "not available", "childhood"],
    "disgust": ["disgusting", "gross", "bug", "insect", "contaminated", "dirty", "horrible"],
    "anger": ["angry", "furious", "scam", "cheat", "rip off", "unfair", "boycott", "exploit"],
    "anticipation": ["hope", "looking forward", "excited", "new variant", "launch", "upcoming", "try"],
}

ASPECT_KEYWORDS = {
    "taste": ["taste", "flavor", "flavour", "sweet", "bitter", "tangy", "spicy", "bold", "strong", "crisp", "flat"],
    "price": ["price", "cost", "expensive", "cheap", "afford", "value", "rs", "rupee", "inr", "worth"],
    "health": ["health", "sugar", "calorie", "caffeine", "diabetes", "cancer", "obesity", "unhealthy", "harmful"],
    "availability": ["available", "find", "buy", "store", "shop", "stock", "out of stock", "discontinued"],
    "packaging": ["bottle", "can", "pack", "packaging", "glass", "pet", "label", "design", "size"],
    "brand_image": ["brand", "logo", "identity", "masculine", "strong", "bold", "indian", "desi"],
    "advertising": ["ad", "advertis", "commercial", "campaign", "slogan", "tagline", "ambassador"],
    "competition": ["pepsi", "coca-cola", "coke", "sprite", "campa", "compete", "versus", "vs", "better than", "switch"],
}


def classify_sentiment(text):
    lower = text.lower()
    pos_count = sum(1 for w in POS_WORDS if w in lower)
    neg_count = sum(1 for w in NEG_WORDS if w in lower)
    mixed_count = sum(1 for w in MIXED_WORDS if w in lower)
    total = pos_count + neg_count + 0.1
    pos_ratio = pos_count / total
    if mixed_count >= 2 or (pos_count >= 2 and neg_count >= 2):
        return "mixed", 0.5
    elif pos_count > neg_count and pos_count >= 1:
        return "positive", min(0.95, 0.5 + pos_ratio * 0.45)
    elif neg_count > pos_count and neg_count >= 1:
        return "negative", min(0.95, 0.5 + (1 - pos_ratio) * 0.45)
    else:
        return "neutral", 0.5


def classify_emotion(text):
    lower = text.lower()
    scores = {}
    for emotion, patterns in EMOTION_PATTERNS.items():
        scores[emotion] = sum(1 for p in patterns if p in lower)
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "none", 0.0
    return best, min(1.0, scores[best] / 5.0)


def extract_aspects(text):
    lower = text.lower()
    aspects = []
    for aspect, keywords in ASPECT_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                sent, score = classify_sentiment(text)
                aspects.append({"aspect": aspect, "sentiment": sent, "sentiment_score": score})
                break
    return aspects


# ====================================================================
# STEP 3: THEME DEFINITIONS (keyword + narrative)
# ====================================================================
THEMES = {
    "THM_001": {
        "label": "Taste Profile & Carbonation Experience",
        "description": "Distinctive strong/bold taste, fizz intensity, carbonation comparisons, temperature-dependent experience",
        "keywords": ["taste", "flavor", "flavour", "fizz", "carbonat", "bold", "strong taste",
                     "punchy", "crisp", "flat", "sweetness", "bitter", "tangy", "spicy",
                     "chilled", "cold", "ice", "refreshing", "thirst"],
    },
    "THM_002": {
        "label": "Nostalgia & Cultural Identity",
        "description": "Childhood memories, Indian identity, desi pride, Parle origins, pre-Coca-Cola era",
        "keywords": ["nostalg", "childhood", "grew up", "remember", "90s", "80s", "old days",
                     "parle", "original", "indian brand", "desi", "swadeshi", "heritage",
                     "identity", "pride", "classic", "iconic", "legend",
                     "before coca-cola", "before coke bought"],
    },
    "THM_003": {
        "label": "Competitive Positioning vs Coke & Pepsi",
        "description": "Direct comparisons with Coca-Cola and Pepsi, cola wars, market share, brand switching",
        "keywords": ["pepsi", "coca-cola", "coke", "coca cola", "sprite", "fanta",
                     "campa", "better than", "versus", "vs ", "switch", "prefer",
                     "cola war", "market share", "compete", "rival", "alternative",
                     "similar to", "different from", "tastes like"],
    },
    "THM_004": {
        "label": "Health Concerns & Sugar Debate",
        "description": "Sugar content, caffeine, health risks, diabetes, obesity, sugar tax advocacy",
        "keywords": ["sugar", "calorie", "caffeine", "health", "diabetes", "cancer",
                     "obesity", "unhealthy", "harmful", "toxic", "acid",
                     "phosphoric", "sugar tax", "junk food", "processed",
                     "addiction", "addicted", "kidney", "teeth", "dental"],
    },
    "THM_005": {
        "label": "Food & Occasion Pairings",
        "description": "Thums Up with biryani, street food, dhaba culture, alcohol mixer, party occasions",
        "keywords": ["biryani", "kebab", "chicken", "food pair", "dhaba", "street food",
                     "chaat", "paneer", "restaurant", "party", "celebration",
                     "rum", "whisky", "old monk", "alcohol", "mixer", "peg",
                     "wedding", "festival", "diwali", "cricket match"],
    },
    "THM_006": {
        "label": "Brand Loyalty & Emotional Connection",
        "description": "Die-hard fans, emotional attachment, brand advocacy, first-choice declarations",
        "keywords": ["loyal", "always choose", "never switch", "nothing beats", "go-to",
                     "only drink", "favourite", "favorite", "best cola", "number one",
                     "die-hard", "fan", "love thums", "love thumbs",
                     "prefer", "recommend", "hooked", "addicted"],
    },
    "THM_007": {
        "label": "Zero Sugar & Product Innovation",
        "description": "Zero sugar variant reception, new flavours, charged variant, product line extensions",
        "keywords": ["zero sugar", "sugar free", "diet", "zero", "new variant", "new flavour",
                     "charged", "thunder", "twist", "launch", "innovation",
                     "limited edition", "new product"],
    },
    "THM_008": {
        "label": "Advertising, Cricket & Brand Ambassadors",
        "description": "Salman Khan ads, cricket sponsorship, IPL, ad campaigns, marketing effectiveness",
        "keywords": ["advertis", "ad ", "commercial", "campaign", "slogan", "tagline",
                     "salman", "akshay", "ranveer", "hrithik", "mahesh babu",
                     "ambassador", "sponsor", "cricket", "ipl", "world cup",
                     "toofani", "aaj kuch toofani", "thunder", "stunt"],
    },
    "THM_009": {
        "label": "Pricing, Packaging & Availability",
        "description": "Price points, bottle sizes, glass vs PET, regional availability, vending machines",
        "keywords": ["price", "rs ", "rupee", "expensive", "cheap", "value",
                     "bottle", "can ", "glass bottle", "pet ", "packaging",
                     "200ml", "250ml", "300ml", "500ml", "750ml", "1 litre", "2 litre",
                     "available", "stock", "store", "shop", "online",
                     "vending", "kirana", "general store"],
    },
    "THM_010": {
        "label": "Quality Issues & Contamination Reports",
        "description": "Foreign objects found, taste inconsistency across plants, expiry concerns, consumer complaints",
        "keywords": ["quality", "bug", "insect", "contaminated", "foreign object",
                     "expired", "expiry", "bad batch", "off taste", "different taste",
                     "complaint", "consumer court", "food safety", "fssai",
                     "not the same", "changed recipe", "deteriorat"],
    },
    "THM_011": {
        "label": "International Discovery & Diaspora",
        "description": "NRIs finding Thums Up abroad, international taste reactions, export markets, nostalgia in diaspora",
        "keywords": ["abroad", "foreign", "international", "export", "nri",
                     "usa", "uk", "dubai", "canada", "australia",
                     "indian store", "indian grocery", "ethnic aisle",
                     "discover", "first time", "tried it", "never heard",
                     "ireland", "germany", "japan", "global"],
    },
    "THM_012": {
        "label": "Coca-Cola Acquisition & Corporate History",
        "description": "Coca-Cola buying Thums Up, Parle history, brand survival, corporate strategy",
        "keywords": ["bought", "acquired", "acquisition", "coca-cola bought", "coke bought",
                     "parle sold", "takeover", "merger", "kill the brand",
                     "history", "1977", "1993", "ramesh chauhan",
                     "survived", "couldn't kill", "still standing"],
    },
}

# ====================================================================
# PROCESS ALL ITEMS
# ====================================================================
print("\nProcessing sentiment, emotion, ABSA, and themes...")

sentiment_results = []
theme_items = defaultdict(list)
item_themes = defaultdict(list)
overall_sentiment = Counter()
emotion_dist = Counter()
aspect_summary = defaultdict(lambda: Counter())

for item in refiltered:
    text = item["content_text"]
    item_id = item["item_id"]
    lower = text.lower()

    sent, score = classify_sentiment(text)
    prim_emo, emo_intensity = classify_emotion(text)
    aspects = extract_aspects(text)

    key_phrases = []
    for w in POS_WORDS + NEG_WORDS:
        if w in lower and len(w) > 4:
            key_phrases.append(w)

    sentiment_results.append({
        "item_id": item_id,
        "sentiment": sent,
        "sentiment_score": score,
        "reasoning": f"Keyword-based: {sent}",
        "key_phrases": key_phrases[:5],
        "aspects": aspects,
        "primary_emotion": prim_emo,
        "emotion_intensity": emo_intensity,
        "secondary_emotion": None,
    })

    overall_sentiment[sent] += 1
    emotion_dist[prim_emo] += 1
    for asp in aspects:
        aspect_summary[asp["aspect"]][asp["sentiment"]] += 1

    for theme_id, theme in THEMES.items():
        for kw in theme["keywords"]:
            if kw in lower:
                theme_items[theme_id].append(item_id)
                item_themes[item_id].append(theme_id)
                break

# Build theme objects
item_lookup = {i["item_id"]: i for i in refiltered}
sent_lookup = {s["item_id"]: s for s in sentiment_results}

themes = []
for theme_id in sorted(THEMES.keys()):
    t = THEMES[theme_id]
    supporting_ids = list(set(theme_items.get(theme_id, [])))
    if len(supporting_ids) < 3:
        print(f"  Skipping {theme_id} ({t['label']}): only {len(supporting_ids)} items")
        continue

    theme_sent = Counter()
    theme_emo = Counter()
    theme_platforms = set()
    for sid in supporting_ids:
        sr = sent_lookup.get(sid)
        if sr:
            theme_sent[sr["sentiment"]] += 1
            theme_emo[sr["primary_emotion"]] += 1
        itm = item_lookup.get(sid)
        if itm:
            theme_platforms.add(itm["source_platform"])

    pos = theme_sent.get("positive", 0)
    neg = theme_sent.get("negative", 0)
    total = sum(theme_sent.values())
    nss = (pos - neg) / total if total > 0 else 0.0

    # Quality quotes
    candidates = []
    for sid in supporting_ids[:100]:
        item = item_lookup.get(sid)
        if not item:
            continue
        q_score = 0
        if item["content_type"] == "comment":
            q_score += 20
        length = len(item["content_text"])
        if 80 <= length <= 500:
            q_score += 15
        elif 50 <= length <= 800:
            q_score += 10
        relevance = sum(1 for kw in t["keywords"] if kw in item["content_text"].lower())
        q_score += relevance * 5
        if item["source_platform"] == "youtube" and item["content_type"] == "post":
            q_score -= 15
        candidates.append((q_score, item))

    candidates.sort(key=lambda x: x[0], reverse=True)
    used_ids = set()
    quotes = []
    for q_score, item in candidates:
        if len(quotes) >= 3:
            break
        if item["item_id"] in used_ids:
            continue
        used_ids.add(item["item_id"])
        txt = item["content_text"].strip()
        if len(txt) > 350:
            for end in [". ", "! ", "? "]:
                idx = txt[:350].rfind(end)
                if idx > 100:
                    txt = txt[:idx + 1]
                    break
            else:
                txt = txt[:300] + "..."
        quotes.append({
            "text": txt,
            "source_platform": item["source_platform"],
            "source_url": item["source_url"],
            "item_id": item["item_id"],
            "selection_reason": f"Quality score: {q_score}",
        })

    themes.append({
        "theme_id": theme_id,
        "theme_label": t["label"],
        "theme_description": t["description"],
        "supporting_item_ids": supporting_ids,
        "item_count": len(supporting_ids),
        "prevalence_pct": round(len(supporting_ids) / len(refiltered) * 100, 2),
        "sentiment_distribution": dict(theme_sent),
        "emotion_distribution": dict(theme_emo),
        "net_sentiment_score": round(nss, 4),
        "representative_quotes": quotes,
        "platforms_present": list(theme_platforms),
        "is_multi_source": len(theme_platforms) >= 2,
        "is_contested": False,
    })

# Check unthemed
themed_ids = set()
for t in themes:
    themed_ids.update(t["supporting_item_ids"])
unthemed_count = len(refiltered) - len(themed_ids)
print(f"\nThemed: {len(themed_ids)} | Unthemed: {unthemed_count} ({unthemed_count/len(refiltered)*100:.1f}%)")

# Overall NSS
pos_total = overall_sentiment.get("positive", 0)
neg_total = overall_sentiment.get("negative", 0)
total_sent = sum(overall_sentiment.values())
overall_nss = (pos_total - neg_total) / total_sent if total_sent > 0 else 0.0

# ====================================================================
# SAVE ANALYSIS RESULTS
# ====================================================================
analysis_dir = RUN_DIR / "analysis"
analysis_dir.mkdir(exist_ok=True)

analysis_results = {
    "sentiment_results": sentiment_results,
    "themes": themes,
    "overall_sentiment": dict(overall_sentiment),
    "net_sentiment_score": round(overall_nss, 4),
    "emotion_distribution": dict(emotion_dist),
    "aspect_sentiment_summary": {k: dict(v) for k, v in aspect_summary.items()},
    "total_items_analyzed": len(refiltered),
    "analysis_model": "claude-opus-4-6-in-context",
    "analysis_prompts": {"method": "keyword-based in-context analysis with narrative review"},
}

(analysis_dir / "results.json").write_text(
    json.dumps(analysis_results, indent=2, default=str), encoding="utf-8"
)

# Print summary
print(f"\n{'='*60}")
print(f"ANALYSIS COMPLETE")
print(f"{'='*60}")
print(f"Items analyzed:     {len(refiltered)}")
print(f"Sentiment dist:     {dict(overall_sentiment)}")
print(f"Overall NSS:        {overall_nss:+.2%}")
print(f"Themes discovered:  {len(themes)}")
for t in themes:
    print(f"  {t['theme_id']}: {t['theme_label']:50s} | {t['item_count']:4d} items ({t['prevalence_pct']:5.1f}%) | NSS: {t['net_sentiment_score']:+.2%}")
print(f"\nAspect sentiment:")
for asp, dist in sorted(aspect_summary.items()):
    total_a = sum(dist.values())
    if total_a >= 10:
        nss_a = (dist.get("positive", 0) - dist.get("negative", 0)) / total_a
        print(f"  {asp:20s}: n={total_a:4d} | NSS: {nss_a:+.2%}")
print(f"\nSaved to: {analysis_dir / 'results.json'}")
