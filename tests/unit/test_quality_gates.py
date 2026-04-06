"""Unit tests for quality gate enforcement in pipeline/synthesize.py.

These tests verify that insights failing quality gates are excluded from the
returned list, not just logged. No LLM calls — uses a mock LLM client.
"""
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from consumer_research.models.schemas import (
    AnalysisResults,
    ContentType,
    Emotion,
    Insight,
    NormalizedItem,
    PlatformMetadata,
    Sentiment,
    SentimentResult,
    SourcePlatform,
    Theme,
    VerbatimQuote,
)
from consumer_research.pipeline.synthesize import synthesize_insights


def _make_theme(theme_id: str, label: str, item_ids: list[str]) -> Theme:
    return Theme(
        theme_id=theme_id,
        theme_label=label,
        theme_description=f"Description for {label}",
        supporting_item_ids=item_ids,
        item_count=len(item_ids),
        prevalence_pct=round(len(item_ids) / 100 * 100, 1),
        sentiment_distribution={"positive": 5, "negative": 2, "neutral": 3},
        is_multi_source=True,
        platforms_present=[SourcePlatform.REDDIT],
        representative_quotes=[],
    )


def _make_item(item_id: str) -> NormalizedItem:
    return NormalizedItem(
        item_id=item_id,
        source_platform=SourcePlatform.REDDIT,
        source_url=f"https://reddit.com/{item_id}",
        collected_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        content_text=f"Text for item {item_id}",
        content_type=ContentType.POST,
        collection_query="test",
        collection_method="test",
    )


def _make_analysis(themes: list[Theme]) -> AnalysisResults:
    return AnalysisResults(
        sentiment_results=[],
        themes=themes,
        overall_sentiment={"positive": 5, "negative": 2, "neutral": 3},
        net_sentiment_score=0.3,
        total_items_analyzed=10,
        analysis_model="test",
        analysis_prompts={"sentiment": "test prompt"},
    )


def _mock_llm(insights_data: list[dict]) -> MagicMock:
    """Return a mock LLM that returns the given insights as JSON."""
    client = MagicMock()
    client.generate.return_value = json.dumps(insights_data)
    return client


# ── Core quality gate enforcement ─────────────────────────────────────────────

class TestQualityGateEnforcement:
    def test_all_passing_insights_returned(self, tmp_path):
        themes = [_make_theme("THM_001", "Quality", [f"i{j}" for j in range(5)])]
        items = [_make_item(f"i{j}") for j in range(5)]
        analysis = _make_analysis(themes)

        llm = _mock_llm([{
            "insight_id": "INS_001",
            "source_theme_id": "THM_001",
            "observation": "Quality is mentioned in 40% of posts",
            "insight": "Consumers equate consistency with trust",
            "implication": "Quality gaps erode repeat purchase intent",
            "recommendation": "Publish batch-level QC reports quarterly",
            "further_validation": "Panel study across 6 months",
            "is_grounded": True,
            "is_non_obvious": True,
            "is_actionable": True,
            "is_specific": True,
            "is_falsifiable": True,
        }])

        result = synthesize_insights(analysis, items, "TestBrand", "FMCG", [], tmp_path, llm)
        assert len(result) == 1
        assert result[0].insight_id == "INS_001"

    def test_failed_gate_insight_excluded(self, tmp_path):
        themes = [_make_theme("THM_001", "Quality", [f"i{j}" for j in range(5)])]
        items = [_make_item(f"i{j}") for j in range(5)]
        analysis = _make_analysis(themes)

        # is_grounded = False means this insight should be filtered out
        llm = _mock_llm([{
            "insight_id": "INS_001",
            "source_theme_id": "THM_001",
            "observation": "Something",
            "insight": "Something",
            "implication": "Something",
            "recommendation": "Something",
            "further_validation": "Something",
            "is_grounded": False,
            "is_non_obvious": True,
            "is_actionable": True,
            "is_specific": True,
            "is_falsifiable": True,
        }])

        result = synthesize_insights(analysis, items, "TestBrand", "FMCG", [], tmp_path, llm)
        assert len(result) == 0

    def test_mixed_pass_fail_only_passing_returned(self, tmp_path):
        themes = [
            _make_theme("THM_001", "Quality", [f"i{j}" for j in range(5)]),
            _make_theme("THM_002", "Price", [f"p{j}" for j in range(5)]),
        ]
        items = [_make_item(f"i{j}") for j in range(5)] + [_make_item(f"p{j}") for j in range(5)]
        analysis = _make_analysis(themes)

        llm = _mock_llm([
            {
                "insight_id": "INS_001",
                "source_theme_id": "THM_001",
                "observation": "Quality observation",
                "insight": "Quality insight",
                "implication": "Quality implication",
                "recommendation": "Quality recommendation",
                "further_validation": "Quality validation",
                "is_grounded": True,
                "is_non_obvious": True,
                "is_actionable": True,
                "is_specific": True,
                "is_falsifiable": True,
            },
            {
                "insight_id": "INS_002",
                "source_theme_id": "THM_002",
                "observation": "Price observation",
                "insight": "Price insight",
                "implication": "Price implication",
                "recommendation": "Price recommendation",
                "further_validation": "Price validation",
                "is_grounded": True,
                "is_non_obvious": False,  # FAILS
                "is_actionable": False,   # FAILS
                "is_specific": True,
                "is_falsifiable": True,
            },
        ])

        result = synthesize_insights(analysis, items, "TestBrand", "FMCG", [], tmp_path, llm)
        assert len(result) == 1
        assert result[0].insight_id == "INS_001"

    def test_all_failing_returns_empty(self, tmp_path):
        themes = [_make_theme("THM_001", "Quality", [f"i{j}" for j in range(5)])]
        items = [_make_item(f"i{j}") for j in range(5)]
        analysis = _make_analysis(themes)

        llm = _mock_llm([{
            "insight_id": "INS_001",
            "source_theme_id": "THM_001",
            "observation": "Something",
            "insight": "Something",
            "implication": "Something",
            "recommendation": "Something",
            "further_validation": "Something",
            "is_grounded": False,
            "is_non_obvious": False,
            "is_actionable": False,
            "is_specific": False,
            "is_falsifiable": False,
        }])

        result = synthesize_insights(analysis, items, "TestBrand", "FMCG", [], tmp_path, llm)
        assert result == []

    def test_llm_error_returns_empty(self, tmp_path):
        themes = [_make_theme("THM_001", "Quality", [f"i{j}" for j in range(5)])]
        items = [_make_item(f"i{j}") for j in range(5)]
        analysis = _make_analysis(themes)

        llm = MagicMock()
        llm.generate.side_effect = RuntimeError("API unavailable")

        result = synthesize_insights(analysis, items, "TestBrand", "FMCG", [], tmp_path, llm)
        assert result == []

    def test_insights_json_written_includes_failed(self, tmp_path):
        """insights.json must include ALL insights (for audit), not just passed ones."""
        themes = [
            _make_theme("THM_001", "Quality", [f"i{j}" for j in range(5)]),
            _make_theme("THM_002", "Price", [f"p{j}" for j in range(5)]),
        ]
        items = [_make_item(f"i{j}") for j in range(5)] + [_make_item(f"p{j}") for j in range(5)]
        analysis = _make_analysis(themes)

        llm = _mock_llm([
            {
                "insight_id": "INS_001",
                "source_theme_id": "THM_001",
                "observation": "...", "insight": "...", "implication": "...",
                "recommendation": "...", "further_validation": "...",
                "is_grounded": True, "is_non_obvious": True,
                "is_actionable": True, "is_specific": True, "is_falsifiable": True,
            },
            {
                "insight_id": "INS_002",
                "source_theme_id": "THM_002",
                "observation": "...", "insight": "...", "implication": "...",
                "recommendation": "...", "further_validation": "...",
                "is_grounded": False, "is_non_obvious": True,
                "is_actionable": True, "is_specific": True, "is_falsifiable": True,
            },
        ])

        synthesize_insights(analysis, items, "TestBrand", "FMCG", [], tmp_path, llm)
        saved = json.loads((tmp_path / "insights" / "insights.json").read_text())
        # Both must be in the file (one passed, one failed)
        assert len(saved) == 2
