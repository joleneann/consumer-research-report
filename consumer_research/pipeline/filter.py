"""Stage 3: Relevance filtering using Claude API.

Classifies each item in the normalized corpus as relevant or irrelevant
to the brand perception analysis. Stores rejection reasons for auditability.
Uses temperature=0 for deterministic, reproducible results.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from consumer_research.models.schemas import NormalizedItem, RelevanceClassification

logger = logging.getLogger(__name__)

FILTER_PROMPT_TEMPLATE = """You are a consumer research relevance classifier.

Brand: {brand_name}
Category: {category}

Evaluate whether each of the following items contains genuine consumer perception,
opinion, experience, or discussion about {brand_name}.

IMPORTANT: Content may be in English, Hindi, Hinglish (Hindi-English mix), or other
regional languages. Treat ALL languages equally. A Hindi comment expressing an opinion
about {brand_name} is just as relevant as an English one.

An item is RELEVANT if it:
- Expresses a consumer opinion about {brand_name} (in any language)
- Describes a personal experience with {brand_name}
- Compares {brand_name} to competitors
- Discusses {brand_name}'s attributes (taste, packaging, price, availability, etc.)
- Mentions {brand_name} in the context of purchase decisions or consumption occasions
- Contains consumer humor, memes, or cultural references about {brand_name}

An item is IRRELEVANT if it:
- Only mentions {brand_name} in passing without any opinion or experience
- Is a bot-generated message, spam, or promotional content
- Is about a completely different product/brand that happens to share keywords
- Is a meta-discussion about the subreddit/platform itself
- Contains no substantive consumer perspective

For each item, respond with a JSON array of objects:
[
  {{
    "item_id": "<item_id>",
    "relevant": true/false,
    "confidence": 0.0-1.0,
    "reason": "One sentence explaining why",
    "relevance_type": "direct_mention|comparison|category_discussion|unrelated",
    "language": "en|hi|hinglish|other"
  }}
]

Items to classify:
{items_json}

Respond ONLY with the JSON array, no other text."""


def filter_corpus(
    items: list[NormalizedItem],
    brand_name: str,
    category: str,
    run_dir: Path,
    llm_client,
    batch_size: int = 15,
) -> list[NormalizedItem]:
    """Filter corpus items for relevance using LLM.

    Args:
        items: The normalized corpus to filter.
        brand_name: Brand being analyzed.
        category: Product category.
        run_dir: Run directory for output files.
        llm_client: LLMClient instance (Claude or Gemini).
        batch_size: Items per API call.

    Returns:
        List of items that passed relevance filtering.
    """
    filtered_dir = run_dir / "filtered"
    filtered_dir.mkdir(parents=True, exist_ok=True)

    prompt_template = FILTER_PROMPT_TEMPLATE.format(
        brand_name=brand_name,
        category=category,
        items_json="{items_json}",  # placeholder for batch
    )

    all_classifications: list[RelevanceClassification] = []
    relevant_items: list[NormalizedItem] = []
    rejected_items: list[dict] = []

    # Process in batches
    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        batch_json = json.dumps(
            [
                {
                    "item_id": item.item_id,
                    "source_platform": item.source_platform.value,
                    "content_text": item.content_text[:500],  # Truncate for cost
                    "source_url": item.source_url,
                }
                for item in batch
            ],
            indent=2,
        )

        prompt = FILTER_PROMPT_TEMPLATE.format(
            brand_name=brand_name,
            category=category,
            items_json=batch_json,
        )

        try:
            response_text = llm_client.generate(prompt, max_tokens=4096, temperature=0.0)

            # Parse JSON response - handle potential markdown wrapping
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]

            classifications = json.loads(response_text)

            # Map results back to items
            item_map = {item.item_id: item for item in batch}

            # Check for incomplete LLM response — keep missing items (conservative)
            returned_ids = {c.get("item_id") for c in classifications}
            missing_ids = set(item_map.keys()) - returned_ids
            if missing_ids:
                logger.warning(
                    f"  Filter batch: LLM returned {len(classifications)}/{len(batch)} items. "
                    f"Keeping {len(missing_ids)} missing items as relevant (conservative)."
                )
                for mid in missing_ids:
                    relevant_items.append(item_map[mid])

            for cls_data in classifications:
                cls = RelevanceClassification(**cls_data)
                all_classifications.append(cls)

                if cls.relevant and cls.item_id in item_map:
                    relevant_items.append(item_map[cls.item_id])
                elif cls.item_id in item_map:
                    rejected_items.append(
                        {
                            "item_id": cls.item_id,
                            "reason": cls.reason,
                            "confidence": cls.confidence,
                            "relevance_type": cls.relevance_type,
                            "source_url": item_map[cls.item_id].source_url,
                            "text_preview": item_map[cls.item_id].content_text[:200],
                        }
                    )

            logger.info(
                f"  Filtered batch {i // batch_size + 1}: "
                f"{sum(1 for c in classifications if c.get('relevant'))} relevant / "
                f"{len(classifications)} total"
            )

        except Exception as e:
            logger.error(f"  Filter batch error: {e}. Keeping all items in batch.")
            relevant_items.extend(batch)

    # Write outputs
    corpus_data = [item.model_dump(mode="json") for item in relevant_items]
    (filtered_dir / "corpus.json").write_text(
        json.dumps(corpus_data, indent=2, default=str), encoding="utf-8"
    )

    (filtered_dir / "rejected.json").write_text(
        json.dumps(rejected_items, indent=2, default=str), encoding="utf-8"
    )

    # Store the prompt template for reproducibility
    (filtered_dir / "filter_prompt.txt").write_text(
        FILTER_PROMPT_TEMPLATE.format(
            brand_name=brand_name,
            category=category,
            items_json="[... items ...]",
        ),
        encoding="utf-8",
    )

    logger.info(
        f"Filtering complete: {len(items)} → {len(relevant_items)} relevant "
        f"({len(rejected_items)} rejected)"
    )

    return relevant_items
