# Consumer Research Report Generator

Enterprise-grade brand perception analysis. Brief -> collect -> filter -> analyze -> score -> report (DOCX + Excel).

**This is a discovery engine.** Themes are extracted inductively from the corpus using a two-pass process. The brief defines what to collect, not what to find. Unlike survey-based research where hypotheses are tested, or social listening dashboards where keywords are tracked, this pipeline discovers what consumers are actually talking about. If consumers are discussing something the brand never considered - a cultural reference, a misinformation narrative, a quality perception the brand doesn't track - it will surface.

## Core Rules
- **Max volume always.** Every run uses maximum scraper limits. One quality report per day, not many weak ones.
- **No collector crashes the pipeline.** All collector calls wrapped in `_safe_collect()`. Fail gracefully, log, continue.
- **User brief first.** Never run without a user-approved brief. The brief drives keyword expansion.
- **Data-driven scoring only.** Confidence × Signal Strength, both from data. Insights ranked by confidence (primary) and signal (tiebreaker). No quadrant labels, no LLM opinion on actionability.
- **No AI slop.** Lato font throughout (headings and body), white bg, deep grey (#374151) text, navy (#1E3A5F) accent.

## Pipeline (8 stages, each writes artifacts to `runs/{run_id}/`)
```
[0] BRIEF → brief.json        [1] COLLECT → raw/*.json      [2] NORMALIZE → normalized/corpus.json
[3] FILTER → filtered/        [4] ANALYZE → analysis/        [5] SYNTHESIZE → insights/
[6] SCORE → scored/           [7] REPORT → report/report_v###.docx + report_v###.xlsx
```

## Tooling & Data Sources
| Source | Collector File | API Key Env Var | Free Tier |
|--------|---------------|-----------------|-----------|
| Reddit | `collectors/reddit_mcp.py` | None (public JSON API) | Unlimited (rate limited 1 req/2s) |
| YouTube | `collectors/youtube.py` | `YOUTUBE_API_KEY` | 10K quota units/day |
| Twitter / X | External collection | None (external data) | Via external ingestion |
| Instagram | External collection | None (external data) | Via external ingestion |
| NewsData.io | `collectors/news.py` | `NEWSDATA_API_KEY` | 200 credits/day |
| Serper (Google) | `collectors/web_search.py` | `SERPER_API_KEY` | 2,500 queries |
| OpenAlex | `collectors/academic.py` | None | 100K+ calls/day |
| Google Trends | `collectors/trends.py` | None (PyTrends) | Free, rate limited |
| Crawl4AI | `collectors/web_scraper.py` | None | Unlimited (open source) |
| **Analysis LLM** | `utils/llm_client.py` | `ANTHROPIC_API_KEY` | $5 purchased |

## Key Files
```
consumer_research/
  config.py                    — All defaults (collection limits, scoring weights)
  run.py                       — CLI entry point
  models/schemas.py            — All Pydantic models (NormalizedItem, ScoredInsight, etc.)
  utils/llm_client.py          — Unified LLM client (Claude or Gemini)
  utils/keywords.py            — Auto-expands brief -> 50+ keywords
  utils/hashing.py             — Deterministic SHA-256 item IDs
  utils/rate_limiter.py        — Token-bucket rate limiter
  pipeline/brief.py            — Stage 0: structured research brief
  pipeline/normalize.py        — Stage 2: thread-level dedup + engagement filter
  pipeline/filter.py           — Stage 3: LLM relevance classification (multilingual)
  pipeline/analyze.py          — Stage 4: sentiment + Plutchik emotion + ABSA + themes + NSS + triangulation
  pipeline/synthesize.py       — Stage 5: one insight per theme, mandatory coverage
  pipeline/scoring.py          — Stage 6: confidence (5 factors) + signal strength (4 factors) + Brand Health Score (0-100)
  pipeline/orchestrator.py     — Wires all stages, _safe_collect() wrapper
  pipeline/ingest.py           — Generic data ingestion: auto-detects JSON format, handles scrapers + external data
  pipeline/validate.py         — Validation gates: theme coverage check, methodology selector
  report/docx_generator.py     — python-docx DOCX report (flowing, Google Doc-compatible, serial-numbered)
  report/pptx_generator.py     — python-pptx slide deck (legacy, no longer primary output)
  report/pdf_generator.py      — WeasyPrint + Jinja2 HTML -> PDF (legacy)
  report/charts.py             — Matplotlib chart generation (Tufte-inspired, 11 chart types)
  report/templates/styles.css  — Consulting design spec
  report/templates/report.html — Jinja2 report template
# scripts/ — all runnable scripts
scripts/stage6_7_score_report.py — Stages 6+7: data-driven scoring + chart/DOCX generation (no API). Loads config from run's config.json. Usage: `python scripts/stage6_7_score_report.py [run_id]` (defaults to latest run)
scripts/regenerate_report.py   — Regenerate DOCX from existing scored data (no API). Usage: `python scripts/regenerate_report.py [run_id]` (defaults to latest run)
scripts/fix_quotes.py          — Fix representative quotes: quality scoring, cross-theme dedup, consumer voice priority (per-study)
scripts/add_narrative_themes.py — Add narrative themes missed by keyword pass (per-study). See Procedure 15
scripts/resume_stage3.py       — Resume from Stage 3. Usage: `python scripts/resume_stage3.py <run_id>`
scripts/resume_stage4.py       — Resume from Stage 4. Usage: `python scripts/resume_stage4.py <run_id>`
scripts/rescore.py             — Re-score insights (data-driven, no API)
scripts/resynthesize.py        — Re-synthesize insights via API
scripts/export_to_excel.py     — Export run data to Excel (flat, by platform)
scripts/export_insights_excel.py — Export insight-organised Excel: one tab per theme + unthemed items. Usage: `python scripts/export_insights_excel.py [run_id]`
# examples/ — showcase artifacts and per-study scripts
examples/studies/weight_loss/  — run_weight_loss.py, stage4_analysis.py, stage5_synthesis.py
examples/outcomes/             — DOCX reports, manifests, READMEs for all completed studies
examples/briefs/               — Research brief JSONs for all completed studies
# data/ — raw input data files (gitignored)
data/                          — make_in_india.json, weight_loss.json, working samples
```

## Collection Defaults (MINIMUMS — do not reduce)
Reddit: 500 posts, 20 comments/post | YouTube: 50 videos, 100 comments/video | News: 200 articles | Academic: 50 papers | Serper: 100 results | Trends: full 12-month history (separate quantitative layer)

## Engagement Philosophy (Critical — Do Not Revert)
**Engagement is a visibility signal, not a truth, quality, or representativeness signal.** Likes, upvotes, and shares are driven by platform algorithms, timing, language, and audience demographics - none of which correlate cleanly with how representative an opinion is of real consumers.

**No engagement thresholds.** Every item that passes quality controls (non-empty text, minimum length, deduplication) enters the corpus. A zero-likes YouTube comment counts the same as a 50-upvote Reddit post in sentiment, prevalence, and NSS.

**Engagement as scoring metadata, not admission gate.** Engagement metrics are preserved on every item (`platform_metadata.score`, `like_count`) and used in Stage 6 scoring to compute Signal Strength - how visible and resonant the conversation is. But they never determine what enters the corpus.

**Thread cap is random, not engagement-sorted.** The 5-comments-per-thread cap in `normalize.py` selects randomly (seed 42) rather than keeping the highest-engagement comments. This prevents viral voices from dominating within threads.

**What this means for reports:** The corpus reflects what everyone thinks. The scoring reflects how visible and validated those opinions are. A theme could have moderate NSS (because quiet voices pull it down) but strong signal (because the engaged voices are very engaged). This tells the client "this theme has broad but lukewarm support, with a vocal minority driving the conversation."

**Why this matters:** In the hair colour study, 59.9% of the corpus fell below engagement thresholds. That is the majority of consumers, not a noise fringe. Filtering them out was hiding meaningful signal - the silent majority's sentiment diverged by 11% overall and by 20-33% on specific themes.

## Data Quality Architecture (3-layer defence)
**Layer 1 — Brand-anchored keywords** (`keywords.py`): Every search query MUST include the brand name. Category-only queries ("best [category]", "[category] review") return generic noise. `_generate_category_terms()` now prepends brand name to all terms. Never revert this.

**Layer 2 — Collector-level brand validation**: YouTube and Reddit collectors check that video titles/post titles mention the brand before fetching comments. If a video titled "DIY Probiotic Soda" is returned by a broad query, the collector skips it instead of collecting 100 irrelevant comments. The check is bypassed when the query itself contains the brand name (trusting the platform's relevance ranking).

**Layer 3 — Post-collection quality audit** (`orchestrator.py`): After all collectors finish, samples 50 items per source and checks what percentage mention the brand. Logs a warning if <50% mention the brand. This catches quality issues before they propagate to normalization.

**Why this matters**: In a prior run, category-only queries (e.g., "best [category]", "[category] review") returned 57% noise from YouTube - generic content unrelated to the brand under study. Root cause: brandless search terms plus brand name matching common words/gestures. All three layers prevent this from recurring.

## Known Analytical Limitations (document honestly, never hide)
These are structural limitations of social listening methodology. They cannot be fully eliminated - only mitigated and disclosed. Every report should acknowledge the ones relevant to that study.

**Bias chain** (6 layers, each compounds the previous): Brief scope, Keyword framing, Platform algorithms, Relevance filter, Engagement filter, Language.

| # | Limitation | Severity | Fixable? | How to Fix | Status |
|---|-----------|----------|----------|-----------|--------|
| 1 | **Query framing bias** - Keywords presuppose contexts. You find what you search for. Keyword expansion follows the brief's framing, no adversarial or blank-slate queries. | CRITICAL | Partially | (a) Mandatory blank-slate queries (brand name only, no context), (b) query attribution reporting showing which queries drove which themes, (c) adversarial query generation for contexts the brief did NOT mention. | Not implemented |
| 2 | **Platform demographic bias** - Reddit skews male/urban/18-34, Twitter politically engaged, YouTube extreme reactions, Instagram female/influencer-driven. No weighting applied. | MEDIUM | Partially | Per-platform demographic weighting using known platform demographics as priors. Requires external demographic benchmarks. | Not implemented |
| 3 | **Unknown universe / no sampling frame** - No denominator. Prevalence is within-corpus only, never projectable to the general population. | HIGH | No | Structural limitation of social listening. Can only be addressed by pairing with a structured survey. | Inherent limitation |
| 4 | **Engagement filter excludes silent majority** - Engagement thresholds systematically excluded moderate consumers and over-indexed on extreme sentiment. | MEDIUM | Partially | Hard engagement thresholds removed. Thread cap uses random selection. However, built-in collectors still fetch visibility-ranked content (Reddit sort="top", YouTube order="relevance"), so platform algorithms still influence which items are collected. Fully resolving this would require randomized collection strategies. | **MITIGATED** |
| 5 | **No bot/astroturf detection** - Zero detection of coordinated campaigns, paid reviews, brand-planted content, or bot networks. | MEDIUM | Yes | (a) Account age/karma checks on Reddit, (b) posting pattern analysis for coordinated timing, (c) text similarity clustering for copy-paste campaigns. | Not implemented |
| 6 | **Sarcasm/irony misclassification** - Keyword mode reads sarcasm as literal. Narrative review helps for unthemed items but doesn't audit already-themed items. | MEDIUM | Partially | (a) LLM-based sarcasm detection pass on themed items, (b) flag items with sentiment-text mismatch for manual review. | Not implemented |
| 7 | **Influencer vs authentic voice conflated** - A 1M-subscriber sponsored review and a genuine Reddit complaint weighted identically. No sponsored content detection. | MEDIUM | Yes | (a) Follower/subscriber count weighting, (b) sponsored content keyword detection ("ad", "collab", "#sponsored"), (c) separate influencer vs organic voice layers. | Not implemented |
| 8 | **Near-duplicate inflation** - SHA-256 dedup catches exact copies but not paraphrases. Viral takes with slight modifications inflate theme prevalence. | LOW | Yes | Semantic similarity clustering (embedding-based) to group near-duplicates and count them as one signal. | Not implemented |
| 9 | **Language classification accuracy unvalidated** - The LLM processes any language present in the corpus (English, Hindi, Hinglish, Tamil, Telugu, Korean, Arabic, etc.) and does not filter by language. However, sentiment and theme classification accuracy has only been validated on English and Hindi/Hinglish. Accuracy on other languages is assumed but unverified. | LOW | Yes | Run validation samples on non-English/Hindi items to measure classification accuracy per language. | Not implemented |
| 10 | **No temporal weighting in theme extraction** - A 6-month-old viral thread counts the same as last week's organic discussion in theme prevalence. | LOW | Yes | Apply exponential decay weighting during theme extraction (not just at insight scoring). | Not implemented |
| 11 | **Cross-theme interactions not surfaced** - Items are multi-coded but insights are one-per-theme. Theme pairs with >20% overlap split across separate insights, never analysed as distinct findings. | MEDIUM | Yes | (a) Compute theme co-occurrence matrix after Stage 4, (b) identify pairs with >20% shared items, (c) generate cross-theme insights (cap 3-5), (d) report co-occurrence matrix visual. Report prevalence as "exclusive" and "inclusive". | Not implemented |
| 12 | **No reliable demographic data** - No platform provides verified age, gender, or location. Any demographic inference is speculative and must not be presented as fact. | CRITICAL | No | Structural limitation of social listening. For demographic segmentation, commission a structured survey using this report's insights as stimulus. | Inherent limitation |
| 14 | **Geographic relevance not verified** - Corpus is collected using market-specific queries (brand names, "India", regional terms) but no platform provides verified geolocation. Audit of two studies found 2-3% of items are likely from non-target markets (US product listings with USD prices, UK/EU healthcare references, "FDA approved" discussions). These items are topically relevant but geographically wrong. Reports describe "conversations about [brand] in the Indian market context" not "conversations from Indian consumers." | LOW | Partially | (a) Add geographic relevance check to Stage 3 filter prompt, (b) flag items with non-target-market currency/retailer/regulatory references, (c) disclose in methodology that geographic origin is inferred from context, not verified. | Not implemented |
| 13 | **LLM non-determinism in theme extraction** - Same corpus can produce slightly different theme assignments across runs. Code-level sources (stochastic keyword expansion at temperature 0.3, order-dependent sampling, unpinned model aliases) have been fixed. Remaining variance comes from model inference itself (floating-point batching, GPU parallelism), which cannot be eliminated in code. | MEDIUM | Partially | (a) Keyword expansion pinned to temperature 0.0, (b) theme discovery sample sorted by item_id before sampling, (c) theme mapping batches sorted by item_id, (d) Gemini model pinned to dated version. Remaining model-level variance is inherent to LLM inference. | **MITIGATED** |

## Zero-API Architecture
**No external API calls.** All analysis is performed by the Claude Code session itself - the model running this conversation IS the analysis engine. The Anthropic API is never called for sentiment, themes, or synthesis. This means:
- $0 per run (included in Claude Code / Claude Max subscription)
- No API key required for analysis (only for automated pipeline runs without Claude Code)
- The session model reads the data, classifies it, and writes the results directly

## Analysis Methodology
The automated pipeline always uses LLM-backed analysis via `analyze_corpus()` — there is no automatic switching between code paths based on corpus size. The two approaches below are workflow-level distinctions, not code branches:

**Automated pipeline** (this codebase): `analyze_corpus()` calls the LLM API for sentiment classification, theme extraction, and synthesis regardless of corpus size. Theme extraction uses a two-pass approach (stratified discovery sample + full-corpus batch mapping). ~$1-2 per run via Anthropic API.

**Manual in-context workflow** (Claude Code session): A human runs analysis directly inside a Claude Code session. The session model reads items, classifies them, and writes results to disk — no API calls, $0 cost. The mandatory narrative review pass (Procedure 15) is part of this workflow.

**Validation gate** (`pipeline/validate.py`): `validate_theme_coverage()` checks that >=90% of items are assigned to at least one theme. Called automatically in the orchestrator between Stage 4 and Stage 5. Also callable from any script via `from consumer_research.pipeline.validate import validate_theme_coverage`.

## Flexible Data Ingestion
The pipeline accepts data from any source via `pipeline/ingest.py`:

**Built-in collectors**: Reddit, YouTube, News, Academic, Trends, Web Search (API-based collection)

**External JSON** (pre-collected data): `ingest_external_data(path)` auto-detects format:
- **Platform-scraped format**: `{metadata_content, engagements, comments, source}` - handles Twitter, YouTube, Reddit, Instagram with nested comments
- **E-commerce review format**: `{asin, reviews[], product_details, source}` - handles Amazon/Flipkart product reviews with star ratings, review dates, and product metadata
- **Mixed format**: Files containing both platform-scraped and e-commerce records are auto-detected and each item routed to the correct sub-ingester
- **Simple format**: `[{text, source, url, date}]` - any flat list with a text field
- **Pre-normalized format**: Already-normalized NormalizedItem dicts (pass-through)

Field names are auto-detected (text/content/body/message, source/platform/channel, url/link/permalink, date/created_at/timestamp). No code changes needed for new data shapes - the ingester adapts.

## Insight Methodology
1. **Observation**: What the data shows (theme + evidence)
2. **Insight**: What it means for the consumer (the "why")
3. **Implication**: What it means for the business ("So What")
4. **Recommendation**: What the client should do ("Now What")
5. **Further Validation**: What additional research would strengthen this

**One insight per theme** — synthesis prompt mandates exactly one insight per theme, no consolidation, no omissions. `{theme_count}` enforced in prompt. Validation logging warns if LLM under-generates.

**Quality gates** (all must pass): Grounded (≥3 sources), Non-obvious, Actionable, Specific, Falsifiable

**In-context synthesis**: When Claude Code is running, synthesize insights directly in the session. The model running the session IS the analysis model. No external API calls needed - ever. All sentiment classification, theme extraction, and insight synthesis happens in-context at zero marginal cost.

## Scoring (fully data-driven)
**Confidence** (5 factors, weights in `config.py: ScoringConfig`): Sample size (0.25), Source diversity (0.25), Temporal consistency (0.15), Internal agreement (0.20), Data recency (0.15). All factors use continuous logarithmic/percentile scoring for differentiation across insights.

**Signal Strength** (4 factors, weights in `config.py: ScoringConfig`): Prevalence (0.35), Engagement level (0.30), Sentiment intensity (0.20), Conversation depth (0.15). Engagement uses percentile rank across insights to guarantee spread.

**Ranking**: Insights are sorted by confidence score (primary) then signal strength (tiebreaker). Both scores shown as percentages in the report. Thresholds: HIGH confidence >= 0.75, STRONG signal >= 0.75.

**Brand Health Score** (0-100, 5 components): Sentiment (0.30) + Engagement (0.25) + Advocacy (0.20) + Resilience (0.15) + Conversation (0.10). All data-driven. `scoring.py: compute_brand_health()`

## Enhanced Analysis (Phase 1 — Implemented)
- **Plutchik Emotion Classification**: 8 primary emotions (joy, trust, fear, surprise, sadness, disgust, anger, anticipation) classified alongside sentiment in the same LLM call. Zero additional API cost. `schemas.py: Emotion enum`, `analyze.py: SENTIMENT_PROMPT`
- **Aspect-Based Sentiment Analysis (ABSA)**: Sentiment scored PER aspect (e.g., taste: positive 0.85, price: negative 0.3). Aspects require n≥10 mentions to appear in report (below this, NSS is meaningless). `schemas.py: AspectSentiment`, `analyze.py` parser
- **Net Sentiment Score (NSS)**: (positive - negative) / total. Range -1.0 to +1.0. Computed overall, per-theme, per-aspect. Industry standard (Brandwatch, Sprinklr, YouGov). `schemas.py: compute_nss()`

## Report Design Principles (DOCX)
- **No truncation**: DOCX cells wrap naturally — never add `[:N]` character limits anywhere
- **No em dashes**: Never use `—` or `–` anywhere. All LLM text passes through `_clean()` (replaces with `-`). Blockquote source uses ` - ` not ` — `.
- **Typography**: Lato font throughout — headings and body. `HEADING_FONT = "Lato"`, `BODY_FONT = "Lato"`. Charts also use Lato via `rcParams["font.sans-serif"] = ["Lato", ...]`.
- **Table contrast**: Headers Navy bg + white text. Alternating rows for readability.
- **Charts**: Embedded as PNG inline at natural reading points. Tufte-inspired — no left spine, light gridlines. Lato font in all chart text.
- **Colours**: Navy (#1E3A5F), Green (#059669) positive, Red (#DC2626) negative, Amber (#D97706) neutral/watch
- **Verbatims**: Block-quoted, indented, italic, 10pt. Source platform shown after ` - `. Max 3 per insight.
- **Report sections** (8, current): Cover → Data Universe → Sentiment & Emotion → Insight Landscape → Insight Deep Dives → Brand Health Score → Methodology → Data Provenance
- **Cover page structure** (exact, do not change):
  1. Brand name — left-aligned, 36pt Lato Bold, Navy
  2. `Research Report: Consumer Sentiment & Brand Perception` — 14pt, slate grey
  3. `Analysis Date: Month YYYY` — 11pt, grey
  4. Divider rule
  5. `Research Objectives` (H2) — bullet list from `config.collection.business_objectives`
  6. Divider rule
  7. `Summary of Data and Findings` (H2) — 2-column table with 6 rows: Items Analysed | {n}, Content Date Range | {Mon YYYY - Mon YYYY} (min/max `source_timestamp` in corpus - this is when content was published, not when collection ran), Insights Identified | {n}, Net Sentiment Score | {+X.X%} (green/red), Brand Health Score | {X}/100 (green/amber/red), Data Sources | {n} platforms (computed from distinct `source_platform` values in `items`)
  8. Page break
- **Brand Health section**: Components table followed by a conditional Note paragraph — if `conversation_component < 50`, adds a callout explaining what the low score means (thin organic conversation, reactive not spontaneous). This surfaces the "transactional brand" finding explicitly rather than burying it in a table row.
- **Data Universe section**: Starts with a **Collection Funnel** table (3 rows: Raw collected → After dedup & engagement filter → After relevance classification) showing item counts and notes. Raw counts read from `run_dir/raw/*.json`, normalized from `run_dir/normalized/corpus.json`. Percentage of raw shown inline. Then Platform Breakdown table + platforms chart. Then **Temporal Distribution** chart (`chart_temporal.png`) showing item count by year — makes data recency and concentration immediately visible. Then Collection Methodology paragraph.
- **Insight Landscape table**: 6 columns — Insight, Items, Prevalence in Dataset, Signal Strength, Confidence Score, NSS. Signal and Confidence joined from `scored_insights` by `theme_id`.
- **Insight Deep Dive structure** (exact order, do not change): (1) H2 heading with number + theme name, (2) single data line [n= | Confidence | Signal | % of Dataset | NSS], (3) radar chart PNG, (4) What the Data Shows, (5) What it Means, (6) Business Implication & Rationale, (7) Recommendation, (8) Further Validation — no data stats here, (9) Representative Voices 2-3 quotes
- **Executive Summary**: Opens with total items, NSS, insight count + theme count. Names top 3 insights by confidence. "Top Insights at a Glance" table shows top 5 by confidence with Confidence% and Signal% columns. No quadrant labels anywhere.
- **Recommendations section**: Sorted by confidence (primary) then signal (tiebreaker). Headings are "Recommendation 01", "Recommendation 02", etc. — no quadrant bracket labels.
- **Radar charts**: Named `chart_radar_{insight_id}.png` — never positional. Title = theme label only (no INS_xxx). Looked up by `ins.insight_id` in deep dives. One radar per insight (count varies per run). Total chart count = 7 standard (sentiment, platforms, temporal, themes, matrix, emotions, aspect_heatmap) + N radar charts.
- **Regeneration**: `scripts/regenerate_report.py [run_id]` calls `generate_all_charts()` then `generate_docx_report()`. Defaults to latest run if no run_id given. Loads config from `config.json`. Always regenerate charts before DOCX to pick up any changes.
- **Excel export**: `scripts/export_insights_excel.py [run_id]` generates a theme-organised Excel workbook. One tab per theme (sorted by confidence) containing all corpus items for that theme, plus an "Unthemed Items" tab and a Summary tab. Each theme tab has metadata (theme label, item count, NSS, confidence, signal strength). Items can appear in multiple tabs (multi-coded). Lato font throughout. Run after Stage 7 to produce the client-ready data export alongside the DOCX report.

## Report Naming Convention
Reports use serial numbering: `report_v001.docx`, `report_v002.docx`, etc. Each regeneration auto-increments. Never overwrite previous versions. The generator scans for existing `report_v*.docx` files and picks the next number using numeric max (not alphabetical sort — mixed zero-padded versions break alphabetical).

## Design Decisions
- **Thread-level dedup**: Max 5 comments per Reddit thread, selected randomly (seed 42) to prevent high-engagement voices from dominating
- **No engagement filter**: All items enter the corpus regardless of likes/upvotes. Engagement is preserved as metadata for Signal Strength scoring but never gates corpus admission. Quality controls (empty text, minimum length, dedup) handle actual noise.
- **Multilingual**: Hindi/Hinglish supported for Indian market studies. Filter prompt explicitly handles mixed-language content
- **Trends separated**: Google Trends = quantitative validation layer. NOT sent through opinion relevance filter
- **Keyword expansion**: Brief → brand variants, misspellings, Hindi, competitor comparisons, occasions, complaints
- **Deterministic IDs**: SHA-256(source_url + content_text) — same content always gets same ID

## Known Failure Modes & Resolutions
| Issue | Cause | Resolution | Fail-safe |
|-------|-------|-----------|-----------|
| Google Trends timeout | PyTrends connects to `trends.google.com` which can timeout | Non-fatal — trends is a separate quantitative layer | `_safe_collect()` catches, logs, saves empty, continues |
| YouTube API timeouts | `googleapis.com` throttles at high volume (50 videos × 100 comments) | Per-video catch in collector; pipeline continues with partial data | Individual video errors caught; overall collector still returns what it got |
| Reddit 429 rate limiting | Public JSON API limits ~1 req/2s; 60 keywords × 10 subreddits exceeds this | 10s backoff + retry; later keyword variants may fail | Core data from early keywords already collected before rate limit hits |
| Brand name collisions | Brand name matches unrelated content (e.g., when brand name has colloquial meaning) | Stage 3 relevance filter removes them | LLM classification with reasons; rejected items saved for audit |
| Mixed timezone datetimes | Some collectors return UTC-aware, others naive datetimes | `_to_utc()` normalizes all to UTC-aware before any comparison or sort | Applied in normalize.py sort, stats min/max, AND scoring.py temporal consistency. Every `sorted(timestamps)` must use normalized timestamps |
| Pipeline crash after collection | Bug in Stage 2+ crashes after raw data already saved | **Resume from Stage 2** — load `raw/*.json`, skip re-collection | Raw data always saved to disk BEFORE any processing begins |
| Lato font not in matplotlib cache | Lato TTFs not found by matplotlib — charts render in fallback font | Install Lato via system fonts or copy TTFs to `matplotlib/mpl-data/fonts/ttf/`. Delete `~/.matplotlib/fontlist-*.json` and restart Python. | Cache rebuilds automatically on next matplotlib import after cache file is deleted. |
| Anthropic credits not seen | API key created under "Claude Code" workspace doesn't see org credits | Create key under "Default" workspace | Test key with simple API call before running pipeline |
| PyTrends duplicate keywords | Auto-expanded keywords include duplicates | PyTrends throws "already exists" error | Caught by `_safe_collect()`; related queries still collected |
| Theme extraction sees only 200 items | `_extract_themes()` had `items[:200]` hardcoded cap — themes had 3-5 items despite 900+ corpus | **FIXED**: Two-pass approach — discover themes from 300-item stratified sample, map ALL items in batches of 30 | analyze.py now uses `THEME_DISCOVERY_PROMPT` + `THEME_MAPPING_PROMPT` |
| NormalizedItem not hashable | Using `set(sample)` with Pydantic models fails — models are unhashable by default | Use `{i.item_id for i in sample}` (set of strings) instead of `set(items)` | Fixed in `_extract_themes()` — always key sets by `item_id` string |
| Corpus cap blocking analysis | `orchestrator.py` had `corpus = corpus[:max_corpus_size]` defaulting to 1000 items | **REMOVED** the cap entirely. `max_corpus_size` removed from config. Never add cost-control caps — they destroy analysis quality | All items from normalization now pass to Stage 3 |
| Anthropic API key not in bash env | Key set in Windows user env vars but not inherited by bash subshell | Read from `.env` file in project root using Python: `pathlib.Path('.env').read_text()` | `.env` file written during setup; all resume scripts load it at startup |
| 529 Overloaded errors | Anthropic API busy during peak hours | SDK auto-retries with exponential backoff; pipeline continues | Built into `anthropic` SDK — no manual handling needed |
| Sentiment results not reused on resume | If pipeline crashes after sentiment but before themes, sentiment re-runs wasting credits | Save `analysis/results.json` after sentiment step; resume scripts load `sentiment_results` from it | `resume_stage4b.py` demonstrates: load saved sentiment, skip re-classification |
| Sentiment zeros in report | `resume_stage4b.py` sources sentiment from a prior run. If that run crashed before writing `analysis/results.json`, loaded `sentiment_results` is empty. | **Patch the production run's `analysis/results.json`**: load sentiment from the nearest completed run with real data (`sentiment_results count > 0`), overwrite `sentiment_results` and `overall_sentiment`, then regenerate the DOCX. Check: `python -c "import json; d=json.load(open('runs/RUN_ID/analysis/results.json')); print(d['overall_sentiment'], len(d['sentiment_results']))"` | Before generating any report, verify `overall_sentiment` is non-zero. |
| Aspect NSS all showing +100% | Aspects with n=2-6 mentions had trivially perfect NSS (3/3 positive = +100%). These tiny samples floated to top when sorted by `abs(NSS)`. | **FIXED**: n≥10 minimum threshold enforced. Sort by sample size (most discussed first), not by raw NSS. | Never show aspect NSS for aspects with fewer than 10 mentions. |
| Serial naming picks wrong version | Mixed zero-padded and non-padded filenames cause alphabetical sort to pick wrong version. Lock files (`~$`) match the glob. | **FIXED**: Parse all version numbers numerically and take `max()`. Filter `~$` lock files. | Always use numeric max of parsed version numbers. |
| VerbatimQuote not a dict in DOCX generator | `isinstance(q, dict)` check in `_section_verbatims()` and `_section_deep_dives()` always fails — `representative_quotes` are `VerbatimQuote` Pydantic objects, not dicts. Verbatim sections rendered with zero quotes. | **FIXED**: Added `else` branch using `getattr(q, "text", "")` and `getattr(q, "source_platform", None).value` to handle Pydantic objects. | When iterating `representative_quotes`, always handle three cases: dict, str, and Pydantic object. |
| Decimal truncation in observation text | `obs.split(".")[0]` splits on the decimal point in "4.6%" — "44 consumer mentions (4.6% prevalence)..." became "44 consumer mentions (4". | **FIXED**: Use `re.split(r'\.\s+', obs)[0]` — only splits at period followed by space (sentence boundary). Then removed limit entirely: DOCX cells wrap naturally. | Never use `.split(".")` on observation text. Never add `[:N]` truncation limits in DOCX — let cells wrap. |
| Radar chart mismatch | Radar charts indexed positionally (`chart_radar_0.png`) but deep dives sorted by confidence — positions didn't match, wrong chart shown under each insight. | **FIXED**: Charts named `chart_radar_{insight_id}.png` (e.g. `chart_radar_INS_003.png`). Deep dives look up `chart_radar_{ins.insight_id}.png`. Sort-order independent. | Never use positional index for radar chart filenames. Always key by `insight_id`. |
| Synthesis under-generates insights | Prompt said "for each theme" but Claude only generated 5 of 11. No hardcoded limit — Claude just decided to skip themes. | **FIXED**: Prompt now mandates `{theme_count}` insights with "no exceptions." Validation logging warns if count < expected. | Always verify insight count matches theme count after synthesis. |
| Re-synthesis overwrites scored data | Running `resynthesize.py` with depleted API credits wrote 0 insights to `scored_insights.json`, destroying the existing 5. | Restored from prior run (`f00e82`). Script should check API availability before overwriting. | Before re-running synthesis, back up existing `insights/` and `scored/` directories. |
| Representative quotes repeat across themes | Quotes selected by text length — long posts (YouTube descriptions, mega Reddit posts) match keywords in many themes, appearing as "representative voice" for 5+ unrelated themes. | **FIXED**: Quality scoring system: prefer comments over posts, prefer medium length (80-500 chars), score by keyword-hit count per theme, penalise YouTube descriptions and promo content, enforce global dedup (each item used as quote in at most 1 theme). `fix_quotes.py` | Never select quotes by text length alone. Always enforce cross-theme dedup. Prefer `content_type=comment` for representative voices. |
| VerbatimQuote missing `selection_reason` | Stage 4 in-context analysis wrote quote dicts without `selection_reason` field — Pydantic validation fails when loading `AnalysisResults`. | **FIXED**: All quote-writing code must include `selection_reason` field. | `VerbatimQuote` schema requires `selection_reason: str`. Always include it when building quote objects. |
| Instagram not in SourcePlatform enum | External data import included Instagram posts/comments but `SourcePlatform` enum only had reddit/youtube/news/academic/trends/amazon. | **FIXED**: Added `INSTAGRAM = "instagram"` to `SourcePlatform` enum and Instagram-specific fields (`followers`, `share_count`, `engagement_rate`, `media_type`) to `PlatformMetadata`. | When adding new data sources, add enum value to `SourcePlatform` and any platform-specific metadata fields to `PlatformMetadata`. |
| `.env` loading uses `setdefault` — key not picked up | `os.environ.setdefault()` does not override if the key already exists (even as empty string) in the inherited shell environment. | **FIXED**: Use `os.environ[key] = val` instead of `os.environ.setdefault(key, val)` when loading `.env`. | Always use direct assignment (`os.environ[key] = val`) for `.env` loading, not `setdefault`. |
| Instagram comments have no score or timestamp | Instagram comment data lacks `score`, `created_at`, and unique `id` fields. Thread-level cap sorts by score (all 0 = random selection), timestamp sort puts all IG comments at end. | Construct unique `source_url` from `parent_url + "#comment_" + user_id + "_" + text_hash[:8]`. Accept that IG comment selection within thread cap is effectively random. | When ingesting platforms without engagement scores on comments, sort by text length as secondary key for richer content. |
| Empty Instagram captions (video/reel content) | 497 of 900 Instagram posts had empty captions — reels/videos with no text description. | Skip empty-caption posts in ingestion (no text to analyse), but keep their comments which may contain valuable consumer opinions. | Always check for empty `caption` field on Instagram posts. The comments under captionless posts are still valid data. |
| Category-only search queries flood corpus with noise | `_generate_category_terms()` produced brandless queries like "best [category]" that YouTube/Reddit returned generic content for. In one run, 57% of YouTube data was irrelevant. | **FIXED**: 3-layer defence: (1) `keywords.py` now brand-anchors ALL category terms, (2) YouTube/Reddit collectors validate brand mention in video title/post title before fetching comments, (3) orchestrator runs post-collection quality audit sampling 50 items per source. | Every search query MUST include the brand name. Never generate brandless category queries. See "Data Quality Architecture" section. |
| Keyword-only theme discovery misses narrative patterns | Keyword-based theme mapping found themes but missed narrative-level patterns (cultural references, misinformation framing, moral debates). In one study, 21% of corpus items had no theme after keyword pass alone. | **FIXED**: Added mandatory Procedure 15 - read unthemed items contextually after keyword pass, looking for cultural references, misinformation framing, moral debates, sarcasm. `add_narrative_themes.py` adds discovered narrative themes. | Keyword matching finds vocabulary. Narrative patterns require contextual reading. NEVER ship a report without the narrative review pass (Procedure 15). |
| Top-down keyword themes substituted for inductive discovery | Pre-wrote keyword regex themes before reading the corpus, then pattern-matched items against them. Missed entire consumer segments (beard/men's grooming: 499+ items) and collapsed distinct themes into overly broad categories. One run produced only 11 themes from 7,688 items when a prior run found 21 themes from 4,314 items. When 38% came back unthemed, broadened regex and deleted remainder as "off-topic" instead of reading them. | Root cause: optimised for speed on large corpus without being asked to. | **NEVER pre-write keyword themes.** Pass 1 (Discovery) must involve reading a stratified sample and noting what patterns emerge inductively. Keywords are for Pass 2 (Mapping) only. When items are unthemed after mapping, READ THEM to find missed patterns — never delete unthemed items as "off-topic" without reading them first. A larger corpus has more signal to discover, not less. |
| Data Provenance section hardcoded for specific brand | `_section_data_provenance()` had hardcoded platform table, geographic coverage, temporal coverage, and demographic accuracy text referencing a specific brand. None adapted to new runs. | **FIXED**: Section now derives everything from `items` parameter - platform table built from actual `source_platform` counts, date range from actual `source_timestamp` min/max, geographic coverage from `config.collection.trends_geo`, demographic bias text assembled from which platforms are actually present. No brand-specific references. | Data Provenance must NEVER contain hardcoded brand names, dates, platform lists, or subreddit names. Everything must be derived from the run's actual data and config. |
| Radar charts identical across insights | Scoring used coarse bands (e.g., n>=100 -> 1.0, >=3 platforms -> 1.0) that saturated in large corpora. All insights got near-identical scores, producing identical-looking radar charts. | **FIXED**: Replaced band-based scoring with continuous functions: log-scaled sample size relative to corpus, Herfindahl diversity with balance penalty, temporal evenness across quartiles, exponential recency decay, percentile-ranked engagement. | Never use discrete bands for scoring factors. All factors must use continuous scoring that produces meaningful spread across the insight set. |
| Methodology section hardcoded | Hardcoded "966 items", "claude-opus-4-6", "FMCG benchmark", "5 platforms", "Reddit >=3 upvotes", scoring weights as string literals. | **FIXED**: All values now derived from `config`, `analysis`, and `items` parameters. Platform list derived from actual data. Scoring weights read from `config.scoring`. | Methodology section must NEVER contain hardcoded numbers, model names, or platform lists. Everything derived from config and data. |
| Scoring matrix threshold mismatch | `_matrix_quadrant()` used >= 0.5 for Key Finding but `_confidence_tier()` used >= 0.75 for HIGH. Result: MEDIUM-confidence insights labeled "Key Finding". In one run, 14/15 insights were Key Findings with 0 high-confidence insights. | **FIXED**: Matrix concept removed entirely. Insights ranked by continuous confidence and signal scores shown as percentages. No categorical quadrant labels. | Do not reintroduce categorical quadrant labels. Use continuous scores. |
| LLM provider priority backwards | `create_llm_client()` docstring said "Claude first" but code tried Gemini first. `--model` CLI arg stored in config but never passed to LLM client. | **FIXED**: Auto-detect order swapped to Claude first. `create_llm_client()` now accepts optional `model` parameter. Orchestrator passes `config.analysis.claude_model`. | Provider priority: Claude → Gemini. Always pass model from config. |
| Web search results mislabeled as NEWS | `SourcePlatform` had no `WEB` value. Serper results written as `NEWS`, corrupting platform counts and source diversity scoring. | **FIXED**: Added `WEB = "web"` to `SourcePlatform` enum. `web_search.py` now uses `SourcePlatform.WEB`. | Web search and news are distinct evidence layers. Never collapse them. |
| Silent data loss on incomplete LLM batches | If LLM returned fewer items than sent in filter/analyze batches, missing items silently vanished. No completeness check. | **FIXED**: `filter.py` now checks returned item_ids against sent batch — missing items kept as relevant (conservative). `analyze.py` logs warning with missing item_ids. | After parsing any LLM batch response, always check that all sent item_ids are accounted for. |
| Main CLI doesn't produce DOCX | `run.py` → `run_pipeline()` → Stage 7 only generated PDF/PPTX. The flagship DOCX artifact required separate scripts. | **FIXED**: Orchestrator Stage 7 now calls `generate_all_charts()` + `generate_docx_report()` alongside PDF/PPTX. | The main entry point must produce the primary deliverable. |
| Adaptive methodology never called | `select_methodology()` was dead code with a misleading docstring claiming no external API calls. | **FIXED**: Deleted entirely. Orchestrator now calls `validate_theme_coverage()` from `validate.py` instead of reimplementing the check inline. | Do not add methodology selection functions that imply code branches where none exist. |
| Failed run printed as success | `run.py` always printed "Run complete" even when pipeline aborted at theme coverage gate. | **FIXED**: Checks for `summary.json` (only written on full completion). Prints "Run INCOMPLETE" and exits with code 1 if missing. | Never report success without verifying the run completed fully. |
| "Latest run" picks wrong directory | `scripts/stage6_7_score_report.py` and `scripts/regenerate_report.py` sorted run dirs by name, not modification time. Mixed naming schemes broke lexical sort. | **FIXED**: Sort by `p.stat().st_mtime` instead of `p.name`. | Always sort run directories by modification time, not by name. |
| Non-deterministic keyword order | `_generate_brand_variants()` used `list(set(...))` — undefined order across Python runs. | **FIXED**: Changed to `sorted(set(...))` for deterministic output. | Never use `list(set(...))` for reproducible pipelines. Always `sorted(set(...))`. |
| DOCX insight count shows theme count | Cover page and Insight Landscape used `len(analysis.themes)` instead of `len(scored_insights)`. If synthesis under-generated, count was wrong. | **FIXED**: Both locations now use `len(scored_insights)`. | Insight count must always come from scored insights, not themes. |
| Missing dependencies in requirements.txt | `python-docx` (needed by docx_generator.py) and `google-genai` (needed by llm_client.py) not listed. Fresh clone would fail. | **FIXED**: Both added to `requirements.txt`. | All imports must have corresponding entries in requirements.txt. |

## Procedures
1. **Before any run**: Get user-approved brief (brand, questions, competitors, geo, aspects). NEVER skip this.
2. **Before first run on a new machine**: Set all env vars, `pip install -r requirements.txt`. Write API key to `.env` file in project root.
3. **Setting ANTHROPIC_API_KEY**: The key must be from the **Default workspace** at console.anthropic.com/settings/keys — NOT the "Claude Code" workspace. Claude Code's internal OAuth token (`sk-ant-oat01-...`) does NOT work for API calls. Write the key to `.env` and load it via Python, not bash (Windows env vars don't inherit into bash shells).
4. **During run**: Monitor logs. If a collector fails, pipeline continues. Check `raw/` files after Stage 1 to verify data volume.
5. **After run**: Check `summary.json` for item counts, insight count. Open `report/report_v###.docx`. Check insights have ≥10 items each — if insights have 3-5 items, the two-pass theme extraction may have failed.
6. **If run crashes mid-pipeline**: Check the last log line. Fix the bug. **Resume from the failed stage** — raw data, normalized corpus, filtered corpus, and sentiment results are all saved to disk. Load from the last good artifact. Do NOT re-collect or re-classify what's already done.
7. **Resume scripts**: `scripts/resume_stage3.py <run_id>` (from normalization), `scripts/resume_stage4.py <run_id>` (from filtering). All accept the source run ID as a CLI argument and load brand/category config from the source run's `config.json`. Never hardcode run IDs or brand configs in these scripts.
8. **Daily limit awareness**: NewsData.io resets daily (200 credits). Serper has 2,500 total (lifetime). Reddit rate limits recover in minutes. YouTube quota (10K units) resets daily. Anthropic credits deducted per token (~$2-3 per full 1000-item run).
9. **If YouTube is timing out**: Check `ping www.googleapis.com`. If ping is fine, it's API throttling — let it grind through. If ping fails, switch to mobile hotspot or check VPN.
10. **Verify theme quality after Stage 4**: Each theme should have ≥20 items and ≥1.5% prevalence for a 900+ item corpus. If themes are smaller, check that two-pass extraction ran (look for "Theme mapping: batch X/Y done" in logs).
11. **In-context synthesis**: When running inside Claude Code, synthesize insights directly in the session by reading theme data from `analysis/results.json` and writing insights to `insights/insights.json`. Then run `rescore.py` (data-driven, no API needed). This avoids burning Anthropic API credits. Only use external API calls via `resynthesize.py` during automated pipeline runs.
12. **Before re-running synthesis**: Always back up `insights/` and `scored/` directories first. A failed synthesis (e.g., depleted credits) will overwrite existing data with empty arrays.
13. **External data ingestion**: Use `pipeline/ingest.py` for any pre-collected data: `from consumer_research.pipeline.ingest import ingest_external_data; items = ingest_external_data(Path("data/myfile.json"))`. Auto-detects format (platform-scraped with nested comments, simple flat list, or pre-normalized). For study-specific orchestration scripts, see `examples/studies/weight_loss/run_weight_loss.py` as a template. Always add new platforms to `SourcePlatform` enum first.
14. **In-context analysis workflow (BYO data, no API calls)**

When a user says "analyse run X" or "run stages 3-5 on run X", follow this procedure. You ARE the analysis engine - read the data, classify it, and write results directly to disk. No external API calls needed.

**Prerequisites**: A run directory exists at `runs/<run_id>/` with `normalized/corpus.json` and `config.json` (created by `consumer-research ingest`).

**Step 1 - Load and understand the corpus**
```python
import json
from pathlib import Path
from consumer_research.config import RUNS_DIR

run_id = "<run_id>"
run_dir = RUNS_DIR / run_id
config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
corpus = json.loads((run_dir / "normalized" / "corpus.json").read_text(encoding="utf-8"))
brand = config["brand_name"]
category = config["category"]
```
Read a sample of 20-30 items to understand the data shape, platforms present, and content types.

**Step 2 - Stage 3: Relevance filter**
Read each item and classify as relevant or not to the brand/topic. Remove items that are generic category discussion with no brand connection, spam, or completely off-topic. Write results:
- `runs/<run_id>/filtered/corpus.json` - list of relevant NormalizedItem dicts
- `runs/<run_id>/filtered/rejected.json` - rejected items with reasons (for audit)

**Step 3 - Stage 4a: Sentiment, emotion, and ABSA**
For each filtered item, classify:
- Sentiment: positive / negative / neutral / mixed (with score 0.0-1.0)
- Primary Plutchik emotion: joy / trust / fear / surprise / sadness / disgust / anger / anticipation / none
- Aspect-based sentiment: per-aspect scores (e.g., taste: positive 0.85, price: negative 0.3)
Write as `SentimentResult` objects. Process in batches if corpus is large.

**Step 4 - Stage 4b: Theme extraction (two-pass)**
- Pass 1 (Discovery): Read a stratified sample of ~300 items across platforms. Identify 8-15 candidate themes with labels, descriptions, and keywords.
- Pass 2 (Mapping): Classify ALL remaining items against discovered themes in batches of ~30. Each item can map to 0+ themes.
- Verify: each theme should have >=20 items and >=1.5% prevalence for a 900+ corpus.

**Step 5 - Stage 4c: Narrative review pass (MANDATORY - never skip)**
After keyword-based theme mapping, check how many items remain unthemed.
- Read **ALL unthemed items** plus a **10% random sample of themed items**
- If this exceeds context, read in batches until all unthemed items are covered
- Look for narrative patterns keywords cannot detect: (a) cultural/celebrity references, (b) misinformation and miracle claims, (c) stigma, shame, moral debate, (d) sarcasm, irony, memes, (e) cross-cutting emotional narratives
- **Completion criterion: unthemed items must be below 10% of corpus**. If above 10%, keep reading and classifying.
- This step was skipped once and resulted in missing themes containing 21% of the corpus.

**Step 6 - Write analysis results**
Assemble all results into `AnalysisResults` and write to `runs/<run_id>/analysis/results.json`:
```python
from consumer_research.models.schemas import AnalysisResults, compute_nss
results = AnalysisResults(
    sentiment_results=all_sentiment_results,
    themes=all_themes,
    overall_sentiment={"positive": n_pos, "negative": n_neg, "neutral": n_neu, "mixed": n_mix},
    net_sentiment_score=compute_nss(overall_sentiment),
    total_items_analyzed=len(filtered),
    analysis_model="claude-code-in-context",
    analysis_prompts={"method": "in-context analysis by Claude Code session"},
)
(run_dir / "analysis" / "results.json").write_text(
    json.dumps(results.model_dump(mode="json"), indent=2, default=str), encoding="utf-8"
)
```

**Step 7 - Stage 5: Synthesise insights**
Read theme data from `analysis/results.json`. For each theme, write one structured insight:
- Observation: what the data shows (theme + evidence)
- Insight: what it means for the consumer (the "why")
- Implication: what it means for the business ("So What")
- Recommendation: what the client should do ("Now What")
- Further Validation: what additional research would strengthen this

Quality gates (all must pass): Grounded, Non-obvious, Actionable, Specific, Falsifiable.
Write to `runs/<run_id>/insights/insights.json` as a list of `Insight` dicts.

**Step 8 - Score and generate report**
```bash
consumer-research score-report <run_id>
```
This runs Stage 6 (scoring) and Stage 7 (charts + DOCX) automatically. No API calls.

**Expected artifacts when complete:**
```
runs/<run_id>/
  brief.json                    # from ingest
  config.json                   # from ingest
  raw/external_ingested.json    # from ingest
  normalized/corpus.json        # from ingest
  filtered/corpus.json          # Stage 3 (you wrote this)
  analysis/results.json         # Stage 4 (you wrote this)
  insights/insights.json        # Stage 5 (you wrote this)
  scored/scored_insights.json   # Stage 6 (score-report wrote this)
  report/report_v001.docx       # Stage 7 (score-report wrote this)
```

## Stage 4 Theme Extraction Architecture (Critical — Do Not Revert)
Theme extraction uses a **two-pass approach** to handle large corpora without token limit issues:

**Pass 1 — Discovery** (`THEME_DISCOVERY_PROMPT`):
- Stratified sample: up to 300 items, proportionally drawn from each platform
- LLM identifies 8-15 candidate themes with labels, descriptions, keywords, and initial supporting item_ids
- Random seed 42 for reproducibility

**Pass 2 — Mapping** (`THEME_MAPPING_PROMPT`):
- ALL remaining items (corpus minus the discovery sample) classified in batches of 30
- Each item matched to 0+ themes from the discovered list
- Theme item counts accumulate across all batches → real prevalence across full corpus

**Result**: Themes reflect the full corpus (e.g., 1000+ items -> themes with 10-100+ items, 1-10% prevalence) instead of only the first 200 items.

## Private
`Consuma AI/` and `Jolene Growth Handover/` — proprietary reference material. Never commit to public repo.
