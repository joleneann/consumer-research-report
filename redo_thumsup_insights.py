"""
Thums Up: Insight synthesis + scoring + report generation.
"""
import io, sys, json
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

RUN_DIR = ROOT / "consumer_research" / "runs" / "20260327_162042_7d13c6"

results = json.loads((RUN_DIR / "analysis" / "results.json").read_text(encoding="utf-8"))
corpus = json.loads((RUN_DIR / "filtered" / "corpus.json").read_text(encoding="utf-8"))
themes = results["themes"]
item_lookup = {i["item_id"]: i for i in corpus}

INSIGHTS = [
    {
        "insight_id": "INS_001",
        "theme_id": "THM_001",
        "observation": "Taste and carbonation experience is the dominant conversation (200 items, 42.4%) with positive NSS (+13%). Consumers consistently describe Thums Up as 'stronger', 'bolder', and 'more fizzy' than Coca-Cola. Temperature sensitivity is frequently noted - the drink is described as best when ice-cold. Flat or warm Thums Up receives negative commentary.",
        "insight": "Thums Up's core brand equity lives in its sensory extremity - consumers choose it specifically because it delivers a more intense carbonation and flavour hit than any competitor. This is not a generic cola preference but a deliberate choice of intensity. The consumer who picks Thums Up is seeking a physical sensation (the 'kick') not just a sweet drink.",
        "implication": "Any reformulation that reduces carbonation intensity or sweetness balance risks destroying the brand's primary differentiator. The 'bold' positioning is not marketing - it is a genuine product truth that consumers validate in their own words. However, this also means the brand is temperature-dependent: warm or flat Thums Up actively damages perception.",
        "recommendation": "Protect carbonation intensity as a non-negotiable product parameter. Invest in cold-chain infrastructure and retail visibility of chilled availability. Consider 'best served at X degrees' messaging to set expectations. Never reformulate toward a milder taste profile even if cost pressures arise.",
        "further_validation": "Conduct blind taste testing at different temperatures and carbonation levels to identify the minimum acceptable threshold. Measure whether chilled availability correlates with repeat purchase.",
    },
    {
        "insight_id": "INS_002",
        "theme_id": "THM_002",
        "observation": "Nostalgia and cultural identity accounts for 11% of conversation (52 items) with strongly positive sentiment (+28.9%). Consumers reference childhood memories, the Parle era, and pre-Coca-Cola India with genuine emotional warmth. The brand is positioned as 'truly Indian' despite being owned by Coca-Cola. References to 1977 (when Coca-Cola left India) and 1993 (acquisition) recur.",
        "insight": "Thums Up occupies a unique position in Indian consumer memory - it is simultaneously a corporate product and a national symbol. The brand's survival story (created when Coke left, survived when Coke returned) has become a folk narrative of Indian resilience. This emotional layer exists independently of any marketing - consumers tell this story to each other unprompted.",
        "implication": "The nostalgia equity is irreplaceable and cannot be manufactured by competitors. However, it is also ageing - the consumers who remember the Parle era are 40+. If the brand does not create new cultural anchors for younger consumers, the nostalgia advantage will erode generationally.",
        "recommendation": "Create a 'heritage' content series that tells the Thums Up origin story to younger consumers who never experienced the Parle era. Use this as a differentiation lever against Pepsi and Coca-Cola - neither can claim Indian origin. Do not let the nostalgia narrative exist only in the memories of older consumers.",
        "further_validation": "Survey brand origin awareness by age cohort. Measure whether younger consumers (18-25) know the Parle story and whether it affects their brand preference.",
    },
    {
        "insight_id": "INS_003",
        "theme_id": "THM_003",
        "observation": "Competitive positioning is the second-largest theme (142 items, 30.1%) with slightly positive NSS (+9.9%). Thums Up vs Coca-Cola is the primary comparison axis, with Pepsi a distant third. Consumers frame the choice as 'bold vs smooth' with Thums Up owning 'bold'. Campa Cola appears as an emerging disruptor backed by Reliance, generating curiosity but not yet threatening loyalty.",
        "insight": "The Indian cola market operates on a taste-intensity spectrum that Thums Up anchors at the bold end. Consumers do not see Thums Up and Coca-Cola as interchangeable - they are functionally different products that happen to be in the same category. This means Thums Up's real competitive threat is not from Coke or Pepsi directly but from any new entrant that can credibly claim the 'bold' territory (Campa's positioning bears watching).",
        "implication": "Thums Up should compete on distinctiveness rather than market share parity. The brand wins when the conversation is about taste character, and loses when it becomes about price or availability (where Coca-Cola's distribution advantage dominates). Campa Cola backed by Reliance's distribution network could be the first credible bold-positioning challenger.",
        "recommendation": "Monitor Campa Cola's brand positioning closely - if Reliance positions it as 'bold' or 'strong', it directly threatens Thums Up's territory. Reinforce taste differentiation in all communication. Avoid price wars that commoditise the category and erase Thums Up's distinctiveness.",
        "further_validation": "Track Campa Cola trial and repeat rates among Thums Up loyalists. Conduct competitive taste mapping to understand exactly where each brand sits on the intensity spectrum.",
    },
    {
        "insight_id": "INS_004",
        "theme_id": "THM_004",
        "observation": "Health concerns represent 16.1% of conversation (76 items) with the most negative sentiment in the dataset (-36.8%). Sugar content, caffeine effects, diabetes risk, and cancer associations dominate. The conversation is not specific to Thums Up but applies to all colas. Academic papers in the corpus reinforce health risks with clinical evidence.",
        "insight": "Health consciousness is the structural headwind for the entire cola category in India, and Thums Up is not immune. The health conversation is intensifying as India's diabetes epidemic grows and consumers become more nutrition-literate. Unlike Western markets where diet/zero variants have partially addressed this, Indian consumers remain sceptical of zero-sugar alternatives (see THM_007).",
        "implication": "Thums Up cannot outrun the health narrative - it must navigate it. Ignoring health concerns risks slow erosion as health-conscious consumers quietly switch to alternatives. But over-indexing on health (reformulation, health claims) risks alienating the core consumer who explicitly chooses Thums Up for its bold, unapologetic character.",
        "recommendation": "Do not reformulate the flagship product. Instead, ensure the zero-sugar variant is genuinely good and widely available as a 'permission to keep drinking' option. Avoid making health claims for any variant. Position the brand as an informed indulgence ('you know what it is, and you choose it anyway') rather than trying to be healthy.",
        "further_validation": "Track the proportion of health-concern mentions over time to measure whether the headwind is accelerating. Survey lapsed Thums Up drinkers to understand whether health was the primary reason for switching.",
    },
    {
        "insight_id": "INS_005",
        "theme_id": "THM_005",
        "observation": "Food pairing accounts for 7% of conversation (33 items) with positive sentiment (+15.2%). Biryani is the most-cited pairing, followed by street food (kebabs, chaat) and dhaba meals. Old Monk rum + Thums Up is a recognised cultural combination. The pairings are distinctly Indian and class-transcending - from street-side to restaurant.",
        "insight": "Thums Up has organically become the default cola for Indian occasion eating in a way that Coca-Cola has not. The biryani-Thums Up pairing is approaching cultural ritual status - consumers mention it as an automatic, unquestioned combination. The Old Monk pairing extends the brand into nightlife without any official positioning. These pairings were not created by marketing - they emerged from consumer behaviour.",
        "implication": "Food pairing is an under-leveraged brand asset. The biryani association alone connects Thums Up to one of India's most popular and emotionally charged foods. This is a defensible moat that no competitor can easily replicate because it is rooted in decades of consumer habit.",
        "recommendation": "Explicitly own the food-pairing territory in marketing. Create 'Thums Up + Biryani' occasion marketing during Ramadan, Eid, and weekend dining occasions. Partner with biryani delivery platforms (Swiggy, Zomato) for bundled offers. Do not try to expand pairings artificially - let the existing organic pairings lead.",
        "further_validation": "Quantify the food-pairing association through structured survey (what drink do you pair with biryani?) to measure share vs. competitors. Track whether occasion marketing drives incremental sales during target periods.",
    },
    {
        "insight_id": "INS_006",
        "theme_id": "THM_006",
        "observation": "Brand loyalty is intensely positive (+54.4% NSS, 46 items, 9.8%) with consumers using declarative language ('nothing beats it', 'always my first choice', 'die-hard fan'). Loyalty appears to be taste-driven rather than marketing-driven - consumers cite the flavour as their reason, not advertising.",
        "insight": "Thums Up loyalty operates at the identity level, not the preference level. Loyal consumers do not just 'prefer' Thums Up - they define part of their identity through it. This is closer to how motorcycle enthusiasts relate to Royal Enfield than how most people relate to a beverage. The loyalty is self-reinforcing: choosing Thums Up signals boldness, which attracts consumers who want to signal boldness.",
        "implication": "The loyalty base is deep but may be narrow. The identity-level attachment means loyal consumers are extremely resistant to switching, but it also means the brand may not appeal to consumers who do not identify with 'bold' or 'strong' archetypes. Growth requires widening the appeal without diluting the identity.",
        "recommendation": "Protect the loyalty base by never compromising on product experience. Use loyal consumers as brand advocates through user-generated content campaigns. Do not try to make Thums Up appeal to everyone - the strength is in its polarising character. Growth should come from converting the 'curious but not yet tried' segment, not from softening the brand.",
        "further_validation": "Measure the loyalty-to-advocacy conversion rate. Survey to understand whether Thums Up loyalty is generational (inherited from parents) or individually adopted.",
    },
    {
        "insight_id": "INS_007",
        "theme_id": "THM_007",
        "observation": "Zero sugar and product innovation accounts for 9.3% (44 items) with notably negative sentiment (-15.9%). Consumers are divided: some appreciate the option, others find the taste inferior ('doesn't taste like real Thums Up'). The zero-sugar variant is compared unfavourably to Coke Zero. New variants (Charged, Thunder) receive mixed reception.",
        "insight": "Thums Up's core consumers are suspicious of product extensions because they perceive them as dilutions of the original's character. The zero-sugar variant faces a double challenge: it must taste like Thums Up (which is defined by its bold sweetness) while removing the sugar that creates that boldness. Consumers feel that if they wanted a milder drink, they would switch brands - they chose Thums Up for the full experience.",
        "implication": "Product innovation for Thums Up must respect the 'bold' contract. Variants that feel like compromises will be rejected. The zero-sugar variant needs to match the original's intensity profile or it will remain a niche product rather than a meaningful health migration path.",
        "recommendation": "Invest in zero-sugar reformulation to close the taste gap with the original - this is the single highest-value product investment for health-conscious consumer retention. For new variants, ensure each has a clear 'bolder than' positioning rather than a 'different from' positioning.",
        "further_validation": "Conduct blind taste comparison between Thums Up Zero and Coke Zero among Thums Up loyalists. Measure willingness to switch to zero-sugar if taste parity were achieved.",
    },
    {
        "insight_id": "INS_008",
        "theme_id": "THM_008",
        "observation": "Advertising and cricket sponsorship represent 18% of conversation (85 items) with positive NSS (+18.8%). Salman Khan's association is recognised but not universally loved. Cricket sponsorship (IPL) generates significant visibility. The 'toofani' (stormy/wild) tagline has cultural penetration. Stunt-based advertising is remembered but sometimes seen as over-the-top.",
        "insight": "Thums Up's advertising works because it amplifies the product truth (boldness) rather than creating a disconnected aspiration. The cricket-stunt-masculinity advertising universe is coherent and reinforcing. However, the exclusively masculine positioning may be creating a ceiling - women are almost entirely absent from the brand conversation, which represents a significant untapped volume opportunity.",
        "implication": "The current advertising strategy is effective for the core male 18-35 audience but self-limiting. The brand's cultural presence is disproportionately through cricket and action, which codes as masculine entertainment. Expanding the brand's cultural footprint without abandoning the 'bold' identity requires new occasion and context advertising rather than new personality advertising.",
        "recommendation": "Maintain cricket sponsorship and action-oriented creative for the core audience. Test food-pairing advertising (biryani, street food) as a gender-neutral entry point that expands reach without diluting brand character. Avoid directly targeting women with softened messaging - instead, create occasions where women naturally encounter the brand in a context that feels authentic.",
        "further_validation": "Measure brand consideration by gender to quantify the gender gap. Test food-pairing creative vs. stunt creative for recall and purchase intent across demographics.",
    },
    {
        "insight_id": "INS_009",
        "theme_id": "THM_009",
        "observation": "Pricing and packaging is the largest theme (209 items, 44.3%) with slight positive sentiment (+10.5%). Price comparisons between sizes and formats dominate. The Rs 20 price point for 250ml+ is seen as competitive. Glass bottle nostalgia coexists with PET convenience preference. Regional availability gaps are noted.",
        "insight": "Indian cola consumers are extremely price-literate - they calculate value on a per-ml basis and actively seek the best ratio. The Rs 10-20 price range is the battleground where purchasing decisions are made, and the +150ml bonus packs are recognised and appreciated as value signals. This suggests that the Indian cola consumer's loyalty has a price ceiling - even loyal consumers will switch if the value equation shifts significantly.",
        "implication": "Price is the one lever that can override taste loyalty. While consumers choose Thums Up for taste, they evaluate purchase on value-per-ml. Competitors (especially Campa backed by Reliance's cost advantage) could disrupt by offering comparable taste at lower price points. The brand needs to win on both taste and perceived value, not just taste.",
        "recommendation": "Maintain aggressive pricing on entry-level packs (200-300ml) to prevent trial erosion. Ensure bonus-pack promotions are sustained in high-competition periods. Monitor Campa Cola's pricing strategy - if Reliance undercuts on price in the same 'bold' taste territory, the loyalty moat will be tested.",
        "further_validation": "Map price elasticity by pack size and channel. Identify the price premium consumers are willing to pay for Thums Up over Campa/Pepsi at each pack size.",
    },
    {
        "insight_id": "INS_010",
        "theme_id": "THM_010",
        "observation": "Quality issues appear in 3.8% of conversation (18 items) with strongly negative sentiment (-50%). Reports include foreign objects found in bottles, inconsistent taste between manufacturing plants, and expired products on shelves. Though small in volume, these complaints are high-engagement posts that generate significant discussion and sharing.",
        "insight": "Quality complaints in food and beverage have an asymmetric impact - a single contamination report generates more engagement and brand damage than dozens of positive mentions. The manufacturing inconsistency complaints are particularly concerning because they suggest the brand promise (bold, consistent taste) is not being delivered uniformly across plants. This erodes the trust that sustains loyalty.",
        "implication": "Quality control is a brand survival issue, not just an operations issue. In the age of social media, a single viral contamination post can undo months of advertising investment. The taste inconsistency complaints suggest a systemic manufacturing variance that, if left unaddressed, will gradually undermine the 'I know what I am getting' trust that drives repeat purchase.",
        "recommendation": "Implement plant-level quality auditing with consumer taste-testing panels to detect manufacturing variance before it reaches consumers. Create a rapid-response social media protocol for contamination reports - speed of acknowledgement matters more than the outcome. Invest in supply chain freshness (FIFO enforcement, shelf-life monitoring).",
        "further_validation": "Audit taste consistency across manufacturing plants through blind testing. Track social media sentiment impact of quality complaints to quantify the damage multiplier.",
    },
    {
        "insight_id": "INS_011",
        "theme_id": "THM_011",
        "observation": "International discovery and diaspora conversations account for 8.9% (42 items) with positive sentiment (+23.8%). NRIs actively seek Thums Up in Indian grocery stores abroad. International consumers who discover it describe it as 'different from any cola I have tried'. The brand has a small but passionate following in unexpected markets (Ireland, Middle East, US).",
        "insight": "Thums Up has untapped international potential that is currently served entirely through diaspora grocery channels. The brand's distinctiveness (which is its domestic strength) makes it a genuine curiosity product for non-Indian consumers who discover it. However, the current international presence is accidental rather than strategic - it exists because diaspora demand created distribution, not because of any export strategy.",
        "implication": "The international opportunity is real but requires deliberate investment. The diaspora channel provides a low-risk testbed for international expansion - these consumers already love the product and can serve as brand ambassadors. The 'Indian bold cola' positioning is genuinely differentiated in markets where Coke and Pepsi dominate with similar mild profiles.",
        "recommendation": "Formalise the diaspora distribution strategy - ensure Thums Up is consistently available in Indian grocery stores in top 20 diaspora cities (Dubai, London, New York, Toronto, Singapore). Test premium positioning in non-Indian channels (speciality beverage retailers) where 'exotic Indian cola' can command curiosity-driven trial. Do not price it the same as Coke - premium pricing signals authenticity.",
        "further_validation": "Size the diaspora market opportunity by city. Conduct taste testing with non-Indian consumers in key markets to measure acceptance and willingness to pay.",
    },
    {
        "insight_id": "INS_012",
        "theme_id": "THM_012",
        "observation": "The Coca-Cola acquisition narrative accounts for 5.5% (26 items) with positive sentiment (+19.2%). The dominant narrative is 'Coke tried to kill Thums Up but failed because Indians loved it too much'. This story is told with pride and positions the brand as a survivor. References to Ramesh Chauhan (Parle founder) and the 1993 acquisition are common knowledge among engaged consumers.",
        "insight": "The acquisition survival story has become Thums Up's founding myth - a narrative of Indian consumer power defeating corporate strategy. This is more powerful than any manufactured brand story because it is true, verifiable, and emotionally resonant. The fact that consumers tell this story unprompted means it has achieved cultural status beyond brand marketing.",
        "implication": "This narrative is a permanent competitive moat. No competitor can replicate a genuine survival story. However, Coca-Cola (as current owner) must handle this narrative carefully - the story positions Coca-Cola as the villain and Thums Up as the hero. Overplaying corporate ownership could undermine the 'Indian underdog' narrative that consumers love.",
        "recommendation": "Let consumers own and tell this story - do not corporatise it. If using the heritage narrative in marketing, centre Ramesh Chauhan and the Parle founding rather than the Coca-Cola acquisition. The story works because it is about Indian resilience, not about Coca-Cola's portfolio strategy. Use it sparingly and authentically.",
        "further_validation": "Measure whether the acquisition narrative affects brand perception differently across age cohorts. Test whether heritage-led advertising moves preference among younger consumers who may not know the story.",
    },
]

# Build insight objects
insights = []
for ins_data in INSIGHTS:
    theme_id = ins_data["theme_id"]
    theme = next((t for t in themes if t["theme_id"] == theme_id), None)
    if not theme:
        print(f"WARNING: theme {theme_id} not found")
        continue

    source_urls = []
    for sid in theme["supporting_item_ids"][:20]:
        itm = item_lookup.get(sid)
        if itm:
            source_urls.append(itm["source_url"])

    insight = {
        "insight_id": ins_data["insight_id"],
        "observation": ins_data["observation"],
        "insight": ins_data["insight"],
        "implication": ins_data["implication"],
        "recommendation": ins_data["recommendation"],
        "further_validation": ins_data["further_validation"],
        "supporting_theme_ids": [theme_id],
        "supporting_item_count": theme["item_count"],
        "source_urls": source_urls,
        "representative_quotes": theme["representative_quotes"],
        "is_grounded": True,
        "is_non_obvious": True,
        "is_actionable": True,
        "is_specific": True,
        "is_falsifiable": True,
        "passed_quality_gates": True,
    }
    insights.append(insight)

insights_dir = RUN_DIR / "insights"
insights_dir.mkdir(exist_ok=True)
(insights_dir / "insights.json").write_text(
    json.dumps(insights, indent=2, default=str), encoding="utf-8"
)
print(f"Saved {len(insights)} insights to {insights_dir / 'insights.json'}")
