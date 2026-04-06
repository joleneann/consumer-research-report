"""
Fix representative quotes: select genuinely representative, unique consumer voices
per theme instead of just the longest items.

Criteria:
1. Must be a COMMENT (real consumer voice), not a post/video description
2. Must strongly match the theme (multiple keyword hits, not just one)
3. Must not be reused across themes
4. Prefer medium length (50-500 chars) - long enough to be meaningful, short enough to be a genuine voice
5. Prefer items with engagement (upvotes/likes > 0)
"""
import io, sys, json, re
from pathlib import Path
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = Path(__file__).parent.parent  # scripts/ -> repo root

if len(sys.argv) > 1:
    RUN_DIR = ROOT / "runs" / sys.argv[1]
else:
    runs = sorted((ROOT / "runs").iterdir(), key=lambda p: p.name, reverse=True)
    RUN_DIR = runs[0]
print(f"Run directory: {RUN_DIR.name}")

# Load data
results = json.loads((RUN_DIR / "analysis" / "results.json").read_text(encoding="utf-8"))
corpus = json.loads((RUN_DIR / "filtered" / "corpus.json").read_text(encoding="utf-8"))
insights_data = json.loads((RUN_DIR / "insights" / "insights.json").read_text(encoding="utf-8"))
item_lookup = {i["item_id"]: i for i in corpus}

# Theme keyword definitions (same as stage4)
THEMES_KW = {
    "THM_001": ["ozempic", "mounjaro", "wegovy", "saxenda", "zepbound", "rybelsus",
                 "semaglutide", "tirzepatide", "liraglutide", "glp-1", "glp1",
                 "injection", "dose", "dosing"],
    "THM_002": ["side effect", "nausea", "vomit", "bloat", "sulphur burp", "sulfur burp",
                "fatigue", "constipat", "diarr", "gastroparesis", "pancreatit",
                "ozempic face", "hair loss", "hair fall", "muscle loss", "muscle mass",
                "gallbladder", "gallstone", "stomach pain", "acid reflux", "heartburn"],
    "THM_003": ["diet plan", "calorie deficit", "calorie count", "1500 calori",
                "meal plan", "meal prep", "roti", "chapati", "dal", "sabji",
                "paratha", "dosa", "idli", "poha", "upma", "khichdi",
                "tdee", "indian diet", "desi diet", "what i eat", "cheat meal"],
    "THM_004": ["gym", "workout", "exercise", "cardio", "running", "walk ",
                "yoga", "zumba", "weight training", "strength train",
                "deadlift", "squat", "treadmill", "hiit", "push up"],
    "THM_005": ["cost", "price", "expensive", "afford", "cheap", "insurance",
                "available in india", "pharmacy", "prescription",
                "off-label", "generic", "per month", "novo nordisk", "eli lilly"],
    "THM_006": ["transform", "before and after", "journey", "progress", "motivat",
                "glow up", "inspire", "fat to fit", "goal weight",
                "lost 10", "lost 15", "lost 20", "lost 30", "lost 5"],
    "THM_007": ["protein", "whey", "bcaa", "creatine", "fiber", "fibre",
                "vitamin", "b12", "iron", "omega", "collagen",
                "nutrition", "supplement", "amino"],
    "THM_008": ["pcos", "pcod", "thyroid", "insulin resist", "hormone", "hormonal",
                "endocrin", "metformin", "pregnan", "postpartum",
                "diabetes", "diabetic", "blood sugar", "cortisol"],
    "THM_009": ["ayurved", "ayush", "homeopath", "herbal", "home remed",
                "detox", "green tea", "apple cider", "lemon water", "jeera water",
                "amla", "turmeric", "haldi", "triphala", "ashwagandha",
                "herbalife", "natural remed", "desi dawa"],
    "THM_010": ["bariatric", "gastric bypass", "gastric sleeve", "sleeve gastrectomy",
                "liposuction", "surgery", "surgeon", "post-op"],
    "THM_011": ["intermittent fasting", "fasting", "16:8", "18:6", "omad",
                "one meal a day", "eating window", "water fast"],
    "THM_012": ["junk food", "processed food", "ultra-processed", "fast food",
                "food addict", "food industry", "sugar addict", "crav",
                "binge", "emotional eat", "food noise", "maida"],
}


def theme_relevance_score(text, theme_id):
    """Count how many keywords from this theme match the text."""
    lower = text.lower()
    return sum(1 for kw in THEMES_KW.get(theme_id, []) if kw in lower)


def quote_quality_score(item, theme_id):
    """Score an item's suitability as a representative quote for a theme."""
    text = item["content_text"]
    score = 0

    # Prefer comments over posts (real consumer voices)
    if item["content_type"] == "comment":
        score += 20

    # Prefer medium length (50-500 chars)
    length = len(text)
    if 80 <= length <= 500:
        score += 15
    elif 50 <= length <= 800:
        score += 10
    elif length > 800:
        score += 2  # too long = probably a post/description, not a voice
    elif length < 50:
        score += 3  # too short

    # Theme keyword relevance (more matches = more representative)
    relevance = theme_relevance_score(text, theme_id)
    score += relevance * 5

    # Prefer items with engagement
    meta = item.get("platform_metadata", {})
    if meta:
        eng = meta.get("score") or meta.get("like_count") or 0
        if eng > 10:
            score += 10
        elif eng > 3:
            score += 5

    # Penalise YouTube video descriptions (often just SEO keywords)
    if item["source_platform"] == "youtube" and item["content_type"] == "post":
        score -= 15

    # Penalise if it looks like promotional/influencer content
    promo_signals = ["link in bio", "subscribe", "follow for more", "comment recipe",
                     "dm me", "use code", "affiliate", "sponsored"]
    if any(p in text.lower() for p in promo_signals):
        score -= 10

    return score


# Track used quotes globally to avoid repeats
used_item_ids = set()

print("Selecting representative quotes per theme...\n")

for theme in results["themes"]:
    theme_id = theme["theme_id"]
    supporting_ids = theme["supporting_item_ids"]

    # Score all items in this theme
    candidates = []
    for sid in supporting_ids:
        item = item_lookup.get(sid)
        if not item:
            continue
        if sid in used_item_ids:
            continue  # already used in another theme

        q_score = quote_quality_score(item, theme_id)
        candidates.append((q_score, item))

    # Sort by quality score descending
    candidates.sort(key=lambda x: x[0], reverse=True)

    # Pick top 3
    selected = []
    for q_score, item in candidates:
        if len(selected) >= 3:
            break
        selected.append(item)
        used_item_ids.add(item["item_id"])

    # Build quote objects
    new_quotes = []
    for item in selected:
        txt = item["content_text"].strip()
        # Trim to 300 chars at a sentence boundary if too long
        if len(txt) > 350:
            # Find last sentence end before 300
            for end in [". ", "! ", "? "]:
                idx = txt[:350].rfind(end)
                if idx > 100:
                    txt = txt[:idx+1]
                    break
            else:
                txt = txt[:300] + "..."

        new_quotes.append({
            "text": txt,
            "source_platform": item["source_platform"],
            "source_url": item["source_url"],
            "item_id": item["item_id"],
            "selection_reason": f"High theme-relevance consumer voice (quality score: {quote_quality_score(item, theme_id)})",
        })

    theme["representative_quotes"] = new_quotes

    print(f"{theme_id}: {theme['theme_label']}")
    for i, q in enumerate(new_quotes):
        print(f"  Q{i+1}. [{q['source_platform']:10}] {q['text'][:120]}")
    print()

# Save updated analysis results
(RUN_DIR / "analysis" / "results.json").write_text(
    json.dumps(results, indent=2, default=str), encoding="utf-8"
)
print("Updated analysis/results.json")

# Also update insights quotes to match
for ins in insights_data:
    theme_id = ins["supporting_theme_ids"][0]
    theme = next((t for t in results["themes"] if t["theme_id"] == theme_id), None)
    if theme:
        ins["representative_quotes"] = theme["representative_quotes"]

(RUN_DIR / "insights" / "insights.json").write_text(
    json.dumps(insights_data, indent=2, default=str), encoding="utf-8"
)
print("Updated insights/insights.json")
