"""Stage 0: User Briefing — structured research brief before any data collection.

The brief captures what the user wants to analyze and drives keyword generation.
No collection happens until the brief is confirmed.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ResearchBrief:
    """Structured research brief that drives the entire pipeline."""
    brand_name: str
    category: str
    business_questions: list[str] = field(default_factory=list)
    aspects: list[str] = field(default_factory=list)  # e.g., perception, occasions, competitive, pricing, quality
    target_audience: str = ""
    competitors: list[str] = field(default_factory=list)
    geographic_focus: str = ""
    time_period_months: int = 12
    additional_context: str = ""

    def to_dict(self) -> dict:
        return {
            "brand_name": self.brand_name,
            "category": self.category,
            "business_questions": self.business_questions,
            "aspects": self.aspects,
            "target_audience": self.target_audience,
            "competitors": self.competitors,
            "geographic_focus": self.geographic_focus,
            "time_period_months": self.time_period_months,
            "additional_context": self.additional_context,
        }

    def save(self, run_dir: Path) -> None:
        path = run_dir / "brief.json"
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        logger.info(f"Brief saved to {path}")

    @classmethod
    def load(cls, run_dir: Path) -> "ResearchBrief":
        path = run_dir / "brief.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(**data)


def create_brief_interactive() -> ResearchBrief:
    """Create a research brief via interactive prompts (for CLI use)."""
    print("\n=== RESEARCH BRIEF ===\n")

    brand = input("Brand/product name: ").strip()
    category = input("Product category: ").strip()

    print("\nBusiness questions (what do you want to know? Enter one per line, empty to finish):")
    questions = []
    while True:
        q = input("  > ").strip()
        if not q:
            break
        questions.append(q)

    print("\nAspects to analyze (comma-separated, e.g., perception, occasions, competitive, pricing, quality):")
    aspects_input = input("  > ").strip()
    aspects = [a.strip() for a in aspects_input.split(",") if a.strip()] if aspects_input else []

    target = input("\nTarget audience (e.g., 'Indian millennials', 'urban consumers 18-35'): ").strip()

    print("\nCompetitors to compare against (comma-separated):")
    comp_input = input("  > ").strip()
    competitors = [c.strip() for c in comp_input.split(",") if c.strip()] if comp_input else []

    geo = input("\nGeographic focus (e.g., 'India', 'IN', 'Mumbai'): ").strip()

    period_input = input("\nTime period in months (default 12): ").strip()
    period = int(period_input) if period_input.isdigit() else 12

    context = input("\nAny additional context? ").strip()

    brief = ResearchBrief(
        brand_name=brand,
        category=category,
        business_questions=questions,
        aspects=aspects,
        target_audience=target,
        competitors=competitors,
        geographic_focus=geo,
        time_period_months=period,
        additional_context=context,
    )

    print(f"\n--- BRIEF SUMMARY ---")
    print(f"Brand: {brief.brand_name} ({brief.category})")
    print(f"Questions: {len(brief.business_questions)}")
    print(f"Aspects: {', '.join(brief.aspects) if brief.aspects else 'all'}")
    print(f"Competitors: {', '.join(brief.competitors) if brief.competitors else 'none specified'}")
    print(f"Geo: {brief.geographic_focus or 'global'}")
    print(f"Period: {brief.time_period_months} months")

    return brief


def create_brief_from_args(
    brand_name: str,
    category: str,
    keywords: list[str] | None = None,
    objectives: list[str] | None = None,
    competitors: list[str] | None = None,
    geo: str = "",
    aspects: list[str] | None = None,
) -> ResearchBrief:
    """Create a brief from CLI arguments (non-interactive)."""
    return ResearchBrief(
        brand_name=brand_name,
        category=category,
        business_questions=objectives or [],
        aspects=aspects or ["perception", "occasions", "competitive", "quality"],
        competitors=competitors or [],
        geographic_focus=geo,
        additional_context=f"Additional keywords: {', '.join(keywords)}" if keywords else "",
    )
