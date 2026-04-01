"""
Stage 5: In-context insight synthesis for Make in India.
One insight per theme, synthesized from reading theme data.
"""
import io, sys, json
from pathlib import Path
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

RUN_DIR = ROOT / "consumer_research" / "runs" / "make_in_india_20260401_202927_95b158"
print(f"Run directory: {RUN_DIR.name}")

results = json.loads((RUN_DIR / "analysis" / "results.json").read_text(encoding="utf-8"))
corpus = json.loads((RUN_DIR / "filtered" / "corpus.json").read_text(encoding="utf-8"))
themes = results["themes"]
item_lookup = {i["item_id"]: i for i in corpus}
total = len(corpus)
print(f"Loaded {len(themes)} themes, {total} items")

INSIGHTS = [
    {
        "insight_id": "INS_001",
        "theme_id": "THM_001",
        "observation": f"The Make in India policy debate is the single largest conversation theme with {themes[1]['item_count']} mentions ({themes[1]['prevalence']*100:.1f}% of dataset). Supporters cite mobile manufacturing growth (2 factories in 2014 to 300+ in 2025), $667B cumulative FDI, and record pharma exports to 200+ countries. Critics counter that manufacturing's GDP share has fallen from 17.3% to ~14% (against a 25% target), unemployment persists at record highs, and FDI benefits large corporations not ordinary workers. NSS is +0.160 - mildly positive but deeply divided.",
        "insight": "The Make in India conversation has fractured into two irreconcilable narratives that talk past each other. Government supporters measure success in absolute terms (number of factories, total FDI inflow, export volumes) while critics measure in relative terms (GDP share, per-capita impact, employment rate). Neither side engages with the other's metrics, creating a discourse where both 'Make in India has succeeded' and 'Make in India has failed' can be simultaneously supported with legitimate data. This metrics disconnect is the defining feature of the MII debate.",
        "implication": "Any organisation engaging with the MII narrative - whether government, brand, or media - must be explicit about which metrics they are using and why. Cherry-picking statistics fuels the polarisation rather than informing the consumer or investor. The credibility gap between absolute and relative metrics creates space for independent, balanced analysis that acknowledges both the real achievements and the missed targets.",
        "recommendation": "Develop a balanced 'MII Scorecard' that tracks both absolute progress (factory count, export value, FDI) AND relative performance (GDP share, employment generation per rupee invested, global manufacturing competitiveness index). Present both sides to build credibility with the informed middle ground that exists between partisan camps.",
        "further_validation": "Commission independent economic analysis comparing India's manufacturing trajectory with Vietnam, Bangladesh, and Indonesia over the same 2014-2025 period using identical metrics. Survey consumer awareness of both sets of metrics.",
        "supporting_theme_ids": ["THM_001", "THM_009"],
    },
    {
        "insight_id": "INS_002",
        "theme_id": "THM_002",
        "observation": f"The 'Assembly vs True Manufacturing' debate spans {themes[13]['item_count']} items ({themes[13]['prevalence']*100:.1f}%). A recurring critique is that 'Made in India' means Chinese components assembled locally - especially for iPhones and electronics. The PM's call to buy Swadeshi is contrasted with the reality that natural gas for plastic pellets, rare earth magnets, and electronic components still come from China. Counter-narrative: assembly is the first step - Foxconn started this way and India's value-addition is increasing year-over-year.",
        "insight": "The assembly-vs-manufacturing debate reveals a fundamental consumer trust deficit around the 'Made in India' label. Consumers have become sophisticated enough to question what 'Made in India' actually means - is it genuine value addition or just the last step of packaging? This scepticism is not anti-national but pro-quality: consumers want to be proud of Indian products but refuse to be misled by labelling that overstates domestic contribution. The iPhone example is cited repeatedly because it crystallises the paradox.",
        "implication": "The 'Made in India' label has a credibility problem. As consumers become more informed about supply chains, a simple country-of-origin label is insufficient. Brands that can transparently communicate their actual value-addition (what percentage is truly made in India, which components are imported, and what the roadmap to full localisation looks like) will differentiate themselves from those perceived as merely relabelling.",
        "recommendation": "Introduce a tiered labelling system (e.g., 'Assembled in India', 'Manufactured in India', 'Designed & Made in India') that gives consumers honest information. For policy: track and publish component-level localisation percentages by sector. For brands: publish annual 'localisation reports' showing increasing Indian content.",
        "further_validation": "Conduct consumer research on willingness-to-pay premium for products with higher Indian content percentage. Test different labelling frameworks for consumer comprehension and trust.",
        "supporting_theme_ids": ["THM_002", "THM_007"],
    },
    {
        "insight_id": "INS_003",
        "theme_id": "THM_003",
        "observation": f"Tariff and trade war discussions account for {themes[12]['item_count']} items ({themes[12]['prevalence']*100:.1f}%). The conversation centres on Trump's 50% tariff on Indian imports, India's retaliatory tariffs on 29 items, and the strategic calculus of India-US-China trade triangulation. NSS is +0.225 - consumers see tariffs as both a threat (export disruption, price rises) and an opportunity (forcing domestic manufacturing). India's engineering goods exports rose ~24% and electronics ~39% despite tariffs.",
        "insight": "The tariff crisis has paradoxically strengthened the Make in India argument in public discourse. Rather than triggering panic, Trump's tariffs have activated a 'siege mentality' that converts abstract patriotism into concrete consumer action. The data shows that sectors already benefiting from PLI schemes (electronics, engineering goods) are demonstrating resilience, which provides proof-of-concept for the self-reliance narrative. The consumer reads tariffs not as economic pain but as a call-to-arms for Indian manufacturing.",
        "implication": "Tariff tensions create a narrow but powerful window for Indian manufacturers to capture domestic market share from imports - not just through policy protection but through consumers who are actively seeking Indian alternatives. However, this window closes if Indian products fail to match quality expectations, turning patriotic buying into a one-time event rather than a sustained shift.",
        "recommendation": "Indian manufacturers should use the tariff window to invest in quality upgrades, not just capacity expansion. Marketing should connect the product to the self-reliance narrative without relying on it - 'Buy this because it's world-class AND Indian' rather than 'Buy this because it's Indian.' Build quality reputation during the tariff protection period so products remain competitive when tariffs eventually normalise.",
        "further_validation": "Track actual consumer purchase behaviour changes in tariff-affected categories (electronics, toys, furniture, steel products). Measure whether quality perception of Indian alternatives improves alongside tariff-driven trial.",
        "supporting_theme_ids": ["THM_003", "THM_011"],
    },
    {
        "insight_id": "INS_004",
        "theme_id": "THM_004",
        "observation": f"Vocal for Local and Swadeshi movement content spans {themes[6]['item_count']} items ({themes[6]['prevalence']*100:.1f}%) with the highest positive skew in the dataset (NSS +0.287, only 17 negative mentions out of 665). Content peaks around Independence Day, Diwali, and Republic Day. PM Modi's calls from Red Fort feature prominently. A critical counter-thread exists: Modi wearing Bvlgari glasses, Movado watches, and using BMW while preaching Swadeshi.",
        "insight": "Vocal for Local has achieved cultural penetration but not behavioural lock-in. The movement's sentiment is overwhelmingly positive because it functions as a seasonal patriotic ritual rather than a daily purchasing habit - similar to how Republic Day parade viewership doesn't translate into year-round military engagement. The hypocrisy critique (leaders preaching Swadeshi while using foreign brands) is small in volume but devastating in impact because it gives consumers permission to be selectively patriotic: 'If the PM uses an iPhone, why can't I?'",
        "implication": "Vocal for Local's success as a sentiment generator masks its failure as a behaviour changer. Brands leveraging the movement gain festive-season spikes but not sustained preference shifts. The movement needs to evolve from 'buy Indian because duty' to 'buy Indian because better' - a transition that requires product quality, not just patriotic messaging.",
        "recommendation": "Move beyond seasonal Vocal for Local campaigns to everyday 'Indian by Default' positioning. Create comparison content (Indian vs imported products) that demonstrates quality parity or superiority. Address the hypocrisy critique head-on by partnering with public figures who genuinely use Indian products in their daily lives, not just during campaigns.",
        "further_validation": "Measure actual purchasing behaviour changes outside festive windows. Track whether Vocal for Local messaging converts to repeat purchase or one-time trial. Survey consumers on what would make them permanently switch to Indian products.",
        "supporting_theme_ids": ["THM_004", "THM_013"],
    },
    {
        "insight_id": "INS_005",
        "theme_id": "THM_005",
        "observation": f"Boycott movements span {themes[14]['item_count']} items ({themes[14]['prevalence']*100:.1f}%). Targets include Chinese products (dominant), Turkish brands, Israeli products, Bangladeshi goods, and Nike. Boycotts are reactive and event-driven: anti-China sentiment follows geopolitical tensions, anti-Bangladesh follows Hindu persecution reports, anti-Nike follows perceived anti-India messaging. NSS +0.142 indicates boycott callers frame their stance positively (protecting India) not negatively.",
        "insight": "Boycott movements in the Indian Make in India context function as emotional release valves rather than sustained economic actions. Each boycott wave follows a specific geopolitical trigger, gains intense but brief social media traction, and dissipates without measurable import reduction. The India-China trade deficit actually doubled from $43B to $99B during peak 'Boycott China' sentiment (FY21-FY25). This pattern suggests boycotts serve a psychological need (expressing agency in the face of perceived threats) rather than a commercial one.",
        "implication": "Brands should not fear boycott movements as sustained commercial threats, but should understand them as signals of consumer sentiment that can be redirected toward positive action. The real opportunity is converting boycott energy ('stop buying foreign') into brand-building energy ('start buying this specific Indian alternative'). The failure of past boycotts also suggests that consumers ultimately value product-market fit over patriotic principle.",
        "recommendation": "Do not position Indian products primarily as 'alternatives to foreign brands being boycotted.' Instead, build independent brand equity that makes boycott sentiment a tailwind, not the entire engine. For policy: acknowledge that boycotts alone cannot substitute for manufacturing competitiveness - actual supply-side capacity must exist for consumers to act on their intent.",
        "further_validation": "Track purchase data in boycotted categories during and after boycott waves to measure actual behaviour change. Identify which specific product categories see genuine import substitution vs. which return to status quo.",
        "supporting_theme_ids": ["THM_005", "THM_010"],
    },
    {
        "insight_id": "INS_006",
        "theme_id": "THM_006",
        "observation": f"Indian D2C brands and startup ecosystem content spans {themes[7]['item_count']} items ({themes[7]['prevalence']*100:.1f}%) with NSS +0.266. Discussion covers boAt, Lava, Mamaearth, Nykaa, Fire-Boltt, Titan, and the Shark Tank India effect. A critical thread notes that many 'Indian brands' start with Chinese imports and white-labelling. Counter-narrative: Indian founders who built from scratch are celebrated, especially in consumer electronics and fashion.",
        "insight": "The Indian D2C ecosystem exists in a trust paradox: consumers want to support Indian brands but suspect many are merely repackaging Chinese products under Indian names. Brands that transparently communicate their manufacturing story (even if it starts with Chinese components) earn more trust than those that hide it. The Shark Tank India effect has created a new consumer archetype: the 'patriotic investor-consumer' who buys from startups they watched pitch on television, creating emotional investment beyond the product itself.",
        "implication": "For Indian D2C brands, manufacturing transparency is the new competitive advantage. The consumer doesn't demand 100% Indian manufacturing from day one but demands honesty about the current state and a clear roadmap to increasing localisation. Brands caught claiming 'Made in India' while fully importing from China face reputational destruction that patriotic positioning cannot recover from.",
        "recommendation": "Indian D2C brands should publish 'origin stories' that honestly show what is currently manufactured in India vs. sourced externally, with annual localisation targets. Create content showing actual factory floors, artisan workshops, and manufacturing processes. Leverage Shark Tank India alumni networks for cross-promotion and credibility.",
        "further_validation": "Survey Indian consumers on trust factors for D2C brands. Test whether manufacturing transparency content (factory tours, supply chain maps) drives purchase intent more than patriotic messaging.",
        "supporting_theme_ids": ["THM_006", "THM_002"],
    },
    {
        "insight_id": "INS_007",
        "theme_id": "THM_007",
        "observation": f"Quality perception and trust deficit spans {themes[11]['item_count']} items ({themes[11]['prevalence']*100:.1f}%) with NSS +0.204. Recurring complaints: Indian versions of global brands (Levi's, Coca-Cola, Vaseline) are perceived as inferior to their US/EU counterparts. Crash test failures in Indian cars are cited. Export-quality products are seen as better than domestic-market products. A counter-thread exists: specific Indian brands (Amul, Tata, some pharma) are trusted for world-class quality.",
        "insight": "Indian consumers harbour a specific form of quality scepticism that is not blanket anti-Indian but product-category specific. They trust Indian pharma, dairy (Amul), and heavy industry (Tata Steel) but distrust Indian consumer electronics, fast fashion, and food products sold in domestic markets. The 'dual quality standard' perception - that companies export their best products while selling inferior versions domestically - is corrosive because it suggests Indian consumers are treated as second-class customers by both MNCs and Indian companies alike.",
        "implication": "The quality perception gap is the single biggest barrier to sustained Make in India success at the consumer level. Policy achievements (factory counts, export volumes) become irrelevant if the average Indian consumer's daily experience of 'Made in India' products is one of disappointment. Closing this gap requires not just manufacturing upgrades but regulatory enforcement of quality standards for domestic-market products.",
        "recommendation": "Establish and enforce a 'Same Quality India' standard that mandates equivalent quality for products sold domestically vs. exported. Create consumer-facing quality certifications beyond BIS that are easy to understand. For brands: stop maintaining dual quality tiers and communicate quality investments in domestic products explicitly.",
        "further_validation": "Conduct blind product testing of Indian vs. imported versions of identical brands across categories. Measure whether quality perception changes after transparent quality communication.",
        "supporting_theme_ids": ["THM_007", "THM_002"],
    },
    {
        "insight_id": "INS_008",
        "theme_id": "THM_008",
        "observation": f"Defence and strategic manufacturing spans {themes[8]['item_count']} items ({themes[8]['prevalence']*100:.1f}%) with NSS +0.253. Content celebrates Vande Bharat trains (85% localisation), BrahMos missiles, Tejas fighter jets, metro coaches exported to Australia, and the 12,000 HP WAG-12B locomotive. Defence production reached Rs 1.27 lakh crore in FY24. Arms exports growing. Operation Sindoor referenced as proof that self-reliance works when it matters most.",
        "insight": "Defence manufacturing has become the unassailable proof-point for Make in India, functioning as the movement's emotional anchor. Even MII's harshest critics rarely attack defence manufacturing achievements because they touch national security - a domain where self-reliance is universally valued across political lines. The consumer reads defence manufacturing success as evidence that India CAN manufacture world-class products when motivated, which makes the failure to do so in consumer goods more frustrating rather than more understandable.",
        "implication": "Defence manufacturing's halo effect can be leveraged to build credibility for civilian manufacturing - but only with specific, verifiable claims. Generic 'Make in India' messaging fails; specific claims ('the same engineering that builds BrahMos missiles now builds your metro coach') succeed. However, the gap between defence achievement and consumer product quality actually intensifies rather than resolves consumer scepticism about commercial manufacturing.",
        "recommendation": "Create content connecting defence manufacturing capabilities to civilian product quality (technology transfer stories, dual-use engineering narratives). Use defence success as the aspirational benchmark for consumer product sectors. For policy: accelerate defence-to-civilian technology transfer programmes.",
        "further_validation": "Measure whether exposure to defence manufacturing content improves quality perception of Indian consumer products. Track technology transfer from defence to civilian sectors.",
        "supporting_theme_ids": ["THM_008", "THM_015"],
    },
    {
        "insight_id": "INS_009",
        "theme_id": "THM_009",
        "observation": f"Political polarisation dominates the dataset with {themes[0]['item_count']} items ({themes[0]['prevalence']*100:.1f}%). BJP supporters frame MII as a historic transformation; Congress/opposition frames it as a failed promise. Specific data points are weaponised by both sides - the same FDI numbers are cited as 'record achievement' and 'insufficient for the population.' Hindi and English content is equally politically charged. Modi is mentioned in 40%+ of political content.",
        "insight": "Make in India has become so deeply embedded in India's political identity war that separating the policy's actual performance from its political narrative has become nearly impossible for the average citizen. When every data point is pre-filtered through partisan framing before reaching the consumer, the policy's real outcomes matter less than which political tribe the consumer belongs to. This politicisation means MII's actual commercial impact on consumers is obscured by its function as a political loyalty test.",
        "implication": "Any commercial strategy that relies on Make in India messaging inherits the political polarisation attached to it. Using MII branding may attract BJP-aligned consumers while repelling opposition-aligned ones - a net-zero game in a politically divided market. Brands need to decouple their Indian manufacturing story from the political MII narrative.",
        "recommendation": "Commercial brands should avoid direct MII branding and instead build independent 'Indian-made' narratives that focus on product quality and local employment rather than government policy. Use specific, apolitical proof points ('made by 500 workers in our Pune factory') rather than government-associated slogans. Keep the patriotic pride but remove the partisan politics.",
        "further_validation": "A/B test marketing messages: MII-branded vs. apolitical 'Indian-made' messaging across politically diverse consumer segments. Measure purchase intent and brand perception differences.",
        "supporting_theme_ids": ["THM_009", "THM_001"],
    },
    {
        "insight_id": "INS_010",
        "theme_id": "THM_010",
        "observation": f"The China dependency paradox spans {themes[4]['item_count']} items ({themes[4]['prevalence']*100:.1f}%) with the lowest positive NSS in the dataset (+0.099). India's trade deficit with China doubled from $43B (FY21) to $99B (FY25) during peak boycott-China sentiment. India imported $113B from China in FY25 while exporting only $14B. Rare earth magnets, electronic components, pharmaceutical intermediates, and solar panels remain heavily China-dependent.",
        "insight": "The China dependency discussion reveals the most uncomfortable truth in the Make in India narrative: India's manufacturing ambition is structurally dependent on the very country it seeks to replace. This is not a failure of intent but of industrial ecosystem maturity - you cannot boycott your own supply chain. The doubling of the trade deficit during 'Boycott China' years demonstrates that consumer sentiment and industrial reality operate on entirely different timescales. Consumers can switch brands overnight; supply chains take decades to redirect.",
        "implication": "Any realistic MII strategy must acknowledge that China dependency will persist for 10-15 years in critical sectors (electronics, pharma intermediates, rare earths) regardless of consumer sentiment. The path to reducing dependency runs through building component-level manufacturing capacity, not through consumer boycotts or tariff walls alone.",
        "recommendation": "Shift the public narrative from 'replace China' to 'reduce China dependency in critical sectors over a defined timeline.' Publish sector-wise roadmaps showing 5-year, 10-year, and 15-year localisation targets with annual progress reports. Invest in component manufacturing (PCBs, semiconductor packaging, active pharmaceutical ingredients) where India has the strongest path to self-sufficiency.",
        "further_validation": "Track component-level import dependency ratios across key manufacturing sectors annually. Benchmark India's supply chain diversification against Vietnam and Indonesia's approach to reducing China dependency.",
        "supporting_theme_ids": ["THM_010", "THM_002"],
    },
    {
        "insight_id": "INS_011",
        "theme_id": "THM_011",
        "observation": f"PLI scheme and industrial policy discussions span {themes[2]['item_count']} items ({themes[2]['prevalence']*100:.1f}%) with NSS +0.282. PLI has attracted Rs 1.76 lakh crore in investments. Mobile manufacturing under PLI created 1.33 million jobs in 5 years. The Electronics Component Manufacturing Scheme aims for Rs 4,56,500 crore in production. GST rationalisation to two rates (5% and 18%) is cited as a major reform. 100% FDI in insurance now permitted.",
        "insight": "PLI has emerged as the most credible proof-point in the MII ecosystem because it provides verifiable, sector-specific metrics rather than abstract national-level claims. When consumers see '1.33 million jobs created in mobile manufacturing' or 'Rs 25,000 crore in wages in FY25 alone,' it is more persuasive than aggregate FDI numbers because it connects to tangible outcomes in a specific industry they understand. PLI's sector-by-sector approach makes MII's otherwise abstract promise measurable.",
        "implication": "PLI's success model should be the template for all MII communication: sector-specific, metrics-driven, verifiable. The challenge is that PLI benefits are concentrated in large-scale manufacturing (Foxconn, Samsung, Tata) while MSMEs - which employ the vast majority of Indian workers - feel excluded. If PLI's benefits don't trickle down to the MSME ecosystem, it risks becoming another 'big industry vs. common man' narrative.",
        "recommendation": "Extend PLI-style incentive frameworks to MSME clusters with modified thresholds. Publish sector-wise PLI impact reports that go beyond investment committed to actual jobs created, wages paid, and local supply chains developed. Create MSME-accessible simplified compliance pathways for PLI-like benefits.",
        "further_validation": "Survey MSME awareness and perception of PLI schemes. Track whether PLI investment is creating local supplier ecosystems or remaining concentrated in large anchor factories.",
        "supporting_theme_ids": ["THM_011", "THM_012"],
    },
    {
        "insight_id": "INS_012",
        "theme_id": "THM_012",
        "observation": f"Employment and MSME impact discussions span {themes[3]['item_count']} items ({themes[3]['prevalence']*100:.1f}%) with NSS +0.248. The conversation is divided: government claims 17 crore jobs added since 2017-18; critics cite unemployment still at record highs, MSMEs closing since demonetisation, and wages not keeping pace. A specific pain point: running an MSME in India involves regulatory harassment, and many have closed since 2014. H-1B visa controversy (Trump telling tech giants to stop hiring from India) adds another dimension.",
        "insight": "Employment is the ultimate litmus test for Make in India in the eyes of the Indian public, and it is the area where the perception gap between policy claims and lived experience is widest. Factory opening announcements and PLI investment figures feel abstract to a worker whose wages have not risen or a small business owner facing regulatory burden. The disconnect between macro employment data (jobs created) and micro employment reality (quality of jobs, wage levels, ease of doing business for MSMEs) creates persistent scepticism even among those who want MII to succeed.",
        "implication": "Until employment impact is felt at the individual level - better wages, easier business compliance, visible local factory jobs - MII will remain a policy success story that feels like a personal failure to many Indians. The MSME segment is particularly critical because it employs the majority of India's non-agricultural workforce and is the bridge between macro policy and micro experience.",
        "recommendation": "Create a 'MII Employment Dashboard' tracking not just jobs created but job quality (wages, benefits, formality). Simplify MSME compliance dramatically - every regulation that closes a small business is a step backward for MII regardless of what large-factory numbers show. Develop regional employment impact stories that connect MII policy to specific communities and families.",
        "further_validation": "Conduct longitudinal tracking of MSME survival rates in manufacturing clusters. Survey workers in PLI-beneficiary factories on wage and working condition improvements.",
        "supporting_theme_ids": ["THM_012", "THM_011"],
    },
    {
        "insight_id": "INS_013",
        "theme_id": "THM_013",
        "observation": f"The nationalism vs pragmatism tension spans {themes[10]['item_count']} items ({themes[10]['prevalence']*100:.1f}%) with the highest positive NSS outside self-reliance (+0.338). Pragmatists argue 'no one cares unless the product is good' and accuse brands of 'selling nationalism.' Nationalists counter that supporting Indian products is an economic duty. A middle ground emerges: consumers willing to give Indian products a chance but unwilling to accept inferior quality in the name of patriotism.",
        "implication": "The nationalism-pragmatism tension reveals the maturation point of Indian consumer consciousness. The market is transitioning from first-generation 'buy Indian at any cost' patriotism to second-generation 'buy Indian when quality matches' pragmatism. Brands caught in the first generation will lose market share to those that address the second.",
        "insight": "Indian consumers have evolved past blind patriotic purchasing. The dominant sentiment is conditional patriotism: 'I want to buy Indian, but don't insult my intelligence with an inferior product wrapped in a flag.' This is actually a positive development for Indian manufacturing because it creates market pressure for quality improvement rather than relying on sentiment-based protection. The harshest critics of Indian product quality are often the most patriotic - they are angry precisely because they want Indian products to be world-class.",
        "recommendation": "Position Indian products on quality-first, patriotism-second messaging. Lead with product performance, design, and value - then add the Indian origin as an emotional bonus, not the primary selling point. Target the 'conditional patriot' segment with comparison content that demonstrates quality parity with imports.",
        "further_validation": "Quantify the 'conditional patriot' segment size through purchase intent surveys with quality-controlled stimuli. Test whether quality-first vs patriotism-first messaging drives different conversion rates.",
        "supporting_theme_ids": ["THM_013", "THM_007", "THM_004"],
    },
    {
        "insight_id": "INS_014",
        "theme_id": "THM_014",
        "observation": f"Sector success stories span {themes[5]['item_count']} items ({themes[5]['prevalence']*100:.1f}%) with the second-highest NSS (+0.376). Mobile manufacturing dominates: 99% of phones sold in India now assembled locally vs 80% imported in 2014. iPhone exports hit record $10B. Pharma exports to 200+ countries - 'Made in India vaccine saved the world' during Covid. Toy imports fell 70%. Samsung and Apple expanding India manufacturing. Electronics component manufacturing scheme approved.",
        "insight": "India's MII success story is not evenly distributed across sectors but concentrated in a handful of 'hero sectors' - mobile phones, pharma, defence, and toys - that provide disproportionate proof-of-concept for the entire initiative. These sectors share common characteristics: government incentives (PLI), a large domestic market for scale, and at least one anchor company that de-risked the investment. The consumer perceives MII's credibility through these specific sectors rather than through aggregate national data.",
        "implication": "The 'hero sector' model suggests that future MII expansion should replicate the conditions that made mobile and pharma successful rather than spreading resources thinly across all sectors. Each new hero sector (semiconductors, EVs, green energy) needs its own anchor company, its own PLI scheme, and its own consumer-facing narrative.",
        "recommendation": "Identify the next 3-5 potential hero sectors based on the success criteria of existing ones (domestic market size, global demand, technology readiness, available anchor companies). Create sector-specific public narratives with clear 5-year milestones. Semiconductor and green energy manufacturing are the strongest candidates based on current policy momentum.",
        "further_validation": "Benchmark India's sector-level manufacturing competitiveness against Vietnam, Thailand, and Mexico. Track consumer awareness and pride in hero sector achievements to gauge narrative effectiveness.",
        "supporting_theme_ids": ["THM_014", "THM_011"],
    },
    {
        "insight_id": "INS_015",
        "theme_id": "THM_015",
        "observation": f"Atmanirbhar Bharat and self-reliance vision spans {themes[9]['item_count']} items ({themes[9]['prevalence']*100:.1f}%) with the highest NSS in the dataset (+0.412). Only 25 negative mentions out of 485 - self-reliance is the most universally supported concept. Content ranges from PM Modi's vision statements to grassroots discussions about reducing import dependency. Operation Sindoor is cited as proof that self-reliance saves lives. India 2047 vision (developed nation by centenary) provides the aspirational horizon.",
        "insight": "Self-reliance (Atmanirbharta) has achieved something rare in India's polarised discourse: near-universal appeal across political lines. Unlike specific policy debates (PLI, tariffs, GST) which divide along party lines, the abstract concept of self-reliance unites because it connects to deep cultural values of independence, dignity, and sovereignty that predate current politics. However, this unity exists precisely because 'self-reliance' remains abstract - as soon as it is operationalised into specific policy choices, consensus fractures.",
        "implication": "Self-reliance is the strategic high ground for any Make in India communication because it transcends political polarisation. But it must be kept aspirational to maintain its unifying power - the moment it becomes specific policy, it becomes controversial. The challenge is bridging the gap between universal aspiration and specific action without losing the audience.",
        "recommendation": "Use Atmanirbhar Bharat as the aspirational umbrella while letting sector-specific narratives carry the operational details. Create 'self-reliance milestones' that celebrate specific achievements without partisan framing. Connect self-reliance to personal empowerment (financial independence, skill development) not just national policy.",
        "further_validation": "Survey consumer understanding of what 'self-reliance' means to them personally vs. nationally. Test whether self-reliance messaging drives different behaviour than patriotic messaging.",
        "supporting_theme_ids": ["THM_015", "THM_004"],
    },
    {
        "insight_id": "INS_016",
        "theme_id": "THM_016",
        "observation": f"Indian economic growth and global standing content spans {themes[15]['item_count']} items ({themes[15]['prevalence']*100:.1f}%) with NSS +0.169. Discussion centres on India's position as the 4th/5th largest economy, GDP growth trajectory, UPI revolution, infrastructure development (highways, metro, railways), and the aspiration to reach $5 trillion/$30 trillion GDP. Counterpoints include low per-capita income, purchasing power limitations, and infrastructure-reality gaps.",
        "insight": "The economic growth narrative functions as the background music to the entire Make in India conversation. Consumers engage with specific MII topics (tariffs, brands, quality) against a backdrop of either optimism ('India is rising, 4th largest economy') or pessimism ('per capita income is still low, 80% live on less than $3/day'). This background sentiment colours how they interpret every MII data point - the same factory opening feels like proof of progress to an optimist and like inadequate progress to a pessimist.",
        "implication": "Macro-economic narrative setting is as important as micro-level product marketing for MII success. If the dominant background narrative shifts to pessimism (recession, job losses, inflation), even strong MII sector achievements will be dismissed. Conversely, in an optimistic backdrop, even modest achievements will be celebrated.",
        "recommendation": "Maintain economic growth narrative through transparent, regularly-updated public dashboards rather than sporadic government announcements. Ground macro numbers in micro stories ('India's 4th largest economy means your neighbourhood factory now exports to 30 countries'). Address the per-capita critique honestly rather than ignoring it.",
        "further_validation": "Track correlation between consumer economic sentiment and willingness to buy Indian products. Measure whether economic confidence predicts MII engagement more than patriotism.",
        "supporting_theme_ids": ["THM_016", "THM_001"],
    },
]

# Build representative quotes for each insight
import random
random.seed(42)

for ins in INSIGHTS:
    theme_id = ins["theme_id"]
    theme = next((t for t in themes if t["theme_id"] == theme_id), None)
    if not theme:
        ins["representative_quotes"] = []
        continue

    # Get theme items
    theme_items_list = [item_lookup[iid] for iid in theme["item_ids"] if iid in item_lookup]

    # Prefer posts over comments, medium length, diverse platforms
    posts = [i for i in theme_items_list if i["content_type"] == "post" and 80 < len(i["content_text"]) < 500]
    comments = [i for i in theme_items_list if i["content_type"] == "comment" and 50 < len(i["content_text"]) < 400]

    quotes = []
    used_platforms = set()
    for pool, max_count in [(posts, 2), (comments, 1)]:
        random.shuffle(pool)
        count = 0
        for item in pool:
            if count >= max_count:
                break
            plat = item["source_platform"]
            text = item["content_text"].strip()
            # Clean
            text = text.replace("\n", " ").replace("  ", " ")
            if len(text) > 300:
                text = text[:297] + "..."
            quotes.append({
                "text": text,
                "source_platform": plat,
                "source_url": item.get("source_url", ""),
                "selection_reason": f"Representative {item['content_type']} from {plat} for theme {theme_id}",
            })
            used_platforms.add(plat)
            count += 1

    ins["representative_quotes"] = quotes

# Save insights
insights_dir = RUN_DIR / "insights"
insights_dir.mkdir(exist_ok=True)
(insights_dir / "insights.json").write_text(
    json.dumps(INSIGHTS, indent=2, default=str, ensure_ascii=False), encoding="utf-8"
)
print(f"\nSaved {len(INSIGHTS)} insights to insights/insights.json")

# Print summary
for ins in INSIGHTS:
    print(f"  {ins['insight_id']}: {ins['theme_id']} - {ins['observation'][:80]}...")
