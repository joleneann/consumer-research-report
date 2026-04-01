"""CLI entry point for the consumer research pipeline.

Usage:
    python -m consumer_research.run --brand "Thums Up" --category "Carbonated Beverages" --geo IN
    python -m consumer_research.run --interactive  # Interactive briefing mode
"""

from __future__ import annotations

import argparse
import logging
import sys

from consumer_research.config import (
    AnalysisConfig,
    CollectionConfig,
    PipelineConfig,
    ScoringConfig,
)
from consumer_research.pipeline.orchestrator import run_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="Consumer Research Report Generator — Enterprise-grade brand perception analysis"
    )
    parser.add_argument("--brand", required=True, help="Brand name to analyze")
    parser.add_argument("--category", required=True, help="Product category")
    parser.add_argument(
        "--keywords", nargs="*", default=[], help="Additional search keywords (auto-expanded from brief)"
    )
    parser.add_argument(
        "--subreddits", nargs="*", default=[], help="Subreddits to search"
    )
    parser.add_argument("--geo", default="", help="Geographic region (e.g., IN for India)")
    parser.add_argument(
        "--objectives", nargs="*", default=[], help="Business objectives / research questions"
    )
    parser.add_argument(
        "--competitors", nargs="*", default=[], help="Competitor brands to compare against"
    )
    parser.add_argument(
        "--max-posts", type=int, default=500,
        help="Max Reddit posts (default 500 — this is a MINIMUM, not a cap)"
    )
    parser.add_argument(
        "--model", default="claude-sonnet-4-20250514", help="Claude model for analysis"
    )
    parser.add_argument(
        "--max-corpus", type=int, default=1000,
        help="Max corpus size for analysis (controls API cost)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose logging"
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    config = PipelineConfig(
        collection=CollectionConfig(
            brand_name=args.brand,
            category=args.category,
            keywords=args.keywords,
            subreddits=args.subreddits,
            trends_geo=args.geo,
            news_country=args.geo.lower() if args.geo else "",
            business_objectives=args.objectives,
            competitors=args.competitors,
            reddit_max_posts=args.max_posts,
        ),
        analysis=AnalysisConfig(
            claude_model=args.model,
            max_corpus_size=args.max_corpus,
        ),
    )

    run_dir = run_pipeline(config)
    print(f"\nRun complete. Output: {run_dir}")


if __name__ == "__main__":
    main()
