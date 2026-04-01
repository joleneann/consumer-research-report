"""
Stage 4: In-context analysis for Make in India.
Keyword-based sentiment, emotion, ABSA, and theme mapping.
No API calls.
"""
import io, sys, json, re, random, hashlib
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

RUN_DIR = ROOT / "consumer_research" / "runs" / "make_in_india_20260401_202927_95b158"
print(f"Run directory: {RUN_DIR.name}")

corpus = json.loads((RUN_DIR / "filtered" / "corpus.json").read_text(encoding="utf-8"))
print(f"Loaded {len(corpus)} filtered items")

# ====================================================================
# THEME DEFINITIONS (discovered from reading 300-item stratified sample)
# ====================================================================
THEMES = {
    "THM_001": {
        "label": "Make in India Policy - Success vs Failure Debate",
        "description": "Central debate on whether MII has achieved its goals. GDP share falling vs mobile factories growing. FDI claims vs unemployment reality. 25% target vs 14% actual.",
        "keywords": ["make in india", "mii", "makeinindia", "make-in-india", "11 years",
                     "10 years", "gdp share", "manufacturing share", "25%", "25 percent",
                     "manufacturing gdp", "success story", "success or failure",
                     "failed", "failure", "working", "not working",
                     "मेक इन इंडिया", "मेक इन", "ground reality"],
    },
    "THM_002": {
        "label": "Assembly vs True Manufacturing",
        "description": "Debate on whether 'Made in India' means genuine manufacturing or just assembly of imported components. iPhone assembly controversy. Chinese components in Indian products.",
        "keywords": ["assembl", "assemble in india", "assembled", "component",
                     "just assemble", "just put together", "not manufactur",
                     "white label", "white-label", "relabel", "re-label",
                     "made in india.*china", "china.*component", "import.*component",
                     "actually made", "truly made", "genuinely made",
                     "foxconn", "iphone.*india", "iphone.*export"],
    },
    "THM_003": {
        "label": "Tariff, Trade War & Geopolitical Tensions",
        "description": "US-India tariff tensions (Trump 50%), India imposing retaliatory tariffs, trade deals, India-China trade deficit, geopolitical positioning.",
        "keywords": ["tariff", "trade war", "trade deal", "trade deficit",
                     "trump.*india", "india.*trump", "reciprocal tariff",
                     "50% tariff", "import duty", "customs duty",
                     "trade tension", "trade partner", "trade relation",
                     "fta", "free trade"],
    },
    "THM_004": {
        "label": "Vocal for Local & Swadeshi Movement",
        "description": "PM Modi's Vocal for Local call, Swadeshi ideology, buy Indian campaigns, festive season patriotic buying, historical Swadeshi connection.",
        "keywords": ["vocal for local", "vocalforlocal", "swadeshi", "स्वदेशी",
                     "buy indian", "buy local", "buy.*made in india",
                     "shop local", "support local", "support indian",
                     "indian product", "desi product", "khadi",
                     "har ghar swadeshi", "hargharswadeshi",
                     "bhारतीय उत्पाद", "स्थानीय", "लोकल"],
    },
    "THM_005": {
        "label": "Boycott Foreign Brands & Products",
        "description": "Consumer-driven boycotts of Chinese, Turkish, Israeli, Bangladeshi and American products. Reactive nationalism. Brand-level boycott campaigns.",
        "keywords": ["boycott", "ban china", "ban chinese", "chinese product",
                     "chinese goods", "boycott turkey", "boycott turkish",
                     "boycott israel", "boycott bangladesh", "boycott nike",
                     "boycott american", "stop buying", "stop supporting",
                     "बहिष्कार", "बॉयकॉट"],
    },
    "THM_006": {
        "label": "Indian D2C Brands & Startup Ecosystem",
        "description": "Homegrown D2C brands gaining traction. Shark Tank India effect. Indian founders building products. Brand pride in Indian startups.",
        "keywords": ["d2c", "direct to consumer", "indian brand", "desi brand",
                     "homegrown", "indian startup", "startup india",
                     "shark tank", "indian founder", "indian entrepreneur",
                     "lava", "boat", "mamaearth", "nykaa", "noise",
                     "indian unicorn", "proudly indian", "indian company",
                     "indian business", "msme"],
    },
    "THM_007": {
        "label": "Quality Perception & Trust Deficit",
        "description": "Indian products perceived as inferior quality. Different quality for export vs domestic. Indian version vs US/EU version of same brand. Counterfeit and fake products.",
        "keywords": ["quality", "inferior", "cheap quality", "poor quality",
                     "bad quality", "low quality", "build quality",
                     "indian version", "us version", "export quality",
                     "counterfeit", "fake product", "duplicate",
                     "not reliable", "durability", "world class",
                     "global standard", "crash test", "substandard"],
    },
    "THM_008": {
        "label": "Defence & Strategic Manufacturing",
        "description": "Defence manufacturing success stories. Vande Bharat trains. HAL, BEML, Tata defence. Arms exports. Missile and drone indigenous production.",
        "keywords": ["defence", "defense", "military", "armed force",
                     "vande bharat", "hal ", "beml", "bharat electronics",
                     "arms export", "defence export", "missile",
                     "drone", "indigenous", "tejas", "brahmos",
                     "submarine", "aircraft carrier", "weapon",
                     "locomotive", "metro rake", "coach factory",
                     "isro", "satellite", "space"],
    },
    "THM_009": {
        "label": "Political Polarisation & Narrative Wars",
        "description": "BJP vs Congress framing of MII. Modi personality cult vs opposition criticism. Rahul Gandhi attacks. Political propaganda and counter-narratives.",
        "keywords": ["bjp", "congress", "modi", "rahul gandhi",
                     "ragा", "pappu", "bhakt", "andh bhakt",
                     "opposition", "propaganda", "narrative",
                     "election", "vote bank", "political",
                     "viksit bharat", "naya bharat", "inc ",
                     "sonia", "kejriwal"],
    },
    "THM_010": {
        "label": "China Dependency Paradox",
        "description": "India's increasing trade deficit with China despite boycott rhetoric. China's structural manufacturing advantage. Can't beat China's ecosystem. Electronics dependency.",
        "keywords": ["china", "chinese", "trade deficit.*china",
                     "china.*import", "import.*china", "china.*depend",
                     "replace china", "china alternative", "beat china",
                     "china supply chain", "china.*export",
                     "china.*factory", "world factory",
                     "vietnam", "bangladesh.*manufactur"],
    },
    "THM_011": {
        "label": "PLI Scheme, FDI & Industrial Policy",
        "description": "Production Linked Incentive scheme impact. FDI inflows. Semiconductor mission. Electronics component manufacturing. Government incentives for manufacturing.",
        "keywords": ["pli", "production linked", "fdi",
                     "foreign direct invest", "semiconductor",
                     "chip manufactur", "chip making", "fab ",
                     "electronics component", "solar panel",
                     "ease of doing business", "investment",
                     "subsidy", "incentive", "industrial corridor",
                     "gst", "tax reform"],
    },
    "THM_012": {
        "label": "Employment, Jobs & MSME Impact",
        "description": "Jobs promise vs reality. MSME struggles. Unemployment data. Ease of doing business for small manufacturers. Startup vs employment gap.",
        "keywords": ["job", "employment", "unemploy", "hired",
                     "hiring", "msme", "small business",
                     "kirana", "small manufacturer", "worker",
                     "labour", "labor", "wages", "salary",
                     "100 million jobs", "employment generation",
                     "self employed", "rozgar", "berozgar",
                     "रोजगार", "बेरोजगार"],
    },
    "THM_013": {
        "label": "Nationalism vs Consumer Pragmatism",
        "description": "Tension between patriotic buying and rational consumer choice. Should quality drive choice or nationalism? Corporate nationalism critique. Performative patriotism.",
        "keywords": ["nationalism", "patriotism", "patriotic",
                     "national pride", "india first",
                     "blind nationalism", "performative",
                     "rational choice", "consumer choice",
                     "product.*good", "product.*quality",
                     "no one cares unless product is good",
                     "selling nationalism", "emotional buying"],
    },
    "THM_014": {
        "label": "Sector Success Stories - Mobile, Pharma, Electronics",
        "description": "Specific sectors where MII has shown results. Mobile phone manufacturing boom. Pharma export leadership. Electronics growth. Toy industry resurgence.",
        "keywords": ["mobile manufactur", "phone manufactur",
                     "smartphone.*india", "mobile.*factory",
                     "pharma", "pharmaceutical", "vaccine",
                     "medicine", "generic drug",
                     "electronic", "toy industry", "toy manufactur",
                     "textile", "garment", "automobile",
                     "auto sector", "ev ", "electric vehicle"],
    },
    "THM_015": {
        "label": "Atmanirbhar Bharat & Self-Reliance Vision",
        "description": "The broader Atmanirbhar Bharat vision beyond MII. Self-reliance as national aspiration. Reducing import dependency. India 2047 vision.",
        "keywords": ["atmanirbhar", "aatmanirbhar", "self relian",
                     "self-relian", "आत्मनिर्भर",
                     "import substitut", "reduce depend",
                     "india 2047", "viksit bharat",
                     "5 trillion", "superpower",
                     "self sufficient"],
    },
}

# ====================================================================
# SENTIMENT KEYWORDS
# ====================================================================
POSITIVE_KW = [
    "success", "excellent", "great", "amazing", "wonderful", "proud", "pride",
    "impressive", "achievement", "milestone", "progress", "growth", "boom",
    "revolution", "transformative", "incredible", "fantastic", "brilliant",
    "empowering", "best", "leading", "innovative", "historic", "record",
    "bravo", "congratulat", "massive", "landmark", "remarkable",
    "शानदार", "बहुत अच्छा", "गर्व", "सफल", "बढ़िया",
    "jai hind", "जय हिंद", "well done", "love india", "proud indian",
]
NEGATIVE_KW = [
    "fail", "failure", "disaster", "terrible", "worst", "pathetic", "scam",
    "fraud", "corrupt", "lies", "propaganda", "fake", "shame", "shameful",
    "useless", "hopeless", "joke", "punchline", "collapse", "crash",
    "declining", "falling", "crisis", "hypocris", "hypocrisy",
    "बेकार", "फेल", "धोखा", "झूठ", "भ्रष्ट", "बर्बाद",
    "ruined", "destroying", "damaged", "beyond repair", "cooked",
]
MIXED_KW = [
    "but", "however", "although", "on one hand", "pros and cons",
    "mixed", "both good and bad", "complicated", "nuanced",
    "some success", "partially", "not entirely",
]

# ====================================================================
# EMOTION KEYWORDS (Plutchik's 8)
# ====================================================================
EMOTION_MAP = {
    "joy": ["proud", "pride", "happy", "celebration", "celebrate", "joy",
            "excited", "thrilled", "love", "wonderful", "fantastic",
            "गर्व", "खुशी", "जश्न", "jai hind", "bravo"],
    "trust": ["reliable", "trust", "confident", "credible", "proven",
              "track record", "deliver", "commitment", "faith",
              "विश्वास", "भरोसा"],
    "fear": ["worried", "concern", "risk", "danger", "threat",
             "vulnerable", "dependenc", "crisis", "alarm",
             "चिंता", "खतरा", "डर"],
    "surprise": ["shocking", "surprising", "unexpected", "unbelievable",
                 "wow", "didn't expect", "amazed", "incredible",
                 "हैरान", "चौंका"],
    "sadness": ["sad", "unfortunat", "tragic", "disappoint", "regret",
                "heartbreak", "painful", "suffering", "loss",
                "दुख", "निराशा", "दुर्भाग्य"],
    "disgust": ["disgust", "shameful", "pathetic", "disgusting", "sick",
                "corrupt", "crony", "scam", "exploitation",
                "घृणा", "शर्मनाक"],
    "anger": ["angry", "furious", "outrage", "rage", "infuriat",
              "enough", "unacceptable", "stop", "protest",
              "गुस्सा", "आक्रोश", "नाराज"],
    "anticipation": ["hope", "future", "soon", "upcoming", "potential",
                     "expect", "looking forward", "vision", "2047",
                     "dream", "aspir", "opportunity",
                     "उम्मीद", "भविष्य", "संभावना"],
}

# ====================================================================
# ASPECT DEFINITIONS
# ====================================================================
ASPECTS = {
    "policy_effectiveness": ["policy", "scheme", "initiative", "government",
                             "reform", "regulation", "compliance", "target",
                             "goal", "gdp", "implement"],
    "product_quality": ["quality", "standard", "inferior", "superior",
                        "world class", "global", "durable", "reliable",
                        "crash test", "build quality"],
    "price_competitiveness": ["price", "cost", "expensive", "cheap",
                              "affordable", "competitive", "value for money",
                              "overpriced", "undercut"],
    "employment_impact": ["job", "employment", "unemploy", "hiring",
                          "worker", "labour", "salary", "wages",
                          "livelihood", "rozgar"],
    "consumer_nationalism": ["nationalism", "patriotism", "patriotic",
                             "swadeshi", "boycott", "vocal for local",
                             "desi", "indian first", "pride"],
    "sector_performance": ["defence", "pharma", "electronics", "mobile",
                           "semiconductor", "auto", "textile", "toy",
                           "manufacturing sector"],
    "trade_competitiveness": ["export", "import", "tariff", "trade",
                              "fdi", "investment", "global market",
                              "supply chain"],
    "startup_ecosystem": ["startup", "d2c", "entrepreneur", "founder",
                          "homegrown", "brand", "msme", "small business",
                          "shark tank", "unicorn"],
    "self_reliance": ["atmanirbhar", "self relian", "self-relian",
                      "import substitut", "dependenc", "indigenous",
                      "reduce import"],
}


def classify_sentiment(text: str) -> tuple:
    """Returns (sentiment, score, confidence)."""
    text_l = text.lower()
    pos_hits = sum(1 for kw in POSITIVE_KW if kw in text_l)
    neg_hits = sum(1 for kw in NEGATIVE_KW if kw in text_l)
    mixed_hits = sum(1 for kw in MIXED_KW if kw in text_l)

    total = pos_hits + neg_hits + max(mixed_hits, 1)
    if pos_hits == 0 and neg_hits == 0:
        return "neutral", 0.5, 0.3
    elif mixed_hits > 0 and pos_hits > 0 and neg_hits > 0:
        return "mixed", 0.5, 0.5
    elif pos_hits > neg_hits:
        score = min(0.95, 0.5 + (pos_hits - neg_hits) / total * 0.45)
        return "positive", score, min(0.9, 0.4 + pos_hits * 0.1)
    elif neg_hits > pos_hits:
        score = max(0.05, 0.5 - (neg_hits - pos_hits) / total * 0.45)
        return "negative", score, min(0.9, 0.4 + neg_hits * 0.1)
    else:
        return "mixed", 0.5, 0.4


def classify_emotion(text: str) -> str:
    text_l = text.lower()
    scores = {}
    for emotion, keywords in EMOTION_MAP.items():
        scores[emotion] = sum(1 for kw in keywords if kw in text_l)
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "none"
    return best


def classify_aspects(text: str) -> list:
    text_l = text.lower()
    results = []
    for aspect, keywords in ASPECTS.items():
        hits = sum(1 for kw in keywords if kw in text_l)
        if hits >= 1:
            # Quick sentiment for this aspect
            # Find sentences containing aspect keywords
            sent, score, _ = classify_sentiment(text)
            results.append({
                "aspect": aspect,
                "sentiment": sent,
                "sentiment_score": round(score, 2),
            })
    return results


def classify_themes(text: str) -> list:
    text_l = text.lower()
    matched = []
    for theme_id, theme in THEMES.items():
        for kw in theme["keywords"]:
            if ".*" in kw:
                if re.search(kw, text_l):
                    matched.append(theme_id)
                    break
            elif kw in text_l:
                matched.append(theme_id)
                break
    return matched


# ====================================================================
# MAIN PROCESSING
# ====================================================================
print("\n== CLASSIFYING ALL ITEMS ==")
sentiment_results = []
theme_items = defaultdict(list)
aspect_counts = defaultdict(lambda: defaultdict(int))
emotion_counts = Counter()
overall_pos = 0
overall_neg = 0
overall_neu = 0
overall_mix = 0

for i, item in enumerate(corpus):
    text = item.get("content_text", "")
    item_id = item.get("item_id", str(i))

    # Sentiment
    sent, score, conf = classify_sentiment(text)
    if sent == "positive": overall_pos += 1
    elif sent == "negative": overall_neg += 1
    elif sent == "neutral": overall_neu += 1
    else: overall_mix += 1

    # Emotion
    emotion = classify_emotion(text)
    emotion_counts[emotion] += 1

    # Aspects
    aspects = classify_aspects(text)
    for asp in aspects:
        aspect_counts[asp["aspect"]][asp["sentiment"]] += 1

    # Themes
    themes = classify_themes(text)
    for t in themes:
        theme_items[t].append(item_id)

    sentiment_results.append({
        "item_id": item_id,
        "sentiment": sent,
        "sentiment_score": round(score, 2),
        "confidence": round(conf, 2),
        "emotion": emotion,
        "aspects": aspects,
        "themes": themes,
    })

    if (i + 1) % 2000 == 0:
        print(f"  Processed {i+1}/{len(corpus)} items...")

total = len(corpus)
print(f"\n== SENTIMENT SUMMARY ==")
print(f"  Positive: {overall_pos} ({overall_pos/total*100:.1f}%)")
print(f"  Negative: {overall_neg} ({overall_neg/total*100:.1f}%)")
print(f"  Neutral:  {overall_neu} ({overall_neu/total*100:.1f}%)")
print(f"  Mixed:    {overall_mix} ({overall_mix/total*100:.1f}%)")
nss = (overall_pos - overall_neg) / total
print(f"  NSS: {nss:+.3f}")

print(f"\n== EMOTION DISTRIBUTION ==")
for emo, cnt in emotion_counts.most_common():
    print(f"  {emo}: {cnt} ({cnt/total*100:.1f}%)")

print(f"\n== THEME DISTRIBUTION ==")
for tid in sorted(THEMES.keys()):
    items = theme_items.get(tid, [])
    label = THEMES[tid]["label"]
    print(f"  {tid}: {label}: {len(items)} items ({len(items)/total*100:.1f}%)")

# Count unthemed
themed_ids = set()
for items in theme_items.values():
    themed_ids.update(items)
all_ids = {item.get("item_id", str(i)) for i, item in enumerate(corpus)}
unthemed = all_ids - themed_ids
print(f"\n  Unthemed: {len(unthemed)} ({len(unthemed)/total*100:.1f}%)")

print(f"\n== ASPECT SENTIMENT ==")
for aspect, sentiments in sorted(aspect_counts.items()):
    total_asp = sum(sentiments.values())
    pos = sentiments.get("positive", 0)
    neg = sentiments.get("negative", 0)
    asp_nss = (pos - neg) / total_asp if total_asp > 0 else 0
    print(f"  {aspect}: n={total_asp}, pos={pos}, neg={neg}, NSS={asp_nss:+.2f}")

# ====================================================================
# SAVE RESULTS
# ====================================================================
# Build themes list
themes_list = []
for tid in sorted(THEMES.keys()):
    items_in_theme = theme_items.get(tid, [])
    if len(items_in_theme) < 5:
        continue
    # Compute theme-level sentiment
    theme_pos = sum(1 for sr in sentiment_results if tid in sr["themes"] and sr["sentiment"] == "positive")
    theme_neg = sum(1 for sr in sentiment_results if tid in sr["themes"] and sr["sentiment"] == "negative")
    theme_total = len(items_in_theme)
    theme_nss = (theme_pos - theme_neg) / theme_total if theme_total > 0 else 0

    themes_list.append({
        "theme_id": tid,
        "label": THEMES[tid]["label"],
        "description": THEMES[tid]["description"],
        "item_ids": items_in_theme,
        "item_count": len(items_in_theme),
        "prevalence": round(len(items_in_theme) / total, 4),
        "sentiment_distribution": {
            "positive": theme_pos,
            "negative": theme_neg,
            "neutral": theme_total - theme_pos - theme_neg,
        },
        "net_sentiment_score": round(theme_nss, 4),
    })

# Build aspect results
aspect_results = []
for aspect, sentiments in sorted(aspect_counts.items()):
    total_asp = sum(sentiments.values())
    if total_asp < 10:
        continue
    pos = sentiments.get("positive", 0)
    neg = sentiments.get("negative", 0)
    aspect_results.append({
        "aspect": aspect,
        "sentiment": "positive" if pos > neg else ("negative" if neg > pos else "neutral"),
        "sentiment_score": round(pos / total_asp, 2),
        "sample_size": total_asp,
        "nss": round((pos - neg) / total_asp, 4),
    })

# Overall results
results = {
    "brand_name": "Make in India",
    "category": "government initiative / economic policy / consumer nationalism",
    "total_items_analyzed": total,
    "overall_sentiment": {
        "positive": overall_pos,
        "negative": overall_neg,
        "neutral": overall_neu,
        "mixed": overall_mix,
    },
    "net_sentiment_score": round(nss, 4),
    "emotion_distribution": dict(emotion_counts.most_common()),
    "themes": themes_list,
    "aspect_sentiments": aspect_results,
    "sentiment_results": sentiment_results,
}

# Save
analysis_dir = RUN_DIR / "analysis"
analysis_dir.mkdir(exist_ok=True)
(analysis_dir / "results.json").write_text(
    json.dumps(results, indent=2, default=str, ensure_ascii=False), encoding="utf-8"
)
print(f"\nSaved analysis to {analysis_dir / 'results.json'}")
print(f"Themes: {len(themes_list)}, Aspects: {len(aspect_results)}")
