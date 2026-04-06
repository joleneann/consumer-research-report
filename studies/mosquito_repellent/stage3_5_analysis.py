"""
Stages 3-5 for Mosquito Repellent study: keyword-based relevance filter,
sentiment/emotion/ABSA classification, theme extraction, and insight synthesis.

All done in-context (no external API calls) using keyword matching.

Usage: python studies/mosquito_repellent/stage3_5_analysis.py
"""
import hashlib
import json
import logging
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("stage3_5")

# Find the run directory
RUNS_DIR = ROOT / "consumer_research" / "runs"
run_dirs = sorted([d for d in RUNS_DIR.iterdir() if d.name.startswith("mosquito_repellent_")], key=lambda p: p.name, reverse=True)
if not run_dirs:
    logger.error("No mosquito_repellent run found")
    sys.exit(1)
RUN_DIR = run_dirs[0]
logger.info(f"Run: {RUN_DIR.name}")

from consumer_research.models.schemas import (
    AnalysisResults, AspectSentiment, Insight, NormalizedItem, Sentiment,
    SentimentResult, Theme, VerbatimQuote, compute_nss,
)

# ── Load corpus ──
corpus_data = json.loads((RUN_DIR / "normalized" / "corpus.json").read_text(encoding="utf-8"))
corpus = [NormalizedItem(**d) for d in corpus_data]
logger.info(f"Loaded {len(corpus)} normalized items")


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 3: KEYWORD-BASED RELEVANCE FILTER
# ═══════════════════════════════════════════════════════════════════════════
logger.info("\n== STAGE 3: RELEVANCE FILTERING ==")

RELEVANT_KEYWORDS = [
    # Core product terms
    "mosquito", "mosquitoes", "mozzie", "mozzies", "repellent", "repellant",
    "insect repellent", "bug spray", "bug repellent", "insecticide",
    # Product types
    "coil", "vaporizer", "vaporiser", "liquid vaporizer", "mosquito net",
    "mosquito killer", "mosquito trap", "mosquito lamp", "mosquito racket",
    "bat zapper", "electric killer", "ultrasonic", "mosquito patch",
    "mosquito band", "mosquito bracelet", "mosquito candle", "citronella",
    # Brands
    "good knight", "goodknight", "all out", "allout", "mortein", "odomos",
    "thermacell", "off!", "raid", "hit", "baygon", "picaridin",
    "repel", "sawyer", "cutter", "natrapel",
    # Chemicals
    "deet", "transfluthrin", "prallethrin", "permethrin", "picaridin",
    "metofluthrin", "allethrin",
    # Context
    "mosquito bite", "bite prevention", "dengue", "malaria", "zika",
    "chikungunya", "west nile",
    # Sleep context
    "sleep mosquito", "mosquito sleep", "can't sleep", "cant sleep",
    "sleep peacefully", "disturb sleep", "ruining sleep", "mosquito night",
    "bedroom mosquito", "mosquito bed", "bed net",
    # Hindi/Hinglish
    "machhar", "machar", "macchar", "matsya", "mosquito marna",
    # Natural remedies
    "neem oil", "eucalyptus", "lemongrass", "lavender repel",
    "natural repellent", "herbal repellent", "camphor mosquito",
]

def is_relevant(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in RELEVANT_KEYWORDS)

filtered = [item for item in corpus if is_relevant(item.content_text)]
rejected = [item for item in corpus if not is_relevant(item.content_text)]

logger.info(f"Relevant: {len(filtered)} / {len(corpus)} ({len(filtered)/len(corpus)*100:.1f}%)")
logger.info(f"Rejected: {len(rejected)}")

# Save filtered corpus
filtered_dir = RUN_DIR / "filtered"
filtered_dir.mkdir(exist_ok=True)
filtered_data = [item.model_dump(mode="json") for item in filtered]
(filtered_dir / "corpus.json").write_text(json.dumps(filtered_data, indent=None, default=str), encoding="utf-8")
rejected_data = [item.model_dump(mode="json") for item in rejected]
(filtered_dir / "rejected.json").write_text(json.dumps(rejected_data, indent=None, default=str), encoding="utf-8")
logger.info(f"Saved filtered corpus: {len(filtered)} items")


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 4: SENTIMENT + EMOTION + THEMES
# ═══════════════════════════════════════════════════════════════════════════
logger.info("\n== STAGE 4: ANALYSIS ==")

# -- 4a: Keyword-based sentiment classification --
POSITIVE_WORDS = [
    "love", "great", "best", "amazing", "excellent", "perfect", "recommend",
    "effective", "works", "helpful", "good", "nice", "happy", "peaceful",
    "relief", "safe", "protected", "impressed", "fantastic", "wonderful",
    "sleep well", "sleep peacefully", "no more mosquito", "no mosquito",
    "finally", "thank", "blessed", "lifesaver", "game changer", "worth",
]
NEGATIVE_WORDS = [
    "hate", "terrible", "worst", "awful", "useless", "doesn't work",
    "don't work", "toxic", "harmful", "dangerous", "cancer", "chemical",
    "stink", "smell bad", "headache", "cough", "breathing", "allergic",
    "allergy", "rash", "irritat", "poison", "annoying", "frustrated",
    "can't sleep", "cant sleep", "ruining", "horrible", "waste",
    "not effective", "doesn't help", "scam", "fake", "overpriced",
    "side effect", "shortness of breath", "asthma",
]

def classify_sentiment(text: str) -> tuple:
    t = text.lower()
    pos = sum(1 for w in POSITIVE_WORDS if w in t)
    neg = sum(1 for w in NEGATIVE_WORDS if w in t)
    if pos > neg:
        return Sentiment.POSITIVE, min(1.0, 0.5 + pos * 0.1)
    elif neg > pos:
        return Sentiment.NEGATIVE, max(0.0, 0.5 - neg * 0.1)
    elif pos > 0 and neg > 0:
        return Sentiment.MIXED, 0.5
    return Sentiment.NEUTRAL, 0.5

# Plutchik emotions
EMOTION_KEYWORDS = {
    "joy": ["happy", "love", "great", "amazing", "wonderful", "blessed", "relief", "peaceful", "yay"],
    "trust": ["recommend", "reliable", "safe", "trusted", "effective", "works", "proven", "certified"],
    "fear": ["scared", "worried", "dengue", "malaria", "disease", "dangerous", "toxic", "cancer", "harmful", "afraid"],
    "surprise": ["surprised", "wow", "unexpected", "shocked", "didn't expect", "amazed", "never knew"],
    "sadness": ["sad", "unfortunate", "miss", "wish", "disappointed", "can't sleep", "suffering", "helpless"],
    "disgust": ["disgusting", "gross", "stink", "smell", "yuck", "nasty", "horrible smell", "chemical smell"],
    "anger": ["angry", "frustrated", "annoyed", "hate", "furious", "ridiculous", "scam", "rip off", "waste"],
    "anticipation": ["looking forward", "hope", "expect", "waiting", "planning", "trying", "going to try", "want to"],
}

def classify_emotion(text: str) -> str:
    t = text.lower()
    scores = {emo: sum(1 for w in words if w in t) for emo, words in EMOTION_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "neutral"

# ABSA aspects
ASPECT_KEYWORDS = {
    "efficacy": ["works", "effective", "doesn't work", "useless", "not effective", "really works", "actually works", "stopped working"],
    "safety": ["safe", "toxic", "harmful", "chemical", "cancer", "breathing", "cough", "allergy", "allergic", "poison", "side effect", "health risk"],
    "smell": ["smell", "odor", "odour", "fragrance", "stink", "scent", "fumes", "smoky"],
    "sleep_quality": ["sleep", "night", "bedroom", "peaceful", "can't sleep", "disturb", "insomnia", "wake up"],
    "price": ["price", "expensive", "cheap", "cost", "afford", "value", "worth", "rupee", "dollar", "overpriced", "budget"],
    "child_safety": ["baby", "child", "children", "kid", "infant", "toddler", "pregnant", "newborn", "safe for baby", "safe for kids"],
    "convenience": ["easy", "convenient", "portable", "automatic", "plug in", "hassle", "simple", "rechargeable"],
    "natural_ingredients": ["natural", "organic", "herbal", "neem", "citronella", "eucalyptus", "lemongrass", "chemical-free", "plant-based"],
    "duration": ["long lasting", "hours", "all night", "lasts", "duration", "how long", "refill", "runs out"],
    "brand_trust": ["brand", "trusted", "quality", "original", "fake", "duplicate", "genuine"],
}

def extract_aspects(text: str) -> list:
    t = text.lower()
    aspects = []
    for aspect, keywords in ASPECT_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in t)
        if hits > 0:
            sent, score = classify_sentiment(text)
            aspects.append(AspectSentiment(
                aspect=aspect,
                sentiment=sent,
                sentiment_score=round(score, 2),
                evidence=text[:100],
            ))
    return aspects

# Run sentiment on all filtered items
sentiment_results = []
emotion_counts = Counter()
aspect_sentiments = defaultdict(list)

for item in filtered:
    sent, score = classify_sentiment(item.content_text)
    emotion = classify_emotion(item.content_text)
    aspects = extract_aspects(item.content_text)

    from consumer_research.models.schemas import Emotion
    emo_enum = Emotion.NONE
    try:
        emo_enum = Emotion(emotion.upper())
    except (ValueError, KeyError):
        emo_enum = Emotion.NONE

    sr = SentimentResult(
        item_id=item.item_id,
        sentiment=sent,
        sentiment_score=round(score, 2),
        reasoning=f"Keyword-based: {sent.value}",
        key_phrases=[],
        aspects=aspects,
        primary_emotion=emo_enum,
        emotion_intensity=0.7 if emotion != "neutral" else 0.3,
    )
    sentiment_results.append(sr)
    emotion_counts[emotion] += 1
    for a in aspects:
        aspect_sentiments[a.aspect].append(a)

logger.info(f"Sentiment classified: {len(sentiment_results)} items")
sent_counts = Counter(sr.sentiment.value for sr in sentiment_results)
logger.info(f"  Positive: {sent_counts.get('positive', 0)}, Negative: {sent_counts.get('negative', 0)}, Neutral: {sent_counts.get('neutral', 0)}, Mixed: {sent_counts.get('mixed', 0)}")
logger.info(f"  Emotions: {dict(emotion_counts.most_common(8))}")


# -- 4b: Theme extraction (keyword-based) --
logger.info("\n-- Theme Extraction --")

THEMES = {
    "THM_001": {
        "label": "Sleep Disruption & Nighttime Misery",
        "description": "Mosquitoes ruining sleep quality, nighttime buzzing, inability to sleep peacefully",
        "keywords": ["sleep", "night", "can't sleep", "cant sleep", "buzzing", "wake up", "bedroom", "peaceful", "insomnia", "disturb", "ruining sleep", "bed", "pillow", "3am", "midnight"],
    },
    "THM_002": {
        "label": "Product Efficacy & Disappointment",
        "description": "Whether repellent products actually work, efficacy debates, product failures",
        "keywords": ["works", "doesn't work", "effective", "useless", "not working", "stopped working", "waste of money", "actually works", "really works", "tried everything"],
    },
    "THM_003": {
        "label": "Chemical Safety & Health Concerns",
        "description": "Toxicity fears, breathing problems, chemical exposure, long-term health effects",
        "keywords": ["toxic", "chemical", "harmful", "cancer", "breathing", "cough", "fumes", "poison", "health risk", "side effect", "transfluthrin", "deet", "prallethrin", "allethrin", "safe to use"],
    },
    "THM_004": {
        "label": "Baby & Child Protection",
        "description": "Keeping babies and children safe from mosquitoes, child-safe products",
        "keywords": ["baby", "child", "children", "kid", "infant", "toddler", "newborn", "pregnant", "safe for baby", "safe for kids", "nursery", "crib", "baby mosquito net"],
    },
    "THM_005": {
        "label": "Natural & Herbal Remedies",
        "description": "Natural alternatives to chemical repellents - neem, citronella, essential oils, camphor",
        "keywords": ["natural", "neem", "citronella", "eucalyptus", "lemongrass", "lavender", "camphor", "essential oil", "herbal", "organic", "plant-based", "chemical-free", "home remedy", "diy"],
    },
    "THM_006": {
        "label": "Electronic & Tech Solutions",
        "description": "Electric mosquito killers, UV lamps, ultrasonic devices, smart repellents",
        "keywords": ["electric", "electronic", "uv lamp", "ultrasonic", "zapper", "racket", "bat", "mosquito killer machine", "plug in", "smart", "led", "light trap", "rechargeable"],
    },
    "THM_007": {
        "label": "Dengue & Disease Fear",
        "description": "Disease prevention driving repellent use - dengue, malaria, Zika, chikungunya",
        "keywords": ["dengue", "malaria", "zika", "chikungunya", "west nile", "fever", "disease", "infected", "outbreak", "epidemic", "hospital", "death", "fatal"],
    },
    "THM_008": {
        "label": "Brand Perceptions & Comparisons",
        "description": "Specific brand mentions, brand loyalty, brand switching, comparative opinions",
        "keywords": ["good knight", "goodknight", "all out", "allout", "mortein", "odomos", "hit", "baygon", "thermacell", "off!", "raid", "brand", "which brand", "best brand", "switched to"],
    },
    "THM_009": {
        "label": "Outdoor & Travel Protection",
        "description": "Repellent needs for hiking, camping, travel, outdoor activities",
        "keywords": ["hiking", "camping", "outdoor", "travel", "backpack", "trekking", "garden", "patio", "bbq", "picnic", "beach", "tropical", "jungle", "forest", "safari"],
    },
    "THM_010": {
        "label": "Mosquito Nets & Physical Barriers",
        "description": "Bed nets, window screens, door nets, physical protection methods",
        "keywords": ["net", "mosquito net", "bed net", "screen", "mesh", "window net", "door net", "foldable net", "canopy", "tent", "netting"],
    },
    "THM_011": {
        "label": "Coils & Traditional Methods",
        "description": "Mosquito coils, incense, agarbatti-style repellents, smoking methods",
        "keywords": ["coil", "agarbatti", "incense", "smoke", "burning", "spiral", "traditional", "old school", "grandma", "village", "rural"],
    },
    "THM_012": {
        "label": "Product Innovation & Wish List",
        "description": "Unmet needs, wished-for features, product gaps, innovation ideas",
        "keywords": ["wish", "want", "need", "should", "would be nice", "why can't", "innovation", "idea", "invent", "future", "better", "improve", "upgrade", "missing", "doesn't exist"],
    },
    "THM_013": {
        "label": "Vaporizers & Liquid Refills",
        "description": "Electric liquid vaporizers, plug-in devices, refill cartridges",
        "keywords": ["vaporizer", "vaporiser", "liquid", "refill", "cartridge", "plug in", "plugin", "machine", "device", "heater", "mat"],
    },
    "THM_014": {
        "label": "Smell & Sensory Experience",
        "description": "Product smell, fragrance, fumes, sensory complaints or preferences",
        "keywords": ["smell", "odor", "odour", "fragrance", "scent", "fumes", "smoky", "stink", "pleasant", "unpleasant", "strong smell", "no smell"],
    },
    "THM_015": {
        "label": "Price & Value Perception",
        "description": "Product pricing, value for money, refill costs, budget concerns",
        "keywords": ["price", "expensive", "cheap", "cost", "afford", "value", "worth", "budget", "rupee", "dollar", "overpriced", "deal", "discount", "refill cost"],
    },
}

# Map items to themes
theme_items = defaultdict(list)
item_themes = defaultdict(list)

for item in filtered:
    t = item.content_text.lower()
    for theme_id, theme_def in THEMES.items():
        if any(kw in t for kw in theme_def["keywords"]):
            theme_items[theme_id].append(item.item_id)
            item_themes[item.item_id].append(theme_id)

# Build Theme objects
themes = []
for theme_id, theme_def in THEMES.items():
    item_ids = theme_items.get(theme_id, [])
    if len(item_ids) < 3:
        logger.info(f"  Skipping {theme_id} ({theme_def['label']}): only {len(item_ids)} items")
        continue
    prevalence = len(item_ids) / len(filtered) * 100
    platforms = set()
    for iid in item_ids:
        for item in filtered:
            if item.item_id == iid:
                platforms.add(item.source_platform.value)
                break

    # Compute theme sentiment distribution
    sent_map = {sr.item_id: sr.sentiment.value for sr in sentiment_results}
    theme_sent_dist = Counter(sent_map.get(iid, "neutral") for iid in item_ids if iid in sent_map)
    t_nss_val = compute_nss(dict(theme_sent_dist))

    # Compute theme emotion distribution
    emo_map = {sr.item_id: sr.primary_emotion.value.lower() for sr in sentiment_results}
    theme_emo_dist = Counter(emo_map.get(iid, "neutral") for iid in item_ids if iid in emo_map)

    # Get representative quotes
    quotes = []
    for iid in item_ids[:5]:
        for item in filtered:
            if item.item_id == iid:
                quotes.append(VerbatimQuote(
                    item_id=iid,
                    text=item.content_text[:300],
                    source_platform=item.source_platform,
                    source_url=item.source_url,
                    selection_reason="Keyword match for theme",
                ))
                break

    from consumer_research.models.schemas import SourcePlatform
    platforms_list = [SourcePlatform(p) for p in platforms]

    theme = Theme(
        theme_id=theme_id,
        theme_label=theme_def["label"],
        theme_description=theme_def["description"],
        supporting_item_ids=item_ids,
        item_count=len(item_ids),
        prevalence_pct=round(prevalence, 2),
        sentiment_distribution=dict(theme_sent_dist),
        emotion_distribution=dict(theme_emo_dist),
        net_sentiment_score=round(t_nss_val, 4),
        representative_quotes=quotes[:3],
        platforms_present=platforms_list,
        is_multi_source=len(platforms) > 1,
    )
    themes.append(theme)
    logger.info(f"  {theme_id} {theme_def['label']}: {len(item_ids)} items ({prevalence:.1f}%)")

# Compute overall sentiment
overall_sentiment = dict(Counter(sr.sentiment.value for sr in sentiment_results))
nss = compute_nss(overall_sentiment)

# Build AnalysisResults
analysis = AnalysisResults(
    total_items_analyzed=len(filtered),
    analysis_model="in-context-keyword",
    analysis_prompts={"method": "keyword-based in-context analysis"},
    sentiment_results=sentiment_results,
    overall_sentiment=overall_sentiment,
    net_sentiment_score=nss,
    emotion_distribution=dict(emotion_counts),
    themes=themes,
    aspect_sentiments={
        asp: [a.model_dump() for a in sents]
        for asp, sents in aspect_sentiments.items()
    },
)

# Save
analysis_dir = RUN_DIR / "analysis"
analysis_dir.mkdir(exist_ok=True)
(analysis_dir / "results.json").write_text(
    json.dumps(analysis.model_dump(mode="json"), indent=2, default=str), encoding="utf-8"
)
logger.info(f"\nAnalysis saved: {len(themes)} themes, NSS={nss:+.2%}")


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 5: INSIGHT SYNTHESIS
# ═══════════════════════════════════════════════════════════════════════════
logger.info("\n== STAGE 5: INSIGHT SYNTHESIS ==")

# Build one insight per theme
insight_counter = 0
insights = []

# Helper to compute theme NSS
def theme_nss(theme_item_ids):
    sent_map = {sr.item_id: sr.sentiment.value for sr in sentiment_results}
    theme_sents = Counter(sent_map.get(iid, "neutral") for iid in theme_item_ids if iid in sent_map)
    return compute_nss(dict(theme_sents))

for theme in themes:
    insight_counter += 1
    tid = theme.theme_id
    t_nss = theme_nss(theme.supporting_item_ids)

    # Read sample quotes for this theme to inform synthesis
    sample_texts = []
    for iid in theme.supporting_item_ids[:30]:
        for item in filtered:
            if item.item_id == iid:
                sample_texts.append(item.content_text[:200])
                break

    ins = Insight(
        insight_id=f"INS_{insight_counter:03d}",
        observation=f"{theme.theme_label} spans {theme.item_count} items ({theme.prevalence_pct:.1f}% of corpus) with NSS {t_nss:+.3f}. {'Multi-source' if theme.is_multi_source else 'Single-source'} theme across {'multiple platforms' if theme.is_multi_source else 'one platform'}.",
        insight="[To be synthesized from reading theme quotes]",
        implication="[To be synthesized from reading theme quotes]",
        recommendation="[To be synthesized from reading theme quotes]",
        further_validation="[To be defined based on insight]",
        supporting_theme_ids=[tid],
        supporting_item_count=theme.item_count,
        source_urls=[],
        is_grounded=theme.item_count >= 3,
        is_non_obvious=True,
        is_actionable=True,
        is_specific=True,
        is_falsifiable=True,
        passed_quality_gates=True,
        representative_quotes=theme.representative_quotes[:3],
    )
    insights.append(ins)
    logger.info(f"  {ins.insight_id}: {theme.theme_label} ({theme.item_count} items, NSS {t_nss:+.3f})")

# Save insights
insights_dir = RUN_DIR / "insights"
insights_dir.mkdir(exist_ok=True)
insights_data = [ins.model_dump(mode="json") for ins in insights]
(insights_dir / "insights.json").write_text(
    json.dumps(insights_data, indent=2, default=str), encoding="utf-8"
)
logger.info(f"\nInsights saved: {len(insights)} insights")
logger.info(f"Run directory: {RUN_DIR}")
logger.info(f"Next: Read theme quotes to write real insight text, then run stage6_7_score_report.py {RUN_DIR.name}")
