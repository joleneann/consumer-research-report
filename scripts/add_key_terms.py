"""Add Key Terms sections to methodology.docx and product_documentation.docx.

Inserts:
- methodology.docx: new Section 2 "Key Terms" before Stage 0, renumbers subsequent sections
- product_documentation.docx: new "Key Terms" subsection inside Section 1

Also fixes font to Lato throughout both documents (replacing Cambria and other fonts).

Run: py scripts/add_key_terms.py
"""

from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Pt, RGBColor
from pathlib import Path
import copy

DOCS_DIR = Path(__file__).parent.parent / "docs"
METHODOLOGY = DOCS_DIR / "methodology.docx"
PRODUCT = DOCS_DIR / "product_documentation.docx"

LATO = "Lato"


# ---------------------------------------------------------------------------
# Paragraph builder helpers
# ---------------------------------------------------------------------------

def _make_para_elem(style_val: str, segments: list) -> object:
    """Build a <w:p> element.

    segments: list of (text, bold) tuples. text may contain leading/trailing spaces.
    """
    p = OxmlElement("w:p")
    pPr = OxmlElement("w:pPr")
    pStyle = OxmlElement("w:pStyle")
    pStyle.set(qn("w:val"), style_val)
    pPr.append(pStyle)
    p.append(pPr)

    for text, bold in segments:
        if not text:
            continue
        r = OxmlElement("w:r")
        rPr = OxmlElement("w:rPr")
        # Font
        rFonts = OxmlElement("w:rFonts")
        rFonts.set(qn("w:ascii"), LATO)
        rFonts.set(qn("w:hAnsi"), LATO)
        rPr.append(rFonts)
        if bold:
            b = OxmlElement("w:b")
            rPr.append(b)
        r.append(rPr)
        t = OxmlElement("w:t")
        t.text = text
        if text.startswith(" ") or text.endswith(" "):
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        r.append(t)
        p.append(r)

    return p


def _insert_before(ref_para, paragraphs_content: list):
    """Insert multiple paragraphs before ref_para (in order).

    paragraphs_content: list of (style_val, segments) tuples.
    Inserts in reverse so final order matches list order.
    """
    ref = ref_para._element
    for style_val, segments in paragraphs_content:
        p = _make_para_elem(style_val, segments)
        ref.addprevious(p)


# ---------------------------------------------------------------------------
# Key Terms content
# ---------------------------------------------------------------------------

# Each entry: (style_val, [(text, bold), ...])
# style_val: "Heading1", "Heading2", "Heading3", "Normal"
# Bold term name followed by definition in one paragraph = two runs

def _term(name: str, definition: str):
    """Return a Normal paragraph with bold term name followed by definition."""
    return ("Normal", [(name, True), (": " + definition, False)])


METHODOLOGY_KEY_TERMS = [
    # Section heading
    ("Heading1", [("2. Key Terms", False)]),
    ("Normal", [("The following terms are used throughout this document and in all research reports. Definitions are provided here to prevent misinterpretation.", False)]),

    # 2.1 Core Concepts
    ("Heading1", [("2.1 Core Concepts", False)]),

    _term("Source",
        "A single piece of content collected from a platform: a Reddit comment, a YouTube "
        "comment, a news article, a product review, an academic abstract, or a web search result. "
        "Each source has a platform, a timestamp, engagement metadata, and text content. This is "
        "the atomic unit of evidence in the pipeline. Source is not the same as platform. A single "
        "platform can contribute thousands of sources. The quality gate 'Grounded (>=3 sources)' "
        "means at least three distinct data items must support a theme - not three platforms."),

    _term("Platform",
        "The channel or service where content was published. Currently supported: Reddit, YouTube, "
        "News, Academic Research, Google Trends, Web Search, Amazon, Flipkart, Instagram, and "
        "Twitter/X. Platform is a property of each source item, not interchangeable with source "
        "count. Platform diversity is a distinct scoring dimension in Confidence: an insight backed "
        "by sources from five platforms scores higher than one backed by the same number of sources "
        "all from a single platform."),

    _term("Corpus",
        "The deduplicated, relevance-filtered collection of all data items after Stage 3. The "
        "corpus contains unique items that passed relevance classification. Items rejected during "
        "relevance filtering are not part of the corpus. Example: if 2,000 items are collected and "
        "60% pass relevance filtering, the corpus contains 1,200 items. All analysis in Stages 4-7 "
        "operates on the corpus."),

    _term("Theme",
        "A recurring pattern of discussion extracted inductively from the corpus during Stage 4. "
        "Themes are not predefined - they emerge from reading the data. The analyst does not decide "
        "in advance what themes to look for; the corpus reveals them. A theme becomes well-formed "
        "when it has at least 20 supporting items and at least 1.5% prevalence in the corpus. A "
        "theme is not yet an insight - it is the observed pattern. 'Consumers frequently discuss "
        "taste changes after reformulation' is a theme."),

    _term("Insight",
        "The synthesised, decision-grade output built on top of one theme during Stage 5. Every "
        "theme produces exactly one insight. An insight has five layers: Observation (what the data "
        "shows), Insight (what it means for the consumer - the why), Implication (what it means for "
        "the business), Recommendation (what the client should do), and Further Validation (what "
        "research would strengthen this). An insight must pass five quality gates before it is "
        "included in the report. 'Consumers frequently discuss taste changes' is an observation. "
        "The insight is why they are discussing it and what it means for the business."),

    _term("Brief",
        "A structured research specification agreed with the client before data collection begins. "
        "The brief defines the brand, category, research questions, geographic scope, competitor "
        "set, and aspects to investigate. The brief drives keyword expansion and collection scope. "
        "The brief defines what to collect, not what to find - themes emerge from the data "
        "regardless of whether they were anticipated in the brief."),

    _term("Inductive",
        "A bottom-up analytical approach: conclusions emerge from the data rather than being tested "
        "against predefined hypotheses. Theme extraction in this pipeline is inductive - no themes "
        "are specified in advance. This contrasts with deductive research (surveys, A/B tests) "
        "where hypotheses are stated upfront and data is used to confirm or deny them. The "
        "practical implication: the pipeline may surface themes the client did not expect or ask about."),

    # 2.2 Scoring and Measurement
    ("Heading1", [("2.2 Scoring and Measurement", False)]),

    _term("Net Sentiment Score (NSS)",
        "A measure of overall sentiment balance. Formula: NSS = (positive items - negative items) "
        "/ total items. The total includes all items: positive, negative, neutral, and mixed. "
        "Produces a value from -1.0 to +1.0. For reporting, this is converted to a percentage: "
        "-100% to +100%. An NSS of +0.15 is displayed as +15%. NSS is calculated overall, per "
        "theme, and per aspect."),

    _term("Confidence Score",
        "A measure of how certain we are that an insight reflects a real consumer pattern and not "
        "a sampling artefact. Ranges from 0.0 to 1.0 (displayed as 0-100% in reports). Calculated "
        "as a weighted average of five factors: Sample Size (25%), Source Diversity (25%), Internal "
        "Agreement (20%), Temporal Consistency (15%), and Data Recency (15%). "
        "Tiers: HIGH >=75%, MEDIUM >=50%, DIRECTIONAL >=25%, INSUFFICIENT <25%."),

    _term("Signal Strength",
        "A measure of how prominently and emphatically consumers are expressing a sentiment across "
        "the corpus. Ranges from 0.0 to 1.0 (displayed as 0-100% in reports). Calculated as a "
        "weighted average of four factors: Prevalence (35%), Engagement Level (30%), Sentiment "
        "Intensity (20%), and Conversation Depth (15%). Tiers: STRONG >=75%, MODERATE >=50%, "
        "WEAK >=25%, TRACE <25%. A theme can have moderate Signal Strength but high Confidence - "
        "this indicates broad but lukewarm sentiment that is statistically reliable."),

    _term("Prevalence",
        "The percentage of total corpus items classified as belonging to a specific theme. An item "
        "can be assigned to multiple themes; each theme's prevalence is calculated independently. "
        "Example: if 150 of 1,000 items are classified under a theme, that theme has 15% "
        "prevalence. Prevalence is within-corpus only - it cannot be projected to the general "
        "population."),

    _term("Brand Health Score",
        "A composite 0-100 score summarising overall brand perception across five components: "
        "Sentiment (30%), Engagement (25%), Advocacy (20%), Resilience (15%), and Conversation "
        "(10%). All components are data-driven. Sentiment uses NSS rescaled to 0-100. Advocacy is "
        "the proportion of items expressing strongly positive sentiment (score >=0.8 and "
        "classification = positive). Resilience measures consistency of sentiment across platforms. "
        "Conversation is log-scaled volume plus average thread depth."),

    _term("Quality Gates",
        "Five mandatory criteria that every insight must satisfy before inclusion in the report: "
        "Grounded (supported by at least three distinct source items - not three platforms), "
        "Non-obvious (not something the client already knows without data), Actionable (the client "
        "can do something with this finding), Specific (the insight is precise, not generic), "
        "Falsifiable (the insight could be proven wrong with new data). All five gates must pass. "
        "An insight that fails any gate is excluded."),

    # 2.3 Report Sections
    ("Heading1", [("2.3 Report Sections", False)]),

    _term("Insight Landscape",
        "A summary table in the report listing all insights with six columns: Insight title, Items "
        "(count of supporting sources), Prevalence in dataset, Signal Strength, Confidence Score, "
        "and NSS. This is the navigation layer - it shows the full set of findings at a glance and "
        "allows the reader to prioritise which Deep Dives to read first."),

    _term("Deep Dive",
        "The full analytical presentation of a single Insight in the report. Structure (in order): "
        "Insight title with number, data line (item count, Confidence, Signal, prevalence, NSS), "
        "radar chart, What the Data Shows, What it Means, Business Implication and Rationale, "
        "Recommendation, Further Validation, and 2-3 verbatim consumer quotes."),

    _term("Verbatim / Verbatim Quotes",
        "Direct quotations from consumers, extracted from the corpus items. Also called "
        "'Representative Voices.' Presented in the Deep Dive section for each insight. Selection "
        "criteria: preference for comments over posts (more conversational), medium length "
        "(80-500 characters), direct relevance to the theme, and cross-theme deduplication (the "
        "same item is not quoted in more than one theme). Verbatims are lightly edited only for "
        "length (ellipsis shown) - never paraphrased."),

    _term("Relevance Filter",
        "Stage 3 of the pipeline. An AI classification step that reads each item and decides "
        "whether it is genuinely about the brand or topic under study. Items that discuss the "
        "category generically without brand connection, spam, or completely off-topic content are "
        "rejected. The relevance filter is distinct from engagement filtering - it removes "
        "off-topic content regardless of engagement level, and retains on-topic content regardless "
        "of engagement level."),

    # 2.4 Pipeline Terms
    ("Heading1", [("2.4 Pipeline Terms (Technical)", False)]),

    _term("Normalization",
        "Stage 2 of the pipeline. The conversion of data from platform-specific formats into a "
        "standardised structure: text content, source platform, unique ID, publication date, URL, "
        "and engagement score. This allows Reddit comments, YouTube comments, news articles, and "
        "product reviews to be processed identically in downstream stages. After normalization, "
        "the origin platform is metadata - not a structural difference."),

    _term("Deduplication",
        "The removal of duplicate items during Stage 2. Each item receives a deterministic ID "
        "generated by hashing the source URL and content text together using SHA-256. If the same "
        "piece of content appears in multiple collection passes or from multiple search queries, it "
        "is counted once. Thread-level deduplication also applies: a maximum of five comments per "
        "Reddit thread are retained, selected by random seed (not by engagement) to prevent "
        "high-engagement comments from dominating."),

    _term("Sentiment Classification",
        "The categorisation of each corpus item as positive, negative, neutral, or mixed. "
        "Performed during Stage 4. Each item also receives a numeric sentiment score from -1.0 to "
        "+1.0. A score near +1.0 indicates strong positive sentiment; near -1.0 indicates strong "
        "negative; near 0 indicates neutral. Mixed items contain both positive and negative "
        "signals within the same text. Sentiment classification (categorical) is distinct from "
        "sentiment score (continuous numeric)."),

    _term("Aspect-Based Sentiment Analysis (ABSA)",
        "Sentiment analysis performed per aspect (feature) of the brand or product, not just "
        "overall. For a food brand, aspects might include taste, price, packaging, and "
        "availability. Each item may express positive sentiment about taste and negative sentiment "
        "about price simultaneously. ABSA surfaces these distinctions. Aspects with fewer than 10 "
        "mentions are excluded from reporting as the sample is too small to compute a meaningful NSS."),

    _term("Emotion Classification (Plutchik)",
        "Classification of each item against Plutchik's Wheel of Emotions: eight primary emotions "
        "- joy, trust, fear, surprise, sadness, disgust, anger, and anticipation. Each item "
        "receives one primary emotion label in addition to its sentiment score. Emotion "
        "distribution across themes surfaces patterns beyond positive/negative - a theme may have "
        "positive sentiment but high fear (consumers who approve of the product but worry about "
        "ingredients). Performed in the same pass as sentiment classification."),

    _term("Internal Agreement",
        "A Confidence factor (weight 20%) measuring how consistently items within a theme express "
        "the same sentiment direction. Calculated as the proportion of items matching the dominant "
        "sentiment, adjusted downward for fragmentation across multiple sentiment categories. High "
        "agreement (e.g., 80% of theme items are positive) scores higher than a polarised split. "
        "A theme with high agreement is more likely to reflect a genuine, stable consumer sentiment."),

    _term("Source Diversity",
        "A Confidence factor (weight 25%) measuring how many platforms contribute to a theme and "
        "how evenly items are distributed across them. Uses the Herfindahl-Hirschman Index (HHI), "
        "an economic concentration measure. Score = 0.6 * (platforms covered / total platforms) + "
        "0.4 * balance penalty (1/n_platforms / HHI). A theme supported equally by three platforms "
        "scores higher than a theme where 95% of items come from one platform."),

    _term("Temporal Consistency",
        "A Confidence factor (weight 15%) measuring whether a theme's signal persists across the "
        "study period or appears as a brief spike. The study period is divided into four equal time "
        "windows; item distribution across windows is measured for evenness. A theme with "
        "consistent presence across all four windows scores higher than one where 80% of items "
        "appear in a single week."),

    _term("Data Recency",
        "A Confidence factor (weight 15%) measuring how recent the supporting items are. Uses "
        "exponential decay: score = exp(-0.005 * days_old), giving a half-life of approximately "
        "140 days. Items from the last 30 days score highest; scores decay continuously with age. "
        "Items older than one year approach zero but do not reach it."),

    _term("Sentiment Intensity",
        "A Signal Strength factor (weight 20%) measuring the average emotional strength of items "
        "in a theme. Calculated as a blend of two components: average absolute distance of "
        "sentiment scores from neutral (0.5), and standard deviation of sentiment scores across "
        "items (polarisation). Formula: min(1.0, avg_distance * 2.5 + std_dev * 1.5). Captures "
        "both how extreme and how polarised the sentiment is. Distinct from the per-item sentiment "
        "score - it measures strength, not direction."),

    _term("Engagement Level",
        "A Signal Strength factor (weight 30%) measuring how engaged the audience was with items "
        "in a theme (upvotes on Reddit, likes on YouTube, comment counts on news). Calculated as "
        "a blend of two components: absolute engagement ratio (item average / corpus-wide p75 "
        "engagement, log-scaled, 40% weight) and relative percentile rank of the insight's average "
        "engagement among all insights (60% weight). The relative component guarantees "
        "differentiation across insights regardless of overall engagement levels."),

    _term("Conversation Depth",
        "A Signal Strength factor (weight 15%) measuring the average reply depth of items in a "
        "theme. Calculated as 60% comment ratio (proportion of items that are comments, not posts) "
        "plus 40% average comment depth (number of reply layers, log-scaled). Platforms supporting "
        "threaded discussion (Reddit, YouTube, news) contribute to this factor. Items with no "
        "replies contribute zero to the depth component."),

    _term("Two-Pass Approach",
        "The theme extraction method used in Stage 4. Pass 1 (Discovery): an AI model reads a "
        "stratified sample of up to 300 items and identifies 8-15 candidate themes with labels, "
        "descriptions, and keywords. Pass 2 (Mapping): all remaining corpus items are classified "
        "against the discovered themes in batches of 30. Each item can match zero, one, or "
        "multiple themes. The discovery sample is excluded from Pass 2 to avoid bias."),

    _term("Stratified Sample",
        "Items drawn from each platform in proportion to that platform's share of the corpus. If "
        "the corpus is 40% Reddit, 50% YouTube, and 10% News, the 300-item discovery sample "
        "contains approximately 120 Reddit items, 150 YouTube items, and 30 News items. This "
        "ensures themes are discovered across all platforms, not just the dominant one. "
        "Random seed 42 is used for reproducibility."),

    _term("Validation Gate",
        "An automated check run between Stage 4 (Analysis) and Stage 5 (Synthesis). Verifies that "
        "fewer than 10% of corpus items remain unassigned to any theme after Pass 2. If more than "
        "10% are unthemed, the pipeline halts and requires a Narrative Review Pass before synthesis "
        "proceeds. This prevents the report from being generated on incomplete theme coverage."),

    _term("Narrative Review Pass",
        "A mandatory human-or-AI pass over unthemed items after Pass 2 of theme extraction. The "
        "reviewer reads unthemed items looking for patterns that keyword matching cannot detect: "
        "cultural or celebrity references, misinformation framing, moral debates, sarcasm, irony, "
        "and memes. Any newly discovered narrative themes are added and items reclassified. "
        "Completes when fewer than 10% of corpus items remain unthemed. Never skipped."),

    _term("Keyword Expansion",
        "The process of converting a research brief into a comprehensive set of search queries. "
        "Generates brand name variants, common misspellings, Hindi and Hinglish equivalents for "
        "Indian market studies, competitor comparison terms, occasion-based terms, and "
        "complaint-pattern terms. Every generated query includes the brand name - category-only "
        "queries (e.g., 'best shampoo') are not generated, as they return generic content "
        "unrelated to the brand."),

    _term("Query Framing Bias",
        "A structural limitation of keyword-driven collection. The search queries used determine "
        "which content is found. Queries not mentioning a topic will not surface that topic "
        "regardless of how much consumers discuss it. Mitigated through inductive theme extraction "
        "(themes discovered from data, not pre-specified) and mandatory blank-slate queries "
        "(brand name only, no contextual framing). Cannot be fully eliminated."),

    _term("Signal vs. Noise",
        "Signal is genuine consumer opinion relevant to the research question. Noise is off-topic "
        "content, spam, bots, and low-quality data. The pipeline applies three layers of noise "
        "removal: brand-anchored keyword expansion (Layer 1), collector-level brand validation "
        "(Layer 2), and post-collection quality audit (Layer 3). Further filtered by Stage 3 "
        "Relevance Filter. The corpus is the signal layer."),

    _term("Triangulation",
        "Using multiple independent data sources to corroborate a finding. A theme supported by "
        "Reddit posts, YouTube comments, and news articles is more robust than a theme found only "
        "on Reddit, because three independent channels point to the same consumer behaviour. "
        "Source Diversity in Confidence scoring formalises triangulation: insights with "
        "cross-platform support receive higher confidence scores."),
]


PRODUCT_KEY_TERMS = [
    ("Heading3", [("Key Terms", False)]),
    ("Normal", [("The following terms appear throughout this document and in all research reports. "
                 "Read these before Section 2.", False)]),

    _term("Source",
        "A single piece of content: a Reddit comment, a YouTube comment, a news article, a product "
        "review. This is the unit of evidence the pipeline collects and analyses. Not the same as "
        "platform. One platform can contribute thousands of sources. When the report says an "
        "insight is 'supported by 127 sources,' it means 127 individual pieces of content - not "
        "127 platforms."),

    _term("Platform",
        "The channel where content was published: Reddit, YouTube, Instagram, News, Amazon, and so "
        "on. Platform is a property of each source item. Source diversity in Confidence scoring "
        "rewards insights corroborated across multiple platforms, not just multiple items from "
        "one platform."),

    _term("Corpus",
        "The full set of deduplicated, on-topic items after relevance filtering. The corpus is the "
        "evidence layer - everything in the report is derived from it. Corpus size (shown on the "
        "cover page as 'Items Analysed') reflects items after deduplication and relevance "
        "filtering, not raw collected volume."),

    _term("Theme",
        "A recurring pattern of discussion discovered inductively from the corpus. Themes are not "
        "predefined - they emerge from reading the data. The pipeline identifies 8-16 themes per "
        "study. Themes are an internal processing stage; the client-facing equivalent is an Insight."),

    _term("Insight",
        "The synthesised, decision-grade output built on top of one theme. Each insight has five "
        "layers: Observation (what the data shows), Insight (what it means for the consumer), "
        "Implication (what it means for the business), Recommendation (what to do), and Further "
        "Validation (what research would strengthen this). There is exactly one insight per theme. "
        "When the report says '12 insights,' it means 12 themes were discovered and synthesised "
        "into 12 decision-grade findings."),

    _term("Brief",
        "The structured research specification agreed before collection begins. The brief defines "
        "the brand, category, research questions, geographic scope, competitors, and aspects. The "
        "brief tells the pipeline what to collect - not what to find. Themes emerge from the data "
        "regardless of whether they were anticipated in the brief."),

    _term("Inductive",
        "Bottom-up analysis: conclusions emerge from the data rather than being tested against "
        "predefined hypotheses. The pipeline does not decide in advance what themes to look for. "
        "This is why findings sometimes surprise clients - the data surfaces what consumers are "
        "actually talking about, including topics the brief did not mention."),

    _term("Net Sentiment Score (NSS)",
        "A measure of sentiment balance. Formula: (positive items - negative items) / total items. "
        "The total includes all items (positive, negative, neutral, mixed). Displayed as a "
        "percentage: +15% means 15% more positive than negative items. Range is -100% to +100%. "
        "Calculated overall, per insight, and per aspect (e.g., packaging NSS vs. taste NSS)."),

    _term("Confidence Score",
        "How certain we are that an insight is real and not a sampling artefact. Displayed as a "
        "percentage (0-100%). Combines five factors: how many items support the insight, how many "
        "platforms they come from, how consistently they express the same sentiment, how evenly "
        "distributed they are over time, and how recent they are. HIGH confidence (75%+) means the "
        "finding is robust. DIRECTIONAL (25-50%) means it is indicative but needs validation."),

    _term("Signal Strength",
        "How prominently and emphatically consumers are expressing a sentiment. Displayed as a "
        "percentage (0-100%). Combines prevalence (how many items), engagement (upvotes, likes, "
        "shares), sentiment intensity (how strong and polarised the feeling), and conversation "
        "depth (how much discussion it generated). STRONG (75%+) means the topic is both "
        "widespread and emotionally charged."),

    _term("Prevalence",
        "The percentage of corpus items that belong to a given insight's theme. A theme with 15% "
        "prevalence means 15% of all analysed items discuss that topic. Prevalence is within the "
        "corpus only - it cannot be projected to the general population."),

    _term("Brand Health Score",
        "A composite 0-100 score derived from five data components: overall sentiment (30%), "
        "engagement level (25%), proportion of strongly positive items (20%), consistency of "
        "sentiment across platforms (15%), and conversation volume and depth (10%). Shown on the "
        "cover page and in a dedicated section of the report."),

    _term("Quality Gates",
        "Five criteria every insight must pass to appear in the report: Grounded (supported by at "
        "least 3 source items - not 3 platforms), Non-obvious (not already known without data), "
        "Actionable (the client can act on it), Specific (not vague), and Falsifiable (could be "
        "proven wrong). All five must pass. This prevents the report from surfacing trivial or "
        "unsubstantiated findings."),

    _term("Insight Landscape",
        "The summary table in the report listing all insights with their item counts, prevalence, "
        "Signal Strength, Confidence, and NSS. Use it to orient yourself before reading the Deep "
        "Dives, and to prioritise which findings deserve the most attention."),

    _term("Deep Dive",
        "The full analytical presentation of one insight in the report. Includes: observation, "
        "insight, business implication, recommendation, further validation, and 2-3 verbatim "
        "consumer quotes. Preceded by a radar chart showing the insight's Confidence and Signal "
        "Strength scoring profile."),

    _term("Verbatim Quotes",
        "Direct quotations from consumers in the corpus, presented in each Deep Dive. Also called "
        "'Representative Voices.' These are exact quotes, not paraphrases. Selected to be "
        "representative of the theme's sentiment, appropriately concise, and drawn from genuine "
        "consumer voices (comments preferred over brand or media posts)."),

    _term("Relevance Filter",
        "The Stage 3 step that removes off-topic content from the corpus. An AI classifier reads "
        "each item and removes it if it discusses the category generically without brand connection, "
        "is spam, or is completely off-topic. Distinct from engagement filtering: removes off-topic "
        "content at any engagement level and retains on-topic content at any engagement level."),

    _term("Signal vs. Noise",
        "Signal is genuine consumer opinion relevant to the research question. Noise is off-topic "
        "content, spam, generic category discussion, and low-quality data. The corpus is the signal "
        "layer - every insight in the report is derived exclusively from signal."),
]


# ---------------------------------------------------------------------------
# Font fix helpers
# ---------------------------------------------------------------------------

def _fix_fonts_in_doc(doc):
    """Replace Cambria (and any non-Lato font) with Lato throughout the doc XML."""
    BAD_FONTS = {"Cambria", "Cambria Math", "Times New Roman", "Calibri", "Arial"}
    ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

    for elem in doc.element.iter():
        tag = elem.tag.replace("{" + ns + "}", "w:")
        if tag in ("w:rFonts", "w:fonts"):
            for attr in list(elem.attrib):
                val = elem.attrib[attr]
                if val in BAD_FONTS:
                    elem.attrib[attr] = LATO

    # Also fix default fonts in styles
    for style in doc.styles:
        try:
            if style.font.name and style.font.name in BAD_FONTS:
                style.font.name = LATO
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Renumber methodology sections
# ---------------------------------------------------------------------------

def _renumber_methodology(doc):
    """Increment section numbers 2-10 in Heading 1 paragraphs."""
    for para in doc.paragraphs:
        if para.style.name != "Heading 1":
            continue
        text = para.text.strip()
        # Match "N. " at start where N is a digit 2-9 or "10."
        for old, new in [("10.", "11."), ("9.", "10."), ("8.", "9."),
                         ("7.", "8."), ("6.", "7."), ("5.", "6."),
                         ("4.", "5."), ("3.", "4."), ("2.", "3.")]:
            if text.startswith(old + " "):
                # Replace only in the run that contains the number
                for run in para.runs:
                    if run.text.startswith(old):
                        run.text = run.text.replace(old, new, 1)
                        break
                    elif old in run.text:
                        run.text = run.text.replace(old, new, 1)
                        break
                break


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def update_methodology():
    doc = Document(METHODOLOGY)

    # Find "2. Stage 0" paragraph (insert Key Terms before it)
    ref_para = None
    for p in doc.paragraphs:
        if p.style.name == "Heading 1" and p.text.strip().startswith("2."):
            ref_para = p
            break

    if ref_para is None:
        print("ERROR: Could not find Stage 0 section in methodology.docx")
        return

    # Renumber existing sections first (2->3, 3->4, etc.)
    _renumber_methodology(doc)

    # Insert Key Terms section before (now renumbered) Stage 0
    _insert_before(ref_para, METHODOLOGY_KEY_TERMS)

    # Fix fonts
    _fix_fonts_in_doc(doc)

    doc.save(METHODOLOGY)
    print(f"methodology.docx updated: Key Terms added, sections renumbered, fonts fixed")


def update_product():
    doc = Document(PRODUCT)

    # Find "2. The Mental Model" paragraph (insert Key Terms before it)
    ref_para = None
    for p in doc.paragraphs:
        if p.style.name == "Heading 1" and p.text.strip().startswith("2."):
            ref_para = p
            break

    if ref_para is None:
        print("ERROR: Could not find Section 2 in product_documentation.docx")
        return

    _insert_before(ref_para, PRODUCT_KEY_TERMS)
    _fix_fonts_in_doc(doc)

    doc.save(PRODUCT)
    print(f"product_documentation.docx updated: Key Terms added, fonts fixed")


if __name__ == "__main__":
    update_methodology()
    update_product()
    print("Done.")
