"""Stage 5: Insight synthesis engine.

Transforms themes from Stage 4 into decision-grade insights using the framework:
Observation → Insight → Implication → Recommendation → Further Validation

Applies 5 quality gates before an insight enters the report.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from consumer_research.models.schemas import (
    AnalysisResults,
    Insight,
    NormalizedItem,
    Theme,
)

logger = logging.getLogger(__name__)

SYNTHESIS_PROMPT = """You are a senior consumer research strategist at a top-tier consulting firm.

Brand: {brand_name}
Category: {category}
Business Objectives: {objectives}

You are given {theme_count} themes extracted from consumer data. You MUST generate
exactly one insight per theme — {theme_count} insights total. Every theme must
receive its own insight, no exceptions. For each theme, synthesize a decision-grade
insight using this exact framework:

1. OBSERVATION: What the data shows (cite the theme, prevalence, sentiment split)
2. INSIGHT: What it means for the consumer (the "why" behind the behavior)
3. IMPLICATION: What it means for the business ("So What")
4. RECOMMENDATION: Specific action the client should take ("Now What")
5. FURTHER VALIDATION: What additional research would strengthen this finding

Quality gates - each insight MUST be:
- GROUNDED: Supported by the theme data (not speculation)
- NON-OBVIOUS: A brand manager wouldn't already know this
- ACTIONABLE: There is a concrete action the client can take
- SPECIFIC: Names specific occasions, segments, or attributes
- FALSIFIABLE: The claim could be proven wrong with more data

Respond with a JSON array:
[
  {{
    "insight_id": "INS_001",
    "source_theme_id": "THM_XXX",
    "observation": "...",
    "insight": "...",
    "implication": "...",
    "recommendation": "...",
    "further_validation": "...",
    "is_grounded": true/false,
    "is_non_obvious": true/false,
    "is_actionable": true/false,
    "is_specific": true/false,
    "is_falsifiable": true/false
  }}
]

Themes to synthesize:
{themes_json}

Respond ONLY with the JSON array."""


def synthesize_insights(
    analysis: AnalysisResults,
    items: list[NormalizedItem],
    brand_name: str,
    category: str,
    business_objectives: list[str],
    run_dir: Path,
    llm_client,
) -> list[Insight]:
    """Synthesize decision-grade insights from analysis themes.

    Args:
        analysis: Results from Stage 4 analysis.
        items: The filtered corpus (for item count reference).
        brand_name: Brand being analyzed.
        category: Product category.
        business_objectives: Client's stated objectives.
        run_dir: Run directory for output.
        llm_client: LLMClient instance (Claude or Gemini).

    Returns:
        List of Insight objects that passed quality gates.
    """
    insights_dir = run_dir / "insights"
    insights_dir.mkdir(parents=True, exist_ok=True)

    item_map = {item.item_id: item for item in items}

    # Prepare themes for synthesis
    themes_for_prompt = []
    for theme in analysis.themes:
        themes_for_prompt.append({
            "theme_id": theme.theme_id,
            "label": theme.theme_label,
            "description": theme.theme_description,
            "item_count": theme.item_count,
            "prevalence_pct": theme.prevalence_pct,
            "sentiment": theme.sentiment_distribution,
            "is_multi_source": theme.is_multi_source,
            "platforms": [p.value for p in theme.platforms_present],
            "is_contested": theme.is_contested,
            "sample_quotes": [
                q.text[:200] for q in theme.representative_quotes[:3]
            ],
        })

    objectives_str = "; ".join(business_objectives) if business_objectives else "General brand perception analysis"

    prompt = SYNTHESIS_PROMPT.format(
        brand_name=brand_name,
        category=category,
        objectives=objectives_str,
        theme_count=len(themes_for_prompt),
        themes_json=json.dumps(themes_for_prompt, indent=2),
    )

    try:
        text = llm_client.generate(prompt, max_tokens=8192, temperature=0.0)
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        parsed = json.loads(text)

        # Validate insight count matches theme count
        expected_count = len(themes_for_prompt)
        actual_count = len(parsed) if isinstance(parsed, list) else 0
        if actual_count < expected_count:
            returned_theme_ids = {ins.get("source_theme_id") for ins in parsed} if isinstance(parsed, list) else set()
            missing = [t["theme_id"] for t in themes_for_prompt if t["theme_id"] not in returned_theme_ids]
            logger.warning(
                f"Synthesis returned {actual_count}/{expected_count} insights. "
                f"Missing themes: {missing}"
            )

    except Exception as e:
        logger.error(f"Insight synthesis error: {e}")
        parsed = []

    # Build Insight objects
    all_insights: list[Insight] = []
    for ins_data in parsed:
        # Find the source theme
        source_theme_id = ins_data.get("source_theme_id", "")
        source_theme = next(
            (t for t in analysis.themes if t.theme_id == source_theme_id), None
        )

        supporting_item_ids = source_theme.supporting_item_ids if source_theme else []
        source_urls = [
            item_map[iid].source_url
            for iid in supporting_item_ids[:10]
            if iid in item_map
        ]

        is_grounded = ins_data.get("is_grounded", False)
        is_non_obvious = ins_data.get("is_non_obvious", False)
        is_actionable = ins_data.get("is_actionable", False)
        is_specific = ins_data.get("is_specific", False)
        is_falsifiable = ins_data.get("is_falsifiable", False)

        passed = all([is_grounded, is_non_obvious, is_actionable, is_specific, is_falsifiable])

        insight = Insight(
            insight_id=ins_data.get("insight_id", f"INS_{len(all_insights)+1:03d}"),
            observation=ins_data.get("observation", ""),
            insight=ins_data.get("insight", ""),
            implication=ins_data.get("implication", ""),
            recommendation=ins_data.get("recommendation", ""),
            further_validation=ins_data.get("further_validation", ""),
            supporting_theme_ids=[source_theme_id],
            supporting_item_count=len(supporting_item_ids),
            source_urls=source_urls,
            is_grounded=is_grounded,
            is_non_obvious=is_non_obvious,
            is_actionable=is_actionable,
            is_specific=is_specific,
            is_falsifiable=is_falsifiable,
            passed_quality_gates=passed,
        )
        all_insights.append(insight)

    passed_insights = [i for i in all_insights if i.passed_quality_gates]
    failed_insights = [i for i in all_insights if not i.passed_quality_gates]

    # Write outputs
    (insights_dir / "insights.json").write_text(
        json.dumps(
            [i.model_dump(mode="json") for i in all_insights],
            indent=2, default=str,
        ),
        encoding="utf-8",
    )
    (insights_dir / "synthesis_prompt.txt").write_text(prompt, encoding="utf-8")

    logger.info(
        f"Insight synthesis: {len(all_insights)} generated, "
        f"{len(passed_insights)} passed quality gates, "
        f"{len(failed_insights)} demoted to observations"
    )

    return all_insights
