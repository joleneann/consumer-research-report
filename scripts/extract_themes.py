"""Theme extraction: map all filtered items to discovered themes."""
import json, re, sys
from pathlib import Path
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding='utf-8')

RUN_DIR = Path('runs/20260407_184943_08eb92')
corpus = json.loads((RUN_DIR / 'filtered/corpus.json').read_text(encoding='utf-8'))

# 12 Themes discovered from stratified sample of 300 items
THEMES = [
    {
        "theme_id": "THM_01",
        "label": "Make in India: Success vs Failure Debate",
        "description": "Political and public debate over whether the Make in India initiative has succeeded or failed. Includes claims of manufacturing growth, FDI attraction, and export expansion vs criticisms of unmet GDP targets, continued import dependence, and hollow slogans.",
        "keywords": [
            r'make\s+in\s+india.*(?:success|fail|work|result|achieve|deliver)',
            r'(?:success|fail|failure|failed|working|not\s+working).*make\s+in\s+india',
            r'make\s+in\s+india.*(?:promise|slogan|rhetoric|jhumla|jumla)',
            r'(?:success|failure)\s+of\s+(?:make\s+in\s+india|mii|modi)',
            r'(?:11|10|eleven|ten)\s+years?\s+of\s+make\s+in\s+india',
            r'make\s+in\s+india.*FAILED',
            r'make\s+in\s+india.*grand\s+success',
            r'(?:is|was)\s+make\s+in\s+india',
            r'MakeInIndia.*(?:success|fail)',
            r'(?:success|fail).*MakeInIndia',
            r'make\s+in\s+india\b',
            r'11YearsOfMakeInIndia',
        ],
    },
    {
        "theme_id": "THM_02",
        "label": "PLI Scheme & Electronics Manufacturing",
        "description": "The Production Linked Incentive scheme's impact on electronics/mobile manufacturing. Foxconn and Apple iPhone production in India, semiconductor initiatives, and the electronics export boom.",
        "keywords": [
            r'\bPLI\b', r'production.linked.incentive',
            r'foxconn', r'iphone.*india', r'india.*iphone',
            r'mobile\s+(?:manufactur|phone.*manufactur|phone.*india)',
            r'(?:manufactur|assembl).*(?:mobile|phone|smartphone|electronic)',
            r'semiconductor.*india', r'india.*semiconductor',
            r'semicon\b', r'chip.*(?:manufactur|fab|plant)',
            r'electronics.*(?:manufactur|export|sector|industry)',
            r'apple.*(?:india|manufactur|production|shift)',
            r'india.*(?:electronics|mobile).*(?:export|manufactur)',
        ],
    },
    {
        "theme_id": "THM_03",
        "label": "Vocal for Local & Swadeshi Movement",
        "description": "Consumer sentiment supporting Indian-made products, the 'Vocal for Local' movement, Swadeshi ethos, and calls to buy Indian. Includes both genuine patriotic consumer advocacy and commercial promotion of local brands.",
        "keywords": [
            r'vocal\s+for\s+local', r'swadeshi', r'buy\s+indian',
            r'support\s+indian', r'choose\s+(?:indian|desi|local)',
            r'(?:ditch|reject|avoid).*(?:import|foreign|chinese|american)',
            r'be\s+indian\s+buy\s+indian',
            r'shop\s+(?:indian|desi|local)',
            r'buy.*(?:made\s+in\s+india|desi|local|indian\s+brand)',
            r'(?:prefer|choose|switch\s+to).*indian',
            r'(?:garv|pride).*(?:swadeshi|indian|desi)',
            r'local\s+for\s+vocal', r'khadi',
            r'support\s+local\s+brand', r'support\s+local\s+artisan',
            r'boycott.*(?:american|chinese|foreign|import)',
            r'(?:diwali|festive|festival).*(?:swadeshi|local|indian\s+brand)',
            r'SwadeshiVsUSA', r'BoycottChina', r'BoycottAmerica',
            r'BuyIndian', r'VocalForLocal',
        ],
    },
    {
        "theme_id": "THM_04",
        "label": "India vs China: Trade Deficit & Competition",
        "description": "Concerns about India's massive trade deficit with China, Chinese products dominating Indian markets, comparisons of manufacturing capability, and whether India can realistically compete with or replace China.",
        "keywords": [
            r'china.*(?:india|indian).*(?:trade|import|export|deficit|compete|product)',
            r'(?:india|indian).*china.*(?:trade|import|export|deficit|compete|product)',
            r'trade\s+deficit.*china', r'china.*trade\s+deficit',
            r'chinese\s+(?:product|import|goods|manufactur)',
            r'import.*from\s+china', r'china.*import',
            r'india.*vs.*china', r'china.*vs.*india',
            r'china.*(?:ahead|better|superior|outperform)',
            r'(?:replace|rival|compete\s+with).*china',
            r'china\+1', r'china\s+plus\s+one',
            r'(?:made\s+in|import\s+from)\s+china',
            r'flooded.*chinese', r'chinese.*flood',
        ],
    },
    {
        "theme_id": "THM_05",
        "label": "Product Quality & Consumer Trust",
        "description": "Consumer perceptions of Indian product quality vs foreign alternatives. Includes concerns about Indian versions of global brands being inferior, the assembly-vs-manufacturing debate, and trust issues with 'Made in India' labeling.",
        "keywords": [
            r'(?:indian|india).*(?:quality|inferior|superior|substandard|poor\s+quality|world\s+class)',
            r'quality.*(?:indian|india)', r'(?:cheap|low).*quality.*india',
            r'(?:indian|india).*version.*(?:inferior|different|worse|better)',
            r'assembl(?:y|ed|ing).*(?:not|vs|versus).*manufactur',
            r'(?:screwdriver|screw\s+driver).*(?:tech|assembl)',
            r'made\s+in\s+india.*(?:scam|fake|label|real)',
            r'(?:trust|reliable|durability).*(?:indian|india)',
            r'(?:indian|india).*(?:trust|reliable|durability)',
            r'(?:levi|coke|coca.cola|nestle|cerelac|nutella).*(?:india|indian)',
            r'(?:india|indian).*(?:levi|coke|coca.cola|nestle)',
            r'(?:india|indian).*(?:brand|product).*(?:trust|quality|reliable)',
            r'consumer.*(?:trust|confidence).*(?:india|indian)',
            r'(?:white\s+label|relabel|rebrand).*(?:china|chinese|import)',
        ],
    },
    {
        "theme_id": "THM_06",
        "label": "Defence Manufacturing & Strategic Self-Reliance",
        "description": "India's defence production capabilities and the push for indigenous military equipment. Includes DRDO, HAL, Tejas, Brahmos, Operation Sindoor, Kaveri engine, defence exports, and the strategic importance of self-reliance in defence.",
        "keywords": [
            r'defence.*(?:manufactur|produc|export|india|indigenous)',
            r'defense.*(?:manufactur|produc|export|india|indigenous)',
            r'\bDRDO\b', r'\bHAL\b.*(?:india|manufactur|defence|aircraft)',
            r'brahmos', r'tejas', r'(?:kaveri|kavari).*engine',
            r'(?:missile|weapon|warship|frigate|fighter|aircraft).*(?:india|indigenous|make\s+in)',
            r'(?:india|indigenous).*(?:missile|weapon|warship|frigate|fighter)',
            r'operation\s+sindoor', r'sindoor.*(?:india|defence|weapon)',
            r'(?:india|indian).*(?:defence|defense).*(?:export|production|sector)',
            r'(?:military|armed\s+force|army|navy|air\s+force).*(?:india|indigenous|make\s+in)',
            r'(?:assault\s+rifle|rifle).*(?:india|indigenous)',
            r'atmanirbhar.*(?:defence|defense|military)',
        ],
    },
    {
        "theme_id": "THM_07",
        "label": "Indian Brand Ecosystem & D2C/Startup Growth",
        "description": "The rise of Indian homegrown brands, D2C startups, and entrepreneurship. Consumers discovering and endorsing Indian alternatives to global brands across categories - skincare, food, fashion, electronics, automotive.",
        "keywords": [
            r'indian\s+brand', r'desi\s+brand', r'homegrown\s+brand',
            r'(?:indian|desi|local)\s+brand.*(?:support|quality|better|love|prefer)',
            r'D2C.*india', r'india.*D2C',
            r'(?:indian|india).*startup', r'startup.*(?:indian|india)',
            r'(?:indian|desi|homegrown).*(?:alternative|option|replacement)',
            r'(?:move|switch|shift).*(?:indian|desi|local)\s+brand',
            r'(?:patanjali|boat|mamaearth|sugar\s+cosmetic|minimalist|plum|ather|ultraviolette)',
            r'(?:indian|desi)\s+(?:brand|product).*(?:recommend|review|try|discover)',
            r'(?:entrepreneur|founder).*(?:india|indian)',
            r'(?:india|indian).*(?:entrepreneur|founder)',
            r'micro\s*brand.*(?:india|indian)',
        ],
    },
    {
        "theme_id": "THM_08",
        "label": "Manufacturing GDP & Economic Fundamentals",
        "description": "Discussion of manufacturing's share of GDP (stuck at ~14-17% vs 25% target), India's overall economic growth trajectory, economic reforms (GST, FDI liberalization), and structural economic challenges.",
        "keywords": [
            r'manufactur.*(?:GDP|share|percent|%)',
            r'GDP.*(?:manufactur|growth|india|economy|4th|third|trillion)',
            r'(?:india|indian).*(?:GDP|economy).*(?:growth|fourth|4th|trillion)',
            r'(?:GST|reform).*(?:india|economy|manufactur)',
            r'(?:india|indian).*(?:reform|GST)',
            r'(?:4th|fourth|third|3rd).*(?:largest|biggest).*economy',
            r'(?:5|five)\s+trillion.*economy',
            r'(?:india|indian).*(?:economic|economy).*(?:growth|decline|stagnant|boom)',
            r'viksit\s+bharat', r'developed\s+nation.*(?:2047|india)',
            r'(?:FDI|foreign\s+direct\s+invest).*(?:india|billion|crore)',
            r'(?:ease\s+of\s+doing\s+business|EODB)',
            r'(?:india|indian).*(?:ease\s+of\s+doing)',
        ],
    },
    {
        "theme_id": "THM_09",
        "label": "US Tariff War & Trade Policy",
        "description": "Impact of US tariffs on Indian goods, India's retaliatory measures, trade negotiations, the boycott of American brands movement, and broader trade policy implications for Indian manufacturing.",
        "keywords": [
            r'tariff.*(?:india|indian|trump|US|america)',
            r'(?:india|indian).*tariff', r'trump.*(?:india|tariff)',
            r'trade\s+war.*(?:india|indian)',
            r'(?:india|indian).*trade\s+war',
            r'boycott.*(?:american|US\s+brand|america)',
            r'(?:american|US).*(?:brand|product).*(?:india|boycott)',
            r'(?:customs?\s+duty|import\s+duty).*(?:india|increase|hike)',
            r'(?:retaliatory|retaliation).*(?:tariff|india)',
            r'(?:india|indian).*(?:retaliatory|retaliation)',
            r'(?:trump|US|america).*(?:50%|26%|tariff).*india',
        ],
    },
    {
        "theme_id": "THM_10",
        "label": "Assembly vs Manufacturing: The Value-Add Question",
        "description": "Critical debate about whether 'Make in India' constitutes genuine manufacturing or merely assembly/packaging of imported components. Questions about real value addition, component-level self-reliance, and the gap between 'assembled in India' and 'manufactured in India'.",
        "keywords": [
            r'assembl(?:y|ed|e|ing).*(?:india|not\s+manufactur)',
            r'(?:india|indian).*(?:assembl(?:y|ed|e|ing))',
            r'(?:screwdriver|screw.driver).*(?:tech|assembl|india)',
            r'(?:component|part).*(?:import|china|still.*import)',
            r'(?:value\s+add|value.addition).*(?:india|low|minimal)',
            r'(?:india|indian).*(?:value\s+add|value.addition)',
            r'(?:just|only|merely).*assembl',
            r'(?:import|imported).*component',
            r'(?:label|relabel|rebrand).*(?:india|indian)',
            r'(?:not|no)\s+real\s+manufactur',
            r'(?:assemble\s+in\s+india|assembled\s+in\s+india)',
        ],
    },
    {
        "theme_id": "THM_11",
        "label": "Infrastructure & Industrial Capacity Building",
        "description": "Development of physical and industrial infrastructure enabling manufacturing - expressways, factory parks, logistics corridors, ports, railways, smart cities, and mega projects as enablers of the Make in India vision.",
        "keywords": [
            r'(?:infrastructure|expressway|highway|road).*(?:india|manufactur|develop)',
            r'(?:india|indian).*(?:infrastructure|expressway|highway)',
            r'(?:factory|industrial).*(?:park|corridor|zone|cluster|hub).*india',
            r'(?:india|indian).*(?:factory|industrial).*(?:park|corridor|zone)',
            r'(?:bullet\s+train|high.speed\s+rail|metro).*india',
            r'(?:port|airport|logistics).*(?:india|develop|modern)',
            r'(?:smart\s+city|smart\s+cities).*india',
            r'(?:india|indian).*(?:mega\s+project|infra.*develop)',
            r'(?:india|indian).*(?:logistics|supply\s+chain|connectivity)',
            r'(?:expressway|nhia|nhai|bharat\s+mala|sagar\s+mala)',
        ],
    },
    {
        "theme_id": "THM_12",
        "label": "Employment & Workforce Development",
        "description": "Discussion of job creation (or lack thereof) from Make in India, youth unemployment, women in manufacturing, skill development initiatives, and the gap between employment promises and ground reality.",
        "keywords": [
            r'(?:job|employment|unemploy|jobless).*(?:india|manufactur|create)',
            r'(?:india|indian).*(?:job|employment|unemploy|jobless)',
            r'(?:2\s+crore|two\s+crore|million).*job',
            r'(?:women|female).*(?:workforce|worker|employ|factory|manufactur)',
            r'(?:skill|skilled|skilling).*(?:india|worker|youth|develop)',
            r'(?:brain\s+drain|talent\s+leaving|move\s+abroad)',
            r'(?:youth|young).*(?:india|unemploy|job)',
            r'(?:lakh|crore|million).*(?:job|employ).*(?:creat)',
            r'(?:factory|plant).*(?:worker|job|hiring|workforce)',
            r'(?:blue.collar|manufacturing).*(?:job|wage|salary)',
        ],
    },
]


def map_item_to_themes(item):
    """Map a single item to 0+ themes using keyword matching."""
    text = item.get('content_text', '')
    matched_themes = []

    for theme in THEMES:
        for kw in theme['keywords']:
            if re.search(kw, text, re.IGNORECASE):
                matched_themes.append(theme['theme_id'])
                break

    return matched_themes


# Map all items
theme_items = defaultdict(list)
item_themes = {}
unthemed_count = 0

for item in corpus:
    themes = map_item_to_themes(item)
    item_themes[item['item_id']] = themes

    if themes:
        for t in themes:
            theme_items[t].append(item['item_id'])
    else:
        unthemed_count += 1

# Stats
print(f"Total items: {len(corpus)}")
print(f"Themed items: {len(corpus) - unthemed_count} ({(len(corpus) - unthemed_count)/len(corpus)*100:.1f}%)")
print(f"Unthemed items: {unthemed_count} ({unthemed_count/len(corpus)*100:.1f}%)")
print()

for theme in THEMES:
    tid = theme['theme_id']
    count = len(theme_items[tid])
    pct = count / len(corpus) * 100
    print(f"  {tid}: {theme['label'][:50]:50s} | {count:5d} items ({pct:.1f}%)")

# Save theme mapping
theme_output = {
    'themes': [
        {
            'theme_id': t['theme_id'],
            'label': t['label'],
            'description': t['description'],
            'item_ids': theme_items[t['theme_id']],
            'item_count': len(theme_items[t['theme_id']]),
            'prevalence': len(theme_items[t['theme_id']]) / len(corpus),
        }
        for t in THEMES
    ],
    'item_themes': item_themes,
    'unthemed_count': unthemed_count,
    'total_items': len(corpus),
}

out_path = RUN_DIR / 'analysis'
out_path.mkdir(exist_ok=True)
(out_path / 'themes_pass1.json').write_text(
    json.dumps(theme_output, indent=2, ensure_ascii=False), encoding='utf-8'
)
print(f"\nSaved to {out_path / 'themes_pass1.json'}")
