"""Stage 4b: Theme extraction and mapping.
Two-pass approach: themes discovered from reading, now map ALL items.
"""
import json
import sys
import re
import pathlib

sys.stdout.reconfigure(encoding="utf-8")

RUN_DIR = pathlib.Path("runs/20260407_173532_06e43d")
filtered = json.loads((RUN_DIR / "filtered" / "corpus.json").read_text(encoding="utf-8"))

# Themes discovered from reading stratified sample of 300+ items
THEMES = [
    {
        "theme_id": "THM_01",
        "label": "GLP-1 Medication Efficacy & Personal Journeys",
        "description": "Users sharing weight loss results, progress updates, dosage experiences, and personal stories on GLP-1 medications (Ozempic, Mounjaro, Wegovy, Zepbound)",
        "keywords": [
            "ozempic", "mounjaro", "wegovy", "zepbound", "semaglutide", "tirzepatide",
            "glp-1", "glp1", "glp 1", "lost weight", "lost kg", "lost pound",
            "down kg", "weight down", "week update", "month update", "my journey",
            "progress", "before and after", "transformation", "results",
            "dose", "dosage", "mg dose", "injection", "pen", "shot",
            "started taking", "been on", "months on", "weeks on",
            "retatrutide", "saxenda", "liraglutide", "rybelsus",
        ],
    },
    {
        "theme_id": "THM_02",
        "label": "Side Effects & Health Risks",
        "description": "Discussion of medication side effects (nausea, muscle loss, hair loss, Ozempic face), safety concerns, and adverse experiences",
        "keywords": [
            "side effect", "nausea", "vomiting", "diarrhea", "constipation",
            "hair loss", "muscle loss", "bone loss", "fatigue", "headache",
            "bloating", "sulphur burp", "acid reflux", "gallstone", "pancreatitis",
            "thyroid", "cancer risk", "stomach paralysis", "gastroparesis",
            "ozempic face", "ozempic teeth", "insomnia", "dry mouth",
            "horror story", "adverse", "hospitalized", "dangerous",
            "long-term risk", "long term risk", "safety concern",
            "vision loss", "eye effect", "kidney",
        ],
    },
    {
        "theme_id": "THM_03",
        "label": "India Market Access & Affordability",
        "description": "Mounjaro launch in India, cost and pricing discussions, prescription access, generic availability, doctor recommendations in Indian cities",
        "keywords": [
            "india", "indian", "launched in india", "available in india",
            "mounjaro india", "ozempic india", "cost", "price", "expensive",
            "afford", "rupee", "rs ", "inr", "insurance", "coverage",
            "generic", "patent expir", "eli lilly", "novo nordisk",
            "prescribe", "prescription", "doctor in", "endocrinologist",
            "bangalore", "mumbai", "delhi", "hyderabad", "chennai", "kolkata",
            "pharmacy", "medical store", "where to get", "where to buy",
            "sugar.fit", "sugarfit", "avataar",
        ],
    },
    {
        "theme_id": "THM_04",
        "label": "Celebrity & Bollywood Ozempic Speculation",
        "description": "Discussion about whether Bollywood celebrities and public figures used Ozempic/GLP-1 for weight loss, speculation about transformations",
        "keywords": [
            "bollywood", "celebrity", "actor", "actress",
            "kapil sharma", "karan johar", "kjo", "sara ali khan",
            "bhumi pednekar", "kusha kapila", "salman khan", "ram kapoor",
            "vidya balan", "oprah", "twinkle", "janhvi",
            "huma qureshi", "aishwarya mohanraj", "rakul",
            "jacqueline", "sarfaraz khan", "prithvi shaw",
            "weight loss secret", "transformation secret",
            "ozempic user", "on ozempic",
        ],
    },
    {
        "theme_id": "THM_05",
        "label": "Natural Alternatives & Anti-Medication Stance",
        "description": "Advocacy for natural GLP-1 boosters, Ayurvedic remedies, diet/exercise-first approach, criticism of medication as shortcut",
        "keywords": [
            "natural", "ayurvedic", "ayurveda", "home remedy", "herbal",
            "without medication", "without injection", "no injection",
            "nature's ozempic", "natural glp", "yerba mate", "apple cider",
            "chia seed", "blueberr", "fiber", "prebiotic",
            "not ozempic", "not on ozempic", "no pill", "no drug",
            "diet and exercise", "naturally", "organic", "holistic",
            "traditional", "homeopathic", "unani",
            "shortcut", "easy way", "quick fix", "magic pill",
            "real way", "right way", "hard work",
        ],
    },
    {
        "theme_id": "THM_06",
        "label": "Stigma, Shame & Social Judgment",
        "description": "Medication stigma, 'easy way out' narrative, fat shaming, body image issues, celebrities not admitting Ozempic use, moral judgment",
        "keywords": [
            "stigma", "shame", "sham", "judg", "lazy", "cheating",
            "easy way out", "easy way", "shortcut to",
            "body sham", "fat sham", "body image",
            "not owning up", "not admitting", "hiding",
            "willpower", "discipline vs", "personal failure",
            "obesity is a disease", "chronic disease",
            "trend", "trendy", "fad",
            "deserve", "earn", "suffer",
            "bullying", "invisible", "broken",
        ],
    },
    {
        "theme_id": "THM_07",
        "label": "Diet & Nutrition on GLP-1",
        "description": "Protein prioritization, meal planning while on medication, food choices, calorie tracking, eating challenges on GLP-1",
        "keywords": [
            "protein", "meal plan", "what i eat", "wieiad",
            "calorie", "macro", "fiber", "nutrition",
            "high protein", "protein goal", "protein intake",
            "eating on glp", "eating on ozempic", "diet with ozempic",
            "food aversion", "food noise", "appetite",
            "breakfast", "lunch", "dinner", "snack",
            "meal prep", "recipe", "food choice",
            "eat enough", "not eating enough", "under-eating",
            "nourish", "fuel", "hydration",
        ],
    },
    {
        "theme_id": "THM_08",
        "label": "Sustainability & Weight Regain Fears",
        "description": "Concerns about lifelong medication dependency, weight regain after stopping, exit strategies, long-term maintenance",
        "keywords": [
            "regain", "gained back", "bounce back", "weight back",
            "after stopping", "stop taking", "discontinue", "come off",
            "lifelong", "forever", "how long", "dependency",
            "sustainable", "maintain", "maintenance",
            "exit strategy", "long term", "permanent",
            "keep off", "keep the weight", "not sustainable",
            "yo-yo", "yoyo", "cycle",
        ],
    },
    {
        "theme_id": "THM_09",
        "label": "Indian Weight Loss Culture & Desi Diet",
        "description": "Indian-specific diet plans, vegetarian protein challenges, traditional food for weight loss, cultural eating patterns, desi fitness",
        "keywords": [
            "indian diet", "indian food", "indian meal", "indian cuisine",
            "vegetarian", "veg diet", "paneer", "dal", "roti", "phulka",
            "chapati", "rice", "ghee", "oil content",
            "desi", "hindi", "hinglish",
            "soya chunk", "tofu", "lentil", "chickpea",
            "idli", "dosa", "upma", "poha",
            "south indian", "north indian",
            "intermittent fasting", "keto indian",
            "indian gym", "indian fitness",
            "calorie deficit", "1500 calorie", "1200 calorie",
        ],
    },
    {
        "theme_id": "THM_10",
        "label": "Medical Science & GLP-1 Education",
        "description": "How GLP-1 works scientifically, clinical trial data, insulin resistance education, diabetes connection, doctor explanations",
        "keywords": [
            "how does", "how it works", "mechanism", "science",
            "clinical trial", "study", "research", "data shows",
            "insulin", "insulin resistance", "blood sugar", "glucose",
            "receptor agonist", "hormone", "peptide",
            "fda approved", "approved for", "type 2 diabetes",
            "endocrinologist", "obesity medicine", "medical",
            "gastric emptying", "satiety", "hunger hormone",
            "evidence", "proven", "clinical",
            "select trial", "cardiovascular", "heart",
        ],
    },
    {
        "theme_id": "THM_11",
        "label": "Obesity Epidemic & Systemic Food Issues",
        "description": "Ultra-processed food as root cause, food industry blame, obesity as systemic/societal problem, pharmaceutical industry dynamics",
        "keywords": [
            "ultra processed", "processed food", "junk food",
            "food industry", "food system", "capitalism",
            "addicted", "addiction", "overconsumption",
            "obesity rate", "obesity epidemic", "obesity crisis",
            "systemic", "root cause", "real problem",
            "pharmaceutical", "big pharma", "drug company",
            "novo nordisk", "eli lilly", "stock", "invest",
            "food environment", "modern food",
        ],
    },
    {
        "theme_id": "THM_12",
        "label": "PCOS, Hormones & Women's Health",
        "description": "PCOS-specific weight struggles, hormonal weight management, postpartum weight loss, menopause, women's unique challenges with weight",
        "keywords": [
            "pcos", "pcod", "polycystic",
            "hormone", "hormonal", "endocrine",
            "postpartum", "post-pregnancy", "after pregnancy", "after delivery",
            "menopause", "perimenopause", "menopausal",
            "thyroid", "hypothyroid", "hashimoto",
            "birth control", "contraceptive",
            "women", "female", "ladies",
            "period", "menstrual", "cycle",
            "fertility", "pregnant", "pregnancy",
            "insulin resistance women",
        ],
    },
]


def map_item_to_themes(item):
    """Map a single item to 0+ themes based on keyword matching."""
    text = item.get("content_text", "").lower()
    matched = []
    for theme in THEMES:
        score = sum(1 for k in theme["keywords"] if k in text)
        if score >= 1:
            matched.append({"theme_id": theme["theme_id"], "score": score})
    # Sort by score descending
    matched.sort(key=lambda x: x["score"], reverse=True)
    return [m["theme_id"] for m in matched]


# Map ALL items to themes
theme_items = {t["theme_id"]: [] for t in THEMES}
item_themes = {}  # item_id -> list of theme_ids
unthemed = []

for item in filtered:
    item_id = item["item_id"]
    themes = map_item_to_themes(item)
    if themes:
        item_themes[item_id] = themes
        for tid in themes:
            theme_items[tid].append(item_id)
    else:
        unthemed.append(item_id)

# Stats
print(f"Total items: {len(filtered)}")
print(f"Themed: {len(item_themes)} ({len(item_themes)*100//len(filtered)}%)")
print(f"Unthemed: {len(unthemed)} ({len(unthemed)*100//len(filtered)}%)")
print()
print("Theme breakdown:")
for theme in THEMES:
    tid = theme["theme_id"]
    count = len(theme_items[tid])
    pct = count * 100 / len(filtered)
    print(f"  {tid} [{theme['label'][:45]}]: {count} items ({pct:.1f}%)")

# Build theme objects with item lists
themes_output = []
for theme in THEMES:
    tid = theme["theme_id"]
    themes_output.append({
        "theme_id": tid,
        "label": theme["label"],
        "description": theme["description"],
        "keywords": theme["keywords"],
        "item_ids": theme_items[tid],
        "item_count": len(theme_items[tid]),
        "prevalence": round(len(theme_items[tid]) / len(filtered), 4),
    })

# Save intermediate results
(RUN_DIR / "analysis" / "themes_pass1.json").write_text(
    json.dumps(themes_output, indent=2, ensure_ascii=False), encoding="utf-8"
)
(RUN_DIR / "analysis" / "unthemed_ids.json").write_text(
    json.dumps(unthemed, indent=2), encoding="utf-8"
)
(RUN_DIR / "analysis" / "item_themes.json").write_text(
    json.dumps(item_themes, indent=2), encoding="utf-8"
)
print(f"\nSaved themes_pass1.json, unthemed_ids.json, item_themes.json")
