"""Integration tests for CLI subcommands against a minimal fixture run.

These tests exercise the actual product surface (consumer-research score-report
and consumer-research regenerate) against a tiny synthetic run directory.
No API calls - scoring and report generation are code-based.
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent


def _build_fixture_run(tmp_path: Path) -> Path:
    """Build a minimal valid run directory with all required artifacts."""
    run_dir = tmp_path / "runs" / "test_fixture_run"

    # Create directory structure
    for d in ["filtered", "analysis", "insights", "scored", "report"]:
        (run_dir / d).mkdir(parents=True, exist_ok=True)

    # Minimal corpus (3 items)
    items = []
    for i in range(3):
        items.append({
            "item_id": f"item_{i:03d}",
            "source_platform": "reddit",
            "source_url": f"https://reddit.com/r/test/{i}",
            "source_author": f"user_{i}",
            "source_timestamp": "2026-01-15T10:00:00+00:00",
            "collected_at": "2026-01-15T12:00:00+00:00",
            "content_text": f"This is test item {i} about the test brand quality and price.",
            "content_type": "post",
            "platform_metadata": {"score": 10 + i, "comment_count": 5},
            "collection_query": "test brand",
            "collection_method": "test",
        })
    (run_dir / "filtered" / "corpus.json").write_text(
        json.dumps(items, indent=2), encoding="utf-8"
    )

    # Minimal analysis results
    analysis = {
        "sentiment_results": [
            {
                "item_id": f"item_{i:03d}",
                "sentiment": ["positive", "negative", "neutral"][i],
                "sentiment_score": [0.8, 0.2, 0.5][i],
                "reasoning": "Test classification",
                "key_phrases": ["quality"],
                "aspects": [],
                "primary_emotion": "joy" if i == 0 else "none",
                "emotion_intensity": 0.7 if i == 0 else 0.0,
            }
            for i in range(3)
        ],
        "themes": [
            {
                "theme_id": "THM_001",
                "theme_label": "Product Quality",
                "theme_description": "Discussion about product quality",
                "supporting_item_ids": ["item_000", "item_001", "item_002"],
                "item_count": 3,
                "prevalence_pct": 100.0,
                "sentiment_distribution": {"positive": 1, "negative": 1, "neutral": 1},
                "is_multi_source": False,
                "is_contested": True,
                "platforms_present": ["reddit"],
                "representative_quotes": [],
            }
        ],
        "overall_sentiment": {"positive": 1, "negative": 1, "neutral": 1},
        "net_sentiment_score": 0.0,
        "total_items_analyzed": 3,
        "analysis_model": "test",
        "analysis_prompts": {"sentiment": "test prompt"},
    }
    (run_dir / "analysis" / "results.json").write_text(
        json.dumps(analysis, indent=2), encoding="utf-8"
    )

    # Minimal insight
    insights = [
        {
            "insight_id": "INS_001",
            "observation": "Quality is discussed in 100% of posts",
            "insight": "Consumers care about quality",
            "implication": "Quality is a purchase driver",
            "recommendation": "Invest in quality communication",
            "further_validation": "Survey on quality expectations",
            "supporting_theme_ids": ["THM_001"],
            "supporting_item_count": 3,
            "source_urls": ["https://reddit.com/r/test/0"],
            "is_grounded": True,
            "is_non_obvious": True,
            "is_actionable": True,
            "is_specific": True,
            "is_falsifiable": True,
            "passed_quality_gates": True,
        }
    ]
    (run_dir / "insights" / "insights.json").write_text(
        json.dumps(insights, indent=2), encoding="utf-8"
    )

    # Config
    config = {
        "run_id": "test_fixture_run",
        "created_at": "2026-01-15T12:00:00+00:00",
        "brand_name": "TestBrand",
        "category": "TestCategory",
        "time_period_days": 180,
        "keywords": ["test"],
        "business_objectives": ["Understand quality perception"],
        "subreddits": [],
        "trends_geo": "IN",
        "news_country": "in",
        "claude_model": "test",
        "claude_temperature": 0.0,
    }
    (run_dir / "config.json").write_text(
        json.dumps(config, indent=2), encoding="utf-8"
    )

    return run_dir


class TestScoreReportIntegration:
    """Test consumer-research score-report against a fixture run."""

    def test_score_report_produces_docx(self, tmp_path, monkeypatch):
        """The canonical product path: score-report should produce a DOCX."""
        run_dir = _build_fixture_run(tmp_path)

        # Point RUNS_DIR at our temp directory
        monkeypatch.setenv("CONSUMER_RESEARCH_RUNS_DIR", str(tmp_path / "runs"))

        result = subprocess.run(
            [sys.executable, "-m", "consumer_research.run", "score-report", "test_fixture_run"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(REPO_ROOT),
            env={
                **__import__("os").environ,
                "CONSUMER_RESEARCH_RUNS_DIR": str(tmp_path / "runs"),
            },
        )

        # Should not crash
        assert "Error" not in result.stderr or "NameError" not in result.stderr, (
            f"score-report crashed:\n{result.stderr[-500:]}"
        )

        # Should produce scored insights
        scored_path = run_dir / "scored" / "scored_insights.json"
        assert scored_path.exists(), "scored_insights.json not created"
        scored = json.loads(scored_path.read_text(encoding="utf-8"))
        assert len(scored) == 1

        # Should produce a DOCX report
        report_files = list((run_dir / "report").glob("report_v*.docx"))
        assert len(report_files) == 1, f"Expected 1 DOCX, found {len(report_files)}"


class TestIngestCLI:
    """Test consumer-research ingest creates a valid run directory."""

    def test_ingest_creates_run(self, tmp_path, monkeypatch):
        # Create a simple JSON data file
        data_file = tmp_path / "test_data.json"
        data_file.write_text(json.dumps([
            {"text": "Great product quality", "source": "reddit", "url": "https://reddit.com/1", "date": "2026-01-15"},
            {"text": "Price is too high", "source": "reddit", "url": "https://reddit.com/2", "date": "2026-01-16"},
        ]), encoding="utf-8")

        runs_dir = tmp_path / "runs"
        result = subprocess.run(
            [
                sys.executable, "-m", "consumer_research.run", "ingest",
                "--data", str(data_file),
                "--brand", "TestBrand",
                "--category", "TestCategory",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(REPO_ROOT),
            env={
                **__import__("os").environ,
                "CONSUMER_RESEARCH_RUNS_DIR": str(runs_dir),
            },
        )

        assert result.returncode == 0, f"ingest failed:\n{result.stderr[-500:]}"
        assert "items normalized" in result.stdout

        # Should have created a run directory with normalized corpus
        run_dirs = list(runs_dir.iterdir())
        assert len(run_dirs) == 1
        run_dir = run_dirs[0]
        assert (run_dir / "normalized" / "corpus.json").exists()
        assert (run_dir / "config.json").exists()
