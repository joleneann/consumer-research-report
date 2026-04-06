"""Validation gates for the pipeline.

These checks enforce quality standards between pipeline stages.
They are called automatically in the orchestrator and can be called
manually in scripts and in-context analysis workflows.
"""
from __future__ import annotations

import logging
from consumer_research.models.schemas import AnalysisResults, NormalizedItem

logger = logging.getLogger(__name__)


def validate_theme_coverage(
    analysis: AnalysisResults,
    items: list[NormalizedItem],
    max_unthemed_pct: float = 0.10,
    raise_on_fail: bool = False,
) -> dict:
    """Check that theme coverage meets the minimum threshold.

    This enforces Procedure 15 (narrative review pass). After keyword-based
    theme extraction, the pipeline must NOT proceed to synthesis if >10%
    of items remain unthemed.

    Returns:
        dict with keys: passed (bool), themed_count, unthemed_count,
        themed_pct, unthemed_pct, total_items, threshold
    """
    themed_ids = set()
    for theme in analysis.themes:
        themed_ids.update(theme.supporting_item_ids)

    total = len(items)
    themed = len(themed_ids)
    unthemed = total - themed
    themed_pct = themed / total if total > 0 else 0.0
    unthemed_pct = unthemed / total if total > 0 else 0.0
    passed = unthemed_pct <= max_unthemed_pct

    result = {
        "passed": passed,
        "themed_count": themed,
        "unthemed_count": unthemed,
        "themed_pct": round(themed_pct, 4),
        "unthemed_pct": round(unthemed_pct, 4),
        "total_items": total,
        "threshold": max_unthemed_pct,
    }

    if passed:
        logger.info(
            f"Theme coverage PASSED: {themed_pct:.1%} themed "
            f"({themed}/{total}), {unthemed_pct:.1%} unthemed"
        )
    else:
        msg = (
            f"Theme coverage FAILED: {unthemed_pct:.1%} unthemed "
            f"({unthemed}/{total}), threshold is {max_unthemed_pct:.0%}. "
            f"Run narrative review pass (Procedure 15) before proceeding to synthesis."
        )
        logger.warning(msg)
        if raise_on_fail:
            raise ValueError(msg)

    return result


def select_methodology(corpus_size: int, methodology: str = "auto", threshold: int = 1000) -> str:
    """Select analysis methodology based on corpus size.

    CRITICAL: Neither mode uses external API calls. All analysis is performed
    by the Claude Code session itself (the model running this conversation).

    Args:
        corpus_size: Number of items in the filtered corpus
        methodology: "auto", "in_context_full", or "keyword_narrative"
        threshold: Items below this get full in-context read; above get keyword + narrative

    Returns:
        "in_context_full" or "keyword_narrative"

    Small corpus (<=1000 items) -> "in_context_full":
        Session LLM reads every item directly. Classifies sentiment, emotion,
        aspects, and themes by actually understanding the text. Highest quality.
        No API calls - the Claude Code session IS the analysis engine.

    Large corpus (>1000 items) -> "keyword_narrative":
        Keyword-based classification for initial sentiment/themes (fast, covers
        vocabulary-level patterns). Then MANDATORY narrative review pass where
        the session LLM reads unthemed items and themed samples to catch patterns
        keywords miss (cultural references, sarcasm, memes, emotional narratives).
        Narrative pass is enforced by validation gate - pipeline blocks if >10% unthemed.
    """
    if methodology == "in_context_full":
        logger.info(f"Methodology: in-context full read (forced via config). Session LLM reads every item.")
        return "in_context_full"
    elif methodology == "keyword_narrative":
        logger.info(f"Methodology: keyword + narrative (forced via config). Narrative pass MANDATORY.")
        return "keyword_narrative"
    else:  # auto
        if corpus_size <= threshold:
            logger.info(
                f"Methodology: in-context full read (auto-selected, corpus {corpus_size} <= threshold {threshold}). "
                f"Session LLM will read and classify every item."
            )
            return "in_context_full"
        else:
            logger.info(
                f"Methodology: keyword + narrative (auto-selected, corpus {corpus_size} > threshold {threshold}). "
                f"Keyword pass first, then session LLM reads unthemed items (Procedure 15 MANDATORY)."
            )
            return "keyword_narrative"
