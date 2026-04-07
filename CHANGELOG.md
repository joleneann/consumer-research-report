# Changelog

## v0.2.0 (2026-04-07)

### Breaking Change: Engagement thresholds removed

Engagement (likes, upvotes, helpful votes) is no longer used as a corpus admission gate. Every item that passes quality controls (non-empty text, minimum length, deduplication) enters the corpus regardless of engagement metrics.

**Why:** Engagement is a visibility signal, not a truth, quality, or representativeness signal. Likes and upvotes are driven by platform algorithms, timing, language, and audience demographics - none of which correlate cleanly with how representative an opinion is of real consumers. In the India Hair Colour study, 59.9% of items fell below typical engagement thresholds. Excluding them hid the silent majority and inflated apparent positivity by 11%. On specific themes, the divergence was 20-33%.

**What changed:**
- Removed `reddit_min_score`, `youtube_min_likes`, `twitter_min_likes`, `instagram_min_likes`, `review_min_helpful_votes` from `CollectionConfig`
- Removed engagement filtering from `reddit_mcp.py`, `youtube.py`, and `ingest.py`
- Thread cap in `normalize.py` now uses random selection (seed 42) instead of keeping highest-engagement comments
- Report Collection Funnel says "quality filter" instead of "engagement filter"

**What didn't change:**
- Engagement metadata is preserved on every item (`platform_metadata.score`, `like_count`)
- Signal Strength scoring still uses engagement as a resonance factor (30% weight)
- Quality controls remain: empty text, minimum length, SHA-256 deduplication, thread cap

**The new philosophy:** The corpus reflects what everyone thinks. The scoring reflects how visible and validated those opinions are.

**Limitation #4 (Silent Majority) is now MITIGATED.** Hard engagement gates are gone, but built-in collectors still fetch visibility-ranked content from platforms (Reddit sort="top", YouTube order="relevance"). Fully resolving this would require randomized collection strategies.

### New features
- `consumer-research ingest` CLI command for bring-your-own-data workflow
- `brief.json` provenance artifact on ingested runs (schema-compatible with `ResearchBrief`)
- BOM-encoded JSON support in ingester (handles Windows app exports)

### New study
- India Hair Colour study added to `examples/outcomes/` (4,314 items, 21 insights, NSS +38.8%)

### Improvements
- Unified CLI: `ingest`, `run`, `score-report`, `regenerate`
- `pyproject.toml` with installable package and CLI entry point
- `RUNS_DIR` configurable via `CONSUMER_RESEARCH_RUNS_DIR` env var (default: `./runs/`)
- Dead code removed: `select_methodology()`, `--interactive`, `--max-corpus`, `max_corpus_size`
- Orchestrator uses `validate_theme_coverage()` instead of inline reimplementation
- Batch failures in `analyze.py` emit neutral defaults + DEGRADED ANALYSIS warning
- Procedure 14 rewritten as 8-step in-context analysis playbook
- 126 tests (unit + smoke + integration), no API calls

### Bug fixes
- `resume_stage3.py` NameError (`analysis` vs `analysis_cfg`)
- `run_weight_loss.py` TypeError (removed `max_corpus_size` field)
- `_next_report_version()` extracted and tested directly (was mirror-tested)
- Instagram comment extractor now captures likes field
- Twitter comment extractor now handles nested comments
- RUNS_DIR import ordering fixed in 3 scripts

## v0.1.0 (2026-04-01)

Initial release. 8-stage pipeline: Brief, Collect, Normalize, Filter, Analyze, Synthesize, Score, Report. Four completed studies (Weight Loss, Make in India, Thums Up, Mosquito Repellent). DOCX report output with Tufte-inspired charts. Data-driven scoring (Confidence + Signal Strength + Brand Health Score). 12 documented analytical limitations.
