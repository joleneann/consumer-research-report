"""CLI entry point for the consumer research pipeline.

Usage:
    consumer-research ingest --data data/my_data.json --brand "Thums Up" --category "Beverages"
    consumer-research run --brand "Thums Up" --category "Beverages" --geo IN
    consumer-research score-report [run_id]
    consumer-research regenerate [run_id]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from consumer_research.config import RUNS_DIR


def _resolve_run_dir(run_id: str | None) -> Path:
    """Resolve a run directory from an optional run ID (defaults to most recent)."""
    if run_id:
        run_dir = RUNS_DIR / run_id
        if not run_dir.exists():
            print(f"ERROR: Run directory not found: {run_dir}")
            sys.exit(1)
        return run_dir
    else:
        if not RUNS_DIR.exists():
            print(f"ERROR: No runs directory found at {RUNS_DIR}")
            sys.exit(1)
        runs = sorted(RUNS_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        if not runs:
            print("ERROR: No run directories found")
            sys.exit(1)
        return runs[0]


def _load_run_config(run_dir: Path) -> dict:
    """Load config.json from a run directory."""
    config_path = run_dir / "config.json"
    if not config_path.exists():
        print(f"ERROR: No config.json found in {run_dir}")
        sys.exit(1)
    return json.loads(config_path.read_text(encoding="utf-8"))


def cmd_ingest(args):
    """Ingest external JSON data into a run directory (Stages 0-2).

    Creates a new run with normalized data, ready for in-context analysis
    in a Claude Code session (Stages 3-5), then scoring and report generation
    via consumer-research score-report.
    """
    from datetime import datetime, timezone
    from uuid import uuid4

    from consumer_research.config import CollectionConfig, PipelineConfig
    from consumer_research.models.schemas import RunConfig
    from consumer_research.pipeline.ingest import ingest_external_data
    from consumer_research.pipeline.normalize import normalize_and_deduplicate

    logger = logging.getLogger("ingest")

    data_path = Path(args.data)
    if not data_path.exists():
        print(f"ERROR: Data file not found: {data_path}")
        sys.exit(1)

    # Create run directory
    run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Ingest
    items = ingest_external_data(data_path, collection_query=f"{args.brand} study")
    logger.info(f"Ingested {len(items)} items from {data_path.name}")

    # Save raw data for provenance (Collection Funnel in report reads from raw/)
    import shutil
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(exist_ok=True)
    shutil.copy(str(data_path), str(raw_dir / f"external_{data_path.name}"))
    # Also save as structured JSON so docx_generator can count raw items
    (raw_dir / "external_ingested.json").write_text(
        json.dumps([item.model_dump(mode="json") for item in items], default=str),
        encoding="utf-8",
    )

    # Normalize and deduplicate
    corpus = normalize_and_deduplicate({"external": items}, run_dir)
    logger.info(f"Normalized: {len(corpus)} items after dedup")

    # Save config
    config = PipelineConfig(collection=CollectionConfig(
        brand_name=args.brand,
        category=args.category,
        business_objectives=args.objectives or [],
        trends_geo=args.geo or "",
        news_country=(args.geo or "").lower(),
    ))
    run_config = RunConfig(
        run_id=run_id,
        created_at=datetime.now(timezone.utc),
        brand_name=args.brand,
        category=args.category,
        time_period_days=180,
        keywords=[],
        business_objectives=args.objectives or [],
        subreddits=[],
        trends_geo=args.geo or "",
        news_country=(args.geo or "").lower(),
        claude_model="in-context",
        claude_temperature=0.0,
    )
    (run_dir / "config.json").write_text(
        run_config.model_dump_json(indent=2), encoding="utf-8"
    )

    print(f"\nRun created: {run_id}")
    print(f"  {len(corpus)} items normalized and ready for analysis")
    print(f"  Output: {run_dir}")
    print(f"\nNext steps:")
    print(f"  1. Open this project in Claude Code")
    print(f"  2. Analyze the corpus in-context (Stages 3-5)")
    print(f"  3. Run: consumer-research score-report {run_id}")


def cmd_run(args):
    """Full pipeline: Brief -> Collect -> Normalize -> Filter -> Analyze -> Synthesize -> Score -> Report."""
    from consumer_research.config import (
        AnalysisConfig,
        CollectionConfig,
        PipelineConfig,
        ScoringConfig,
    )
    from consumer_research.pipeline.orchestrator import run_pipeline

    config = PipelineConfig(
        collection=CollectionConfig(
            brand_name=args.brand,
            category=args.category,
            keywords=args.keywords or [],
            subreddits=args.subreddits or [],
            trends_geo=args.geo,
            news_country=args.geo.lower() if args.geo else "",
            business_objectives=args.objectives or [],
            competitors=args.competitors or [],
            reddit_max_posts=args.max_posts,
        ),
        analysis=AnalysisConfig(
            claude_model=args.model,
        ),
    )

    run_dir = run_pipeline(config)
    summary_path = run_dir / "summary.json"
    if summary_path.exists():
        print(f"\nRun complete. Output: {run_dir}")
    else:
        print(f"\nRun INCOMPLETE (stopped at validation gate). Partial output: {run_dir}")
        sys.exit(1)


def cmd_score_report(args):
    """Stages 6+7: Score insights + generate charts and DOCX report (no API calls)."""
    from consumer_research.config import CollectionConfig, PipelineConfig, ScoringConfig
    from consumer_research.models.schemas import AnalysisResults, Insight, NormalizedItem
    from consumer_research.pipeline.scoring import score_insights, compute_brand_health
    from consumer_research.report.charts import generate_all_charts
    from consumer_research.report.docx_generator import generate_docx_report

    run_dir = _resolve_run_dir(args.run_id)
    logger = logging.getLogger("score-report")
    logger.info(f"Run directory: {run_dir.name}")

    corpus = [NormalizedItem(**d) for d in json.loads((run_dir / "filtered" / "corpus.json").read_text(encoding="utf-8"))]
    analysis_data = json.loads((run_dir / "analysis" / "results.json").read_text(encoding="utf-8"))
    analysis = AnalysisResults(**analysis_data)
    insights = [Insight(**d) for d in json.loads((run_dir / "insights" / "insights.json").read_text(encoding="utf-8"))]

    rc = _load_run_config(run_dir)
    config = PipelineConfig(
        collection=CollectionConfig(
            brand_name=rc.get("brand_name", "Unknown"),
            category=rc.get("category", "general"),
            business_objectives=rc.get("business_objectives", []),
            competitors=rc.get("competitors", []),
            trends_geo=rc.get("trends_geo", ""),
            news_country=rc.get("news_country", ""),
        ),
        scoring=ScoringConfig(),
    )

    scored = score_insights(insights, analysis, corpus, run_dir, config=config.scoring)
    brand_health = compute_brand_health(analysis, corpus)
    analysis_data["brand_health"] = brand_health
    (run_dir / "analysis" / "results.json").write_text(
        json.dumps(analysis_data, indent=2, default=str), encoding="utf-8"
    )

    report_dir = run_dir / "report"
    report_dir.mkdir(exist_ok=True)
    charts = generate_all_charts(analysis=analysis, scored_insights=scored, items=corpus, output_dir=report_dir)
    docx_path = generate_docx_report(scored_insights=scored, analysis=analysis, items=corpus, config=config, run_dir=run_dir, brand_health=brand_health)

    logger.info(f"Scored: {len(scored)} insights | Brand Health: {brand_health.get('overall_score', 'N/A')}/100")
    logger.info(f"DOCX: {docx_path}")


def cmd_regenerate(args):
    """Regenerate DOCX report from existing scored data (no API calls)."""
    from consumer_research.config import CollectionConfig, PipelineConfig
    from consumer_research.models.schemas import AnalysisResults, NormalizedItem, ScoredInsight
    from consumer_research.report.charts import generate_all_charts
    from consumer_research.report.docx_generator import generate_docx_report

    run_dir = _resolve_run_dir(args.run_id)
    logger = logging.getLogger("regenerate")
    logger.info(f"Run directory: {run_dir.name}")

    corpus = [NormalizedItem(**d) for d in json.loads((run_dir / "filtered" / "corpus.json").read_text(encoding="utf-8"))]
    analysis_data = json.loads((run_dir / "analysis" / "results.json").read_text(encoding="utf-8"))
    analysis = AnalysisResults(**analysis_data)
    scored_insights = [ScoredInsight(**d) for d in json.loads((run_dir / "scored" / "scored_insights.json").read_text(encoding="utf-8"))]

    rc = _load_run_config(run_dir)
    config = PipelineConfig(collection=CollectionConfig(
        brand_name=rc.get("brand_name", "Unknown"),
        category=rc.get("category", "general"),
        business_objectives=rc.get("business_objectives", []),
        competitors=rc.get("competitors", []),
        trends_geo=rc.get("trends_geo", ""),
        news_country=rc.get("news_country", ""),
    ))

    brand_health = analysis_data.get("brand_health", {})
    charts = generate_all_charts(analysis=analysis, scored_insights=scored_insights, items=corpus, output_dir=run_dir / "report")
    docx_path = generate_docx_report(scored_insights=scored_insights, analysis=analysis, items=corpus, config=config, run_dir=run_dir, brand_health=brand_health)

    logger.info(f"DOCX: {docx_path} ({docx_path.stat().st_size:,} bytes)")


def main():
    parser = argparse.ArgumentParser(
        prog="consumer-research",
        description="Consumer research report generator",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── ingest ──
    p_ingest = subparsers.add_parser("ingest", help="Ingest external JSON data (Stages 0-2)")
    p_ingest.add_argument("--data", required=True, help="Path to JSON data file")
    p_ingest.add_argument("--brand", required=True, help="Brand or topic name")
    p_ingest.add_argument("--category", required=True, help="Product/topic category")
    p_ingest.add_argument("--objectives", nargs="*", help="Business objectives / research questions")
    p_ingest.add_argument("--geo", default="", help="Geographic region (e.g., IN)")
    p_ingest.set_defaults(func=cmd_ingest)

    # ── run ──
    p_run = subparsers.add_parser("run", help="Run full automated pipeline (Stages 0-7, requires ANTHROPIC_API_KEY)")
    p_run.add_argument("--brand", required=True, help="Brand name to analyze")
    p_run.add_argument("--category", required=True, help="Product category")
    p_run.add_argument("--keywords", nargs="*", help="Additional search keywords")
    p_run.add_argument("--subreddits", nargs="*", help="Subreddits to search")
    p_run.add_argument("--geo", default="", help="Geographic region (e.g., IN)")
    p_run.add_argument("--objectives", nargs="*", help="Business objectives / research questions")
    p_run.add_argument("--competitors", nargs="*", help="Competitor brands")
    p_run.add_argument("--max-posts", type=int, default=500, help="Max Reddit posts (default 500)")
    p_run.add_argument("--model", default="claude-sonnet-4-20250514", help="Claude model for analysis")
    p_run.set_defaults(func=cmd_run)

    # ── score-report ──
    p_sr = subparsers.add_parser("score-report", help="Run Stages 6+7: score + report (no API)")
    p_sr.add_argument("run_id", nargs="?", default=None, help="Run ID (defaults to most recent)")
    p_sr.set_defaults(func=cmd_score_report)

    # ── regenerate ──
    p_regen = subparsers.add_parser("regenerate", help="Regenerate DOCX from scored data (no API)")
    p_regen.add_argument("run_id", nargs="?", default=None, help="Run ID (defaults to most recent)")
    p_regen.set_defaults(func=cmd_regenerate)

    # ── Parse ──
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
