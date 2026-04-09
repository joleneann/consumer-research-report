"""Narrative review pass: expand theme mapping to reduce unthemed items below 10%."""
import json, re, sys
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

RUN_DIR = Path('runs/20260407_184943_08eb92')
corpus = json.loads((RUN_DIR / 'filtered/corpus.json').read_text(encoding='utf-8'))
themes_data = json.loads((RUN_DIR / 'analysis/themes_pass1.json').read_text(encoding='utf-8'))

# Additional keyword patterns discovered from narrative review of unthemed items
EXTRA_KEYWORDS = {
    "THM_01": [
        # India makes nothing / India makes everything rebuttals
        r'india\s+makes\s+nothing', r'india.*(?:makes|produces|manufactures)\s+(?:nothing|everything)',
        r'(?:make|makes)\s+in\s+india\b', r'made\s+in\s+india\b',
        r'MakeInIndia', r'#MakeInIndia', r'#MadeinIndia',
        r'MII\b.*(?:success|fail)', r'make\s+in\s+india\s+(?:2025|2024|2026)',
        r'(?:factory|manufacturing).*(?:india|bharat).*(?:success|fail|work)',
        r'india.*(?:not|never).*(?:manufactur|industriali[sz])',
        r'(?:manufactur|industriali[sz]).*(?:india|bharat)',
        r'modi.*(?:make\s+in|manufactur|industrial)',
        r'(?:make\s+in|manufactur|industrial).*modi',
        r'self\s+relian', r'self-relian',
        r'(?:india|bharat).*(?:self.*relian|atmanirbhar)',
        r'(?:india|indian).*(?:capable|incapable).*manufactur',
    ],
    "THM_03": [
        # Boycott patterns, nationalist buying
        r'dabur.*(?:nationali|american|colgate)',
        r'(?:nationalism|patriot).*(?:buy|brand|product|consume)',
        r'(?:buy|brand|product|consume).*(?:nationalism|patriot)',
        r'(?:shun|reject|dump|ditch).*(?:american|foreign|import)',
        r'desi\s+(?:product|alternative|option)',
        r'(?:indian|desi)\s+(?:product|brand).*(?:available|alternative)',
        r'(?:festive|diwali|holi).*(?:desi|local|indian|swadeshi)',
    ],
    "THM_04": [
        # India vs China broader patterns
        r'(?:india|indian).*(?:dumping|flooded|cheap).*(?:chinese|china)',
        r'(?:china|chinese).*(?:dump|flood|cheap).*(?:india|indian)',
        r'dumping\s+ground', r'flooded.*(?:market|product)',
        r'(?:ban|restrict).*(?:chinese|china).*(?:product|import|goods)',
        r'(?:india|indian).*vs\s+(?:vietnam|bangladesh|china)',
        r'(?:china|chinese|vietnam|bangladesh).*(?:india|indian).*(?:manufactur|trade|export)',
    ],
    "THM_05": [
        # Broader quality patterns
        r'(?:india|indian).*(?:3rd\s+rate|third\s+rate|cheap|shoddy|subpar)',
        r'(?:fizzle|fake|scam|fraud).*(?:made\s+in\s+india|indian\s+product)',
        r'(?:india|indian).*(?:brand|product).*(?:quality|trust|reliable|durable)',
        r'(?:relabel|white.*label|copy|fake|counterfeit).*(?:india|indian|china|chinese)',
    ],
    "THM_07": [
        # Broader brand ecosystem
        r'(?:india|indian).*(?:brand|company).*(?:global|world|international|compet)',
        r'(?:tata|mahindra|reliance|bajaj).*(?:own|reviv|bought|acquir)',
        r'(?:indian|desi|homegrown).*(?:brand|startup|company).*(?:grow|rise|emerg)',
        r'(?:pharma|IT|software|diamond|textile).*(?:india|indian).*(?:export|global|world)',
        r'(?:india|indian).*(?:pharma|IT|software|diamond|textile).*(?:export|global|world)',
        r'(?:patanjali|boat|mamaearth|darkins|shopdibz)',
        r'(?:indian|desi)\s+(?:watch|car|bike|shoe|beauty|skincare|food)',
    ],
    "THM_08": [
        # Broader economic patterns
        r'(?:india|indian|bharat).*(?:economy|economic).*(?:golden|boom|growth|surge|rise)',
        r'(?:economy|economic).*(?:india|indian|bharat)',
        r'(?:india|indian).*(?:trillion|billion).*(?:economy|trade|export|import)',
        r'(?:fiscal|monetary|current\s+account).*(?:india|deficit)',
        r'(?:india|indian).*(?:fiscal|current\s+account)',
        r'(?:india|bharat).*(?:milestone|achievement|record)',
        r'(?:milestone|achievement|record).*(?:india|bharat)',
        r'(?:india|indian).*(?:industriali[sz]|not\s+industriali)',
        r'consumer\s+economy.*(?:manufactur|india)',
    ],
    "THM_09": [
        # Broader trade war patterns
        r'(?:ford|tesla|apple|amazon).*(?:invest|billion|million).*india',
        r'(?:india|indian).*(?:ford|tesla).*(?:invest)',
        r'(?:US|america|american).*(?:brand|product|company).*(?:india|indian)',
        r'(?:india|indian).*(?:US|america|american).*(?:brand|product)',
    ],
    "THM_10": [
        # Assembly patterns
        r'(?:100%|all\s+parts|component|design).*(?:india|here|local)',
        r'(?:india|here|local).*(?:100%|all\s+parts|component|design)',
        r'(?:start|begin).*(?:manufactur|making).*(?:india|here|local)',
    ],
    "THM_11": [
        # Broader infrastructure
        r'(?:india|indian|bharat).*(?:5G|broadband|digital|connectivity)',
        r'(?:india|indian).*(?:renewable|solar|wind|nuclear|energy)',
        r'(?:renewable|solar|energy).*(?:india|indian)',
        r'(?:india|indian).*(?:cyber\s+city|industrial\s+park|SEZ|special\s+economic)',
    ],
    "THM_12": [
        # Broader employment
        r'(?:india|indian).*(?:worker|labour|labor|wage|salary|hiring)',
        r'(?:worker|labour|labor|wage|salary).*(?:india|indian)',
        r'(?:india|indian).*(?:H1B|H-1B|visa|outsourc|offshoring)',
    ],
}


# Rebuild theme-item mapping with expanded keywords
item_themes = {iid: list(tlist) for iid, tlist in themes_data['item_themes'].items()}

for item in corpus:
    iid = item['item_id']
    text = item['content_text']
    existing = set(item_themes.get(iid, []))

    for theme_id, patterns in EXTRA_KEYWORDS.items():
        if theme_id not in existing:
            for pat in patterns:
                if re.search(pat, text, re.IGNORECASE):
                    if iid not in item_themes:
                        item_themes[iid] = []
                    item_themes[iid].append(theme_id)
                    existing.add(theme_id)
                    break

# Recount
theme_counts = defaultdict(list)
unthemed = 0
for item in corpus:
    iid = item['item_id']
    tlist = item_themes.get(iid, [])
    if tlist:
        for t in tlist:
            theme_counts[t].append(iid)
    else:
        unthemed += 1

print(f"Total items: {len(corpus)}")
print(f"Themed: {len(corpus) - unthemed} ({(len(corpus) - unthemed)/len(corpus)*100:.1f}%)")
print(f"Unthemed: {unthemed} ({unthemed/len(corpus)*100:.1f}%)")
print()

THEME_LABELS = {t['theme_id']: t['label'] for t in themes_data['themes']}
for tid in sorted(theme_counts.keys()):
    count = len(theme_counts[tid])
    pct = count / len(corpus) * 100
    label = THEME_LABELS.get(tid, tid)
    print(f"  {tid}: {label[:50]:50s} | {count:5d} items ({pct:.1f}%)")

# Update themes data
for t in themes_data['themes']:
    tid = t['theme_id']
    t['item_ids'] = theme_counts.get(tid, [])
    t['item_count'] = len(t['item_ids'])
    t['prevalence'] = t['item_count'] / len(corpus)

themes_data['item_themes'] = item_themes
themes_data['unthemed_count'] = unthemed

(RUN_DIR / 'analysis/themes_pass2.json').write_text(
    json.dumps(themes_data, indent=2, ensure_ascii=False), encoding='utf-8'
)
print(f"\nSaved to {RUN_DIR / 'analysis/themes_pass2.json'}")
