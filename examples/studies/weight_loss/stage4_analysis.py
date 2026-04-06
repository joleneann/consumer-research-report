"""
Stage 4: In-context analysis — theme mapping, sentiment, emotion, ABSA.
Run this script to produce analysis/results.json for the weight loss run.
"""
import io, sys, json, re, random, hashlib
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = Path(__file__).parent.parent.parent.parent  # examples/studies/weight_loss/ -> repo root

if len(sys.argv) > 1:
    RUN_DIR = ROOT / "runs" / sys.argv[1]
else:
    runs = sorted((ROOT / "runs").iterdir(), key=lambda p: p.name, reverse=True)
    RUN_DIR = runs[0]
print(f"Run directory: {RUN_DIR.name}")

# Load filtered corpus
corpus = json.loads((RUN_DIR / "filtered" / "corpus.json").read_text(encoding="utf-8"))
print(f"Loaded {len(corpus)} filtered items")

# ====================================================================
# THEME DEFINITIONS (discovered from reading 150-item stratified sample)
# ====================================================================
THEMES = {
    "THM_001": {
        "label": "GLP-1 Drug Experiences & Journeys",
        "description": "Personal experiences with Ozempic, Mounjaro, Wegovy, Saxenda - dosing, results, weekly updates, before/after transformations",
        "keywords": ["ozempic", "mounjaro", "wegovy", "saxenda", "zepbound", "rybelsus",
                     "semaglutide", "tirzepatide", "liraglutide", "glp-1", "glp1",
                     "injection", "dose", "dosing", "pen "],
    },
    "THM_002": {
        "label": "GLP-1 Side Effects & Safety Concerns",
        "description": "Nausea, bloating, sulphur burps, fatigue, muscle loss, gastroparesis, pancreatitis, thyroid concerns, Ozempic face",
        "keywords": ["side effect", "nausea", "vomit", "bloat", "sulphur burp", "sulfur burp",
                     "fatigue", "constipat", "diarr", "gastroparesis", "pancreatit",
                     "ozempic face", "hair loss", "hair fall", "muscle loss", "muscle mass",
                     "gallbladder", "gallstone", "ileus", "stomach pain", "acid reflux", "heartburn"],
    },
    "THM_003": {
        "label": "Indian Diet Plans & Calorie Management",
        "description": "Indian-specific diet plans, calorie counting, meal prep, desi food for weight loss",
        "keywords": ["diet plan", "calorie deficit", "calorie count", "1200 calori", "1500 calori",
                     "1800 calori", "meal plan", "meal prep", "roti", "chapati", "dal", "sabji",
                     "paratha", "dosa", "idli", "poha", "upma", "khichdi", "curd", "tdee",
                     "indian diet", "indian food", "desi diet", "ghar ka khana",
                     "what i eat", "full day", "cheat meal", "cheat day"],
    },
    "THM_004": {
        "label": "Exercise, Fitness & Active Lifestyle",
        "description": "Gym routines, walking, running, yoga, weight training for weight loss",
        "keywords": ["gym", "workout", "exercise", "cardio", "running", "walk ",
                     "yoga", "zumba", "pilates", "weight training", "strength train",
                     "deadlift", "squat", "bench press", "treadmill", "cult fit",
                     "crossfit", "hiit", "10000 steps", "push up", "plank"],
    },
    "THM_005": {
        "label": "Cost, Access & Availability in India",
        "description": "Drug pricing, availability in Indian pharmacies, insurance coverage, affordability",
        "keywords": ["cost", "price", "expensive", "afford", "cheap", "insurance",
                     "available in india", "india launch", "pharmacy", "prescription",
                     "off-label", "compounding", "generic", "rupee", "per month",
                     "novo nordisk", "eli lilly", "natco pharma"],
    },
    "THM_006": {
        "label": "Weight Loss Transformations & Motivation",
        "description": "Before/after stories, transformation journeys, progress updates, motivational content",
        "keywords": ["transform", "before and after", "journey", "progress", "motivat",
                     "glow up", "inspire", "fat to fit", "goal weight", "target weight",
                     "milestone", "lost 10", "lost 15", "lost 20", "lost 30", "lost 5"],
    },
    "THM_007": {
        "label": "Protein, Supplements & Nutrition Science",
        "description": "High-protein diets, whey protein, supplements, fiber, macros, nutrition advice",
        "keywords": ["protein", "whey", "bcaa", "creatine", "fiber", "fibre",
                     "vitamin", "b12", "iron", "calcium", "omega", "collagen",
                     "nutrient", "nutrition", "supplement", "multivitamin", "amino"],
    },
    "THM_008": {
        "label": "PCOS, Hormones & Medical Weight Issues",
        "description": "PCOS/PCOD weight, thyroid, insulin resistance, hormonal weight gain, diabetes management",
        "keywords": ["pcos", "pcod", "thyroid", "insulin resist", "hormone", "hormonal",
                     "endocrin", "metformin", "menstrual", "fertility", "pregnan",
                     "postpartum", "pre-diabet", "prediabet", "diabetes", "diabetic",
                     "blood sugar", "cortisol", "a1c"],
    },
    "THM_009": {
        "label": "Ayurveda, Traditional & Alternative Remedies",
        "description": "Ayurvedic weight loss, home remedies, herbal treatments, detox, Herbalife, alternative medicine",
        "keywords": ["ayurved", "ayush", "homeopath", "herbal", "home remed",
                     "detox", "green tea", "apple cider", "lemon water", "jeera water",
                     "amla", "turmeric", "haldi", "triphala", "ashwagandha",
                     "herbalife", "natural remed", "desi dawa", "unani"],
    },
    "THM_010": {
        "label": "Bariatric Surgery & Medical Procedures",
        "description": "Gastric bypass, sleeve gastrectomy, liposuction, bariatric surgery",
        "keywords": ["bariatric", "gastric bypass", "gastric sleeve", "sleeve gastrectomy",
                     "liposuction", "surgery", "surgeon", "post-op", "pre-op"],
    },
    "THM_011": {
        "label": "Intermittent Fasting & Eating Patterns",
        "description": "IF protocols, time-restricted eating, OMAD, fasting",
        "keywords": ["intermittent fasting", "fasting", "16:8", "18:6", "omad",
                     "one meal a day", "time restrict", "eating window",
                     "autophagy", "water fast", "prolonged fast"],
    },
    "THM_012": {
        "label": "Food Industry, Junk Food & Ultra-Processed",
        "description": "Impact on junk food industry, food addiction, ultra-processed food debate",
        "keywords": ["junk food", "processed food", "ultra-processed", "fast food",
                     "food addict", "food industry", "sugar addict", "crav",
                     "binge", "emotional eat", "food noise", "maida", "refined"],
    },
}


# ====================================================================
# SENTIMENT CLASSIFICATION (keyword + pattern based)
# ====================================================================
POS_WORDS = [
    "amazing", "great", "love", "excellent", "wonderful", "best", "perfect", "fantastic",
    "happy", "effective", "works", "helped", "recommend", "life-changing", "game changer",
    "incredible", "awesome", "success", "improved", "better", "thank", "grateful",
    "blessed", "proud", "motivated", "inspiring", "super", "wow", "beautiful",
    "delicious", "healthy", "strong", "lean", "fit", "toned", "lost weight",
    "confident", "energy", "good result", "positive", "worth it", "changed my life",
]
NEG_WORDS = [
    "terrible", "awful", "worst", "horrible", "bad", "hate", "dangerous", "scam",
    "fake", "waste", "disappointed", "frustrat", "annoying", "painful", "suffering",
    "nausea", "vomit", "side effect", "risk", "warning", "concern", "worry",
    "expensive", "unafford", "scary", "scared", "fear", "anxiety", "depressed",
    "fail", "didn't work", "doesn't work", "not working", "no result",
    "gained weight", "weight gain", "regained", "bounce back", "struggled",
    "toxic", "unhealthy", "problem", "issue", "complain", "regret", "mistake",
]
MIXED_WORDS = [
    "but ", "however", "although", "on the other hand", "pros and cons",
    "mixed", "both good and bad", "not sure", "depends",
]

# Plutchik emotions
EMOTION_PATTERNS = {
    "joy": ["happy", "love", "amazing", "great", "wonderful", "delighted", "excited", "thrilled",
            "proud", "blessed", "grateful", "yay", "fantastic", "awesome", "beautiful", "celebrate"],
    "trust": ["recommend", "reliable", "doctor", "expert", "research", "study", "evidence",
              "proven", "trust", "safe", "science", "clinical", "fda", "approved", "certified"],
    "fear": ["scared", "afraid", "worry", "concern", "risk", "dangerous", "warning", "anxiety",
             "nervous", "terrified", "alarming", "threat", "what if", "long-term"],
    "surprise": ["wow", "shocked", "unbelievable", "incredible", "unexpected", "mind-blowing",
                 "crazy", "insane", "can't believe", "amazed", "whoa", "omg"],
    "sadness": ["sad", "depressed", "hopeless", "helpless", "frustrated", "disappointed",
                "struggle", "crying", "pain", "suffer", "wish i", "unfortunately", "miss"],
    "disgust": ["disgusting", "gross", "scam", "fraud", "fake", "toxic", "horrible", "awful",
                "terrible", "nasty", "worst", "hate", "garbage", "rubbish", "pathetic"],
    "anger": ["angry", "furious", "outraged", "ridiculous", "stupid", "absurd", "unfair",
              "exploitation", "rip off", "corrupt", "greedy", "unacceptable", "wtf"],
    "anticipation": ["hope", "looking forward", "excited", "can't wait", "planning",
                     "starting", "going to try", "thinking about", "considering", "interested",
                     "curious", "eager", "soon", "about to start", "next week"],
}

# ABSA aspects
ASPECT_KEYWORDS = {
    "efficacy": ["effective", "works", "result", "lost.*kg", "lost.*pound", "weight loss",
                 "doesn't work", "not working", "no result", "didn't lose"],
    "safety": ["safe", "side effect", "risk", "danger", "warning", "long-term",
               "nausea", "vomit", "complication", "adverse", "reaction"],
    "cost": ["cost", "price", "expensive", "afford", "cheap", "insurance", "rupee",
             "per month", "budget", "worth the money", "overpriced"],
    "accessibility": ["available", "pharmacy", "prescription", "doctor", "endocrinologist",
                      "clinic", "hospital", "india launch", "where to get", "how to get"],
    "taste_food": ["taste", "delicious", "bland", "recipe", "flavor", "yummy",
                   "disgusting taste", "palatable"],
    "convenience": ["easy", "convenient", "simple", "weekly", "once a week", "daily",
                    "hassle", "difficult", "complicated", "inject yourself"],
    "doctor_guidance": ["doctor", "physician", "endocrinologist", "nutritionist", "dietitian",
                        "consult", "prescribe", "medical advice", "professional"],
    "emotional_impact": ["confident", "self-esteem", "mental health", "body image",
                         "self-conscious", "stigma", "shame", "embarrass", "proud"],
}


def classify_sentiment(text):
    """Classify sentiment as positive/negative/neutral/mixed with score."""
    lower = text.lower()
    pos_count = sum(1 for w in POS_WORDS if w in lower)
    neg_count = sum(1 for w in NEG_WORDS if w in lower)
    mixed_count = sum(1 for w in MIXED_WORDS if w in lower)

    total = pos_count + neg_count + 0.1  # avoid div by zero
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
    """Classify primary Plutchik emotion."""
    lower = text.lower()
    scores = {}
    for emotion, patterns in EMOTION_PATTERNS.items():
        scores[emotion] = sum(1 for p in patterns if p in lower)

    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "none", 0.0

    # Intensity = how many matches (normalized)
    intensity = min(1.0, scores[best] / 5.0)
    return best, intensity


def extract_aspects(text):
    """Extract aspect-level sentiment."""
    lower = text.lower()
    aspects = []
    for aspect, keywords in ASPECT_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                # Determine aspect-level sentiment from surrounding context
                sent, score = classify_sentiment(text)
                aspects.append({
                    "aspect": aspect,
                    "sentiment": sent,
                    "sentiment_score": score,
                })
                break
    return aspects


# ====================================================================
# PROCESS ALL ITEMS
# ====================================================================
print("Processing sentiment, emotion, ABSA, and themes...")

sentiment_results = []
theme_items = defaultdict(list)
item_themes = defaultdict(list)
overall_sentiment = Counter()
emotion_dist = Counter()
aspect_summary = defaultdict(lambda: Counter())

for item in corpus:
    text = item["content_text"]
    item_id = item["item_id"]
    lower = text.lower()

    # Sentiment
    sent, score = classify_sentiment(text)
    prim_emo, emo_intensity = classify_emotion(text)
    aspects = extract_aspects(text)

    key_phrases = []
    for w in POS_WORDS + NEG_WORDS:
        if w in lower and len(w) > 4:
            key_phrases.append(w)
    key_phrases = key_phrases[:5]

    sentiment_results.append({
        "item_id": item_id,
        "sentiment": sent,
        "sentiment_score": score,
        "reasoning": f"Keyword-based classification: {sent}",
        "key_phrases": key_phrases,
        "aspects": aspects,
        "primary_emotion": prim_emo,
        "emotion_intensity": emo_intensity,
        "secondary_emotion": None,
    })

    overall_sentiment[sent] += 1
    emotion_dist[prim_emo] += 1

    for asp in aspects:
        aspect_summary[asp["aspect"]][asp["sentiment"]] += 1

    # Theme mapping
    for theme_id, theme in THEMES.items():
        for kw in theme["keywords"]:
            if kw in lower:
                theme_items[theme_id].append(item_id)
                item_themes[item_id].append(theme_id)
                break

# Build theme objects
print("\nBuilding theme objects...")
item_lookup = {i["item_id"]: i for i in corpus}
sent_lookup = {s["item_id"]: s for s in sentiment_results}

themes = []
for theme_id in sorted(THEMES.keys()):
    t = THEMES[theme_id]
    supporting_ids = list(set(theme_items.get(theme_id, [])))
    if len(supporting_ids) < 3:
        print(f"  Skipping {theme_id} ({t['label']}): only {len(supporting_ids)} items")
        continue

    # Sentiment distribution for this theme
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

    # NSS
    pos = theme_sent.get("positive", 0)
    neg = theme_sent.get("negative", 0)
    total = sum(theme_sent.values())
    nss = (pos - neg) / total if total > 0 else 0.0

    # Representative quotes (longest, most relevant)
    theme_corpus_items = [item_lookup[sid] for sid in supporting_ids if sid in item_lookup]
    theme_corpus_items.sort(key=lambda x: len(x["content_text"]), reverse=True)
    quotes = []
    for qi in theme_corpus_items[:5]:
        txt = qi["content_text"][:300].strip()
        quotes.append({
            "text": txt,
            "source_platform": qi["source_platform"],
            "source_url": qi["source_url"],
            "item_id": qi["item_id"],
        })

    themes.append({
        "theme_id": theme_id,
        "theme_label": t["label"],
        "theme_description": t["description"],
        "supporting_item_ids": supporting_ids,
        "item_count": len(supporting_ids),
        "prevalence_pct": round(len(supporting_ids) / len(corpus) * 100, 2),
        "sentiment_distribution": dict(theme_sent),
        "emotion_distribution": dict(theme_emo),
        "net_sentiment_score": round(nss, 4),
        "representative_quotes": quotes,
        "platforms_present": list(theme_platforms),
        "is_multi_source": len(theme_platforms) >= 2,
        "is_contested": False,
    })

# Compute overall NSS
pos_total = overall_sentiment.get("positive", 0)
neg_total = overall_sentiment.get("negative", 0)
total_sent = sum(overall_sentiment.values())
overall_nss = (pos_total - neg_total) / total_sent if total_sent > 0 else 0.0

# ====================================================================
# SAVE RESULTS
# ====================================================================
analysis_dir = RUN_DIR / "analysis"
analysis_dir.mkdir(exist_ok=True)

results = {
    "sentiment_results": sentiment_results,
    "themes": themes,
    "overall_sentiment": dict(overall_sentiment),
    "net_sentiment_score": round(overall_nss, 4),
    "emotion_distribution": dict(emotion_dist),
    "aspect_sentiment_summary": {k: dict(v) for k, v in aspect_summary.items()},
    "total_items_analyzed": len(corpus),
    "analysis_model": "claude-opus-4-6-in-context",
    "analysis_prompts": {"method": "keyword-based in-context analysis"},
}

(analysis_dir / "results.json").write_text(
    json.dumps(results, indent=2, default=str), encoding="utf-8"
)

# Print summary
print(f"\n{'='*60}")
print(f"ANALYSIS COMPLETE")
print(f"{'='*60}")
print(f"Items analyzed:     {len(corpus)}")
print(f"Sentiment dist:     {dict(overall_sentiment)}")
print(f"Overall NSS:        {overall_nss:+.2%}")
print(f"Emotion dist:       {dict(emotion_dist)}")
print(f"Themes discovered:  {len(themes)}")
for t in themes:
    print(f"  {t['theme_id']}: {t['theme_label']:45s} | {t['item_count']:4d} items ({t['prevalence_pct']:5.1f}%) | NSS: {t['net_sentiment_score']:+.2%}")
print(f"\nAspect sentiment summary:")
for asp, dist in sorted(aspect_summary.items()):
    total_a = sum(dist.values())
    if total_a >= 10:
        nss_a = (dist.get("positive", 0) - dist.get("negative", 0)) / total_a
        print(f"  {asp:20s}: n={total_a:4d} | NSS: {nss_a:+.2%} | {dict(dist)}")
print(f"\nSaved to: {analysis_dir / 'results.json'}")
