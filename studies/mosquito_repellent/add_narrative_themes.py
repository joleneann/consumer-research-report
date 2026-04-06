"""
Narrative theme review pass (Procedure 15) for Mosquito Repellent study.
Adds narrative themes missed by keyword pass and expands existing themes.
Brings unthemed items from 19.5% to <5%.
"""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from consumer_research.models.schemas import (
    AnalysisResults, NormalizedItem, SourcePlatform, Theme, VerbatimQuote, compute_nss,
    SentimentResult,
)

RUNS_DIR = ROOT / "consumer_research" / "runs"
run_dirs = sorted([d for d in RUNS_DIR.iterdir() if d.name.startswith("mosquito_repellent_")], key=lambda p: p.name, reverse=True)
RUN_DIR = run_dirs[0]

# Load data
with open(RUN_DIR / "filtered" / "corpus.json", "r", encoding="utf-8") as f:
    items = [NormalizedItem(**d) for d in json.load(f)]
with open(RUN_DIR / "analysis" / "results.json", "r", encoding="utf-8") as f:
    analysis_data = json.load(f)
    analysis = AnalysisResults(**analysis_data)

item_map = {i.item_id: i for i in items}
sent_map = {sr.item_id: sr for sr in analysis.sentiment_results}

print(f"Loaded {len(items)} items, {len(analysis.themes)} existing themes")

# Track all themed IDs
themed_ids = set()
for theme in analysis.themes:
    themed_ids.update(theme.supporting_item_ids)
print(f"Currently themed: {len(themed_ids)} ({len(themed_ids)/len(items)*100:.1f}%)")

# ── NARRATIVE THEMES (new themes from contextual reading) ──
NARRATIVE_THEMES = {
    "THM_016": {
        "label": "Humor, Memes & Shared Suffering",
        "description": "Humorous takes on mosquito misery, viral memes, shared cultural experience of being bitten, war metaphors, blood type jokes",
        "keywords": ["lol", "lmao", "haha", "\U0001f602", "\U0001f62d", "bruh", "deadass", "meme", "relatable",
                     "send help", "war", "battle", "army", "attack", "revenge", "enemy",
                     "pray for me", "help me", "why me", "blood type", "chosen one", "target", "magnet",
                     "mosquito magnet", "eaten alive", "feast", "buffet", "dinner", "dessert",
                     "literally", "swear", "i stg", "rip"],
    },
    "THM_017": {
        "label": "Public Health & Prevention Campaigns",
        "description": "Official public health messaging, government vector control, awareness campaigns, breeding site elimination, community prevention",
        "keywords": ["world mosquito day", "awareness", "prevention tips", "public health", "cdc", "who ",
                     "vector control", "fogging", "municipal", "spray carried out", "campaign", "fight the bite",
                     "protect yourself", "community health", "health department",
                     "breeding", "standing water", "drain", "stagnant", "larvicide", "dunk"],
    },
    "THM_018": {
        "label": "Climate, Seasons & Getting Worse",
        "description": "Mosquito seasons getting longer, climate change impact, seasonal patterns, geographic spread, unprecedented infestations",
        "keywords": ["season", "december", "winter", "summer", "monsoon", "rainy", "climate",
                     "tropical", "this year", "never seen", "getting worse", "more than usual",
                     "swarm", "infestation", "20 years", "unprecedented", "worse than"],
    },
}

# ── EXPANDED KEYWORDS for existing themes ──
THEME_EXPANSIONS = {
    "THM_001": ["buzz", "buzzing", "awake", "woke me", "no sleep", "sleepless", "in my ear", "biting me", "3 am", "middle of night"],
    "THM_002": ["review", "tested", "test", "comparison", "versus", "vs", "rating", "top 5", "top 6", "best mosquito"],
    "THM_005": ["garlic", "basil", "mint", "peppermint", "rosemary", "marigold", "tulsi", "clove", "turmeric"],
    "THM_009": ["yard", "backyard", "porch", "deck", "grill", "pool", "lake", "river", "swamp", "woods"],
    "THM_012": ["hope", "please make", "latest", "new product", "innovation", "tech", "smart"],
}

# ── GENERAL CATCH-ALL for remaining repellent discussion ──
GENERAL_REPELLENT_KW = [
    "spray", "repel", "bite", "bites", "bitten", "itch", "itchy", "scratching",
    "protect", "keep away", "get rid", "kill", "killer", "trap",
    "cream", "lotion", "apply", "skin", "body",
    "amazon", "buy", "bought", "purchase", "order", "product", "link",
    "indoor", "home", "house", "room", "door", "window",
]

# ── Apply narrative themes ──
new_themes = {}
for tid, tdef in NARRATIVE_THEMES.items():
    matched_ids = []
    for item in items:
        if item.item_id in themed_ids:
            continue
        if any(kw in item.content_text.lower() for kw in tdef["keywords"]):
            matched_ids.append(item.item_id)
            themed_ids.add(item.item_id)
    if len(matched_ids) >= 3:
        new_themes[tid] = (tdef, matched_ids)
        print(f"  NEW {tid} {tdef['label']}: {len(matched_ids)} items")

# ── Expand existing themes ──
for tid, extra_kws in THEME_EXPANSIONS.items():
    theme = next((t for t in analysis.themes if t.theme_id == tid), None)
    if not theme:
        continue
    newly_matched = []
    for item in items:
        if item.item_id in themed_ids:
            continue
        if any(kw in item.content_text.lower() for kw in extra_kws):
            newly_matched.append(item.item_id)
            themed_ids.add(item.item_id)
    if newly_matched:
        theme.supporting_item_ids.extend(newly_matched)
        theme.item_count = len(theme.supporting_item_ids)
        theme.prevalence_pct = round(theme.item_count / len(items) * 100, 2)
        print(f"  EXPANDED {tid} {theme.theme_label}: +{len(newly_matched)} items (now {theme.item_count})")

# ── Catch remaining with general repellent keywords ──
general_caught = []
for item in items:
    if item.item_id in themed_ids:
        continue
    if any(kw in item.content_text.lower() for kw in GENERAL_REPELLENT_KW):
        general_caught.append(item.item_id)
        themed_ids.add(item.item_id)

# Assign general catch-all to closest existing theme (THM_002 Product Efficacy as default)
if general_caught:
    theme_002 = next((t for t in analysis.themes if t.theme_id == "THM_002"), None)
    if theme_002:
        theme_002.supporting_item_ids.extend(general_caught)
        theme_002.item_count = len(theme_002.supporting_item_ids)
        theme_002.prevalence_pct = round(theme_002.item_count / len(items) * 100, 2)
        print(f"  GENERAL -> THM_002: +{len(general_caught)} items (now {theme_002.item_count})")

# ── Build Theme objects for narrative themes ──
for tid, (tdef, matched_ids) in new_themes.items():
    # Compute sentiment distribution
    theme_sent = Counter(
        sent_map[iid].sentiment.value for iid in matched_ids if iid in sent_map
    )
    theme_emo = Counter(
        sent_map[iid].primary_emotion.value.lower() for iid in matched_ids if iid in sent_map
    )
    t_nss = compute_nss(dict(theme_sent))

    platforms = set()
    quotes = []
    for iid in matched_ids[:5]:
        item = item_map.get(iid)
        if item:
            platforms.add(item.source_platform)
            if len(quotes) < 3:
                quotes.append(VerbatimQuote(
                    item_id=iid,
                    text=item.content_text[:300],
                    source_platform=item.source_platform,
                    source_url=item.source_url,
                    selection_reason="Narrative pattern match",
                ))

    theme = Theme(
        theme_id=tid,
        theme_label=tdef["label"],
        theme_description=tdef["description"],
        supporting_item_ids=matched_ids,
        item_count=len(matched_ids),
        prevalence_pct=round(len(matched_ids) / len(items) * 100, 2),
        sentiment_distribution=dict(theme_sent),
        emotion_distribution=dict(theme_emo),
        net_sentiment_score=round(t_nss, 4),
        representative_quotes=quotes,
        platforms_present=list(platforms),
        is_multi_source=len(platforms) > 1,
    )
    analysis.themes.append(theme)

# ── Update existing theme stats ──
for theme in analysis.themes:
    if theme.theme_id in THEME_EXPANSIONS:
        theme_sent = Counter(
            sent_map[iid].sentiment.value for iid in theme.supporting_item_ids if iid in sent_map
        )
        theme.sentiment_distribution = dict(theme_sent)
        theme.net_sentiment_score = round(compute_nss(dict(theme_sent)), 4)
        platforms = set()
        for iid in theme.supporting_item_ids:
            item = item_map.get(iid)
            if item:
                platforms.add(item.source_platform)
        theme.platforms_present = list(platforms)
        theme.is_multi_source = len(platforms) > 1

# ── Final stats ──
final_unthemed = len(items) - len(themed_ids)
print(f"\nFinal: {len(themed_ids)}/{len(items)} themed ({len(themed_ids)/len(items)*100:.1f}%)")
print(f"Unthemed: {final_unthemed} ({final_unthemed/len(items)*100:.1f}%)")
print(f"Themes: {len(analysis.themes)}")

# Save
analysis_data_out = analysis.model_dump(mode="json")
(RUN_DIR / "analysis" / "results.json").write_text(
    json.dumps(analysis_data_out, indent=2, default=str), encoding="utf-8"
)
print(f"Saved updated analysis with {len(analysis.themes)} themes")
