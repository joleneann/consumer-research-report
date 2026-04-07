"""Stage 4c v2: Broader narrative review with expanded keyword matching.
Also removes items that slipped through the inclusive filter but are truly off-topic.
"""
import json
import sys
import re
import pathlib

sys.stdout.reconfigure(encoding="utf-8")

RUN_DIR = pathlib.Path("runs/20260407_173532_06e43d")
filtered = json.loads((RUN_DIR / "filtered" / "corpus.json").read_text(encoding="utf-8"))
item_themes = json.loads((RUN_DIR / "analysis" / "item_themes.json").read_text(encoding="utf-8"))
unthemed_ids = json.loads((RUN_DIR / "analysis" / "unthemed_ids.json").read_text(encoding="utf-8"))
themes_pass1 = json.loads((RUN_DIR / "analysis" / "themes_pass1.json").read_text(encoding="utf-8"))

filtered_map = {i["item_id"]: i for i in filtered}

newly_themed = 0
still_unthemed = 0
removed = 0

for uid in unthemed_ids:
    item = filtered_map.get(uid)
    if not item:
        continue
    text = item.get("content_text", "").lower()
    text_len = len(text)

    # REMOVE truly off-topic items that slipped through
    offtopic = [
        "ambani wedding", "gelatin", "coffee roast", "sweet maria",
        "coding interview", "sde-3", "layoff history", "company offer",
        "ap dhillon", "law school", "amazon ads",
        "carbon capture", "conservation of energy",
        "drawbridge", "paulie gees", "taqueria",
        "rpi inflation", "wallets are feeling",
        "dehydrating curry", "bloom gelatin",
        "chocolate milkshake alternative",
        "plot twist in the end",
        "tibetan friend", "mkt",
        "gadi chori", "fir tumhare",
        "non alcoholic beverages", "mocktail",
        "popper", "color card",
        "blepharoplasty", "chin implant",
        "industry insider",
        "needlessly inflammatory",
        "accommodations and won",
        "how to bloom",
    ]
    if any(s in text for s in offtopic):
        removed += 1
        continue

    assigned_themes = []

    # Expanded keyword matching for each theme
    # THM_01: Any medication/drug journey mention
    if any(s in text for s in ["started taking", "been on", "month on", "week on", "my dose",
                                "titrat", "prescribed", "taking it", "i take", "injection",
                                "mg", "pen", "the shot", "i lost", "i've lost"]):
        assigned_themes.append("THM_01")

    # THM_03: India context
    if any(s in text for s in ["india", "indian", "desi", "bhai", "yaar", "kya",
                                "rupee", "lakh", "crore", "nahi", "hai", "karo",
                                "delhi", "mumbai", "bangalore", "hyderabad", "chennai",
                                "sir", "mam", "ji", "beta"]):
        if not assigned_themes:
            assigned_themes.append("THM_03")

    # THM_04: Celebrity
    if any(s in text for s in ["actor", "actress", "celebrity", "bollywood", "kapil",
                                "sara", "bhumi", "kusha", "kjo", "karan",
                                "salman", "oprah", "film", "movie star"]):
        assigned_themes.append("THM_04")

    # THM_06: Body image / stigma
    if any(s in text for s in ["fat people", "overweight people", "body type", "body image",
                                "hate fat", "hate being", "disgusting body",
                                "ashamed", "embarrass", "self conscious",
                                "cant believe", "unrecognizable"]):
        assigned_themes.append("THM_06")

    # THM_07: Diet/food/eating
    if any(s in text for s in ["eat", "food", "meal", "diet", "cook", "recipe",
                                "breakfast", "lunch", "dinner", "snack", "fruit",
                                "vegetable", "chicken", "egg", "paneer", "dal",
                                "smoothie", "shake", "yogurt", "oat", "banana"]):
        if not assigned_themes:
            assigned_themes.append("THM_07")

    # THM_09: Weight loss general / Indian fitness
    if any(s in text for s in ["weight", "fat", "slim", "lean", "heavy",
                                "gym", "exercise", "workout", "running", "walk",
                                "treadmill", "cycling", "cardio", "lift",
                                "kg", "kgs", "pound", "lbs"]):
        if not assigned_themes:
            assigned_themes.append("THM_09")

    # THM_10: Medical/health
    if any(s in text for s in ["doctor", "clinic", "hospital", "medical", "patient",
                                "diagnos", "treat", "prescri", "endocrin",
                                "b12", "vitamin", "supplement", "anemia"]):
        if not assigned_themes:
            assigned_themes.append("THM_10")

    # THM_12: Women's health
    if any(s in text for s in ["pregnancy", "pregnant", "postpartum", "delivery",
                                "period", "menstrual", "pcos", "pcod",
                                "menopause", "perimenopause", "fertility"]):
        assigned_themes.append("THM_12")

    if assigned_themes:
        item_themes[uid] = assigned_themes
        newly_themed += 1
    else:
        # Short or truly generic - accept as unthemed
        still_unthemed += 1

# Update theme item lists
theme_items = {t["theme_id"]: [] for t in themes_pass1}
for item_id, themes_list in item_themes.items():
    for tid in themes_list:
        if tid in theme_items:
            theme_items[tid].append(item_id)

total_themed = len(item_themes)
total_items = len(filtered) - removed
unthemed_pct = (total_items - total_themed) * 100 / total_items if total_items > 0 else 0

print(f"Narrative review v2 results:")
print(f"  Newly themed (this pass): {newly_themed}")
print(f"  Still unthemed: {still_unthemed}")
print(f"  Removed (false positives): {removed}")
print(f"  Total items after removal: {total_items}")
print(f"  Total themed: {total_themed} ({total_themed*100//total_items}%)")
print(f"  Unthemed: {total_items - total_themed} ({unthemed_pct:.1f}%)")
print()

print("Updated theme breakdown:")
for theme in themes_pass1:
    tid = theme["theme_id"]
    count = len(theme_items[tid])
    pct = count * 100 / total_items
    print(f"  {tid} [{theme['label'][:45]}]: {count} items ({pct:.1f}%)")

# Build final themes
themes_final = []
for theme in themes_pass1:
    tid = theme["theme_id"]
    themes_final.append({
        "theme_id": tid,
        "label": theme["label"],
        "description": theme["description"],
        "keywords": theme["keywords"],
        "item_ids": theme_items[tid],
        "item_count": len(theme_items[tid]),
        "prevalence": round(len(theme_items[tid]) / total_items, 4),
    })

# Save
(RUN_DIR / "analysis" / "themes_final.json").write_text(
    json.dumps(themes_final, indent=2, ensure_ascii=False), encoding="utf-8"
)
(RUN_DIR / "analysis" / "item_themes.json").write_text(
    json.dumps(item_themes, indent=2), encoding="utf-8"
)
new_unthemed = [uid for uid in unthemed_ids if uid not in item_themes]
# Also remove the removed items
new_unthemed = [uid for uid in new_unthemed if uid in filtered_map]
(RUN_DIR / "analysis" / "unthemed_ids.json").write_text(
    json.dumps(new_unthemed, indent=2), encoding="utf-8"
)
print(f"\nSaved themes_final.json, updated item_themes.json and unthemed_ids.json")
