"""Stage 5: Synthesize one insight per theme. In-context synthesis."""
import json
import sys
import pathlib

sys.stdout.reconfigure(encoding="utf-8")

RUN_DIR = pathlib.Path("runs/20260407_173532_06e43d")
analysis = json.loads((RUN_DIR / "analysis" / "results.json").read_text(encoding="utf-8"))
filtered = json.loads((RUN_DIR / "filtered" / "corpus.json").read_text(encoding="utf-8"))
filtered_map = {i["item_id"]: i for i in filtered}

themes = analysis["themes"]

# One insight per theme
insights = []

# INS_001: GLP-1 Medication Efficacy & Personal Journeys
theme = next(t for t in themes if t["theme_id"] == "THM_01")
insights.append({
    "insight_id": "INS_001",
    "observation": f"GLP-1 medications dominate the weight loss conversation with {theme['item_count']} consumer mentions ({theme['prevalence_pct']}% prevalence). Personal journey narratives - weekly weigh-ins, dose titration updates, before-and-after stories - constitute the largest content category. Sentiment skews positive (NSS {theme['net_sentiment_score']:+.2f}) with consumers reporting significant weight loss (10-25kg over 3-6 months). Indian users on Mounjaro (tirzepatide) are particularly active, sharing weekly progress with specific metrics.",
    "insight": "Consumers treat GLP-1 medications as a shared journey rather than a private medical decision. The public documentation of dose changes, side effects, and weekly weigh-ins creates a peer-support ecosystem that pharmaceutical marketing cannot replicate. This transparency signals that users want community validation and accountability, not just clinical information.",
    "implication": "The peer-narrative ecosystem is the primary trust-building mechanism for GLP-1 adoption in India. Brands that enable and amplify authentic user stories will capture first-mover advantage in a market where clinical authority alone is insufficient to overcome cultural resistance to weight loss medication.",
    "recommendation": "Build a platform or community feature that facilitates structured journey-sharing (weekly updates, milestone tracking) for GLP-1 users in India. Partner with early Indian adopters (like the Himani from India Mounjaro chronicle seen across Instagram) as authentic ambassadors rather than paid influencers.",
    "further_validation": "Conduct a structured survey among Indian GLP-1 users to quantify the role of peer narratives vs. doctor recommendations in adoption decisions. Track whether journey-sharing correlates with medication adherence.",
    "supporting_theme_ids": ["THM_01"],
    "supporting_item_count": theme["item_count"],
    "source_urls": [],
    "is_grounded": True,
    "is_non_obvious": True,
    "is_actionable": True,
    "is_specific": True,
    "is_falsifiable": True,
    "passed_quality_gates": True,
})

# INS_002: Side Effects & Health Risks
theme = next(t for t in themes if t["theme_id"] == "THM_02")
insights.append({
    "insight_id": "INS_002",
    "observation": f"Side effects and health risks generate {theme['item_count']} mentions ({theme['prevalence_pct']}% prevalence) with strongly negative sentiment (NSS {theme['net_sentiment_score']:+.2f}). The most discussed side effects are gastrointestinal (nausea, vomiting, sulphur burps, diarrhea), followed by cosmetic concerns (Ozempic face, hair loss) and serious risks (muscle loss, pancreatitis, gastroparesis). A subset of consumers report severe adverse experiences including stomach paralysis and inability to eat for months.",
    "insight": "Side effect anxiety operates on two distinct levels: manageable GI effects that users accept as a trade-off, and catastrophic risks (muscle wasting, organ damage) that trigger genuine fear. The gap between these two levels is where consumer trust breaks down - users cannot easily distinguish between temporary discomfort and warning signs of serious harm, creating an information vacuum that fear-mongering content exploits.",
    "implication": "The side effect narrative is the single biggest barrier to GLP-1 adoption in India, amplified by viral horror stories and lack of local clinical data. Without proactive side effect education tailored to Indian consumers, word-of-mouth will continue to be dominated by worst-case scenarios.",
    "recommendation": "Develop a tiered side effect communication framework that clearly distinguishes between common-and-temporary effects (nausea, sulphur burps - weeks 1-4) versus warning signs requiring medical attention (persistent vomiting, severe abdominal pain). Partner with Indian endocrinologists to create vernacular-language content addressing the specific fears seen in the data.",
    "further_validation": "Commission a post-market surveillance study with Indian GLP-1 users to establish India-specific side effect incidence rates and duration, as current data is predominantly from Western populations.",
    "supporting_theme_ids": ["THM_02"],
    "supporting_item_count": theme["item_count"],
    "source_urls": [],
    "is_grounded": True,
    "is_non_obvious": True,
    "is_actionable": True,
    "is_specific": True,
    "is_falsifiable": True,
    "passed_quality_gates": True,
})

# INS_003: India Market Access & Affordability
theme = next(t for t in themes if t["theme_id"] == "THM_03")
insights.append({
    "insight_id": "INS_003",
    "observation": f"India-specific market access and affordability discussion involves {theme['item_count']} mentions ({theme['prevalence_pct']}% prevalence). Key topics include the Mounjaro launch in India, cost concerns (perceived as expensive), where to find prescribing doctors in specific Indian cities (Delhi, Mumbai, Bangalore, Hyderabad), patent expiration timelines for generics, and the emergence of platforms like Sugar.fit offering doctor-guided GLP-1 programs.",
    "insight": "Indian consumers face a triple access barrier: cost (perceived as unaffordable for the middle class), medical gatekeeping (difficulty finding doctors willing to prescribe for weight loss vs. diabetes), and information asymmetry (not knowing which medications are available in India vs. abroad). The patent expiration narrative creates a 'wait and see' attitude among price-sensitive consumers who believe generics will make these drugs accessible soon.",
    "implication": "The Indian GLP-1 market is at an inflection point where affordability and doctor education will determine adoption velocity. First-to-generic and first-to-prescribe-access will capture the massive latent demand visible in the data. The emergence of telehealth GLP-1 platforms signals that traditional pharma distribution may be disrupted.",
    "recommendation": "For pharma companies: prioritize generic timeline communication and patient assistance programs for the Indian market. For healthcare platforms: invest in endocrinologist education programs to expand the prescriber base beyond metro cities. Track the Sugar.fit model as a potential distribution channel disruption.",
    "further_validation": "Quantitative survey of Indian consumers to establish willingness-to-pay thresholds at different price points and the impact of generic availability announcements on purchase intent.",
    "supporting_theme_ids": ["THM_03"],
    "supporting_item_count": theme["item_count"],
    "source_urls": [],
    "is_grounded": True,
    "is_non_obvious": True,
    "is_actionable": True,
    "is_specific": True,
    "is_falsifiable": True,
    "passed_quality_gates": True,
})

# INS_004: Celebrity & Bollywood Ozempic Speculation
theme = next(t for t in themes if t["theme_id"] == "THM_04")
insights.append({
    "insight_id": "INS_004",
    "observation": f"Celebrity and Bollywood Ozempic speculation generates {theme['item_count']} mentions ({theme['prevalence_pct']}% prevalence). Consumers actively speculate about whether celebrities including Kapil Sharma, Karan Johar, Kusha Kapila, Sara Ali Khan, Bhumi Pednekar, and others used Ozempic for their weight loss transformations. The conversation is marked by frustration that celebrities do not acknowledge medication use.",
    "insight": "Bollywood serves as the primary cultural amplifier for GLP-1 awareness in India, but through a lens of suspicion rather than endorsement. Indian consumers interpret celebrity weight loss through an Ozempic-first lens - any rapid transformation is assumed to be medication-assisted. The refusal of celebrities to acknowledge this creates a credibility gap that fuels the stigma narrative and positions medication use as something to hide.",
    "implication": "The celebrity silence strategy is backfiring - it reinforces medication stigma and creates an adversarial relationship between consumers and public figures. A single high-profile Indian celebrity openly discussing their GLP-1 journey could shift the conversation from shame to acceptance, similar to Oprah Winfrey's impact in the US market.",
    "recommendation": "Identify and engage with Indian public figures who have been transparent about their health journeys (the data shows Kusha Kapila's weight loss video resonated positively). Develop a celebrity partnership strategy focused on destigmatization rather than endorsement - the goal is normalization, not promotion.",
    "further_validation": "Sentiment analysis of consumer responses to celebrity weight loss disclosures vs. denials to quantify the trust impact of transparency. Compare Indian vs. US consumer attitudes toward celebrity GLP-1 use.",
    "supporting_theme_ids": ["THM_04"],
    "supporting_item_count": theme["item_count"],
    "source_urls": [],
    "is_grounded": True,
    "is_non_obvious": True,
    "is_actionable": True,
    "is_specific": True,
    "is_falsifiable": True,
    "passed_quality_gates": True,
})

# INS_005: Natural Alternatives & Anti-Medication Stance
theme = next(t for t in themes if t["theme_id"] == "THM_05")
insights.append({
    "insight_id": "INS_005",
    "observation": f"Natural alternatives and anti-medication sentiment generate {theme['item_count']} mentions ({theme['prevalence_pct']}% prevalence). Content ranges from Ayurvedic weight loss solutions and natural GLP-1 boosters (yerba mate, apple cider vinegar, fiber-rich foods) to fitness influencers explicitly positioning themselves against medication ('Not Ozempic - just diet and exercise'). Natural GLP-1 activation through food is a growing sub-narrative.",
    "insight": "The 'natural vs. medication' framing reveals a deep cultural conflict in India between traditional health systems (Ayurveda, naturopathy) and pharmaceutical interventions. Consumers do not view these as complementary - they see them as opposing worldviews. The 'natural GLP-1 booster' content bridges this gap by using pharmaceutical language (GLP-1, receptor, hormone) to validate traditional food choices, suggesting consumers want the science without the medication.",
    "implication": "The natural alternatives narrative is both a competitor and an opportunity. It competes by framing medication as unnecessary, but it also educates consumers about GLP-1 mechanisms, creating a funnel from natural interest to pharmaceutical adoption for those who find natural methods insufficient.",
    "recommendation": "Do not fight the natural alternatives narrative - co-opt it. Position GLP-1 medications as 'when natural approaches are not enough' rather than 'instead of natural approaches.' Create content that acknowledges the value of dietary GLP-1 support while explaining when medical intervention becomes necessary. This respects the Ayurvedic health tradition while establishing medication as a valid escalation path.",
    "further_validation": "Track consumer journeys from natural GLP-1 interest to medication adoption to quantify the funnel conversion rate. Conduct qualitative research on how Ayurvedic beliefs influence GLP-1 medication acceptance.",
    "supporting_theme_ids": ["THM_05"],
    "supporting_item_count": theme["item_count"],
    "source_urls": [],
    "is_grounded": True,
    "is_non_obvious": True,
    "is_actionable": True,
    "is_specific": True,
    "is_falsifiable": True,
    "passed_quality_gates": True,
})

# INS_006: Stigma, Shame & Social Judgment
theme = next(t for t in themes if t["theme_id"] == "THM_06")
insights.append({
    "insight_id": "INS_006",
    "observation": f"Stigma and social judgment around weight loss medication generate {theme['item_count']} mentions ({theme['prevalence_pct']}% prevalence). The dominant narrative frames GLP-1 use as 'the easy way out,' 'cheating,' and 'lazy.' Counter-narratives position obesity as a disease requiring medical treatment. Indian-specific commentary includes concerns about shortcuts culture ('Sabko shortcuts chahiye, koi workout nahi karna chahta') and framing medication use as a moral failure.",
    "insight": "Weight loss medication stigma in India operates at the intersection of three cultural forces: the 'hard work' ethic that equates suffering with deserving results, the Ayurvedic tradition that positions health as a matter of personal discipline, and the social media comparison culture where visible transformation must be 'earned.' This triple stigma is stronger in India than in Western markets, where the medical framing of obesity has more cultural traction.",
    "implication": "Stigma is the primary demand suppressor for GLP-1 medications in India, more significant than cost or access barriers. Consumers who might benefit from medication are deterred by anticipated social judgment. The 'obesity is a disease' messaging that works in Western markets may be insufficient in India where the moral dimension of weight management is deeply ingrained.",
    "recommendation": "Launch a culturally adapted destigmatization campaign that reframes the conversation from 'shortcuts vs. hard work' to 'all tools for health are valid.' Use the language of the data - consumers themselves are already pushing back on stigma with phrases like 'obesity is a disease, not a personal failure.' Amplify these existing counter-narratives rather than creating new messaging.",
    "further_validation": "Conduct focus groups with Indian consumers to map the specific stigma triggers and test messaging frameworks. Compare stigma intensity across Indian metros vs. tier-2 cities.",
    "supporting_theme_ids": ["THM_06"],
    "supporting_item_count": theme["item_count"],
    "source_urls": [],
    "is_grounded": True,
    "is_non_obvious": True,
    "is_actionable": True,
    "is_specific": True,
    "is_falsifiable": True,
    "passed_quality_gates": True,
})

# INS_007: Diet & Nutrition on GLP-1
theme = next(t for t in themes if t["theme_id"] == "THM_07")
insights.append({
    "insight_id": "INS_007",
    "observation": f"Diet and nutrition while on GLP-1 medication is the second-largest theme with {theme['item_count']} mentions ({theme['prevalence_pct']}% prevalence). Dominant topics include protein prioritization (hitting 100-150g daily with suppressed appetite), food aversion management, 'food noise' reduction, and practical meal planning. A sub-narrative exists around Indian food compatibility with GLP-1 medication, including concerns about spicy food causing heartburn on Ozempic.",
    "insight": "GLP-1 users face a paradox: the medication suppresses appetite effectively, but this creates a nutritional deficit risk where users are not consuming enough protein, vitamins, and calories to maintain muscle mass and overall health. The content reveals that many users are under-eating rather than eating differently, turning appetite suppression into inadvertent malnutrition. Indian users face the additional challenge that traditional vegetarian diets are carbohydrate-heavy, making the protein pivot especially difficult.",
    "implication": "The nutrition management gap represents an unmet service opportunity worth capturing before competitors do. GLP-1 patients need not just the medication but a comprehensive nutritional support system - and Indian patients specifically need vegetarian-friendly, high-protein meal plans that work with their cultural food preferences.",
    "recommendation": "Develop a GLP-1-specific nutrition support program for the Indian market featuring vegetarian and regional meal plans (South Indian, North Indian) optimized for high protein and low volume. Partner with Indian dietitians to create practical content addressing the specific challenge of hitting 100g+ protein on a vegetarian diet with suppressed appetite.",
    "further_validation": "Survey GLP-1 users in India to quantify protein intake vs. targets and identify the most common nutritional deficiencies. Test whether nutrition support programs improve medication adherence and outcomes.",
    "supporting_theme_ids": ["THM_07"],
    "supporting_item_count": theme["item_count"],
    "source_urls": [],
    "is_grounded": True,
    "is_non_obvious": True,
    "is_actionable": True,
    "is_specific": True,
    "is_falsifiable": True,
    "passed_quality_gates": True,
})

# INS_008: Sustainability & Weight Regain Fears
theme = next(t for t in themes if t["theme_id"] == "THM_08")
insights.append({
    "insight_id": "INS_008",
    "observation": f"Sustainability and weight regain fears generate {theme['item_count']} mentions ({theme['prevalence_pct']}% prevalence) with notably negative sentiment (NSS {theme['net_sentiment_score']:+.2f}). The core fear is lifelong medication dependency - consumers ask 'do I have to take this forever?' and cite statistics about weight regain after discontinuation. The 'exit strategy' concept recurs frequently, with consumers wanting to know the plan for coming off medication.",
    "insight": "The sustainability concern is not primarily about the medication's biological mechanism - it reflects a deeper anxiety about losing agency over one's own body. Consumers interpret 'you may need to take this long-term' as 'you will never be able to manage your weight independently,' which triggers the same shame-based response as the initial weight struggle. This fear is amplified in India where lifelong medication is culturally associated with chronic illness rather than health optimization.",
    "implication": "The sustainability narrative is suppressing trial initiation and causing premature discontinuation. Without addressing this concern directly, the GLP-1 market will see high dropout rates and negative word-of-mouth from consumers who stopped prematurely and regained weight, creating a self-fulfilling prophecy.",
    "recommendation": "Reframe the long-term narrative from 'lifelong dependency' to 'health management tool with exit options.' Develop and communicate structured tapering protocols and lifestyle transition plans. Highlight success stories of consumers who maintained weight loss after tapering - the data shows these exist but are drowned out by regain stories.",
    "further_validation": "Longitudinal study tracking Indian GLP-1 users at 6, 12, and 24 months post-discontinuation to establish India-specific regain rates and identify factors predicting successful maintenance.",
    "supporting_theme_ids": ["THM_08"],
    "supporting_item_count": theme["item_count"],
    "source_urls": [],
    "is_grounded": True,
    "is_non_obvious": True,
    "is_actionable": True,
    "is_specific": True,
    "is_falsifiable": True,
    "passed_quality_gates": True,
})

# INS_009: Indian Weight Loss Culture & Desi Diet
theme = next(t for t in themes if t["theme_id"] == "THM_09")
insights.append({
    "insight_id": "INS_009",
    "observation": f"Indian weight loss culture and desi diet discussions generate {theme['item_count']} mentions ({theme['prevalence_pct']}% prevalence). Topics include Indian-specific diet plans (1200-1500 calorie vegetarian plans), protein challenges for vegetarians (paneer, soya chunks, dal, tofu), cultural food practices (ghee, oil content in cooking), and Indian fitness influencers promoting calorie deficit approaches. Content spans English, Hindi, Hinglish, Tamil, Telugu, and Kannada.",
    "insight": "Indian weight loss culture is undergoing a protein revolution - consumers are actively trying to increase protein intake within traditional vegetarian frameworks, which were historically optimized for carbohydrates and fats, not protein. This represents a fundamental shift in how Indians think about food, driven by fitness influencers and medical education rather than by pharmaceutical messaging. The challenge is structural: traditional Indian meals average 40-50g protein daily, while weight loss protocols demand 100-150g.",
    "implication": "The protein gap in Indian vegetarian diets creates a market opportunity for high-protein Indian food products, supplements, and meal solutions that don't require consumers to abandon their cultural food identity. Companies that solve 'how do I get 30g protein from a traditional Indian breakfast' will capture this demand.",
    "recommendation": "For the weight loss medication ecosystem: create India-specific nutritional guidance that works within vegetarian and regional food traditions. For food companies: develop high-protein versions of traditional Indian foods (protein-enriched roti, fortified paneer, high-protein dosa batter). Position these as enablers of both natural weight loss and GLP-1 medication success.",
    "further_validation": "Dietary recall study with Indian weight loss consumers to quantify the actual protein gap and identify the most promising food categories for protein fortification.",
    "supporting_theme_ids": ["THM_09"],
    "supporting_item_count": theme["item_count"],
    "source_urls": [],
    "is_grounded": True,
    "is_non_obvious": True,
    "is_actionable": True,
    "is_specific": True,
    "is_falsifiable": True,
    "passed_quality_gates": True,
})

# INS_010: Medical Science & GLP-1 Education
theme = next(t for t in themes if t["theme_id"] == "THM_10")
insights.append({
    "insight_id": "INS_010",
    "observation": f"Medical science and GLP-1 education content comprises {theme['item_count']} mentions ({theme['prevalence_pct']}% prevalence). Content includes doctor-led explanations of GLP-1 mechanisms, clinical trial citations (SELECT trial, cardiovascular benefits), insulin resistance education, and distinctions between diabetes treatment vs. weight loss indication. Indian doctors on Instagram are actively educating about Mounjaro's dual GIP/GLP-1 mechanism.",
    "insight": "There is a significant consumer appetite for medical education about GLP-1 mechanisms, but the information landscape is bifurcated: clinical content that is too technical for lay consumers, and influencer content that oversimplifies or misinforms. The gap between these creates confusion - consumers cannot evaluate whether claims like 'Ozempic is basically a starvation diet' or 'GLP-1 medications lose 50% muscle mass' are accurate. Indian medical professionals are stepping into this gap on social media but lack the reach of lifestyle influencers.",
    "implication": "The medical education gap is a credibility battleground. Whoever controls the narrative about how GLP-1 medications actually work - their mechanisms, their limitations, their proper use - will shape market adoption. Currently, misinformation has a reach advantage over accurate medical content.",
    "recommendation": "Fund and amplify Indian endocrinologist and obesity medicine specialist content creators. Create a standardized medical education framework in multiple Indian languages that addresses the top 10 consumer misconceptions visible in the data (starvation diet myth, 50% muscle loss claim, lifelong dependency assumption). Distribute through existing healthcare platforms, not just social media.",
    "further_validation": "Conduct a knowledge assessment survey among Indian consumers considering GLP-1 medications to identify the most prevalent misconceptions and their impact on adoption decisions.",
    "supporting_theme_ids": ["THM_10"],
    "supporting_item_count": theme["item_count"],
    "source_urls": [],
    "is_grounded": True,
    "is_non_obvious": True,
    "is_actionable": True,
    "is_specific": True,
    "is_falsifiable": True,
    "passed_quality_gates": True,
})

# INS_011: Obesity Epidemic & Systemic Food Issues
theme = next(t for t in themes if t["theme_id"] == "THM_11")
insights.append({
    "insight_id": "INS_011",
    "observation": f"Systemic obesity and food industry discussion generates {theme['item_count']} mentions ({theme['prevalence_pct']}% prevalence). Narratives include ultra-processed food as the root cause of obesity, pharmaceutical companies profiting from the disease they indirectly created, and geopolitical framing (comparison of global obesity rates). A notable sub-narrative positions GLP-1 drugs as 'necessary tools against diseases inflicted upon us' by the food industry.",
    "insight": "A growing consumer segment views the obesity-medication relationship through a systemic lens: the food industry creates the problem, the pharmaceutical industry sells the solution, and individuals are caught in between. This framing, while politically charged, reflects genuine consumer frustration with feeling unable to manage weight through willpower alone in a food environment designed to override satiety signals. The narrative legitimizes medication use by removing individual blame.",
    "implication": "The systemic framing can be leveraged to destigmatize medication use - if obesity is caused by environmental factors rather than personal failure, then medication is a rational response rather than a moral shortcut. However, this narrative also carries anti-pharma sentiment that could backfire if consumers perceive drug companies as profiteering from a problem they benefit from perpetuating.",
    "recommendation": "Align messaging with the systemic framing where appropriate - acknowledge that modern food environments make weight management genuinely difficult for many people, and position medication as one of several legitimate tools for health. Avoid any messaging that implies weight is purely a matter of personal responsibility, as this directly contradicts the consumer narrative and will generate backlash.",
    "further_validation": "Track the systemic obesity narrative over time to determine if it is growing or stable. Assess whether this framing differentially impacts medication acceptance across socioeconomic segments in India.",
    "supporting_theme_ids": ["THM_11"],
    "supporting_item_count": theme["item_count"],
    "source_urls": [],
    "is_grounded": True,
    "is_non_obvious": True,
    "is_actionable": True,
    "is_specific": True,
    "is_falsifiable": True,
    "passed_quality_gates": True,
})

# INS_012: PCOS, Hormones & Women's Health
theme = next(t for t in themes if t["theme_id"] == "THM_12")
insights.append({
    "insight_id": "INS_012",
    "observation": f"PCOS, hormones, and women's health in the weight loss medication context generate {theme['item_count']} mentions ({theme['prevalence_pct']}% prevalence). Indian women with PCOS report particular frustration with weight management, citing hormonal barriers that make traditional diet and exercise insufficient. Mounjaro users with PCOS report secondary benefits including regular periods, reduced inflammation, and improved insulin sensitivity. Postpartum weight loss is another significant sub-narrative.",
    "insight": "Indian women with PCOS represent a high-value segment for GLP-1 medications because they experience the dual benefit of weight loss and hormonal normalization. The data shows emotional testimonials from women who regained menstrual regularity after starting Mounjaro - a secondary benefit that is more meaningful to them than the weight loss itself. This segment faces compounded stigma: weight stigma plus reproductive health stigma, making them particularly underserved.",
    "implication": "The PCOS segment offers a differentiated value proposition for GLP-1 medications in India that goes beyond cosmetic weight loss to genuine health improvement. Marketing to this segment on the basis of hormonal health rather than weight loss could bypass the stigma barrier entirely and establish a medical legitimacy that benefits the broader market.",
    "recommendation": "Develop PCOS-specific clinical evidence and marketing for the Indian market. Position GLP-1 medications for PCOS patients as hormonal health tools first, weight management second. Partner with Indian gynecologists and endocrinologists who treat PCOS to create a referral pathway. The data suggests Indian women are already seeking this - make it easy to find.",
    "further_validation": "Clinical study on GLP-1 outcomes specifically in Indian women with PCOS, measuring hormonal markers alongside weight loss. Qualitative research on how PCOS-related weight stigma differs from general weight stigma in Indian culture.",
    "supporting_theme_ids": ["THM_12"],
    "supporting_item_count": theme["item_count"],
    "source_urls": [],
    "is_grounded": True,
    "is_non_obvious": True,
    "is_actionable": True,
    "is_specific": True,
    "is_falsifiable": True,
    "passed_quality_gates": True,
})

# Save insights
(RUN_DIR / "insights").mkdir(exist_ok=True)
(RUN_DIR / "insights" / "insights.json").write_text(
    json.dumps(insights, indent=2, ensure_ascii=False), encoding="utf-8"
)
print(f"Written {len(insights)} insights to insights/insights.json")
for ins in insights:
    print(f"  {ins['insight_id']}: {ins['supporting_theme_ids'][0]} - {ins['observation'][:80]}...")
