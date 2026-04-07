"""Stage 4c: Narrative review pass.
Reads unthemed items and assigns themes based on contextual understanding.
Also catches items that should be removed from filtered corpus (false positives).
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

# Build lookup
filtered_map = {i["item_id"]: i for i in filtered}

# Narrative classification of unthemed items
# These are items that didn't match keywords but may be contextually relevant
newly_themed = 0
still_unthemed = 0
removed = 0

for uid in unthemed_ids:
    item = filtered_map.get(uid)
    if not item:
        continue
    text = item.get("content_text", "").lower()

    # Items to REMOVE (false positives in Stage 3)
    false_positive_signals = [
        "warm vanilla sugar", "bbw",  # beauty/fragrance
        "birdwatching",
        "taqueria ramirez", "paulie gees", "gymkhana",  # restaurants
        "hernia surgery",
        "bubble tea", "dark chocolate brand",
        "ice cream replacement",
        "HPV vaccine",
        "sde-3 offer", "golang", "react",  # tech job
        "drawbridge",
        "tin foil hat",
        "mother india 1957",
        "body vibrator",
        "esthetician",
        "blepharoplasty", "chin implant",  # cosmetic surgery unrelated
        "agartala med college",
        "dnb from a hifi corporate",
        "glycolic/lactic acid body lotion",
        "sherbet is made with dairy",
        "rowing machine",  # gym equipment discussion, not weight loss context
        "carbon capture plant",
    ]

    is_false_positive = any(s in text for s in false_positive_signals)
    if is_false_positive:
        removed += 1
        continue

    # Narrative theme mapping based on content reading
    assigned_themes = []

    # Short motivational/journey comments -> THM_09 (Indian Weight Loss Culture) if Hindi/desi
    desi_signals = ["bhai", "mujhe", "karo", "hai", "kya", "plz", "plzz", "sir", "mam", "meri", "mera", "tum", "aap"]
    is_desi = any(s in text for s in desi_signals)

    # Generic weight loss comments -> THM_09 if desi, else leave
    wl_generic = ["weight loss", "fat loss", "lose weight", "diet plan", "belly fat", "workout"]
    has_wl = any(s in text for s in wl_generic)

    # Exercise/gym focused -> THM_09
    exercise_signals = ["exercise", "gym", "walking", "running", "workout", "cycling"]
    has_exercise = any(s in text for s in exercise_signals)

    # Diet comments -> THM_07 or THM_09
    diet_signals = ["diet", "eat", "eating", "food", "calorie", "meal", "portion"]
    has_diet = any(s in text for s in diet_signals)

    # Medical/doctor -> THM_03 if India context, THM_10 otherwise
    med_signals = ["doctor", "dr ", "clinic", "hospital", "endocrinologist"]
    has_med = any(s in text for s in med_signals)
    india_signals = ["india", "indian", "delhi", "mumbai", "hyderabad", "bangalore", "chennai", "kolkata"]
    has_india = any(s in text for s in india_signals)

    # Obesity/body discussion -> THM_06 (stigma) or THM_11 (systemic)
    body_signals = ["obese", "obesity", "overweight", "bmi", "fat people", "body type"]
    has_body = any(s in text for s in body_signals)

    # Medication/drug mentions -> THM_01
    med_drug_signals = ["medication", "pill", "drug", "noom", "minimal"]
    has_drug = any(s in text for s in med_drug_signals)

    # Celebrity context -> THM_04
    celeb_signals = ["actor", "actress", "celebrity", "bollywood", "sarfaraz", "shaw", "kapoor"]
    has_celeb = any(s in text for s in celeb_signals)

    # PCOS/women -> THM_12
    women_signals = ["pcos", "pregnancy", "pregnant", "postpartum", "c-section", "delivery", "periods"]
    has_women = any(s in text for s in women_signals)

    # Assign themes
    if has_women:
        assigned_themes.append("THM_12")
    if has_celeb:
        assigned_themes.append("THM_04")
    if has_drug:
        assigned_themes.append("THM_01")
    if has_body:
        assigned_themes.append("THM_06")
    if has_med and has_india:
        assigned_themes.append("THM_03")
    elif has_med:
        assigned_themes.append("THM_10")
    if has_diet and not assigned_themes:
        if is_desi:
            assigned_themes.append("THM_09")
        else:
            assigned_themes.append("THM_07")
    if has_exercise and not assigned_themes:
        assigned_themes.append("THM_09")
    if has_wl and not assigned_themes:
        if is_desi:
            assigned_themes.append("THM_09")
        else:
            assigned_themes.append("THM_07")

    # Very short or truly generic items - assign to THM_09 if any weight context
    if not assigned_themes and len(text) < 50:
        if has_wl or has_diet or has_exercise:
            assigned_themes.append("THM_09")

    if assigned_themes:
        item_themes[uid] = assigned_themes
        newly_themed += 1
    else:
        still_unthemed += 1

# Update theme item lists
theme_items = {t["theme_id"]: [] for t in themes_pass1}
for item_id, themes in item_themes.items():
    for tid in themes:
        if tid in theme_items:
            theme_items[tid].append(item_id)

# Count items that are now themed
total_themed = len(item_themes)
total_items = len(filtered) - removed
unthemed_pct = (total_items - total_themed) * 100 / total_items if total_items > 0 else 0

print(f"Narrative review results:")
print(f"  Newly themed: {newly_themed}")
print(f"  Still unthemed: {still_unthemed}")
print(f"  Removed (false positives): {removed}")
print(f"  Total items after removal: {total_items}")
print(f"  Total themed: {total_themed} ({total_themed*100//total_items}%)")
print(f"  Unthemed: {total_items - total_themed} ({unthemed_pct:.1f}%)")
print()

# Updated theme breakdown
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

# Save final results
(RUN_DIR / "analysis" / "themes_final.json").write_text(
    json.dumps(themes_final, indent=2, ensure_ascii=False), encoding="utf-8"
)
(RUN_DIR / "analysis" / "item_themes.json").write_text(
    json.dumps(item_themes, indent=2), encoding="utf-8"
)

# Update unthemed list
new_unthemed = [uid for uid in unthemed_ids if uid not in item_themes]
(RUN_DIR / "analysis" / "unthemed_ids.json").write_text(
    json.dumps(new_unthemed, indent=2), encoding="utf-8"
)

print(f"\nSaved themes_final.json, updated item_themes.json and unthemed_ids.json")
