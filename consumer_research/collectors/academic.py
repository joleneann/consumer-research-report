"""Academic paper collector using OpenAlex API.

Searches for peer-reviewed papers related to the brand/category.
Provides an authoritative evidence layer for cross-validation.

Free, no API key required. 100K+ calls/day.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import requests

from consumer_research.collectors.base import BaseCollector
from consumer_research.models.schemas import (
    ContentType,
    NormalizedItem,
    PlatformMetadata,
    SourcePlatform,
)
from consumer_research.utils.hashing import generate_item_id
from consumer_research.utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

_RATE_LIMITER = RateLimiter(max_calls=10, window_seconds=1.0)

_HEADERS = {
    "User-Agent": "ConsumerResearch/0.1 (mailto:research@example.com)"
}


class AcademicCollector(BaseCollector):
    """Collects academic papers from OpenAlex."""

    platform_name = "academic"

    def __init__(self, max_papers: int = 50):
        self.max_papers = max_papers

    def collect(self, brand_name: str, keywords: list[str], **kwargs) -> list[NormalizedItem]:
        all_items: list[NormalizedItem] = []
        seen_ids: set[str] = set()

        # Search with brand name and each keyword
        search_queries = [brand_name] + keywords
        for query in search_queries:
            papers = self._search_openalex(query)
            for paper in papers:
                title = paper.get("title", "")
                abstract_obj = paper.get("abstract_inverted_index")
                abstract = self._reconstruct_abstract(abstract_obj) if abstract_obj else ""
                full_text = f"{title}. {abstract}".strip()

                if not full_text or len(full_text) < 30:
                    continue

                doi = paper.get("doi", "")
                openalex_id = paper.get("id", "")
                url = doi if doi else openalex_id
                if not url:
                    continue

                item_id = generate_item_id(url, full_text[:500])
                if item_id in seen_ids:
                    continue
                seen_ids.add(item_id)

                pub_date_str = paper.get("publication_date")
                timestamp = None
                if pub_date_str:
                    try:
                        timestamp = datetime.strptime(pub_date_str, "%Y-%m-%d").replace(
                            tzinfo=timezone.utc
                        )
                    except ValueError:
                        pass

                # Get first author
                authorships = paper.get("authorships", [])
                author = "Unknown"
                if authorships:
                    author_obj = authorships[0].get("author", {})
                    author = author_obj.get("display_name", "Unknown")

                # Get journal/source
                primary_location = paper.get("primary_location", {}) or {}
                source = primary_location.get("source", {}) or {}
                journal_name = source.get("display_name", "")

                item = NormalizedItem(
                    item_id=item_id,
                    source_platform=SourcePlatform.ACADEMIC,
                    source_url=url,
                    source_author=author,
                    source_timestamp=timestamp,
                    collected_at=self._now(),
                    content_text=full_text[:3000],
                    content_type=ContentType.PAPER,
                    platform_metadata=PlatformMetadata(
                        citation_count=paper.get("cited_by_count"),
                        doi=doi,
                        journal=journal_name,
                    ),
                    collection_query=query,
                    collection_method="openalex_search",
                )
                all_items.append(item)

            if len(all_items) >= self.max_papers:
                break

        logger.info(f"Academic: collected {len(all_items)} papers for '{brand_name}'")
        return all_items[:self.max_papers]

    def _search_openalex(self, query: str) -> list[dict]:
        _RATE_LIMITER.wait()
        url = "https://api.openalex.org/works"
        params = {
            "search": query,
            "per_page": 25,
            "sort": "relevance_score:desc",
        }

        try:
            resp = requests.get(url, params=params, headers=_HEADERS, timeout=15)
            resp.raise_for_status()
            return resp.json().get("results", [])
        except requests.RequestException as e:
            logger.error(f"OpenAlex API error: {e}")
            return []

    @staticmethod
    def _reconstruct_abstract(inverted_index: dict) -> str:
        """Reconstruct abstract text from OpenAlex's inverted index format."""
        if not inverted_index:
            return ""
        word_positions: list[tuple[int, str]] = []
        for word, positions in inverted_index.items():
            for pos in positions:
                word_positions.append((pos, word))
        word_positions.sort()
        return " ".join(word for _, word in word_positions)
