"""Re-run Stage 3 with a more inclusive filter.
The study is about weight loss medication in India - keep ALL items that are
part of weight loss, health, diet, fitness, or medical conversations.
Only reject items that are clearly off-topic (airports, cricket, cars, etc.)
"""
import json
import sys
import re
import pathlib

sys.stdout.reconfigure(encoding="utf-8")

RUN_DIR = pathlib.Path("runs/20260407_173532_06e43d")
corpus = json.loads((RUN_DIR / "normalized" / "corpus.json").read_text(encoding="utf-8"))

# OFF-TOPIC: only reject items with strong off-topic signals AND no health context
offtopic_phrases = [
    "airport terminal", "rolls royce", "flight booking", "delta points", "skymiles",
    "ipl match", "cricket score", "election result", "vote chori", "evm machine",
    "real estate price", "property market", "mutual fund return",
    "hair care product review", "skincare routine step", "fragrance collection",
    "car review", "automobile",
    "metro construction", "traffic jam", "pollution checkup centre",
    "missing persons case", "mock drill scheduled",
    "jungkook exhibition", "bts army",
    "hypothecation termination", "rto office",
    "bridal lingerie", "lehenga shopping",
    "coding interview", "sde-3 offer", "golang react",
    "brics presidency", "external affairs minister",
    "pride march", "queer-trans",
    "halwara airport", "visakhapatnam airport",
    "atithi restaurant anniversary",
    "rolls royce lined up",
    "delhi cars",
    "meharchand market delhi",
]

# Health/weight context signals - if ANY of these present, keep the item
health_signals = [
    "weight", "diet", "food", "eat", "meal", "calorie", "protein", "carb", "sugar",
    "fat", "gym", "exercise", "workout", "fitness", "health", "body", "muscle",
    "obese", "obesity", "overweight", "bmi", "slim", "thin", "lean",
    "doctor", "medical", "medicine", "drug", "pill", "injection", "treatment",
    "ozempic", "mounjaro", "wegovy", "semaglutide", "tirzepatide", "glp",
    "ayurved", "homeopath", "natural remedy",
    "diabetes", "insulin", "pcos", "thyroid", "hormone",
    "nutrition", "supplement", "vitamin", "mineral",
    "cooking", "recipe", "kitchen", "vegetarian", "vegan", "non-veg",
    "paneer", "dal", "roti", "rice", "ghee", "oil",
    "bollywood", "actor", "actress", "celebrity", "kapil", "sara", "bhumi",
    "transformation", "journey", "before and after", "progress",
    "stomach", "appetite", "hunger", "craving", "nausea",
    "surgery", "bariatric", "liposuction",
    "lose", "gain", "lost", "gained", "burn",
    "fasting", "keto", "intermittent",
    "herbalife", "amway", "nutrilite",
    "skin", "acne", "hair loss",  # can be medication side effects
]

relevant = []
rejected = []

for item in corpus:
    text = item.get("content_text", "").lower()
    text_len = len(text)

    # Skip truly empty/useless items
    if text_len < 10:
        rejected.append({**item, "_rejection_reason": "Too short (<10 chars)"})
        continue

    # Check if item has ANY health/weight context
    has_health = any(k in text for k in health_signals)

    # Check for strong off-topic
    is_offtopic = any(k in text for k in offtopic_phrases)

    if has_health and not is_offtopic:
        relevant.append(item)
    elif is_offtopic and not has_health:
        rejected.append({**item, "_rejection_reason": "Off-topic content"})
    elif is_offtopic and has_health:
        # Has both - keep it (health context takes priority)
        relevant.append(item)
    else:
        # No health signal and no off-topic - check length
        # Short items with no signals are noise
        if text_len < 50:
            rejected.append({**item, "_rejection_reason": "Short with no relevant context"})
        else:
            # Longer items without explicit signals - keep them
            # They may be contextual comments in relevant threads
            relevant.append(item)

print(f"Total: {len(corpus)}")
print(f"Relevant: {len(relevant)} ({len(relevant)*100//len(corpus)}%)")
print(f"Rejected: {len(rejected)} ({len(rejected)*100//len(corpus)}%)")

for p in ["reddit", "instagram", "youtube"]:
    r = sum(1 for i in relevant if i.get("source_platform") == p)
    j = sum(1 for i in rejected if i.get("source_platform") == p)
    print(f"  {p}: {r} relevant, {j} rejected")

# Save
(RUN_DIR / "filtered").mkdir(exist_ok=True)
(RUN_DIR / "filtered" / "corpus.json").write_text(
    json.dumps(relevant, indent=2, default=str, ensure_ascii=False), encoding="utf-8"
)
(RUN_DIR / "filtered" / "rejected.json").write_text(
    json.dumps(rejected, indent=2, default=str, ensure_ascii=False), encoding="utf-8"
)
print("Saved filtered/corpus.json and filtered/rejected.json")
