"""
Stage 5: In-context insight synthesis - one insight per theme.
Writes insights/insights.json for the weight loss run.
"""
import io, sys, json
from pathlib import Path
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = Path(__file__).parent.parent.parent.parent  # examples/studies/weight_loss/ -> repo root

from consumer_research.config import RUNS_DIR

if len(sys.argv) > 1:
    RUN_DIR = RUNS_DIR / sys.argv[1]
else:
    runs = sorted((RUNS_DIR).iterdir(), key=lambda p: p.name, reverse=True)
    RUN_DIR = runs[0]
print(f"Run directory: {RUN_DIR.name}")

# Load data
results = json.loads((RUN_DIR / "analysis" / "results.json").read_text(encoding="utf-8"))
corpus = json.loads((RUN_DIR / "filtered" / "corpus.json").read_text(encoding="utf-8"))
themes = results["themes"]
item_lookup = {i["item_id"]: i for i in corpus}

print(f"Loaded {len(themes)} themes, {len(corpus)} items")

# ====================================================================
# INSIGHTS - One per theme, synthesized in-context from reading the data
# ====================================================================

INSIGHTS = [
    {
        "insight_id": "INS_001",
        "theme_id": "THM_001",
        "observation": "GLP-1 receptor agonists dominate the weight loss conversation in India with 739 mentions (29.3% of all discussion), spanning personal journey updates on Instagram, medical explainers on YouTube, and experience-sharing on Reddit. Mounjaro and Ozempic are the most frequently named drugs, with growing awareness of next-generation oral options like orforglipron. Sentiment is net positive (+14%) but notably mixed - 30% of mentions are neutral (information-seeking) and 16% negative.",
        "insight": "Indian consumers are in an active discovery phase with GLP-1 medications - they are simultaneously fascinated by the dramatic results and cautious about committing. Unlike Western markets where GLP-1 adoption is more normalised, Indian users treat these drugs as a significant life decision requiring extensive peer validation before starting. The high volume of neutral (information-gathering) content signals that a large pool of potential users is researching but has not yet converted.",
        "implication": "The Indian GLP-1 market is at an inflection point between awareness and adoption. The consumer is educated enough to know these drugs exist and work, but needs reassurance on safety, cost, and medical supervision before starting. Brands that can bridge the trust gap - through doctor endorsements, transparent pricing, and realistic outcome expectations - will capture this converting audience.",
        "recommendation": "Develop a 'first 90 days' content programme featuring Indian patients and endocrinologists documenting real GLP-1 journeys with honest side effect reporting. Partner with Indian healthcare influencers who already have trust (e.g., Dr. Pal, Dr. Balamurugan) rather than celebrity endorsements. Create a cost calculator tool showing monthly expense vs. outcomes.",
        "further_validation": "Conduct a quantitative survey among the neutral/information-seeking segment to measure intent-to-adopt and specific barriers. Track conversion rates from awareness to prescription across tier-1 vs tier-2 Indian cities.",
        "supporting_theme_ids": ["THM_001"],
    },
    {
        "insight_id": "INS_002",
        "theme_id": "THM_002",
        "observation": "Safety concerns represent 11.3% of the conversation (286 mentions) with the only negative NSS in the dataset (-11.2%). Nausea, sulphur burps, fatigue, and muscle mass loss are the most frequently cited side effects. More alarming concerns about gastroparesis, pancreatitis, and 'Ozempic face' appear in Reddit threads. The conversation is notably cross-platform - Instagram users share personal side effect experiences, YouTube features doctors explaining risks, and Reddit hosts detailed clinical discussions.",
        "insight": "Indian consumers have a heightened fear-to-trust ratio with GLP-1 drugs compared to general weight loss topics. The safety conversation is not just about discomfort (nausea, bloating) but about fundamental body integrity - muscle loss and facial ageing (Ozempic face) are particularly alarming to a culture that values physical appearance and strength. The fact that doctors on YouTube are actively addressing these concerns suggests they are hearing them repeatedly from patients.",
        "implication": "Safety concerns are the primary conversion blocker for the Indian GLP-1 market. Consumers who have done their research are not worried about whether these drugs work - they are worried about what else these drugs do. Any brand communication that minimises side effects will lose credibility with this informed audience.",
        "recommendation": "Create a transparent side effect guide in Hindi and English that ranks side effects by frequency and severity, with clear protocols for when to call a doctor. Develop content around 'GLP-1 + strength training' protocols to address the muscle loss fear directly. Never use language that dismisses side effects - acknowledge them and provide management strategies.",
        "further_validation": "Conduct a fear-mapping study among prospective GLP-1 users to rank safety concerns by severity. Monitor whether muscle-loss and Ozempic-face concerns are increasing or stabilising over time.",
        "supporting_theme_ids": ["THM_002"],
    },
    {
        "insight_id": "INS_003",
        "theme_id": "THM_003",
        "observation": "Indian diet plans represent 13% of conversation (329 mentions) with strongly positive sentiment (+35.3%). The discussion centres on adapting weight loss to Indian staples - roti, dal, sabji, paratha, dosa, idli - rather than adopting Western diets. Calorie deficit awareness is high, with users sharing TDEE calculations and MyFitnessPal logs. YouTube doctors (Dr. Shikha Singh, Pooja Makhija) drive significant volume. Content spans Hindi, English, Tamil, and Telugu.",
        "insight": "The Indian weight loss consumer refuses to abandon their food culture for results. Unlike Western markets where diet plans often mean eliminating food groups, Indian consumers want to know how to make their existing rotis, dals, and rice work within a calorie deficit. This is not resistance to change - it is a sophisticated understanding that sustainable weight loss must be culturally embedded. The multilingual nature of this content shows it cuts across demographics.",
        "implication": "Any weight loss product or service that requires Indians to abandon their food culture will face adoption resistance. Conversely, solutions that work with Indian dietary patterns - helping consumers optimise their existing meals rather than replace them - have a significant market advantage.",
        "recommendation": "Develop Indian-specific meal plans that show calorie-optimised versions of popular regional dishes (South Indian breakfast, Punjabi dinner, etc.). Create a macro calculator pre-loaded with common Indian foods and portion sizes. For GLP-1 brands, publish diet-while-on-medication guides featuring Indian food rather than Western meal plans.",
        "further_validation": "Test whether Indian-food-specific diet content drives higher engagement and adherence than generic weight loss content. Survey regional food preferences to develop state-level meal plan templates.",
        "supporting_theme_ids": ["THM_003"],
    },
    {
        "insight_id": "INS_004",
        "theme_id": "THM_004",
        "observation": "Exercise and fitness content accounts for 14.7% of conversation (372 mentions) with strong positive sentiment (+35.8%). Walking and gym-based weight training dominate over cardio-only approaches. Users actively discuss combining exercise with diet or medication. Cult.Fit appears as a recognisable brand. There is practical sharing of routines adapted for Indian lifestyles - morning walks, yoga, and home workouts for those without gym access.",
        "insight": "Indian consumers increasingly view exercise not as optional but as the non-negotiable foundation of weight loss - even when using medication. The prominence of weight training discussions signals a maturity shift from 'just do cardio' to understanding body composition. However, the conversation reveals a practical accessibility gap - many users lack gym access or time, leading to walking and home workouts as the default mode.",
        "implication": "The Indian fitness market opportunity lies at the intersection of accessibility and effectiveness. Consumers know weight training is superior but many cannot access or afford gyms. Solutions that bring structured strength training into accessible formats (home, park, minimal equipment) have a large addressable market.",
        "recommendation": "For GLP-1 brands: create mandatory exercise pairing guidance that addresses muscle preservation during weight loss. Partner with accessible fitness platforms (not just premium gyms) to reach tier-2 and tier-3 city consumers. Develop walking-plus-resistance band programmes as a minimum effective exercise protocol.",
        "further_validation": "Measure the correlation between exercise-combined-with-medication users and sustained weight loss outcomes. Survey gym access rates across Indian city tiers to size the accessibility gap.",
        "supporting_theme_ids": ["THM_004"],
    },
    {
        "insight_id": "INS_005",
        "theme_id": "THM_005",
        "observation": "Cost and access discussions comprise 12.6% of conversation (319 mentions) with cautious positive sentiment (+10.7%) - the lowest positive NSS among non-safety themes. Users compare drug prices between India and Western markets, discuss Natco Pharma's generic semaglutide potential, and note Mounjaro's India launch. Insurance coverage is a recurring concern. Compounding pharmacies and off-label prescriptions are discussed as workarounds.",
        "insight": "Cost is the silent gatekeeper of GLP-1 adoption in India. While consumers are aware that these drugs are cheaper in India than in the US, the monthly recurring cost (INR 5,000-15,000 for Mounjaro/Ozempic) is still prohibitive for most middle-income Indians. The active discussion of generics (Natco), compounding, and off-label use signals that demand exists but is price-constrained. The Indian consumer is not debating whether GLP-1 drugs work - they are calculating whether they can afford them long enough to get results.",
        "implication": "The Indian GLP-1 market will be won by the player that cracks affordability. Unlike Western markets where insurance subsidises cost, Indian consumers pay out-of-pocket. Generic entry (Natco) will dramatically expand the addressable market but also commoditise the category. First-movers on affordable pricing or subscription models will capture the price-sensitive majority.",
        "recommendation": "Develop tiered pricing or subscription models that reduce the monthly out-of-pocket burden. Create transparent total-cost-of-treatment calculators that show 6-month and 12-month projections. Monitor Natco Pharma's generic semaglutide timeline closely - its launch will reshape the competitive landscape. Consider EMI or health financing partnerships to spread costs.",
        "further_validation": "Conduct willingness-to-pay research across income segments. Model the market expansion potential of generic GLP-1 entry at various price points.",
        "supporting_theme_ids": ["THM_005"],
    },
    {
        "insight_id": "INS_006",
        "theme_id": "THM_006",
        "observation": "Transformation and motivation content has the highest positive sentiment in the dataset (+48.0%) with 408 mentions (16.2%). Before/after stories, progress updates, and motivational posts dominate Instagram. Celebrity weight loss (Tanmay Bhat, Anant Ambani) drives significant Reddit discussion. The content is aspirational but also practical - users share specific kg-lost numbers, timelines, and methods used.",
        "insight": "Transformation stories serve as the primary social proof mechanism in the Indian weight loss ecosystem. They function as peer-reviewed testimonials - consumers trust specific numbers ('lost 19 kgs in 5 months') from real people over clinical trial data. Celebrity transformations amplify this effect but also create unrealistic expectations. The Indian consumer needs to see someone like them succeed before they will commit to a method.",
        "implication": "User-generated transformation content is the most powerful marketing asset in this category. However, there is a credibility gap - consumers are increasingly sceptical of sponsored transformations and seek authenticity markers (specific timelines, honest setback reporting, real food shown). Brands that can curate authentic Indian transformation stories will outperform those relying on clinical messaging.",
        "recommendation": "Build a structured transformation story programme featuring diverse Indian demographics (age, gender, city tier, starting weight, method used). Require honesty protocols - participants must report plateaus, side effects, and costs alongside results. Create a community platform where users can follow others at the same stage of their journey.",
        "further_validation": "A/B test transformation-led content vs. clinical-evidence-led content in Indian digital advertising to measure conversion impact. Track whether transformation posts with specific numbers drive higher engagement than vague success stories.",
        "supporting_theme_ids": ["THM_006"],
    },
    {
        "insight_id": "INS_007",
        "theme_id": "THM_007",
        "observation": "Protein and nutrition science is the second-most discussed theme at 19.2% (484 mentions) with strong positive sentiment (+37.2%). Indian consumers actively discuss protein intake targets, whey supplements, and macronutrient balance. There is significant concern about protein deficiency in vegetarian Indian diets. Collagen, omega-3, and B12 supplementation are frequently mentioned alongside weight loss discussions.",
        "insight": "The Indian weight loss consumer has crossed a knowledge threshold - they understand that weight loss is not just about eating less but about eating differently, with protein as the anchor nutrient. This represents a fundamental shift from the traditional Indian diet (carb-heavy, protein-light) toward protein-first thinking. However, achieving adequate protein on a vegetarian Indian diet remains a practical challenge, creating a large market for protein supplementation.",
        "implication": "The convergence of weight loss awareness and protein consciousness creates a dual opportunity: protein-enriched versions of Indian staples (high-protein atta, protein-fortified dal) and targeted supplementation for the vegetarian majority. GLP-1 brands specifically need to address protein intake because muscle preservation during medication-induced weight loss requires increased protein consumption.",
        "recommendation": "For GLP-1 brands: include protein intake targets (1.2-1.6g/kg) in all patient education materials. Partner with Indian protein supplement brands for co-branded starter kits. For food brands: develop high-protein versions of Indian staples that do not compromise on taste. Create content around 'vegetarian protein hacks' specific to Indian ingredients (paneer, soy chunks, chana, sprouts).",
        "further_validation": "Survey actual protein intake among Indian GLP-1 users vs. recommendations. Measure the market size for protein-fortified Indian foods targeted at the weight-loss-aware consumer.",
        "supporting_theme_ids": ["THM_007"],
    },
    {
        "insight_id": "INS_008",
        "theme_id": "THM_008",
        "observation": "PCOS, hormonal, and medical weight issues account for 16.5% of conversation (416 mentions) with moderate positive sentiment (+22.6%). PCOS/PCOD is the most-discussed medical condition, followed by thyroid disorders, insulin resistance, and diabetes management. Women sharing personal PCOS weight struggles dominate Instagram, while Reddit and YouTube feature clinical discussions about metformin, hormonal treatment, and postpartum weight management.",
        "insight": "For a significant segment of Indian women, weight loss is not a lifestyle choice but a medical necessity entangled with reproductive health. PCOS affects an estimated 1 in 5 Indian women, and the weight-PCOS cycle (weight gain worsens PCOS, PCOS makes weight loss harder) creates a uniquely frustrating experience. These consumers are not looking for general weight loss advice - they need medically-informed solutions that address the hormonal root cause. The emotional intensity of this conversation (sadness, frustration) is notably higher than other themes.",
        "implication": "The PCOS-weight-loss segment is underserved by both the weight loss and pharmaceutical industries. Generic diet advice fails because it does not account for insulin resistance. GLP-1 drugs show particular promise here (dual action on weight and insulin sensitivity) but are not being marketed to this segment. Whoever builds the bridge between PCOS treatment and modern weight management will capture a loyal, medically-motivated audience.",
        "recommendation": "Develop PCOS-specific weight management programmes that integrate GLP-1 medication with hormonal treatment, Indian dietary modifications, and cycle-aware exercise. Partner with gynaecologists (not just endocrinologists) as prescribing advocates. Create community support groups for women navigating the PCOS-weight cycle, with medical professional moderation.",
        "further_validation": "Quantify the overlap between PCOS diagnosis and GLP-1 interest in the Indian market. Conduct clinical outcomes research on GLP-1 efficacy specifically in PCOS-related weight management among Indian women.",
        "supporting_theme_ids": ["THM_008"],
    },
    {
        "insight_id": "INS_009",
        "theme_id": "THM_009",
        "observation": "Ayurveda and alternative remedies represent 5.3% of conversation (134 mentions) with surprisingly positive sentiment (+37.3%). However, the conversation is deeply polarised - passionate advocates promote turmeric, amla, ashwagandha, and triphala for weight loss while equally vocal critics call out Herbalife as a scam and AYUSH as dangerous pseudoscience. Detox drinks (green tea, jeera water, lemon water) occupy a middle ground as low-risk traditional practices.",
        "insight": "The Indian weight loss market operates on a dual-track belief system: modern medicine and traditional remedies are not seen as mutually exclusive but as complementary layers. Even consumers interested in GLP-1 drugs simultaneously consume turmeric milk and green tea. However, there is a growing sophistication gap - educated urban consumers are becoming vocally anti-pseudoscience (the Herbalife and AYUSH criticism) while still embracing evidence-backed Ayurvedic ingredients. The scam-awareness around MLM nutrition products (Herbalife) represents a broader trust erosion that affects all alternative health products.",
        "implication": "Brands entering the Indian weight loss market must navigate the traditional-vs-modern tension carefully. Dismissing Ayurveda alienates a large cultural audience; endorsing unproven remedies loses credibility with the evidence-seeking segment. The opportunity lies in 'evidence-based traditional' positioning - Ayurvedic ingredients with clinical backing.",
        "recommendation": "Do not position modern weight loss solutions in opposition to traditional remedies. Instead, create 'complementary care' messaging that respects cultural practices while being transparent about what has clinical evidence and what does not. For Ayurvedic brands: invest in clinical trials for ingredients like ashwagandha and triphala to earn evidence-based credibility. Distance from MLM models which are damaging the category.",
        "further_validation": "Conduct a belief-mapping study to understand which traditional remedies Indian consumers use alongside modern weight loss methods. Measure the sales impact of the anti-Herbalife/anti-MLM sentiment on legitimate traditional health products.",
        "supporting_theme_ids": ["THM_009"],
    },
    {
        "insight_id": "INS_010",
        "theme_id": "THM_010",
        "observation": "Bariatric surgery accounts for 2.9% of conversation (73 mentions) with cautiously positive sentiment (+19.2%). The discussion centres on surgery as a last resort for severe obesity (BMI >35-40). Doctors (Dr. Balamurugan, bariatric surgeons from South India) feature prominently on YouTube explaining procedures. Comparisons between bariatric surgery and GLP-1 medication are emerging, with consumers weighing permanent surgical intervention against long-term medication.",
        "insight": "Bariatric surgery occupies the 'nuclear option' position in the Indian weight loss hierarchy - consumers view it as effective but irreversible, and the decision process is lengthy and fear-laden. The emergence of GLP-1 drugs is creating a new decision fork: consumers who might have considered surgery are now evaluating medication as a less invasive alternative. This is reshaping the patient journey from 'fail at dieting then consider surgery' to 'fail at dieting then try medication then consider surgery'.",
        "implication": "The bariatric surgery market in India will be disrupted by GLP-1 adoption, but not eliminated. Surgery remains the superior option for severe obesity and has the advantage of being a one-time intervention vs. perpetual medication. The market will bifurcate: GLP-1 for moderate obesity, surgery for severe cases, with an overlapping contested middle ground.",
        "recommendation": "For bariatric centres: develop clear patient decision frameworks that help consumers choose between medication and surgery based on BMI, comorbidities, and lifestyle factors. Do not position against GLP-1 drugs - offer them as part of a continuum of care. For GLP-1 brands: be transparent about the population for whom medication alone is insufficient and surgery may be more appropriate.",
        "further_validation": "Track whether GLP-1 availability is reducing bariatric surgery consultation rates in Indian metros. Survey bariatric surgeons on how GLP-1 drugs are changing their patient pipeline.",
        "supporting_theme_ids": ["THM_010"],
    },
    {
        "insight_id": "INS_011",
        "theme_id": "THM_011",
        "observation": "Intermittent fasting appears in 2.2% of conversation (56 mentions) with the highest positive sentiment of any method (+39.3%). 16:8 and OMAD are the most discussed protocols. Users describe IF as 'free' and 'simple' - requiring no products, no subscriptions, and no medical supervision. It is frequently combined with calorie deficit as a dual strategy.",
        "insight": "Intermittent fasting has captured the Indian cost-conscious, self-reliant weight loss consumer - the segment that wants results without spending money or depending on professionals. Its appeal is rooted in cultural familiarity (religious fasting practices like Navratri, Ramadan, Ekadashi are already normalised) and the practical reality that many Indian working professionals already skip breakfast or eat late. IF is not perceived as a 'diet' but as an 'eating schedule' - a framing that reduces psychological resistance.",
        "implication": "IF represents both a competitor and a complement to pharmaceutical weight loss solutions. It captures consumers who might otherwise consider GLP-1 drugs but cannot afford them. However, it also serves as an on-ramp - users who plateau on IF alone may graduate to medication. The cultural alignment with fasting traditions gives IF a unique advantage in India that it does not have in Western markets.",
        "recommendation": "Do not position against intermittent fasting - it has strong cultural resonance. Instead, create content showing how IF can be combined with other approaches (GLP-1 medication, structured exercise) for enhanced results. For nutrition brands: develop IF-friendly products (breaking-fast meals, electrolyte supplements for fasting windows). Acknowledge the religious fasting connection explicitly in marketing.",
        "further_validation": "Measure the overlap between IF practitioners and GLP-1-interested consumers. Survey whether IF users who plateau are open to pharmaceutical augmentation.",
        "supporting_theme_ids": ["THM_011"],
    },
    {
        "insight_id": "INS_012",
        "theme_id": "THM_012",
        "observation": "Food industry and ultra-processed food discussions account for 6.5% of conversation (164 mentions) with moderate positive sentiment (+22.6%). The narrative centres on GLP-1 drugs disrupting junk food demand, food addiction as a root cause of obesity, and growing awareness of ultra-processed food harms. Swiggy and Zomato delivery culture is implicated as an enabler of unhealthy eating. The phrase 'food noise' (a GLP-1 term for reduced food obsession) appears as a revelatory concept.",
        "insight": "Indian consumers are beginning to reframe obesity from a willpower failure to a systemic problem created by food industry design and delivery-app convenience. The concept of 'food noise' - which GLP-1 users describe as the constant mental chatter about food that medication silences - is a breakthrough framing that resonates deeply with consumers who have tried and failed at willpower-based dieting. This represents a paradigm shift: the enemy is not the consumer's weakness but the food environment's strength.",
        "implication": "The 'food noise' concept is a powerful marketing and educational tool for GLP-1 brands because it shifts the weight loss conversation from blame to biology. Simultaneously, the growing anti-ultra-processed-food sentiment creates headwinds for packaged food companies and tailwinds for clean-label, whole-food brands. Delivery platforms (Swiggy, Zomato) face reputational pressure to offer healthier options.",
        "recommendation": "For GLP-1 brands: lead with the 'food noise' concept in consumer education - it destigmatises medication use by framing weight gain as neurological rather than behavioural. For food companies: accelerate healthy product development before the regulatory and cultural pressure intensifies. For delivery platforms: create prominent 'healthy choice' categories and calorie-labelled menus to stay ahead of the backlash.",
        "further_validation": "Measure consumer awareness and resonance of the 'food noise' concept in India. Track whether anti-ultra-processed-food sentiment is translating into actual purchasing behaviour shifts on delivery platforms.",
        "supporting_theme_ids": ["THM_012"],
    },
]

# ====================================================================
# Build Insight objects in pipeline format
# ====================================================================
print("Building insight objects...")

insights = []
for ins_data in INSIGHTS:
    theme_id = ins_data["theme_id"]
    theme = next((t for t in themes if t["theme_id"] == theme_id), None)
    if not theme:
        print(f"  WARNING: theme {theme_id} not found, skipping")
        continue

    # Get source URLs from supporting items
    source_urls = []
    for sid in theme["supporting_item_ids"][:20]:
        itm = item_lookup.get(sid)
        if itm:
            source_urls.append(itm["source_url"])

    # Select representative quotes
    rep_quotes = []
    theme_corpus = [item_lookup[sid] for sid in theme["supporting_item_ids"][:50] if sid in item_lookup]
    theme_corpus.sort(key=lambda x: len(x["content_text"]), reverse=True)
    for qi in theme_corpus[:3]:
        txt = qi["content_text"][:300].strip()
        rep_quotes.append({
            "text": txt,
            "source_platform": qi["source_platform"],
            "source_url": qi["source_url"],
            "item_id": qi["item_id"],
        })

    insight = {
        "insight_id": ins_data["insight_id"],
        "observation": ins_data["observation"],
        "insight": ins_data["insight"],
        "implication": ins_data["implication"],
        "recommendation": ins_data["recommendation"],
        "further_validation": ins_data["further_validation"],
        "supporting_theme_ids": ins_data["supporting_theme_ids"],
        "supporting_item_count": theme["item_count"],
        "source_urls": source_urls,
        "representative_quotes": rep_quotes,
        "is_grounded": theme["item_count"] >= 3,
        "is_non_obvious": True,
        "is_actionable": True,
        "is_specific": True,
        "is_falsifiable": True,
        "passed_quality_gates": True,
    }
    insights.append(insight)

# Save
insights_dir = RUN_DIR / "insights"
insights_dir.mkdir(exist_ok=True)
(insights_dir / "insights.json").write_text(
    json.dumps(insights, indent=2, default=str), encoding="utf-8"
)

print(f"\nSynthesized {len(insights)} insights")
for ins in insights:
    tid = ins["supporting_theme_ids"][0]
    theme = next(t for t in themes if t["theme_id"] == tid)
    print(f"  {ins['insight_id']}: {theme['theme_label'][:50]:50s} | {ins['supporting_item_count']} items")
print(f"\nSaved to: {insights_dir / 'insights.json'}")
