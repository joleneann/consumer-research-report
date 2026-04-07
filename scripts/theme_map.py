"""Map all corpus items to themes using keyword patterns."""
import json
import sys
import re
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

run_dir = Path('runs/20260407_143544_98a8c6')
corpus = json.loads((run_dir / 'filtered' / 'corpus.json').read_text(encoding='utf-8'))

THEMES = {
    'THM_01_GREY_COVERAGE': {
        'label': 'Grey Hair Coverage',
        'description': 'Products and discussions about covering grey, white, or silver hair - the primary motivation for hair colour use in India',
        'keywords': [
            r'grey\s*hair|gray\s*hair|white\s*hair|silver\s*hair|safed\s*baal',
            r'grey\s*cover|gray\s*cover|cover.*grey|cover.*gray|cover.*white',
            r'root\s*touch|touch[\s-]*up|root.*cover|root.*conceal',
            r'hide.*grey|hide.*gray|hide.*white',
            r'premature.*grey|premature.*gray|early.*grey|early.*gray',
        ],
    },
    'THM_02_NATURAL_CHEMICAL_FREE': {
        'label': 'Natural & Chemical-Free Products',
        'description': 'Demand for henna-based, herbal, ammonia-free, organic, and ayurvedic hair colour alternatives',
        'keywords': [
            r'natural.*col|natural.*dye|natural.*hair\s*(col|dye)',
            r'chemical[\s-]*free|no[\s-]*chemical|without.*chemical|harsh.*chemical',
            r'ammonia[\s-]*free|no[\s-]*ammonia|without.*ammonia',
            r'organic|herbal|ayurved|plant[\s-]*based|botanical',
            r'paraben[\s-]*free|ppd[\s-]*free|sulph.*free|sulfat.*free',
            r'henna.*natural|natural.*henna|mehndi.*natural',
            r'homemade.*dye|homemade.*col|diy.*natural',
        ],
    },
    'THM_03_PRODUCT_EFFECTIVENESS': {
        'label': 'Product Effectiveness & Results',
        'description': 'Whether products deliver on claims - colour accuracy, coverage quality, actual vs promised results',
        'keywords': [
            r'works?\s*well|effective|not\s*work|doesn.t\s*work|didn.t\s*work',
            r'result|coverage|didn.t\s*cover|not\s*cover|full\s*cover',
            r'colour.*accurate|shade.*accurate|as\s*shown|as\s*described',
            r'claim|promise|expect|disappoint|deliver',
            r'waste.*money|waste.*product|useless|not\s*worth',
            r'excellent|amazing|superb|fantastic|pathetic|terrible|horrible',
        ],
    },
    'THM_04_EASE_CONVENIENCE': {
        'label': 'Ease of Use & Quick Application',
        'description': 'Convenience-focused products - shampoo-based colour, instant sticks, spray-on, 5-minute application',
        'keywords': [
            r'easy\s*to\s*(use|apply)|simple.*apply|convenient|hassle[\s-]*free',
            r'instant|quick|fast|5\s*min|10\s*min|minute',
            r'shampoo.*col|col.*shampoo|colour.*shampoo',
            r'spray|stick|pen|comb.*applicat|mess[\s-]*free|no[\s-]*mess',
            r'on[\s-]*the[\s-]*go|portable|carry|travel',
        ],
    },
    'THM_05_DAMAGE_SAFETY': {
        'label': 'Hair Damage & Safety Concerns',
        'description': 'Concerns about hair damage, dryness, allergic reactions, skin irritation, and chemical safety',
        'keywords': [
            r'damag|hair\s*fall|hair\s*loss|dry|drying|brittle|rough|breakage',
            r'allerg|reaction|irritat|burn|sting|itch|rash|swell',
            r'side\s*effect|harmful|danger|toxic|unsafe|safe\b',
            r'patch\s*test|sensitive|skin.*dark|skin.*stain|transfer',
            r'healthy|nourish|condition|gentle|mild',
        ],
    },
    'THM_06_PRICE_VALUE': {
        'label': 'Price & Value for Money',
        'description': 'Affordability assessments, salon vs home economics, product value evaluation',
        'keywords': [
            r'price|expensive|cheap|afford|value.*money|worth.*money',
            r'cost|budget|pocket[\s-]*friend|economi|overpriced',
            r'rupee|rs\b|inr|\u20b9|\$\d|deal|discount|offer|sale',
            r'salon.*expens|parlour.*expens|save.*money',
        ],
    },
    'THM_07_DIY_HOME_COLOUR': {
        'label': 'DIY & Home Hair Colouring',
        'description': 'At-home colour application experiences, techniques, brand recommendations for home use',
        'keywords': [
            r'at\s*home|home.*col|home.*dye|diy|self.*col|self.*dye',
            r'box.*dye|boxed.*dye|own.*hair',
            r'salon.*vs|vs.*salon|instead.*salon|without.*salon',
            r'myself|my\s*own|first\s*time.*dye|first\s*time.*col',
        ],
    },
    'THM_08_LONGEVITY_FADING': {
        'label': 'Colour Longevity & Fading',
        'description': 'How long colour lasts, fading issues, wash-out concerns, temporary vs permanent preferences',
        'keywords': [
            r'long[\s-]*lasting|last.*long|how\s*long|stays?.*long',
            r'fade|fading|faded|wash.*out|wash.*off|wear.*off',
            r'permanent|semi[\s-]*permanent|temporary|demi',
            r'maintain|maintenance|reapply|touch.*up.*frequen',
            r'weeks?.*last|months?.*last|days?.*last',
        ],
    },
    'THM_09_HENNA_TRADITIONAL': {
        'label': 'Henna & Traditional Hair Colouring',
        'description': 'Traditional henna/mehndi use for hair, indigo combinations, cultural practices, natural dyeing methods',
        'keywords': [
            r'\bhenna\b|mehndi|mehendi|mehandi',
            r'\bindigo\b.*hair|hair.*\bindigo\b',
            r'traditional.*dye|natural.*black.*hair|kattha|shikakai|amla.*hair',
            r'ayurved.*hair|herb.*hair.*col',
        ],
    },
    'THM_10_BEARD_MENS': {
        'label': 'Beard & Mens Grooming',
        'description': 'Men-specific hair and beard colour products, beard grey coverage, male grooming',
        'keywords': [
            r'beard.*col|beard.*dye|moustache.*col|mustache.*col',
            r'beard.*black|black.*beard|beard.*grey|grey.*beard',
            r'men.*hair.*col|hair.*col.*men|for\s*men\b',
            r'beard.*shampoo|beard.*touch',
        ],
    },
    'THM_11_BRAND_TRUST': {
        'label': 'Brand Experience & Trust',
        'description': 'Brand-specific experiences, brand loyalty, fake/counterfeit product complaints, brand recommendations',
        'keywords': [
            r'fake|counterfeit|duplicate|original|genuine|authentic',
            r'garnier|loreal|l.oreal|godrej|streax|paradyes|revlon',
            r'schwarzkopf|matrix|bigen|wella|clairol|kokila|nisha|indica',
            r'recommend.*brand|best.*brand|which.*brand|trust.*brand',
            r'scam|fraud|cheat|rip.*off|mislead',
        ],
    },
    'THM_12_TRENDS_EXPRESSION': {
        'label': 'Colour Trends & Self-Expression',
        'description': 'Creative/fashion hair colours, trends, personal expression, workplace concerns about unconventional colours',
        'keywords': [
            r'trend|fashion|style|bold|vibrant|creative|fun|experiment',
            r'purple|blue|pink|red\s*hair|copper|burgundy|mahogany|auburn|lavender|pastel',
            r'highlight|balayage|ombre|streak|lowlight',
            r'salon.*visit|transform|makeover|new\s*look',
            r'workplace|office|professional.*col',
        ],
    },
}

# Compile patterns
compiled_themes = {}
for theme_id, theme in THEMES.items():
    compiled_themes[theme_id] = [re.compile(p, re.IGNORECASE) for p in theme['keywords']]

# Map all items to themes
theme_items = defaultdict(list)
item_themes = {}

for item in corpus:
    text = item['content_text']
    item_id = item['item_id']
    matched_themes = []

    for theme_id, patterns in compiled_themes.items():
        for pat in patterns:
            if pat.search(text):
                matched_themes.append(theme_id)
                break

    item_themes[item_id] = matched_themes
    for t in matched_themes:
        theme_items[t].append(item_id)

# Stats
print('Theme mapping results:')
print(f'Total items: {len(corpus)}')
themed = sum(1 for v in item_themes.values() if len(v) > 0)
unthemed = sum(1 for v in item_themes.values() if len(v) == 0)
print(f'Themed: {themed} ({themed/len(corpus)*100:.1f}%)')
print(f'Unthemed: {unthemed} ({unthemed/len(corpus)*100:.1f}%)')
print()
for theme_id in sorted(THEMES.keys()):
    count = len(theme_items.get(theme_id, []))
    pct = count / len(corpus) * 100
    print(f'  {theme_id}: {THEMES[theme_id]["label"]:40s} n={count:5d} ({pct:.1f}%)')

# Save
import os
os.makedirs(str(run_dir / 'analysis'), exist_ok=True)
mapping_data = {
    'themes': {tid: {
        'theme_id': tid,
        'label': t['label'],
        'description': t['description'],
        'item_count': len(theme_items.get(tid, [])),
        'item_ids': theme_items.get(tid, []),
    } for tid, t in THEMES.items()},
    'item_themes': item_themes,
    'total_items': len(corpus),
    'themed_count': themed,
    'unthemed_count': unthemed,
}
(run_dir / 'analysis' / 'theme_mapping.json').write_text(
    json.dumps(mapping_data, indent=2), encoding='utf-8'
)
print('\nSaved theme_mapping.json')

# Print some unthemed items to check
unthemed_items = [item for item in corpus if len(item_themes.get(item['item_id'], [])) == 0]
print(f'\nSample unthemed items ({len(unthemed_items)} total):')
import random
random.seed(42)
for item in random.sample(unthemed_items, min(20, len(unthemed_items))):
    text = item['content_text'][:200].replace('\n', ' ')
    print(f'  [{item["source_platform"]}] {text}')
