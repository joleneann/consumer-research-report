/**
 * Generates new_sections.docx with Sections 11-14 for appending to existing documents.
 * Uses the globally installed docx npm package.
 */

const {
  Document,
  Packer,
  Paragraph,
  TextRun,
  HeadingLevel,
  Table,
  TableRow,
  TableCell,
  WidthType,
  BorderStyle,
  AlignmentType,
  ShadingType,
} = require("docx");

const fs = require("fs");
const path = require("path");

// ────────────────────────────────────────────────────────────────────────────────
// Helpers
// ────────────────────────────────────────────────────────────────────────────────

function h1(text) {
  return new Paragraph({
    text,
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 400, after: 200 },
  });
}

function h3(text) {
  return new Paragraph({
    text,
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 300, after: 150 },
  });
}

function para(text) {
  return new Paragraph({
    children: [new TextRun({ text })],
    spacing: { after: 160 },
  });
}

function bullet(text) {
  return new Paragraph({
    children: [new TextRun({ text })],
    bullet: { level: 0 },
    spacing: { after: 100 },
  });
}

function subBullet(text) {
  return new Paragraph({
    children: [new TextRun({ text })],
    bullet: { level: 1 },
    spacing: { after: 80 },
  });
}

/**
 * Build a table from headers and rows.
 * columnWidths: array of DXA widths (1 inch = 1440 DXA; total page width ~9360 DXA usable)
 */
function makeTable(headers, rows, columnWidths) {
  const totalWidth = columnWidths.reduce((a, b) => a + b, 0);

  const headerRow = new TableRow({
    tableHeader: true,
    children: headers.map((h, i) =>
      new TableCell({
        width: { size: columnWidths[i], type: WidthType.DXA },
        shading: { type: ShadingType.CLEAR, color: "auto", fill: "E2E8F0" },
        children: [
          new Paragraph({
            children: [new TextRun({ text: h, bold: true })],
            spacing: { after: 60 },
          }),
        ],
        borders: {
          top: { style: BorderStyle.SINGLE, size: 4, color: "374151" },
          bottom: { style: BorderStyle.SINGLE, size: 4, color: "374151" },
          left: { style: BorderStyle.SINGLE, size: 4, color: "374151" },
          right: { style: BorderStyle.SINGLE, size: 4, color: "374151" },
        },
      })
    ),
  });

  const dataRows = rows.map((row) =>
    new TableRow({
      children: row.map((cell, i) =>
        new TableCell({
          width: { size: columnWidths[i], type: WidthType.DXA },
          children: [
            new Paragraph({
              children: [new TextRun({ text: cell })],
              spacing: { after: 60 },
            }),
          ],
          borders: {
            top: { style: BorderStyle.SINGLE, size: 4, color: "374151" },
            bottom: { style: BorderStyle.SINGLE, size: 4, color: "374151" },
            left: { style: BorderStyle.SINGLE, size: 4, color: "374151" },
            right: { style: BorderStyle.SINGLE, size: 4, color: "374151" },
          },
        })
      ),
    })
  );

  return new Table({
    width: { size: totalWidth, type: WidthType.DXA },
    rows: [headerRow, ...dataRows],
    margins: { top: 60, bottom: 60, left: 80, right: 80 },
  });
}

function spacer() {
  return new Paragraph({ text: "", spacing: { after: 200 } });
}

// ────────────────────────────────────────────────────────────────────────────────
// SECTION 11
// ────────────────────────────────────────────────────────────────────────────────

function section11() {
  return [
    h1("Improving Report Quality Through Expanded Data Collection"),

    h3("The Free-Tier Baseline and Its Quality Ceiling"),
    para(
      "The pipeline runs on free-tier APIs by default. Each source has a hard ceiling:"
    ),
    spacer(),
    makeTable(
      ["Source", "Free Limit", "Quality Implication"],
      [
        [
          "Reddit public API",
          "~500 posts/run, rate-limited to 1 request per 2 seconds",
          "Enough for directional findings; not enough for high-confidence scores on any single theme",
        ],
        [
          "YouTube Data API",
          "10,000 quota units/day (~50 video searches)",
          "Good coverage of major content; misses long-tail and regional videos",
        ],
        [
          "NewsData.io",
          "200 articles/day",
          "Adequate for major brand events; too thin for emerging or regional stories",
        ],
        [
          "Serper (Google Search)",
          "2,500 queries lifetime on free plan",
          "Exhausted quickly on broad keyword lists; must be rationed carefully",
        ],
        [
          "OpenAlex (Academic)",
          "100,000+ calls/day",
          "Not a bottleneck at any realistic research volume",
        ],
      ],
      [2500, 3000, 3860]
    ),
    spacer(),

    h3("How More Data Directly Improves Scoring"),
    para("The pipeline's scoring system rewards volume and diversity:"),
    bullet(
      "Confidence Score — Sample Size factor (25% weight): scores 0.6 for 30–100 items per theme, rises to 1.0 for 100+ items. More data moves themes from \"Directional\" to \"High Confidence.\""
    ),
    bullet(
      "Confidence Score — Source Diversity factor (25% weight): 1 platform scores 0.3, 2 platforms scores 0.7, 3+ platforms scores 1.0. Adding Amazon reviews or Quora as a third source pushes this factor to its ceiling."
    ),
    bullet(
      "Signal Strength — Prevalence factor (35% weight): calculated as a percentage of the total corpus. A larger corpus gives more reliable prevalence percentages."
    ),
    bullet(
      "Net effect: more data produces more \"Key Finding\" insights (top-right of the matrix) and fewer \"Watch Closely\" or \"Noise\" classifications."
    ),
    spacer(),

    h3("Paid Upgrade Options Within the Same Framework"),
    para(
      "No code changes needed. All paid sources output the same schema and flow through Stages 3–7 unchanged."
    ),
    spacer(),
    makeTable(
      ["Source", "Free Limit", "Paid Upgrade", "Approx. Cost", "Quality Gain"],
      [
        [
          "Reddit",
          "~500 posts/run via public API",
          "Apify Reddit Scraper",
          "~$5/run",
          "5–10x volume, no rate limits, historical data available",
        ],
        [
          "YouTube",
          "10K quota units/day",
          "YouTube API quota increase (apply to Google at no charge)",
          "Free to request",
          "Up to 1M units/day — covers 500+ videos",
        ],
        [
          "NewsData.io",
          "200 articles/day",
          "Basic plan",
          "$149/month",
          "10,000 articles/day — full media coverage",
        ],
        [
          "Serper (Google)",
          "2,500 lifetime queries",
          "Pay-as-you-go",
          "~$50/month for 50K queries",
          "Full keyword expansion without exhausting quota",
        ],
        [
          "Amazon/Flipkart Reviews",
          "None (not in free tier)",
          "Apify Amazon/Flipkart actors",
          "~$2–5/run",
          "Verified purchase opinions — highest signal quality of any source",
        ],
        [
          "Quora",
          "None",
          "Apify Quora scraper",
          "~$2–3/run",
          "Long-form Indian Q&A — high relevance for FMCG and beverage brands",
        ],
        [
          "Facebook Pages",
          "None (CrowdTangle shut down August 2024; Graph API has no keyword search and requires app review)",
          "Option A: Apify Facebook Pages Scraper — targets brand Pages by URL",
          "~$15–30/run on $99–199/month plan",
          "Public Page posts and comments. No keyword search across Facebook. Comment authors masked per Meta policy.",
        ],
        [
          "Facebook Pages",
          "None",
          "Option B: Bright Data — enterprise-grade, more stable than Apify",
          "~$50–100/run; $499/month base",
          "Same coverage as Apify but more resilient to Meta front-end changes",
        ],
        [
          "Facebook Pages",
          "None",
          "Option C: Data365 — Facebook/Instagram data feed",
          "300–850 euros/month",
          "500K credits/month (~100K posts with comments); powers several enterprise social listening tools",
        ],
        [
          "Instagram",
          "None (Basic Display API shut down December 2024; hashtag API limited to 30 hashtags/week)",
          "Apify Instagram Comment Scraper (bundled with Facebook plan)",
          "Included in Facebook plan above",
          "Public brand account posts and comments. Non-owned account comments not available per Meta policy.",
        ],
        [
          "Twitter/X",
          "None (API paywalled)",
          "X API Pro",
          "$5,000/month",
          "X conversations — poor ROI for Indian FMCG; X India skews urban and political, not a beverage audience",
        ],
      ],
      [1300, 1700, 1900, 1300, 3160]
    ),
    spacer(),

    h3("New Sources That Plug Into the Same Framework"),
    para(
      "The following sources can be added without touching any existing pipeline stage:"
    ),
    bullet(
      "Amazon and Flipkart reviews: Verified buyers discussing your exact product — the highest-quality consumer signal available. Add collectors/amazon.py or collectors/flipkart.py. Output goes into Stage 2 normalization unchanged."
    ),
    bullet(
      "Quora answers: Long-form Indian Q&A with detailed reasoning about brand choices. High relevance for FMCG and beverage brands. Add collectors/quora.py."
    ),
    bullet(
      "Consumer complaint forums: FSSAI, National Consumer Helpline, Jagran Josh. Official complaint signal — captures safety and quality issues that social media underreports. Add collectors/complaints.py."
    ),
    bullet(
      "Zomato and Swiggy reviews: For food and beverage brands, restaurant pairing mentions and product context. Add collectors/delivery.py."
    ),
    spacer(),

    h3("Budget Guidance by Report Tier"),
    para("Free-data tier (~$1–3/run, ~Rs. 85–250):"),
    bullet(
      "Data sources: Reddit public API, YouTube (free quota), NewsData.io (200 articles/day), OpenAlex, Google Trends. No Meta data. All data collection is free."
    ),
    bullet("Anthropic API: ~$1–3/run — the only cost."),
    bullet("Corpus: 500–1,000 items."),
    bullet("Suitable for: initial brand scan, directional findings."),
    spacer(),
    para("Standard tier (~$10–20/run, ~Rs. 850–1,650):"),
    bullet(
      "Data sources: All free-tier sources plus Apify Reddit (~$5/run), Apify Amazon/Flipkart (~$5/run), Serper paid (~$1/run amortised at $50/month). No Meta data at this tier."
    ),
    bullet("Anthropic API: ~$3–8/run (larger corpus)."),
    bullet("Corpus: 2,000–5,000 items."),
    bullet("Suitable for: quarterly brand tracking, client deliverables."),
    spacer(),
    para("Premium tier (~$55–100/run, ~Rs. 4,600–8,300):"),
    bullet(
      "Data sources: All standard sources plus NewsData.io Basic ($149/month), Quora Apify (~$3/run), Facebook Pages and Instagram via Apify (~$15–30/run) or Bright Data (~$50–100/run) or Data365 (~10–30 euros/run)."
    ),
    bullet("Anthropic API: ~$8–15/run (8,000–15,000 items)."),
    bullet("Corpus: 8,000–15,000 items."),
    bullet(
      "Suitable for: high-stakes decisions including campaign briefs, product launches, and investor materials."
    ),
    bullet(
      "Note: Meta scraping can be the single largest line item at this tier."
    ),
    spacer(),

    h3("How to Configure"),
    para(
      "All paid API keys go in the .env file alongside the existing keys. Collection limits are set in config.py — increase max_posts, max_videos, and max_articles as needed. No changes are required to normalization, filtering, analysis, scoring, or reporting. Apify collectors require an APIFY_API_KEY — one line added to .env."
    ),
    spacer(),
  ];
}

// ────────────────────────────────────────────────────────────────────────────────
// SECTION 12
// ────────────────────────────────────────────────────────────────────────────────

function section12() {
  return [
    h1("Extending to Meta, Twitter/X and Social Listening Platforms"),

    h3("The Meta Reality"),
    para(
      "Meta has systematically restricted API access since 2018, and the situation worsened significantly in 2024:"
    ),
    bullet(
      "CrowdTangle, the tool most social researchers relied on for Facebook data, was shut down on August 14, 2024. Its replacement (Meta Content Library) is available to academic institutions and nonprofits only. For-profit firms cannot access it."
    ),
    bullet(
      "Facebook Graph API: Can retrieve public Page posts and aggregate engagement for pages you do not own, but only with Meta App Review approval (a process that takes weeks to months and can be rejected). Keyword search across Facebook was deprecated years ago. Groups are not accessible. Comment authors are masked as \"Facebook user\" by Meta policy."
    ),
    bullet(
      "Instagram Graph API: The Basic Display API was shut down on December 4, 2024. The current API provides hashtag data for up to 30 unique hashtags per week per connected Business Account — too limited for research. Comments on non-owned accounts are not available."
    ),
    bullet(
      "Legal note: In January 2024, a US federal court ruled in Meta v. Bright Data that scraping publicly visible Facebook and Instagram data does not violate the Computer Fraud and Abuse Act (CFAA). Meta's Terms of Service still prohibit scraping, but the CFAA cannot be used as a federal legal tool to stop it. This is why scraping services like Apify and Bright Data operate openly."
    ),
    spacer(),

    h3("What Social Listening Platforms Actually Cover"),
    para(
      "Enterprise social listening platforms do not have special API access to Facebook or Instagram that is unavailable to others. This is confirmed by their own documentation:"
    ),
    spacer(),
    makeTable(
      [
        "Platform",
        "Annual Cost",
        "Facebook Coverage",
        "Instagram Coverage",
        "What Their Own Docs Say",
      ],
      [
        [
          "Sprinklr",
          "$15,000–$387,000+/year",
          "150K indexed Pages; no keyword search across Facebook",
          "Limited",
          "\"Facebook deprecated the broad keyword-based search API. Any listening topic based on keyword search will not fetch from Facebook.\" Comment authors masked.",
        ],
        [
          "Brandwatch",
          "$20,000–$150,000+/year",
          "Public Page posts (limited)",
          "720K indexed accounts (posts only, no comments on non-owned accounts)",
          "Cannot retrieve comments on Instagram accounts you do not own",
        ],
        [
          "Meltwater",
          "$6,000–$100,000+/year",
          "Only your own connected accounts; no competitor data without their credentials",
          "Only your own connected accounts",
          "Requires connecting brand-owned Meta accounts",
        ],
        [
          "Talkwalker (now Hootsuite)",
          "$18,000–$100,000+/year",
          "Limited",
          "Limited",
          "Self-describes Meta listening as \"very limited\" in their own product documentation",
        ],
        [
          "Mention.com",
          "$599/month enterprise API",
          "Subject to same Meta limits",
          "Subject to same Meta limits",
          "No special access beyond standard Graph API",
        ],
      ],
      [1400, 1700, 1900, 1900, 2460]
    ),
    spacer(),
    para(
      "Conclusion: subscribing to a social listening platform does not give you keyword search across Facebook, access to Groups, or comment author data. You get the same coverage gaps, plus a UI dashboard and sentiment analysis — functions this pipeline already performs."
    ),
    spacer(),

    h3("Practical Options for Facebook and Instagram Data"),
    para("Option A — Apify scrapers (~$29–$199/month):"),
    bullet(
      "Facebook Pages Scraper and Instagram Comment Scraper target brand pages by URL, not by keyword. Legally protected under the CFAA ruling above. Can break periodically when Meta changes its front-end. Best for exploration and periodic research runs."
    ),
    spacer(),
    para(
      "Option B — Bright Data (~$499/month base, $1.50 per 1,000 records pay-as-you-go):"
    ),
    bullet(
      "More stable enterprise-grade infrastructure. Less likely to break when Meta updates its site. Better suited for production runs and client-facing work."
    ),
    spacer(),
    para("Option C — Data365 (300–850 euros/month):"),
    bullet(
      "Positions itself explicitly as a Facebook and Instagram data feed. 500K credits per month equals approximately 100,000 posts with comments. Powers several enterprise social listening tools in the background."
    ),
    spacer(),
    para(
      "All three options are limited to publicly visible content on brand Pages. None provide keyword search across all of Facebook."
    ),
    spacer(),

    h3("Twitter/X: Cost and Coverage"),
    para(
      "Twitter/X data is not included in the default pipeline because the X API is paywalled and the ROI for Indian FMCG brands is poor:"
    ),
    bullet(
      "Basic API: $100/month for 10,000 tweets/month — too low for meaningful research."
    ),
    bullet(
      "Pro API: $5,000/month — provides meaningful volume, but X India skews urban, English-speaking, and politically vocal. For a beverage brand like Thums Up, the consumer conversation happens more on YouTube comments and Reddit than on X."
    ),
    bullet(
      "The exception: if a brand is running an active X campaign, trending on X, or the research question specifically concerns X conversations, the Pro API becomes worth the cost for that run."
    ),
    spacer(),

    h3("When Social Listening Platforms Make Sense"),
    para("A social listening subscription is worth considering when:"),
    bullet(
      "A client requires a branded platform for reporting and dashboards (not the research data itself)"
    ),
    bullet(
      "The team needs real-time alerts and monitoring rather than periodic research runs"
    ),
    bullet(
      "The research covers Twitter/X conversations extensively (some platforms include X access in their subscription)"
    ),
    bullet(
      "Legal or procurement requirements mandate an enterprise vendor with a signed data agreement"
    ),
    spacer(),
    para(
      "For one-off or periodic research runs on Indian FMCG brands, the pipeline described in this document produces equivalent or better analysis at a fraction of the cost."
    ),
    spacer(),
  ];
}

// ────────────────────────────────────────────────────────────────────────────────
// SECTION 13
// ────────────────────────────────────────────────────────────────────────────────

function section13() {
  return [
    h1(
      "Geographic, Demographic and Temporal Data: What We Have and What We Don't"
    ),

    h3("Geographic Data by Source"),
    spacer(),
    makeTable(
      ["Source", "What's Available", "Accuracy"],
      [
        [
          "Reddit",
          "Almost none. Subreddit names (r/india, r/delhi) loosely infer geography. No user location in the public API.",
          "Low — inferred only, not reliable",
        ],
        [
          "YouTube",
          "No user location on comments. Video upload country is available on the video object, not on individual comments.",
          "Very low for comments; moderate for video origin",
        ],
        [
          "NewsData.io",
          "Article country field — the country where the news outlet is based, not where readers are.",
          "Moderate for source origin; not useful for audience geography",
        ],
        [
          "Academic (OpenAlex)",
          "Institution country available in author affiliation metadata.",
          "High — directly stated by the author",
        ],
        [
          "Google Trends",
          "Geography is the primary feature. Returns search interest by country, state, and city over time.",
          "High — first-party Google data, not inferred",
        ],
        [
          "Facebook/Instagram (via scraper)",
          "Page location (city/country) available on brand Pages. User location on comments: not available.",
          "High for brand Pages; none for commenters",
        ],
        [
          "Serper (Google Search)",
          "Can be scoped to a specific country using the gl= parameter. Results come from that country's search index.",
          "Moderate — country-level only",
        ],
      ],
      [2000, 5000, 2360]
    ),
    spacer(),
    para(
      "Practical implication: Google Trends is the only source that provides reliable sub-national geographic data (state and city level within India). Reddit and YouTube comments should be treated as India-biased but geographically unverifiable."
    ),
    spacer(),

    h3("Age Data"),
    para(
      "No platform in this pipeline provides verified user age. What can be inferred — with very low accuracy:"
    ),
    bullet(
      "Content language and cultural references: Bollywood era, product nostalgia, or technology references can loosely suggest a generation."
    ),
    bullet(
      "Subreddit type: r/IndiaAfterHours or r/teenagers loosely implies an age range, but membership is self-selected and unverified."
    ),
    bullet(
      "YouTube channel type: gaming channels, study vlogs, and personal finance content attract different age demographics on average."
    ),
    spacer(),
    para(
      "Accuracy: very low. Age inference from content is speculative and must not be presented as fact in a report."
    ),
    spacer(),

    h3("Gender Data"),
    para(
      "No platform provides verified gender. Inference methods are unreliable and ethically contested:"
    ),
    bullet(
      "Username analysis: limited accuracy, culturally biased, and not appropriate for reporting."
    ),
    bullet(
      "Content topics and language patterns: a very rough proxy at best."
    ),
    bullet(
      "External demographic surveys: for example, r/india is estimated to skew approximately 75% male according to external audience research. These are population-level estimates, not per-user data."
    ),
    spacer(),
    para(
      "Gender is not reported in this pipeline. Findings should not be attributed to gender segments without primary research (surveys, focus groups)."
    ),
    spacer(),

    h3("Temporal Data by Source"),
    spacer(),
    makeTable(
      ["Source", "Timestamp Available", "Accuracy"],
      [
        [
          "Reddit",
          "created_utc on posts and comments — Unix timestamp accurate to the second",
          "High",
        ],
        [
          "YouTube",
          "published_at on videos; published_at on comments",
          "High",
        ],
        [
          "NewsData.io",
          "pubDate field in article metadata",
          "High — usually accurate to the day",
        ],
        [
          "Academic (OpenAlex)",
          "Publication year, sometimes month, from metadata",
          "High for year; month-level varies by publisher",
        ],
        [
          "Google Trends",
          "Weekly or daily search interest over time, up to 5 years back",
          "High — first-party Google data",
        ],
      ],
      [2000, 4500, 2860]
    ),
    spacer(),

    h3("How the Pipeline Uses Temporal Data"),
    bullet(
      "Temporal Consistency factor in the Confidence Score: checks whether an insight appears consistently across multiple weeks and months, or is a spike confined to one period. Consistent signals score higher."
    ),
    bullet(
      "Data Recency factor: items from the last 30 days score 1.0; older items score progressively lower (0.7 for 30–90 days, 0.5 for 90–180 days, 0.3 for older)."
    ),
    bullet(
      "Google Trends provides the most reliable temporal signal because it reflects actual search volume over time, not just the presence of content."
    ),
    spacer(),

    h3("What This Means for the Report"),
    para(
      "Findings in this report reflect what online communities are saying, and when. They do not reliably reflect who is saying it in terms of age, gender, income, or precise geography. Reports should not attribute findings to specific demographic segments without a separate primary research study. What this pipeline does well is identify the topics, themes, and sentiments worth investigating further — the \"what\" and \"when\" rather than the \"who.\""
    ),
    spacer(),
  ];
}

// ────────────────────────────────────────────────────────────────────────────────
// SECTION 14
// ────────────────────────────────────────────────────────────────────────────────

function section14() {
  return [
    h1("Cost and Time: What Each Run Actually Takes"),

    h3("A. The Actual Thums Up Run (Lowest Cost Method)"),
    para(
      "This run used exclusively free-tier data sources. The only monetary cost was the Anthropic API for all LLM-powered stages."
    ),
    spacer(),
    para("Data collection costs: $0 — Reddit public API, YouTube API (free quota), NewsData.io (200 credits/day), OpenAlex, and Google Trends are all free."),
    spacer(),
    para("Anthropic API costs for 966 items:"),
    bullet(
      "Filtering (966 items at approximately 300 tokens each, using Claude Haiku pricing ~$0.0008 per 1,000 input tokens): ~$0.23"
    ),
    bullet(
      "Theme extraction, sentiment classification, and synthesis (approximately 200,000 total tokens, using Claude Sonnet pricing ~$0.003 per 1,000 input tokens): ~$0.60"
    ),
    bullet("Scoring and insight refinement: ~$0.30"),
    bullet(
      "Total: approximately $1–3 per report run (the Anthropic API is the only cost on the free-data tier)"
    ),
    spacer(),
    para("Time breakdown:"),
    bullet(
      "Stage 1 (collection): 45–90 minutes. Reddit rate-limiting is the bottleneck at 1 request per 2 seconds across 60+ keyword and subreddit combinations."
    ),
    bullet(
      "Stage 3 (filtering): 20–40 minutes for approximately 1,000 items, using batched LLM calls with rate limiting."
    ),
    bullet(
      "Stage 4 (analysis): 30–60 minutes for two-pass theme extraction across the full corpus."
    ),
    bullet("Stages 5–6 (synthesis and scoring): 15–30 minutes."),
    bullet("Stage 7 (report generation): 2–5 minutes for PPTX and PDF."),
    bullet(
      "Total: approximately 2–4 hours end to end, mostly waiting on API rate limits."
    ),
    spacer(),

    h3("B. Maximum Quality Run (All Paid Scrapers and APIs)"),
    spacer(),
    makeTable(
      ["Component", "Cost per run", "Monthly subscription", "Notes"],
      [
        [
          "Apify Reddit",
          "~$5",
          "$49/month Starter",
          "5–10x volume vs. public API; no rate limits; historical data",
        ],
        [
          "Apify Amazon + Flipkart",
          "~$5",
          "Included in Apify plan",
          "Verified buyer reviews — highest signal quality of any source",
        ],
        [
          "Apify Facebook Pages + Instagram",
          "~$15–30",
          "$99–199/month",
          "Public brand Pages only; no keyword search across Facebook",
        ],
        [
          "OR: Bright Data (alternative for Meta)",
          "~$50–100",
          "$499/month",
          "More stable for production; $1.50 per 1,000 records",
        ],
        [
          "OR: Data365 (alternative for Meta)",
          "~10–30 euros",
          "300–850 euros/month",
          "500K credits/month; powers several enterprise listening tools",
        ],
        [
          "NewsData.io Basic",
          "~$5",
          "$149/month",
          "10,000 articles/day vs. 200 on free tier",
        ],
        [
          "Serper paid",
          "~$1",
          "$50/month",
          "50,000 queries/month",
        ],
        [
          "Anthropic API (8,000–15,000 items)",
          "~$8–15",
          "—",
          "Scales with corpus size; larger corpus = more LLM tokens",
        ],
        [
          "Total per run (with Apify for Meta)",
          "~$40–60",
          "~$350–500/month",
          "Approximately 10 runs/month at full volume",
        ],
        [
          "Total per run (with Bright Data for Meta)",
          "~$75–125",
          "~$750–1,100/month",
          "Higher stability; recommended for client-facing production runs",
        ],
      ],
      [2800, 1600, 2100, 2860]
    ),
    spacer(),
    para("Time at maximum quality:"),
    bullet(
      "Stage 1 (collection): 20–40 minutes. Paid APIs remove rate limits; Apify runs actors in parallel cloud infrastructure."
    ),
    bullet(
      "Stage 3 (filtering): 60–90 minutes for approximately 8,000 items."
    ),
    bullet(
      "Stage 4 (analysis): 60–120 minutes for two-pass theme mapping across a larger corpus."
    ),
    bullet("Stages 5–6 (synthesis and scoring): 20–30 minutes."),
    bullet(
      "Total: approximately 2–4 hours. The time savings from paid APIs appear in Stage 1 (collection). The analysis stages take longer because the corpus is larger."
    ),
    spacer(),

    h3("What the Budget Does and Does Not Buy"),
    para(
      "More budget buys: higher data volume, more source diversity, verified purchase data from Amazon and Flipkart, and brand Page data from Facebook and Instagram."
    ),
    spacer(),
    para(
      "More budget does not buy: keyword search across Facebook (unavailable at any price since CrowdTangle closed), comment author demographics, access to private Groups, or faster LLM processing per item."
    ),
    spacer(),
    para(
      "The primary return on a larger budget is an improvement in Confidence and Signal Strength scores — which means more insights reach \"Key Finding\" status and fewer remain in \"Watch Closely\" or \"Noise.\""
    ),
    spacer(),
  ];
}

// ────────────────────────────────────────────────────────────────────────────────
// Build and save
// ────────────────────────────────────────────────────────────────────────────────

const allChildren = [
  ...section11(),
  ...section12(),
  ...section13(),
  ...section14(),
];

const doc = new Document({
  sections: [
    {
      children: allChildren,
    },
  ],
});

const outPath = path.join(__dirname, "docs", "new_sections.docx");

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync(outPath, buffer);
  console.log(`Written: ${outPath}`);
});
