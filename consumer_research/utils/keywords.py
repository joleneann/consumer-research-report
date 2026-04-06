"""Keyword expansion from research brief.

Generates comprehensive keyword lists from a structured brief including:
- Brand name variants and misspellings
- Category terms
- Competitor comparison terms
- Occasion/usage terms
- Hindi/regional language equivalents
- Negative/complaint terms
- Attribute-specific terms
"""

from __future__ import annotations

import logging
from consumer_research.pipeline.brief import ResearchBrief

logger = logging.getLogger(__name__)


def expand_keywords(brief: ResearchBrief, llm_client=None) -> dict[str, list[str]]:
    """Generate expanded keyword lists from a research brief.

    Args:
        brief: The research brief driving the analysis.
        llm_client: Optional LLM client for intelligent expansion.

    Returns:
        Dict with keyword categories mapped to keyword lists.
    """
    keywords: dict[str, list[str]] = {
        "brand_variants": [],
        "category": [],
        "competitors": [],
        "occasions": [],
        "regional_language": [],
        "complaints": [],
        "attributes": [],
    }

    brand = brief.brand_name

    # Brand variants - common misspellings and alternate forms
    keywords["brand_variants"] = _generate_brand_variants(brand)

    # Category terms
    keywords["category"] = _generate_category_terms(brand, brief.category)

    # Competitor comparisons
    if brief.competitors:
        keywords["competitors"] = [
            f"{brand} vs {comp}" for comp in brief.competitors
        ] + [
            f"{brand} or {comp}" for comp in brief.competitors
        ] + [
            f"{comp} better than {brand}" for comp in brief.competitors
        ]

    # Occasion terms
    keywords["occasions"] = _generate_occasion_terms(brand, brief.category, brief.aspects)

    # Regional language (Hindi/Hinglish for Indian brands)
    if brief.geographic_focus.upper() in ("IN", "INDIA"):
        keywords["regional_language"] = _generate_hindi_terms(brand, brief.category)

    # Complaint/negative terms
    keywords["complaints"] = [
        f"{brand} problem",
        f"{brand} complaint",
        f"{brand} bad",
        f"{brand} quality issue",
        f"{brand} disappointed",
        f"{brand} worst",
        f"{brand} not good",
    ]

    # Attribute-specific from brief aspects
    if brief.aspects:
        keywords["attributes"] = [
            f"{brand} {aspect}" for aspect in brief.aspects
        ]

    # If LLM client available, do intelligent expansion
    if llm_client:
        keywords = _llm_expand(keywords, brief, llm_client)

    # Flatten for collection use
    all_keywords = []
    for category_keywords in keywords.values():
        all_keywords.extend(category_keywords)

    # Deduplicate preserving order
    seen = set()
    unique = []
    for kw in all_keywords:
        kw_lower = kw.lower()
        if kw_lower not in seen:
            seen.add(kw_lower)
            unique.append(kw)

    total = len(unique)
    logger.info(f"Keyword expansion: {total} unique keywords generated from brief")
    for cat, kws in keywords.items():
        if kws:
            logger.info(f"  {cat}: {len(kws)} keywords")

    return keywords


def get_flat_keywords(brief: ResearchBrief, llm_client=None) -> list[str]:
    """Get a flat deduplicated list of all keywords."""
    expanded = expand_keywords(brief, llm_client)
    all_kw = []
    for kws in expanded.values():
        all_kw.extend(kws)
    seen = set()
    return [k for k in all_kw if k.lower() not in seen and not seen.add(k.lower())]


def _generate_brand_variants(brand: str) -> list[str]:
    """Generate common misspellings and variants of the brand name."""
    variants = [brand]
    lower = brand.lower()

    # Common patterns
    variants.append(brand.replace(" ", ""))  # "Thums Up" -> "ThumsUp"
    variants.append(brand.replace(" ", "-"))  # "Thums Up" -> "Thums-Up"

    # Known misspelling patterns
    if "thums" in lower:
        variants.extend([
            "Thumbs Up", "Thumps Up", "Thumsup", "Thumbsup",
            "Thums up", "thumbs up cola", "thums up cola",
        ])
    elif "coca" in lower or "coke" in lower:
        variants.extend(["Coca Cola", "CocaCola", "Coke", "coca-cola"])
    elif "pepsi" in lower:
        variants.extend(["Pepsi Cola", "pepsi cola"])

    return sorted(set(variants))


def _generate_category_terms(brand: str, category: str) -> list[str]:
    """Generate category-level search terms.

    IMPORTANT: Every term MUST include the brand name to prevent
    collectors from returning irrelevant category-level content.
    Queries like "best cola" or "soda review" without the brand name
    return generic content that pollutes the corpus.
    """
    terms = [
        f"{brand} best {category}",
        f"{brand} {category} review",
        f"{brand} {category} comparison",
        f"favorite {category} {brand}",
        f"{brand} {category} ranking",
    ]

    # Category-specific terms - ALL brand-anchored
    cat_lower = category.lower()
    if "beverage" in cat_lower or "cola" in cat_lower or "drink" in cat_lower:
        terms.extend([
            f"{brand} best cola",
            f"{brand} cola taste test",
            f"{brand} soft drink",
        ])
    elif "cosmetic" in cat_lower or "beauty" in cat_lower:
        terms.extend([
            f"{brand} {category} india",
            f"{brand} honest review",
            f"{brand} worth it",
        ])
    elif "food" in cat_lower or "snack" in cat_lower or "biscuit" in cat_lower:
        terms.extend([
            f"{brand} {category} india",
            f"{brand} taste test",
            f"{brand} honest review",
        ])

    return terms


def _generate_occasion_terms(brand: str, category: str, aspects: list[str]) -> list[str]:
    """Generate occasion and usage context terms."""
    terms = [
        f"{brand} with food",
        f"{brand} when to use",
        f"when do you drink {brand}" if "beverage" in category.lower() else f"when do you use {brand}",
    ]

    cat_lower = category.lower()
    if "beverage" in cat_lower or "cola" in cat_lower or "drink" in cat_lower:
        terms.extend([
            f"{brand} with biryani",
            f"{brand} with meals",
            f"{brand} party",
            f"{brand} summer",
            f"{brand} mixer",
            f"{brand} refreshing",
        ])

    return terms


def _generate_hindi_terms(brand: str, category: str) -> list[str]:
    """Generate Hindi/Hinglish search terms for Indian brands."""
    terms = []
    lower = brand.lower()

    if "thums" in lower:
        terms.extend([
            "थम्स अप", "थम्स अप vs कोक", "थम्स अप स्वाद",
            "thums up kaisa hai", "thums up peena",
            "thums up biryani ke saath",
            "thums up sabse accha cola", "thums up india",
        ])
    else:
        terms.extend([
            f"{brand} kaisa hai",
            f"{brand} review hindi",
            f"best {category} india hindi",
        ])

    return terms


def _llm_expand(
    keywords: dict[str, list[str]],
    brief: ResearchBrief,
    llm_client,
) -> dict[str, list[str]]:
    """Use LLM to intelligently expand keywords based on the brief."""
    import json

    prompt = f"""You are a consumer research keyword strategist.

Brand: {brief.brand_name}
Category: {brief.category}
Geographic focus: {brief.geographic_focus}
Business questions: {'; '.join(brief.business_questions)}
Competitors: {', '.join(brief.competitors)}
Aspects: {', '.join(brief.aspects)}

I already have these keywords:
{json.dumps(keywords, indent=2)}

Generate 10-15 ADDITIONAL keywords I'm missing. Focus on:
- Consumer pain points and complaints specific to this brand
- Cultural/regional usage patterns
- Seasonal or event-driven consumption
- Social media slang or memes about this brand
- Comparison terms consumers actually use

Respond with JSON only:
{{"additional_keywords": ["kw1", "kw2", ...]}}"""

    try:
        text = llm_client.generate(prompt, max_tokens=1024, temperature=0.3)
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        parsed = json.loads(text)
        additional = parsed.get("additional_keywords", [])
        keywords["llm_expanded"] = additional
        logger.info(f"  LLM expanded: {len(additional)} additional keywords")
    except Exception as e:
        logger.warning(f"LLM keyword expansion failed: {e}")

    return keywords
