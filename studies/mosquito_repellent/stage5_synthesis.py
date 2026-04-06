"""
Stage 5: Write real insight text for mosquito repellent study.
Reads the placeholder insights and overwrites with synthesized Observation/Insight/Implication/Recommendation.
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from consumer_research.models.schemas import Insight

RUNS_DIR = ROOT / "consumer_research" / "runs"
run_dirs = sorted([d for d in RUNS_DIR.iterdir() if d.name.startswith("mosquito_repellent_")], key=lambda p: p.name, reverse=True)
RUN_DIR = run_dirs[0]

# Load current insights
insights_data = json.loads((RUN_DIR / "insights" / "insights.json").read_text(encoding="utf-8"))
insights = [Insight(**d) for d in insights_data]

# Overwrite with real synthesis
SYNTHESIS = {
    "INS_001": {
        "observation": "Sleep Disruption and Nighttime Misery spans 1,806 items (33.5% of corpus) with NSS +0.330. The single largest theme in the dataset. Consumers across all four platforms describe mosquitoes as a primary barrier to sleep quality, with emotional language ranging from frustration to helplessness. Power outages compound the problem in tropical markets where fans and electric repellents stop working.",
        "insight": "Mosquito protection is not primarily a pest control purchase - it is a sleep quality purchase. Consumers frame the problem in terms of lost sleep, exhaustion, and inability to function the next day. The emotional intensity of sleep disruption language far exceeds that of disease prevention language, suggesting that the immediate experiential pain of lost sleep outweighs the abstract fear of dengue or malaria for most consumers.",
        "implication": "Brands that position their products as sleep solutions rather than insect killers will capture a larger share of consumer intent. The sleep framing also opens premium pricing territory - consumers will pay more for guaranteed uninterrupted sleep than for generic pest control.",
        "recommendation": "Reframe product marketing from 'kills mosquitoes' to 'protects your sleep'. Develop a sleep-quality guarantee or money-back claim. Consider co-branding or bundling with sleep wellness products (mattress brands, sleep apps). For tropical markets with unreliable power, prioritise battery-powered or passive solutions.",
        "further_validation": "Commission a conjoint analysis testing willingness-to-pay under 'sleep protection' vs 'mosquito killer' positioning. Conduct sleep diary studies measuring actual sleep quality improvement with repellent use.",
    },
    "INS_002": {
        "observation": "Product Efficacy and Disappointment spans 690 items (12.8%) with a very high NSS of +0.854. The overwhelmingly positive sentiment reflects consumers actively seeking and recommending products that work, though a vocal minority expresses frustration with products that fail to deliver.",
        "insight": "Efficacy is table stakes - consumers expect mosquito repellents to work, and when they do, the response is enthusiastic gratitude rather than neutral satisfaction. The high NSS reflects a category where 'it actually works' is still a noteworthy claim, suggesting widespread experience with products that disappoint. The phrase 'actually works' appears repeatedly, implying low baseline expectations.",
        "implication": "The category suffers from a credibility deficit. Consumers have been burned by products that over-promise. Any brand that can demonstrably prove efficacy (through transparent testing, user reviews, or satisfaction guarantees) has a significant competitive advantage.",
        "recommendation": "Invest in transparent efficacy testing and publish results. Implement a satisfaction guarantee programme. Leverage user-generated content showing real-world effectiveness. Avoid vague claims like '12-hour protection' without consumer-verifiable evidence.",
        "further_validation": "Run blinded efficacy trials with consumer panels and publish results. Survey lapsed customers to understand what drove them away from previous products.",
    },
    "INS_003": {
        "observation": "Chemical Safety and Health Concerns spans 678 items (12.6%) with NSS +0.320. This is the most sentiment-polarised theme - consumers split between those who accept chemical repellents as necessary and those who fear health consequences from DEET, transfluthrin, and prallethrin exposure. Breathing difficulties, headaches, and cancer fears are cited.",
        "insight": "Safety anxiety is the category's biggest growth barrier. Consumers who worry about chemical exposure often abandon repellents entirely rather than switching to alternatives, leaving themselves unprotected. The fear is particularly acute among parents, who face a painful trade-off between protecting children from mosquito-borne disease and exposing them to chemical fumes. This is not a rational risk calculation - it is an emotional response driven by unfamiliarity with ingredient safety data.",
        "implication": "The category needs proactive safety communication, not silence. Brands that fail to address chemical safety concerns lose consumers to inaction (no protection at all) rather than to competitors. The opportunity is in transparent ingredient communication and certified-safe product lines.",
        "recommendation": "Create transparent ingredient safety pages with third-party certifications. Develop and prominently market a 'safe for enclosed spaces' product line. Partner with paediatricians and health organisations for endorsements. Use clear, jargon-free safety labelling.",
        "further_validation": "Conduct a quantitative survey on chemical safety perceptions and their impact on purchase behaviour. Test whether safety certification labels increase purchase intent.",
    },
    "INS_004": {
        "observation": "Baby and Child Protection spans 725 items (13.4%) with NSS +0.658. Parents are actively seeking mosquito protection specifically designed for babies and young children. Mosquito nets for cribs, DEET-free formulations, and natural alternatives dominate the conversation. Disease fear (dengue, malaria) is more prominent here than in the general corpus.",
        "insight": "The baby and child segment represents the category's highest-intent, most brand-loyal customer base. Parents researching child-safe repellents are willing to pay premium prices and are less price-sensitive than general consumers. However, they demand absolute safety assurance - a single negative review about a product being unsafe for babies can destroy trust across an entire product line.",
        "implication": "A dedicated child-safe product range with paediatric endorsement could command significant premium pricing and build multi-year brand loyalty as children grow. This segment also serves as a gateway to the household - parents who trust a brand for their baby will trust it for the whole family.",
        "recommendation": "Launch a dedicated child-safe range with paediatrician endorsement and clear age-grading (newborn, 6m+, 2y+). Use transparent DEET-free formulations. Invest in hospital and clinic sampling programmes. Build a parent community around mosquito protection education.",
        "further_validation": "Survey parents on willingness-to-pay for paediatrician-endorsed repellents. Test hospital sampling programme effectiveness in building trial and loyalty.",
    },
    "INS_005": {
        "observation": "Natural and Herbal Remedies spans 1,007 items (18.7%) with NSS +0.517. The second-largest theme after sleep disruption. Consumers actively share and discuss neem, citronella, eucalyptus, lemongrass, camphor, clove, and lime-based DIY repellents. YouTube and Instagram are primary platforms for natural remedy content.",
        "insight": "The natural remedies conversation reveals a massive trust gap in the chemical repellent market. Consumers are not choosing natural alternatives because they are more effective - they are choosing them because they do not trust the safety of chemical products. The DIY culture around natural repellents also signals a desire for control and transparency that packaged products fail to deliver.",
        "implication": "The natural segment is growing but underserved by major brands. Consumers currently rely on home remedies and small D2C brands. There is a significant market opportunity for a mainstream brand to launch a credible natural product line that combines the perceived safety of natural ingredients with the proven efficacy of modern formulations.",
        "recommendation": "Develop a plant-based product line with scientifically validated natural ingredients (PMD/citriodiol, citronella, neem). Position with transparent ingredient lists and 'what is NOT in this product' messaging. Target the DIY natural remedy audience on YouTube and Instagram with educational content.",
        "further_validation": "Test consumer preference between natural-branded products and traditional chemical products at equal price points. Measure whether 'plant-based' labelling increases trial among chemical-averse consumers.",
    },
    "INS_006": {
        "observation": "Electronic and Tech Solutions spans 891 items (16.5%) with NSS +0.435. UV lamps, electric rackets, ultrasonic devices, and smart mosquito killers are widely discussed. YouTube product reviews drive this conversation. Consumers are intrigued by the chemical-free promise but sceptical of efficacy, especially for ultrasonic devices.",
        "insight": "Electronic mosquito solutions are the category's fastest-growing segment by consumer interest, driven by the dual appeal of being chemical-free and visually satisfying (the 'zap' factor). However, the segment is plagued by low-quality products and dubious efficacy claims, particularly from ultrasonic devices that multiple Reddit users call 'complete scams'. The gap between consumer interest and product quality represents both a risk and an opportunity.",
        "implication": "A trusted brand entering the electronic segment with genuinely effective, well-designed products could dominate a space currently filled with generic imports. The 'chemical-free' positioning of electronic solutions directly addresses the safety concerns identified in Theme 3.",
        "recommendation": "If entering the electronic segment, focus on UV trap + fan combination (proven effective) rather than ultrasonic (unproven). Design for the bedroom use case (quiet, no blue light, automatic). Build credibility through transparent efficacy data and money-back guarantees.",
        "further_validation": "Conduct comparative efficacy testing of electronic vs chemical solutions in controlled bedroom environments. Survey consumer willingness-to-pay for a branded electronic solution vs generic imports.",
    },
    "INS_007": {
        "observation": "Dengue and Disease Fear spans 522 items (9.7%) with NSS +0.366. Disease prevention is cited as a motivation for repellent use, but the language is more informational than emotional compared to the sleep disruption theme. Public health messaging, travel advisories, and seasonal outbreak warnings drive this conversation.",
        "insight": "Disease prevention is the rational justification for repellent purchase but not the primary emotional driver. Consumers cite dengue and malaria as reasons to buy repellents, but the urgency peaks seasonally during outbreaks and then subsides. Sleep disruption, by contrast, is a year-round, nightly pain point. This suggests that disease-fear marketing has a ceiling - it motivates purchase during epidemics but does not sustain habitual use.",
        "implication": "Brands that rely solely on disease-fear messaging will see cyclical demand spikes but struggle with year-round sales. The more sustainable positioning combines sleep protection (daily motivation) with disease prevention (rational reinforcement) - 'protect your sleep and your health'.",
        "recommendation": "Use disease prevention as a secondary reinforcement message, not the primary positioning. Lead with sleep quality and comfort, then layer in health protection. During outbreak seasons, amplify the disease prevention messaging but maintain the sleep-quality foundation year-round.",
        "further_validation": "Track purchase intent correlation with dengue case counts to quantify the seasonal disease-fear effect. Test messaging that combines sleep and disease prevention vs each alone.",
    },
    "INS_008": {
        "observation": "Brand Perceptions and Comparisons spans 614 items (11.4%) with NSS +0.391. Good Knight, All Out, Mortein, Odomos, Hit, Raid, and Thermacell are mentioned. Indian consumers default to Good Knight and All Out for indoor vaporizers, Odomos for personal application. Global consumers reference OFF!, Raid, and Thermacell. Reddit shows the most comparative brand discussion.",
        "insight": "The mosquito repellent category has strong regional brand loyalty but weak emotional brand differentiation. Consumers choose brands based on habit and availability rather than meaningful product differences. Most brand mentions are functional ('I use Good Knight') rather than emotional ('I love Good Knight'). This creates vulnerability - habitual loyalty can be broken by a new entrant with a compelling differentiated proposition.",
        "implication": "Incumbent brands are sitting on borrowed loyalty. Any brand that creates genuine emotional differentiation - through superior efficacy, safety credibility, design innovation, or lifestyle positioning - can disrupt category habits. The functional-only loyalty also means private labels and D2C brands face lower switching barriers than in categories with strong emotional bonds.",
        "recommendation": "Audit current brand positioning against competitors - identify the white space between functional parity and emotional differentiation. Invest in building emotional brand equity beyond 'kills mosquitoes'. Consider a repositioning around the sleep-protection or child-safety angles where emotional stakes are highest.",
        "further_validation": "Run a brand equity study measuring aided/unaided awareness, consideration, preference, and emotional associations for top 5 brands in key markets.",
    },
    "INS_009": {
        "observation": "Outdoor and Travel Protection spans 866 items (16.1%) with NSS +0.607. Hiking, camping, travel, garden, and patio use cases are discussed. DEET-based sprays and Thermacell devices dominate the outdoor segment. Travellers to tropical destinations show the highest urgency.",
        "insight": "The outdoor segment has fundamentally different needs from the indoor segment - portability, duration, and water resistance matter more than being chemical-free or quiet. Outdoor consumers are also more willing to accept DEET because the perceived risk of disease in tropical travel outweighs chemical safety concerns. This is the one context where disease prevention genuinely drives purchase behaviour.",
        "implication": "Outdoor and indoor mosquito protection are effectively separate markets that happen to share a category name. A one-size-fits-all product strategy will underserve both. The outdoor segment offers higher margins (travellers are less price-sensitive) and stronger efficacy demands.",
        "recommendation": "Develop distinct product lines for indoor (bedroom-optimised, quiet, chemical-free options) and outdoor (portable, long-lasting, high-efficacy) use cases. For outdoor, partner with travel and outdoor retail channels. For tropical travel, create travel-sized kits with multiple application methods.",
        "further_validation": "Map the purchase journey for outdoor vs indoor use cases to identify different decision points, channels, and price sensitivity.",
    },
    "INS_010": {
        "observation": "Mosquito Nets and Physical Barriers spans 901 items (16.7%) with NSS +0.486. Bed nets, window screens, foldable baby nets, and DIY mesh solutions are widely discussed. YouTube drives most of this content through product reviews and installation guides.",
        "insight": "Physical barriers remain the most trusted form of mosquito protection because they are visible, chemical-free, and perceived as 100% effective within their coverage area. The popularity of nets reflects a consumer preference for certainty over probability - a net guarantees no bites within its enclosure, while sprays and vaporizers offer probabilistic protection. This certainty preference is strongest among parents.",
        "implication": "Physical barriers and chemical/electronic repellents are complementary, not competing. A layered protection strategy (net + vaporizer, screen + spray) matches how consumers actually behave. Brands that sell single-method solutions are leaving money on the table.",
        "recommendation": "Develop bundled protection packages: bed net + nighttime vaporizer, window screen + outdoor spray. Position layered protection as the gold standard rather than competing on single products. For baby products, a net + natural repellent bundle addresses both the certainty need and the chemical-free need.",
        "further_validation": "Survey consumers on current layered protection behaviour and willingness to buy pre-bundled multi-method solutions.",
    },
    "INS_011": {
        "observation": "Coils and Traditional Methods spans 274 items (5.1%) with NSS +0.420. Mosquito coils, incense-style repellents, and traditional smoking methods are discussed primarily by consumers in South and Southeast Asia and rural Africa.",
        "insight": "Coils represent the 'value floor' of the category - the cheapest and most accessible form of mosquito protection, still relied upon by price-sensitive and rural consumers. However, coils are increasingly seen as outdated and unhealthy. The conversation reveals a transition market: consumers want to upgrade from coils but need affordable alternatives that work without electricity.",
        "implication": "The coil-to-modern transition represents a large volume opportunity in emerging markets. Consumers leaving coils want something better but cannot afford premium electronic or branded natural products. The sweet spot is a mid-price, non-electric, lower-fume alternative.",
        "recommendation": "For emerging markets, develop a 'coil upgrade' product at 1.5-2x the price point of traditional coils with significantly reduced smoke/fumes. Position explicitly as the step up from coils. Distribute through the same traditional retail channels where coils currently dominate.",
        "further_validation": "Map the coil market size and consumer upgrade path in key emerging markets (India, Southeast Asia, Sub-Saharan Africa).",
    },
    "INS_012": {
        "observation": "Product Innovation and Wish List spans 986 items (18.3%) with NSS +0.494. Consumers express unmet needs including: all-night protection that does not require refills, solutions for large outdoor spaces, products safe enough to apply on babies, repellents that do not stain clothes, and wearable devices that actually work.",
        "insight": "The innovation conversation reveals that consumers see the category as stagnant. The most common wish-list items - longer duration, no refills, genuinely safe for babies, no staining, no smell - are basic product quality improvements rather than revolutionary innovations. This suggests that existing products fail on fundamental attributes, creating opportunity for brands willing to solve obvious problems.",
        "implication": "The category has been competing on price and distribution rather than product quality. A brand that systematically addresses the top 5 consumer complaints (short duration, frequent refills, chemical concerns, smell, staining) would create significant differentiation in a commoditised market.",
        "recommendation": "Prioritise R&D investment in: (1) extended-duration formulations (8+ hours, no midnight refill), (2) genuinely odourless or pleasant-scented products, (3) non-staining formulations, (4) paediatrician-certified baby-safe range. Each solved complaint becomes a marketing message.",
        "further_validation": "Run a MaxDiff or conjoint study on the relative importance of innovation attributes (duration, smell, safety, staining, price) to prioritise R&D investment.",
    },
    "INS_013": {
        "observation": "Vaporizers and Liquid Refills spans 781 items (14.5%) with NSS +0.529. Electric liquid vaporizers are the most discussed product format for indoor use. Refill frequency, refill cost, and compatibility between devices and refills are common concerns.",
        "insight": "The vaporizer market operates on a razor-and-blade model where the device is cheap but refill revenue is the real margin driver. Consumers are acutely aware of this and express frustration about refill costs, brand lock-in, and refill duration claims that do not match reality. The refill experience is the primary source of brand dissatisfaction in the indoor segment.",
        "implication": "Refill economics are a double-edged sword: they generate recurring revenue but also generate recurring friction. A brand that offers genuinely longer-lasting refills or a more transparent refill pricing model could win significant market share from frustrated consumers.",
        "recommendation": "Extend refill duration meaningfully (not just on the label). Consider a subscription refill model with automatic delivery. Introduce a universal-fit refill that works across multiple device brands to capture frustrated consumers locked into competitors' ecosystems.",
        "further_validation": "Survey vaporizer users on refill satisfaction, frequency of repurchase, and willingness to switch brands for longer-lasting or cheaper refills.",
    },
    "INS_014": {
        "observation": "Smell and Sensory Experience spans 371 items (6.9%) with NSS +0.488. Consumers complain about strong chemical smells, smoky fumes from coils, and headache-inducing fragrances. Positive sentiment focuses on 'no smell' products and pleasant natural scents.",
        "insight": "Smell is a hygiene factor that consumers notice only when it is wrong. A bad smell creates an immediate negative association with the entire product category, while a neutral or pleasant smell is taken for granted. The prevalence of smell complaints suggests that many products still fail this basic test, particularly coils and lower-end vaporizers.",
        "implication": "Sensory experience is an under-invested dimension of product development in this category. Premium-tier products in adjacent categories (home fragrance, personal care) have demonstrated that scent can be a premium differentiator. There is white space for a 'mosquito repellent that smells good' rather than merely 'does not smell bad'.",
        "recommendation": "Reformulate products to eliminate chemical odour. For premium positioning, develop signature scent profiles (lavender-eucalyptus, citrus-mint) that make the repellent experience pleasant rather than merely tolerable. Use scent as a brand differentiator.",
        "further_validation": "Conduct sensory panels testing consumer preference across scent profiles. Measure willingness-to-pay premium for pleasant-scented vs unscented vs traditional-scented repellents.",
    },
    "INS_015": {
        "observation": "Price and Value Perception spans 518 items (9.6%) with NSS +0.600. Consumers discuss product pricing, refill costs, value for money, and budget alternatives. The positive NSS suggests that many consumers find acceptable value, but a significant minority feels products are overpriced relative to their performance.",
        "insight": "Price sensitivity in this category is not uniform - it varies dramatically by use context. Indoor vaporizer refills face intense price scrutiny (daily recurring cost), while travel and outdoor sprays face almost none (one-off, high-urgency purchase). Baby products occupy a middle ground where parents accept premium pricing but expect correspondingly higher quality and safety standards.",
        "implication": "A single pricing strategy across all product formats and use cases will leave money on the table in some segments and lose share in others. The refill business needs to compete on perceived value-per-night, while outdoor and baby products can command significant premiums.",
        "recommendation": "Implement segment-specific pricing: aggressive value positioning for indoor refills (emphasise cost-per-night), premium pricing for baby-safe and outdoor ranges (emphasise efficacy and safety). Consider a 'good-better-best' product tier strategy within each format.",
        "further_validation": "Run a price sensitivity study (Van Westendorp or Gabor-Granger) segmented by use case and product format.",
    },
}

for ins in insights:
    if ins.insight_id in SYNTHESIS:
        s = SYNTHESIS[ins.insight_id]
        ins.observation = s["observation"]
        ins.insight = s["insight"]
        ins.implication = s["implication"]
        ins.recommendation = s["recommendation"]
        ins.further_validation = s["further_validation"]

# Save
insights_data = [ins.model_dump(mode="json") for ins in insights]
(RUN_DIR / "insights" / "insights.json").write_text(
    json.dumps(insights_data, indent=2, default=str), encoding="utf-8"
)
print(f"Synthesized {len(SYNTHESIS)} insights -> {RUN_DIR / 'insights' / 'insights.json'}")
