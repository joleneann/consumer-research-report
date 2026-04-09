"""Stage 5: Synthesize one insight per theme."""
import json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

RUN_DIR = Path('runs/20260407_184943_08eb92')

insights = [
    {
        "insight_id": "INS_001",
        "observation": "The Make in India initiative is the most discussed theme in the corpus (1,756 items, 50% prevalence), with a moderately positive NSS of +0.33. Discourse is sharply polarized along political lines: BJP supporters cite FDI inflows ($667B since 2014), PLI scheme job creation (1.33M), and iPhone export records ($10B), while critics point to manufacturing's stagnant share of GDP (~14-17% vs 25% target), ballooning trade deficit with China ($100B+), and unmet employment promises. The debate is predominantly on Twitter (65% of theme items).",
        "insight": "Make in India has become a political identity marker more than a policy evaluation. Consumers do not assess the initiative on industrial metrics alone - they use it as a proxy for broader trust or distrust in governance. This means the narrative around Make in India is shaped more by political allegiance than by lived manufacturing experience, creating a significant gap between public discourse and ground-level industrial reality.",
        "implication": "For any brand or organization seeking to align with 'Make in India' messaging, the initiative carries heavy political baggage. What was intended as a manufacturing policy brand has become a partisan flashpoint. Communications that uncritically celebrate or criticize 'Make in India' will be perceived as political statements, not business ones.",
        "recommendation": "Reframe communications around specific manufacturing outcomes (jobs created, components localized, exports achieved) rather than invoking 'Make in India' as a slogan. Lead with verifiable metrics: '30,000 jobs at our Karnataka facility' resonates across political lines in ways that '#MakeInIndia success' does not.",
        "further_validation": "Conduct a structured survey segmenting respondents by political affiliation and manufacturing proximity (factory workers, suppliers, local businesses) to separate policy perception from on-the-ground impact assessment.",
        "supporting_theme_ids": ["THM_01"],
        "supporting_item_count": 1756,
        "source_urls": [],
        "is_grounded": True,
        "is_non_obvious": True,
        "is_actionable": True,
        "is_specific": True,
        "is_falsifiable": True,
        "passed_quality_gates": True
    },
    {
        "insight_id": "INS_002",
        "observation": "The PLI Scheme and electronics manufacturing theme (439 items, 11.6%) has the second-highest positive NSS at +0.41. The Foxconn-Apple iPhone story dominates - consumers frequently cite the 150x growth in mobile manufacturing units (from 2 in 2014 to 300+ in 2025), $10B in iPhone exports, and 1.33M jobs created. However, critics argue this is assembly, not true manufacturing, with India still importing the bulk of components (displays, chips, batteries) from China.",
        "insight": "The PLI scheme's electronics success story is the single strongest proof-point for India's manufacturing ambitions, but consumers are increasingly distinguishing between assembly and manufacturing. The iPhone narrative works as a headline but sophisticated consumers (especially on Reddit and in longer Twitter threads) understand that final assembly is only ~15% of value addition. The story is shifting from 'India makes iPhones' to 'India assembles iPhones - when will it make the chips inside them?'",
        "implication": "The PLI story has reached peak narrative effectiveness in its current form. Continuing to tout assembly numbers without showing progression toward component-level self-reliance will trigger consumer skepticism and diminishing returns on the narrative.",
        "recommendation": "Shift the PLI narrative from volume metrics (units produced, jobs created) to value-chain depth metrics (% of components sourced domestically, number of Tier-2 suppliers developed, R&D centers established). Highlight the semiconductor fab investments and OSAT facilities as the next chapter of the story.",
        "further_validation": "Commission a value-chain analysis tracking actual domestic content percentage in PLI-beneficiary products over time, and compare consumer awareness of assembly vs manufacturing distinction across demographics.",
        "supporting_theme_ids": ["THM_02"],
        "supporting_item_count": 439,
        "source_urls": [],
        "is_grounded": True,
        "is_non_obvious": True,
        "is_actionable": True,
        "is_specific": True,
        "is_falsifiable": True,
        "passed_quality_gates": True
    },
    {
        "insight_id": "INS_003",
        "observation": "The Vocal for Local / Swadeshi movement theme (657 items, 17.3%) has the highest positive NSS of any theme at +0.57. Content includes PM Modi's direct appeals to buy Indian, consumer pledges during Diwali/festive seasons, brand-led campaigns (Dabur positioning against Colgate on nationalist grounds), and anti-American/anti-Chinese boycott calls tied to tariff wars and geopolitical tensions (Operation Sindoor, US tariffs). The movement spans Hindi and English content, with significant Hindi-language participation.",
        "insight": "Swadeshi sentiment has evolved from a top-down government campaign into a genuinely consumer-driven movement that activates during three triggers: festive seasons (Diwali = buy Indian), geopolitical friction (US tariffs = boycott American, Pakistan tensions = boycott Chinese), and brand authenticity scandals (discovering global brands sell inferior versions in India). The movement is no longer dependent on government promotion - it has its own consumer momentum, particularly among Hindi-speaking urban consumers.",
        "implication": "There is a large, engaged consumer segment willing to pay attention to and act on 'Buy Indian' messaging, but their motivation is emotional (national pride, geopolitical anger) rather than rational (product comparison). This creates both opportunity (strong brand loyalty once earned) and risk (the same consumers will punish perceived inauthenticity - brands that claim 'Indian' but are actually assembled from Chinese components).",
        "recommendation": "For Indian brands: lean into origin transparency - show the factory, name the city, feature the workers. For global brands operating in India: demonstrate genuine local value creation (local R&D, domestic sourcing) rather than just local assembly. Festive-season and geopolitical-trigger marketing campaigns can leverage Swadeshi sentiment, but must be backed by verifiable Indian content.",
        "further_validation": "Track purchase conversion rates during Swadeshi sentiment spikes (festive seasons, geopolitical events) vs baseline periods. Measure whether stated intent to 'buy Indian' translates into actual purchase behavior change.",
        "supporting_theme_ids": ["THM_03"],
        "supporting_item_count": 657,
        "source_urls": [],
        "is_grounded": True,
        "is_non_obvious": True,
        "is_actionable": True,
        "is_specific": True,
        "is_falsifiable": True,
        "passed_quality_gates": True
    },
    {
        "insight_id": "INS_004",
        "observation": "The India vs China trade deficit theme (313 items, 8.2%) has the lowest positive NSS among all themes at +0.12, reflecting deep anxiety. Consumers cite specific numbers: $100B+ trade deficit with China, 70% electronics import dependence, and Chinese products flooding every category from Diwali lights to industrial equipment. The conversation oscillates between defeatism ('India can never compete with China - not even in the same weight class') and resolve ('ban Chinese products, impose tariffs').",
        "insight": "The China deficit narrative is eroding consumer confidence in Make in India's core promise. For every success story (iPhone assembly, Foxconn factory), consumers can point to a corresponding failure (still importing the components that go into that iPhone from China). The discourse reveals a sophisticated understanding among consumers that India's manufacturing relationship with China is one of structural dependency, not competition - India assembles what China makes. This framing undermines optimistic industrial narratives.",
        "implication": "The China dependency narrative is the single biggest threat to Make in India's credibility. If consumer discourse continues to frame India as structurally dependent on China for manufacturing inputs, no amount of assembly-stage success stories will shift the narrative. The deficit is both an economic reality and a psychological barrier.",
        "recommendation": "Develop and publicize a 'China substitution scorecard' tracking specific product categories where Indian manufacturing is replacing Chinese imports. Focus on winnable categories (pharma APIs, textiles, steel, certain electronics) rather than claiming broad-based competition. Acknowledge the gap honestly while showing trajectory.",
        "further_validation": "Track import substitution rates in specific product categories over time. Pair with consumer perception surveys to measure whether China-substitution progress is reaching public awareness.",
        "supporting_theme_ids": ["THM_04"],
        "supporting_item_count": 313,
        "source_urls": [],
        "is_grounded": True,
        "is_non_obvious": True,
        "is_actionable": True,
        "is_specific": True,
        "is_falsifiable": True,
        "passed_quality_gates": True
    },
    {
        "insight_id": "INS_005",
        "observation": "The product quality and consumer trust theme (416 items, 11.0%) has an NSS of only +0.10, nearly balanced between positive and negative. Consumers frequently cite specific examples of global brands selling inferior versions in India: Levi's with lower-quality materials, Nutella with more palm oil, Cerelac with added sugar absent in European versions. Beyond MNC quality gaps, consumers express deep distrust of 'Made in India' labeling itself - items relabeled from Chinese origins, white-labeled products, and the 'screwdriver technology' critique.",
        "insight": "Consumer trust in 'Made in India' is being undermined by a dual quality problem: global brands selling inferior India-specific versions (creating the perception that Indian consumers deserve less), AND Indian manufacturers labeling Chinese-origin products as domestic (creating the perception that 'Made in India' is a label scam). These two problems compound each other - when a consumer discovers their 'Indian' product is actually Chinese, AND that global brands give India worse quality, the conclusion is that Indian manufacturing is not trustworthy at any level.",
        "implication": "Quality perception is the foundational bottleneck for Make in India. All other positive narratives (jobs, exports, FDI) are undercut if consumers do not trust the quality of what India produces. This is not a PR problem - it requires actual quality infrastructure: standards enforcement, testing, certification, and regulatory teeth.",
        "recommendation": "Establish and promote independent quality certification marks specifically for Indian-manufactured goods (similar to ISI/BIS but consumer-facing and trusted). Investigate and publicize cases where global brands sell inferior India-specific versions, turning the quality narrative from defensive to offensive. Create transparency requirements for 'Made in India' labeling that specify domestic content percentage.",
        "further_validation": "Conduct blind product testing comparing Indian-made vs import versions of the same brand across consumer categories. Survey consumer willingness to pay premium for verified quality certification on Indian products.",
        "supporting_theme_ids": ["THM_05"],
        "supporting_item_count": 416,
        "source_urls": [],
        "is_grounded": True,
        "is_non_obvious": True,
        "is_actionable": True,
        "is_specific": True,
        "is_falsifiable": True,
        "passed_quality_gates": True
    },
    {
        "insight_id": "INS_006",
        "observation": "Defence manufacturing (250 items, 6.6%) carries a moderately positive NSS of +0.36. Discussion centers on DRDO developments, the Tejas fighter program, BrahMos missile exports, indigenous warship launches, and defence equipment performance during Operation Sindoor. The Kaveri jet engine's 39-year development failure is the most cited negative example. Defence exports crossing INR 1 lakh crore is the most cited success metric.",
        "insight": "Defence manufacturing is the most emotionally resonant proof-point for Make in India because it ties directly to national security and sovereignty - 'India makes its own weapons' is a more viscerally convincing statement than 'India assembles phones.' Operation Sindoor's validation of indigenous defence equipment in actual combat created a narrative inflection point that no industrial statistic can match. However, the Kaveri engine failure serves as a persistent counter-narrative about India's inability to master complex, long-cycle manufacturing.",
        "implication": "Defence manufacturing success stories have outsized influence on overall Make in India perception because they carry emotional and strategic weight that consumer goods manufacturing cannot. Each defence milestone (successful missile test, indigenous warship launch, combat-proven weapon system) generates public pride that spills over into broader manufacturing confidence.",
        "recommendation": "Use defence manufacturing narratives as credibility anchors for broader Make in India communications. When launching industrial initiatives, reference defence manufacturing precedents to demonstrate that India can master complex manufacturing when strategic will exists. Address the Kaveri-type failures transparently as learning investments rather than hiding them.",
        "further_validation": "Measure the sentiment spillover effect: does a defence manufacturing milestone (e.g., successful Tejas deployment) measurably improve consumer sentiment toward Make in India in unrelated categories (electronics, consumer goods)?",
        "supporting_theme_ids": ["THM_06"],
        "supporting_item_count": 250,
        "source_urls": [],
        "is_grounded": True,
        "is_non_obvious": True,
        "is_actionable": True,
        "is_specific": True,
        "is_falsifiable": True,
        "passed_quality_gates": True
    },
    {
        "insight_id": "INS_007",
        "observation": "The Indian brand ecosystem (1,128 items, 29.7%) has a positive NSS of +0.33. Consumers are actively discovering and recommending Indian alternatives across categories: skincare (Minimalist, Plum, Kama Ayurveda), fashion (Bombay Shirt Company), auto (Ather, Ultraviolette), food (Darkins chocolate, A2 ghee brands), audio (boAt), and watchmaking (Indian microbrands). However, a strong counter-narrative exists: Indian brands are accused of being white-labeled Chinese products, using the same 10-15 contract manufacturers, and lacking genuine R&D investment.",
        "insight": "India is experiencing a genuine D2C/homegrown brand renaissance, but it faces a credibility crisis. Consumers want to buy Indian, but they increasingly suspect that many 'Indian brands' are marketing wrappers around the same contract-manufactured, often Chinese-sourced products. The brands that break through this skepticism are those that demonstrate genuine differentiation: own manufacturing, visible supply chain, unique formulations, and export-quality credentials. The emerging heuristic is: 'If an Indian brand exports to developed markets, it must be good enough for us.'",
        "implication": "The Indian brand ecosystem is at an inflection point. First-mover D2C brands gained attention through marketing, but the next phase of brand building requires manufacturing credibility. Brands that can demonstrate genuine production capability (own factory, domestic raw materials, R&D investment) will command premium positioning. Those that cannot will be caught in the white-label suspicion trap.",
        "recommendation": "For Indian brands: invest in manufacturing transparency as a marketing asset. Factory tours, supply chain documentation, and 'made in [specific city]' provenance stories build trust. For investors: evaluate D2C brands on manufacturing depth, not just marketing spend. For policy: create a verified 'Indian Origin' certification that requires demonstrated domestic manufacturing, not just assembly or packaging.",
        "further_validation": "Survey consumer willingness-to-pay premium for Indian brands with verified domestic manufacturing vs those suspected of contract/Chinese manufacturing. Track whether export credentials actually influence domestic purchase decisions.",
        "supporting_theme_ids": ["THM_07"],
        "supporting_item_count": 1128,
        "source_urls": [],
        "is_grounded": True,
        "is_non_obvious": True,
        "is_actionable": True,
        "is_specific": True,
        "is_falsifiable": True,
        "passed_quality_gates": True
    },
    {
        "insight_id": "INS_008",
        "observation": "Manufacturing GDP and economic fundamentals (738 items, 19.4%) carry a positive NSS of +0.41. The central tension is between India's headline GDP growth (4th largest economy, 6-7% growth rate, record FDI) and manufacturing's persistent underperformance (stuck at 14-17% of GDP vs 25% target). Consumers cite specific reforms (GST rationalization, FDI liberalization, income tax overhaul) as evidence of serious intent, but also note that these reforms have not yet translated into manufacturing share growth.",
        "insight": "There is a growing disconnect between India's macro-economic narrative (GDP rank, growth rate) and its manufacturing reality (stagnant GDP share, persistent import dependence). Consumers are becoming literate in the distinction: 'India is growing, but not as a manufacturing economy.' The most informed consumer discourse recognizes that India's growth is services-led and consumption-driven, not manufacturing-led, which fundamentally challenges the Make in India premise.",
        "implication": "The 'India is the 4th largest economy' narrative, while true, may actually work against Make in India if consumers interpret it as 'we grew without manufacturing, so why does manufacturing matter?' This creates a communication challenge: how to celebrate economic success while arguing that the model needs to change.",
        "recommendation": "Shift from aggregate economic metrics to manufacturing-specific metrics in public communications. Instead of GDP rank, publicize manufacturing GVA growth, industrial output indices, and manufacturing employment numbers. Create a public-facing 'Manufacturing Dashboard' that tracks the 25% GDP target with quarterly updates.",
        "further_validation": "Conduct a structured survey testing whether consumers who are aware of the GDP-manufacturing disconnect hold different views on Make in India than those who are not. This would quantify the impact of economic literacy on policy perception.",
        "supporting_theme_ids": ["THM_08"],
        "supporting_item_count": 738,
        "source_urls": [],
        "is_grounded": True,
        "is_non_obvious": True,
        "is_actionable": True,
        "is_specific": True,
        "is_falsifiable": True,
        "passed_quality_gates": True
    },
    {
        "insight_id": "INS_009",
        "observation": "The US tariff war and trade policy theme (562 items, 14.8%) has a positive NSS of +0.23. Trump's threatened 50% tariff on Indian goods triggered three distinct consumer responses: (1) nationalist anger leading to boycott calls against American brands (McDonald's, Coca-Cola, Apple, Amazon), (2) pragmatic concern about economic impact on Indian exports and jobs, and (3) opportunistic framing of tariffs as a catalyst for genuine domestic manufacturing. Notably, the boycott sentiment appears organic and widespread, with consumers generating specific alternative lists (Dabur vs Colgate, Indian EVs vs Tesla).",
        "insight": "US tariff pressure is paradoxically strengthening the Make in India narrative among consumers. Rather than creating anxiety about export losses, tariffs are activating a nationalist consumer response that redirects purchasing toward Indian brands. The tariff war is achieving what years of 'Vocal for Local' campaigns struggled to: giving consumers a concrete, emotionally compelling reason to switch from foreign to Indian brands. The threat from outside is doing more for domestic brand preference than internal persuasion.",
        "implication": "Geopolitical friction is a more powerful driver of consumer nationalism than policy campaigns. Every tariff escalation or diplomatic insult creates a window of heightened willingness to 'buy Indian.' However, this sentiment is reactive and may fade when tensions ease. Brands that capture consumers during these moments and retain them through product quality will gain lasting market share.",
        "recommendation": "Monitor geopolitical triggers (tariff announcements, diplomatic incidents) as marketing activation moments for Indian brands. Have 'Buy Indian' campaign assets ready to deploy within 48 hours of a trigger event. Use the emotional window to acquire customers, then retain them through product quality and value, not nationalism alone.",
        "further_validation": "Track actual purchase behavior changes (not just stated intent) during tariff escalation periods vs baseline. Measure customer retention rates for Indian brands acquired during nationalist sentiment spikes.",
        "supporting_theme_ids": ["THM_09"],
        "supporting_item_count": 562,
        "source_urls": [],
        "is_grounded": True,
        "is_non_obvious": True,
        "is_actionable": True,
        "is_specific": True,
        "is_falsifiable": True,
        "passed_quality_gates": True
    },
    {
        "insight_id": "INS_010",
        "observation": "The assembly vs manufacturing debate (379 items, 10.0%) has a moderate NSS of +0.22. The 'screwdriver technology' critique is persistent and specific: consumers distinguish between final assembly (putting imported components together) and genuine manufacturing (designing and producing components domestically). The iPhone is the emblematic case - 'assembled in India' using Chinese displays, chips, and batteries. Critics frame this as value capture of only 10-15%, while proponents argue it is the necessary first step on a value-chain escalator.",
        "insight": "The assembly-vs-manufacturing distinction has become the single most effective counter-argument against Make in India claims. It is used by opposition politicians, media critics, and economically-literate consumers to deflate any manufacturing success story. Importantly, even consumers who support Make in India are increasingly aware of this distinction, creating cognitive dissonance: they want to believe India manufactures, but they know it mostly assembles. The 'value-chain escalator' argument (assembly today leads to components tomorrow) is present but less emotionally compelling than the immediate critique.",
        "implication": "Every manufacturing milestone that cannot withstand the 'but is it really manufactured or just assembled?' test will face immediate narrative deflation. This creates a communications arms race where the definition of success keeps moving upward. Yesterday's win (assembly plant) is today's criticism (just assembly, not manufacturing).",
        "recommendation": "Get ahead of the assembly critique by proactively publishing domestic content percentages and improvement trajectories. Instead of defending assembly as a stepping stone, show concrete milestones: 'Last year 15% domestic content, this year 25%, target 50% by 2028.' Make the value-chain escalator visible and measurable rather than theoretical.",
        "further_validation": "Track domestic content percentages in key PLI-beneficiary product categories over time. Survey consumers on whether they distinguish between assembly and manufacturing, and whether trajectory data (improving domestic content %) changes their perception.",
        "supporting_theme_ids": ["THM_10"],
        "supporting_item_count": 379,
        "source_urls": [],
        "is_grounded": True,
        "is_non_obvious": True,
        "is_actionable": True,
        "is_specific": True,
        "is_falsifiable": True,
        "passed_quality_gates": True
    },
    {
        "insight_id": "INS_011",
        "observation": "Infrastructure and industrial capacity building (1,017 items, 26.8%) has a positive NSS of +0.39. Discussion covers expressways (Delhi-Mumbai Expressway reducing 2 days to 12 hours), airports (new international airports in tier-2 cities), railways (bullet train, Vande Bharat), ports (Sagarmala), industrial corridors, semiconductor fabs, and renewable energy installations. The Mumbai-Ahmedabad bullet train's budget escalation from INR 1.08 lakh crore to INR 2 lakh crore is the most cited negative data point.",
        "insight": "Infrastructure is perceived as the most tangible and politically-neutral evidence of national progress. Unlike manufacturing output statistics that are contested, a new expressway or airport is physically visible and experientially verifiable. This makes infrastructure the strongest foundation for Make in India credibility - consumers can see and use it. However, the infrastructure narrative is vulnerable to cost-overrun and delay stories (bullet train being the prime example), which shift the frame from 'India is building' to 'India is wasting money.'",
        "implication": "Infrastructure development creates a physical foundation for manufacturing confidence. When consumers can see new expressways, industrial parks, and factory clusters, they are more likely to believe that India is genuinely industrializing. This suggests that infrastructure visibility (not just investment) is a critical input to manufacturing narrative credibility.",
        "recommendation": "Connect infrastructure milestones to manufacturing outcomes in communications: 'The Delhi-Mumbai Expressway reduces logistics costs for manufacturers by X%, enabling Y factories to export competitively.' Every infrastructure launch should include a manufacturing impact story. Proactively address cost-overrun narratives with value-delivered metrics.",
        "further_validation": "Survey consumers in regions with new infrastructure (expressway, industrial corridor) vs control regions on their perception of manufacturing opportunity and Make in India credibility. Measure whether infrastructure proximity correlates with manufacturing sentiment.",
        "supporting_theme_ids": ["THM_11"],
        "supporting_item_count": 1017,
        "source_urls": [],
        "is_grounded": True,
        "is_non_obvious": True,
        "is_actionable": True,
        "is_specific": True,
        "is_falsifiable": True,
        "passed_quality_gates": True
    },
    {
        "insight_id": "INS_012",
        "observation": "Employment and workforce development (509 items, 13.4%) has a moderate NSS of +0.28. The PLI-driven employment story (1.33M jobs, 4 lakh direct factory jobs, women comprising a large share of Foxconn workforce) is the most cited positive. Against this, consumers raise persistent concerns: '2 crore jobs per year' promise unfulfilled, youth unemployment at record highs, brain drain of talent to the US/Gulf, and the quality of factory jobs (wage levels, working conditions). The women-in-manufacturing narrative (especially at Foxconn/Apple plants) is notably positive and bipartisan.",
        "insight": "Employment is the ultimate accountability metric for Make in India in consumers' minds - 'if it doesn't create jobs, it doesn't matter.' The 1.33M PLI jobs figure is powerful but is repeatedly challenged by the unfulfilled 2 crore annual promise and by youth unemployment statistics. However, the women-in-manufacturing narrative has emerged as a uniquely uncontested success story - even critics of Make in India acknowledge the social value of women gaining factory employment. This is the single talking point that crosses political lines.",
        "implication": "The jobs narrative is Make in India's most vulnerable flank because it is the most personally relevant to consumers and the most easily falsified by lived experience. A consumer who cannot find a manufacturing job, or whose children cannot, will not be persuaded by macro statistics. However, the women-in-manufacturing story provides a genuinely novel and emotionally compelling sub-narrative that is currently under-leveraged.",
        "recommendation": "Elevate the women-in-manufacturing narrative as a centrepiece of Make in India communications - it is the one story that earns bipartisan respect. Publish granular employment data by district, demographic, and wage level rather than aggregate national figures. Partner with vocational training institutions to create visible pathways from training to manufacturing employment, giving 'jobs' a tangible, accessible meaning.",
        "further_validation": "Conduct a panel study tracking employment outcomes of manufacturing training program graduates over 24 months. Survey perception of Make in India among employed-in-manufacturing vs job-seeking demographics to quantify the lived-experience gap.",
        "supporting_theme_ids": ["THM_12"],
        "supporting_item_count": 509,
        "source_urls": [],
        "is_grounded": True,
        "is_non_obvious": True,
        "is_actionable": True,
        "is_specific": True,
        "is_falsifiable": True,
        "passed_quality_gates": True
    },
]

# Write insights
out_dir = RUN_DIR / 'insights'
out_dir.mkdir(exist_ok=True)
(out_dir / 'insights.json').write_text(
    json.dumps(insights, indent=2, ensure_ascii=False), encoding='utf-8'
)

print(f"Written {len(insights)} insights to {out_dir / 'insights.json'}")
for ins in insights:
    print(f"  {ins['insight_id']}: {ins['observation'][:80]}...")
