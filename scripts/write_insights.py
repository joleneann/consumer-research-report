"""Write synthesized insights based on theme analysis."""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

run_dir = Path('runs/20260407_143544_98a8c6')
analysis = json.loads((run_dir / 'analysis' / 'results.json').read_text(encoding='utf-8'))
corpus = json.loads((run_dir / 'filtered' / 'corpus.json').read_text(encoding='utf-8'))

corpus_by_id = {item['item_id']: item for item in corpus}
theme_data = {t['theme_id']: t for t in analysis['themes']}
total = analysis['total_items_analyzed']

insights = [
    {
        'insight_id': 'INS_001',
        'observation': f"Grey hair coverage dominates consumer motivation for hair colour use, with {theme_data['THM_01_GREY_COVERAGE']['item_count']} items ({theme_data['THM_01_GREY_COVERAGE']['prevalence_pct']}% of corpus) discussing grey coverage. Sentiment is strongly positive (NSS +{theme_data['THM_01_GREY_COVERAGE']['net_sentiment_score']:.0%}) with consumers actively seeking quick, effective solutions. Root touch-up products and instant coverage sticks feature prominently across all platforms.",
        'insight': "For Indian consumers, hair colouring is primarily functional rather than aspirational - covering grey hair is a grooming necessity tied to social perception and professional appearance. The dominant need is not creative expression but managing visible ageing, making speed and effectiveness the primary purchase drivers rather than shade variety.",
        'implication': "Brands that position hair colour as a grey management solution rather than a fashion statement will capture the largest segment of the Indian market. The functional framing allows for premium pricing if speed and reliability are demonstrably superior.",
        'recommendation': "Launch or expand a dedicated grey coverage sub-brand with messaging centred on time savings (5-minute claims), natural appearance, and reliability. Position grey coverage products at eye level in retail and as the default category entry point in e-commerce listings.",
        'further_validation': "Conduct a quantitative survey segmenting consumers by age cohort (25-35, 36-45, 46+) to measure the relative importance of grey coverage vs creative colour by demographic.",
        'supporting_theme_ids': ['THM_01_GREY_COVERAGE'],
        'supporting_item_count': theme_data['THM_01_GREY_COVERAGE']['item_count'],
        'source_urls': [],
        'representative_quotes': theme_data['THM_01_GREY_COVERAGE']['representative_quotes'],
    },
    {
        'insight_id': 'INS_002',
        'observation': f"Natural and chemical-free products generate the highest positive sentiment in the corpus (NSS +{theme_data['THM_02_NATURAL_CHEMICAL_FREE']['net_sentiment_score']:.0%}), with {theme_data['THM_02_NATURAL_CHEMICAL_FREE']['item_count']} items ({theme_data['THM_02_NATURAL_CHEMICAL_FREE']['prevalence_pct']}% prevalence). Consumers actively seek ammonia-free, paraben-free, PPD-free, herbal, and organic formulations. Terms like 'chemical-free', 'natural ingredients', and 'no side effects' consistently drive purchase decisions across Amazon reviews and social media.",
        'insight': "Indian consumers carry a deep-rooted distrust of chemical hair colour formulations, driven by personal or familial experiences with allergic reactions, skin darkening, and hair damage. The 'natural' label functions as a trust signal - consumers equate natural ingredients with safety, even when the actual formulation science may not differ substantially.",
        'implication': "The natural/chemical-free positioning is not a niche premium segment but a mainstream expectation in India. Brands that cannot credibly claim natural credentials will face growing resistance, particularly among health-conscious urban consumers and the ayurveda-aware demographic.",
        'recommendation': "Reformulate or reposition products with prominent 'ammonia-free', 'PPD-free', and 'dermatologist tested' claims. Invest in transparent ingredient communication on packaging and e-commerce listings. Consider launching an ayurvedic or plant-based sub-line for the Indian market.",
        'further_validation': "Run a conjoint analysis testing willingness-to-pay for natural vs conventional formulations, segmented by metro vs tier-2/3 cities.",
        'supporting_theme_ids': ['THM_02_NATURAL_CHEMICAL_FREE'],
        'supporting_item_count': theme_data['THM_02_NATURAL_CHEMICAL_FREE']['item_count'],
        'source_urls': [],
        'representative_quotes': theme_data['THM_02_NATURAL_CHEMICAL_FREE']['representative_quotes'],
    },
    {
        'insight_id': 'INS_003',
        'observation': f"Product effectiveness discussions are the largest theme with {theme_data['THM_03_PRODUCT_EFFECTIVENESS']['item_count']} items ({theme_data['THM_03_PRODUCT_EFFECTIVENESS']['prevalence_pct']}% prevalence), but carry a relatively lower NSS of +{theme_data['THM_03_PRODUCT_EFFECTIVENESS']['net_sentiment_score']:.0%}. While 65% of items are positive, {theme_data['THM_03_PRODUCT_EFFECTIVENESS']['sentiment_distribution'].get('negative', 0)} items express outright dissatisfaction with product claims not matching results - colour coming out different from the box, uneven coverage, and products that simply do not work.",
        'insight': "There is a significant expectations gap in the Indian hair colour market. Consumers purchase based on packaging claims and box colour swatches, but frequently receive different results. This gap is amplified for dark-haired Indian consumers where colour lift is inherently limited without bleaching - a nuance that packaging rarely communicates.",
        'implication': "Unmet expectations drive negative reviews, returns, and brand switching. The gap between marketing claims and actual results on Indian hair textures represents both a risk for incumbent brands and an opportunity for challengers who communicate honestly about expected outcomes on dark hair.",
        'recommendation': "Include realistic before/after photos on Indian hair textures in marketing materials. Add QR codes on packaging linking to application videos showing results on similar hair types. Consider a shade-match guarantee or satisfaction programme.",
        'further_validation': "Analyse return rates and negative review patterns by shade category to identify which specific colour claims have the highest expectation gap.",
        'supporting_theme_ids': ['THM_03_PRODUCT_EFFECTIVENESS'],
        'supporting_item_count': theme_data['THM_03_PRODUCT_EFFECTIVENESS']['item_count'],
        'source_urls': [],
        'representative_quotes': theme_data['THM_03_PRODUCT_EFFECTIVENESS']['representative_quotes'],
    },
    {
        'insight_id': 'INS_004',
        'observation': f"Ease of use and quick application is the most prevalent theme with {theme_data['THM_04_EASE_CONVENIENCE']['item_count']} items ({theme_data['THM_04_EASE_CONVENIENCE']['prevalence_pct']}% prevalence). Shampoo-based colours, instant colour sticks, spray-on products, and 5-10 minute application formats dominate discussions. Consumers repeatedly praise 'instant', 'quick', 'easy to apply', and 'mess-free' attributes.",
        'insight': "Indian consumers are migrating from traditional time-intensive hair colouring rituals (1-2 hour henna applications, multi-step chemical dyes) toward instant-format products. This shift is driven by urban lifestyle pressures, the desire for salon-like results at home, and the growing male grooming segment where simplicity is non-negotiable.",
        'implication': "The future of the Indian hair colour market belongs to convenience-first formats. Shampoo-based colours, colour sticks, and spray products are not just convenience segments - they represent a fundamental format shift that will erode traditional tube-and-developer products.",
        'recommendation': "Expand the instant/shampoo-based colour portfolio with sachet formats for trial and travel. Invest in applicator innovation (built-in combs, no-drip formulas, single-use sachets). Price sachets at Rs 15-30 for impulse purchase in general trade.",
        'further_validation': "Track format-level sales data (shampoo colour vs cream vs powder) quarter-over-quarter to quantify the format migration velocity.",
        'supporting_theme_ids': ['THM_04_EASE_CONVENIENCE'],
        'supporting_item_count': theme_data['THM_04_EASE_CONVENIENCE']['item_count'],
        'source_urls': [],
        'representative_quotes': theme_data['THM_04_EASE_CONVENIENCE']['representative_quotes'],
    },
    {
        'insight_id': 'INS_005',
        'observation': f"Hair damage and safety concerns appear in {theme_data['THM_05_DAMAGE_SAFETY']['item_count']} items ({theme_data['THM_05_DAMAGE_SAFETY']['prevalence_pct']}% prevalence). Despite an overall positive NSS (+{theme_data['THM_05_DAMAGE_SAFETY']['net_sentiment_score']:.0%}), {theme_data['THM_05_DAMAGE_SAFETY']['sentiment_distribution'].get('negative', 0)} items describe adverse experiences including severe allergic reactions, skin darkening around hairlines, chemical burns, hair loss, and products causing itching and irritation. Multiple consumers report requiring medical consultation after use.",
        'insight': "Safety concerns around hair colour are not hypothetical for Indian consumers - they are rooted in lived negative experiences. The tropical climate, combined with frequent reapplication needed for fast-growing dark hair, means Indian consumers face higher cumulative chemical exposure than Western counterparts. Reports of skin darkening are particularly concerning given Indian cultural sensitivity around skin tone.",
        'implication': "A single viral adverse reaction story can disproportionately damage brand trust in India, where word-of-mouth and family recommendations heavily influence purchase decisions. Safety is a competitive moat - brands that demonstrably invest in safety testing on Indian skin types will earn lasting loyalty.",
        'recommendation': "Mandate and prominently display dermatological testing results specifically on Indian skin types. Include clear patch test instructions in local languages. Develop and market a post-colour conditioning treatment that addresses the dryness and damage consumers report.",
        'further_validation': "Commission a dermatological study comparing allergic reaction rates across formulations on Indian skin types, particularly for PPD-containing vs PPD-free products.",
        'supporting_theme_ids': ['THM_05_DAMAGE_SAFETY'],
        'supporting_item_count': theme_data['THM_05_DAMAGE_SAFETY']['item_count'],
        'source_urls': [],
        'representative_quotes': theme_data['THM_05_DAMAGE_SAFETY']['representative_quotes'],
    },
    {
        'insight_id': 'INS_006',
        'observation': f"Price and value discussions span {theme_data['THM_06_PRICE_VALUE']['item_count']} items ({theme_data['THM_06_PRICE_VALUE']['prevalence_pct']}% prevalence). Consumers frequently evaluate products against salon costs, with home colouring explicitly framed as an economical alternative. Deal-hunting behaviour is prominent with consumers sharing discount codes, flash deals, and price comparisons. 'Value for money' and 'pocket-friendly' are recurring positive descriptors.",
        'insight': "Indian hair colour consumers are acutely price-sensitive and view the category through a salon-versus-home savings lens. The purchase decision is rarely about absolute price but about perceived value relative to a salon visit costing Rs 500-2000. Products priced under Rs 100 in sachet format capture impulse purchases, while Rs 200-400 range products must justify the premium through visible quality differentials.",
        'implication': "The Indian market rewards a dual pricing strategy: sachet formats for trial and general trade penetration, and larger formats for repeat purchasers who have validated effectiveness. Pricing above the Rs 400 threshold requires strong quality evidence or the product will be compared unfavourably to salon services.",
        'recommendation': "Maintain a sachet SKU at the Rs 15-30 price point for general trade. For premium products, anchor pricing against salon visit costs (not against competitor products) in all communications. Bundle application tools (gloves, brush) to increase perceived value.",
        'further_validation': "Conduct price elasticity research across metro, tier-2, and tier-3 cities to identify optimal price points by city tier and format.",
        'supporting_theme_ids': ['THM_06_PRICE_VALUE'],
        'supporting_item_count': theme_data['THM_06_PRICE_VALUE']['item_count'],
        'source_urls': [],
        'representative_quotes': theme_data['THM_06_PRICE_VALUE']['representative_quotes'],
    },
    {
        'insight_id': 'INS_007',
        'observation': f"DIY and home hair colouring discussions cover {theme_data['THM_07_DIY_HOME_COLOUR']['item_count']} items ({theme_data['THM_07_DIY_HOME_COLOUR']['prevalence_pct']}% prevalence) with positive NSS (+{theme_data['THM_07_DIY_HOME_COLOUR']['net_sentiment_score']:.0%}). Consumers share application techniques, brand comparisons, and tips for achieving salon-like results at home. First-time users seek guidance while experienced home colourers recommend specific brands and techniques.",
        'insight': "Home hair colouring in India is evolving from a budget compromise to an empowered lifestyle choice. Consumers - particularly younger women in metro cities - view DIY colouring as a form of self-reliance, not just cost savings. Reddit and YouTube function as peer-to-peer salons where technique knowledge is shared freely, reducing dependence on professional stylists.",
        'implication': "The shift to home colouring creates a direct-to-consumer opportunity but also raises the skill bar that products must accommodate. Products that simplify the application process will win in this channel, while brands that rely on salon-professional distribution will face channel erosion.",
        'recommendation': "Create branded tutorial content for YouTube and Instagram showing step-by-step home application on Indian hair. Partner with beauty micro-influencers for authentic home colouring demonstrations. Include QR-linked video tutorials on every box.",
        'further_validation': "Survey home colourers to understand the trigger for first home application (cost, convenience, pandemic habit) and what would make them switch back to salon.",
        'supporting_theme_ids': ['THM_07_DIY_HOME_COLOUR'],
        'supporting_item_count': theme_data['THM_07_DIY_HOME_COLOUR']['item_count'],
        'source_urls': [],
        'representative_quotes': theme_data['THM_07_DIY_HOME_COLOUR']['representative_quotes'],
    },
    {
        'insight_id': 'INS_008',
        'observation': f"Colour longevity and fading discussions span {theme_data['THM_08_LONGEVITY_FADING']['item_count']} items ({theme_data['THM_08_LONGEVITY_FADING']['prevalence_pct']}% prevalence). Consumers consistently report that colour fades faster than expected - within 1-2 weeks for many products, particularly shampoo-based colours and temporary sprays. The tension between wanting damage-free temporary colour and wanting long-lasting results is a recurring frustration.",
        'insight': "Indian consumers face a structural paradox in hair colour: they want chemical-free products that are also long-lasting, but gentle formulations inherently fade faster. The hot, humid Indian climate accelerates fading further. Consumers do not fully understand this trade-off, leading to dissatisfaction when 'gentle' products wash out quickly and 'long-lasting' products damage hair.",
        'implication': "Managing the longevity expectations gap is critical. Brands that explicitly communicate expected duration (number of washes, not weeks) and provide maintenance products (colour-protect shampoo, touch-up sticks) will reduce post-purchase dissatisfaction and drive repeat purchases through the maintenance product ecosystem.",
        'recommendation': "State colour longevity in 'number of washes' rather than 'weeks' on packaging. Launch a colour-maintain product line (colour-protect shampoo + conditioner) as a cross-sell. Offer touch-up sachets as refill products between full applications.",
        'further_validation': "Lab-test colour retention across formulations in humid conditions simulating Indian climate to set honest longevity benchmarks.",
        'supporting_theme_ids': ['THM_08_LONGEVITY_FADING'],
        'supporting_item_count': theme_data['THM_08_LONGEVITY_FADING']['item_count'],
        'source_urls': [],
        'representative_quotes': theme_data['THM_08_LONGEVITY_FADING']['representative_quotes'],
    },
    {
        'insight_id': 'INS_009',
        'observation': f"Henna and traditional hair colouring methods are discussed in {theme_data['THM_09_HENNA_TRADITIONAL']['item_count']} items ({theme_data['THM_09_HENNA_TRADITIONAL']['prevalence_pct']}% prevalence) with the second-highest positive sentiment (NSS +{theme_data['THM_09_HENNA_TRADITIONAL']['net_sentiment_score']:.0%}). Henna-indigo combinations for achieving natural black, traditional mehndi preparation methods, and ayurvedic hair colour recipes are shared across YouTube (regional language content) and Reddit (advice-seeking posts).",
        'insight': "Henna is not just a hair colouring method in India - it is a cultural heritage practice carrying deep trust that no modern brand has been able to fully replicate. Consumers who use henna view it as simultaneously colouring, conditioning, and nourishing hair - a holistic hair treatment rather than just a dye. The willingness to endure 2-3 hours of application time signals how deeply trusted the henna proposition is.",
        'implication': "Pure henna users represent a segment that modern brands struggle to convert because they view chemical products as fundamentally inferior, not just different. However, the pain point of long application time creates an opportunity for henna-hybrid products that deliver the trust of traditional ingredients with modern convenience.",
        'recommendation': "Develop a rapid-henna format (30-minute application with henna + indigo pre-mixed). Partner with ayurvedic brands for co-branded credibility. Use regional language content marketing to reach henna users who consume content in Hindi, Tamil, Telugu, and Malayalam.",
        'further_validation': "Ethnographic research with traditional henna users across north and south India to understand what conditions would make them trial a henna-hybrid product.",
        'supporting_theme_ids': ['THM_09_HENNA_TRADITIONAL'],
        'supporting_item_count': theme_data['THM_09_HENNA_TRADITIONAL']['item_count'],
        'source_urls': [],
        'representative_quotes': theme_data['THM_09_HENNA_TRADITIONAL']['representative_quotes'],
    },
    {
        'insight_id': 'INS_010',
        'observation': f"Beard and mens grooming colour products are discussed in {theme_data['THM_10_BEARD_MENS']['item_count']} items ({theme_data['THM_10_BEARD_MENS']['prevalence_pct']}% prevalence) with a strongly positive NSS (+{theme_data['THM_10_BEARD_MENS']['net_sentiment_score']:.0%}). Beard colour shampoos, instant beard black products, and grey beard coverage dominate. Products like Beardo Blackout Powder and beard colour shampoos are frequently discussed. Men prioritise speed (under 5 minutes), no mess, and natural appearance.",
        'insight': "The Indian male grooming colour segment is rapidly maturing from a niche to a mainstream category, driven by workplace grooming norms and dating culture among urban men aged 25-40. Unlike women who may tolerate complex application processes, men demand extreme simplicity - if a product takes more than 5 minutes or stains the sink, it is rejected. The beard colour segment specifically is growing as facial hair grooming becomes a distinct male beauty ritual.",
        'implication': "The mens hair colour segment in India is underserved relative to demand. Most male-targeted products are simply repackaged womens products. Brands that develop male-specific formulations, packaging, and retail placement will capture an expanding category with less competition than the womens segment.",
        'recommendation': "Launch a dedicated mens hair and beard colour range with male-specific packaging, 3-minute application claims, and pharmacy/general trade distribution. Target communication at normalising male grey coverage as routine grooming, not vanity.",
        'further_validation': "Survey urban Indian men aged 25-45 on grey coverage attitudes, current product usage, and willingness to pay for male-specific products vs using family/unisex products.",
        'supporting_theme_ids': ['THM_10_BEARD_MENS'],
        'supporting_item_count': theme_data['THM_10_BEARD_MENS']['item_count'],
        'source_urls': [],
        'representative_quotes': theme_data['THM_10_BEARD_MENS']['representative_quotes'],
    },
    {
        'insight_id': 'INS_011',
        'observation': f"Brand experience and trust discussions cover {theme_data['THM_11_BRAND_TRUST']['item_count']} items ({theme_data['THM_11_BRAND_TRUST']['prevalence_pct']}% prevalence). Garnier, L'Oreal, Godrej, Streax, Paradyes, Schwarzkopf, Bigen, Kokila, and Wella are frequently mentioned. Concerns about counterfeit/fake products on Amazon and Flipkart are a recurring pain point, with multiple consumers reporting receiving products that do not match the original formulation they previously purchased.",
        'insight': "Trust in the Indian hair colour market is fragile and platform-dependent. Consumers who had positive experiences with a brand in physical retail report receiving 'different' or 'fake' products when purchasing the same brand online. This erodes not just e-commerce trust but brand trust itself, as consumers cannot distinguish between genuine product quality decline and counterfeit infiltration.",
        'implication': "E-commerce counterfeiting is a brand equity crisis, not just a supply chain problem. Every fake product sold under a brands name generates a negative review that damages the brand permanently in search rankings and consumer memory. The cost of inaction exceeds the cost of authentication systems.",
        'recommendation': "Implement QR-based authentication on all products sold through e-commerce channels. Partner with Amazon and Flipkart for Brand Registry and report counterfeit sellers aggressively. Include authenticity verification messaging in packaging ('Scan to verify genuine product').",
        'further_validation': "Mystery shop own brands on Amazon/Flipkart to quantify counterfeit prevalence and identify specific seller accounts distributing fake products.",
        'supporting_theme_ids': ['THM_11_BRAND_TRUST'],
        'supporting_item_count': theme_data['THM_11_BRAND_TRUST']['item_count'],
        'source_urls': [],
        'representative_quotes': theme_data['THM_11_BRAND_TRUST']['representative_quotes'],
    },
    {
        'insight_id': 'INS_012',
        'observation': f"Colour trends and self-expression discussions span {theme_data['THM_12_TRENDS_EXPRESSION']['item_count']} items ({theme_data['THM_12_TRENDS_EXPRESSION']['prevalence_pct']}% prevalence). Burgundy, copper, chocolate brown, highlights, balayage, and ombre are popular creative colour trends. A distinct segment discusses workplace acceptability of unconventional hair colours in Indian IT companies. Purple and red shades are the most sought-after fashion colours.",
        'insight': "A generational split is emerging in the Indian hair colour market: while older consumers use colour defensively (grey coverage), younger consumers aged 18-30 use it as a form of creative self-expression and identity signalling. Workplace norms in Indian IT and services sectors are loosening, creating permission for unconventional colours that were previously restricted to 'college only'. Burgundy and copper function as safe entry points to creative colour.",
        'implication': "The creative colour segment represents future market growth as India's young demographic enters peak spending years. However, the segment requires a fundamentally different go-to-market: trend-driven limited editions, social media-first marketing, and influencer partnerships rather than traditional TV advertising.",
        'recommendation': "Launch seasonal limited-edition creative colour collections (3-4 shades per season). Create a social media campaign encouraging consumers to share hair colour transformations. Position burgundy and copper as 'professional-friendly' creative colours for the workplace-conscious segment.",
        'further_validation': "Track social media trend velocity for specific hair colour shades in India to identify emerging colours before they peak, enabling faster product development cycles.",
        'supporting_theme_ids': ['THM_12_TRENDS_EXPRESSION'],
        'supporting_item_count': theme_data['THM_12_TRENDS_EXPRESSION']['item_count'],
        'source_urls': [],
        'representative_quotes': theme_data['THM_12_TRENDS_EXPRESSION']['representative_quotes'],
    },
]

# Save
import os
os.makedirs(str(run_dir / 'insights'), exist_ok=True)
(run_dir / 'insights' / 'insights.json').write_text(
    json.dumps(insights, indent=2, default=str), encoding='utf-8'
)

print(f'Wrote {len(insights)} insights to insights/insights.json')
for ins in insights:
    print(f'  {ins["insight_id"]}: {ins["supporting_theme_ids"][0]} (n={ins["supporting_item_count"]})')
