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
