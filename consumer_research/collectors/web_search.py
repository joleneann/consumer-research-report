"""Web search collector using Serper (Google Search API).

Finds brand mentions across the open web — blogs, forums, review sites,
news articles, and other pages we'd miss with platform-specific collectors.

Free tier: 2,500 queries (no credit card required).
Requires SERPER_API_KEY environment variable.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

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

_RATE_LIMITER = RateLimiter(max_calls=2, window_seconds=1.0)


class WebSearchCollector(BaseCollector):
    """Collects web mentions via Serper (Google Search API)."""

    platform_name = "web"

    def __init__(self, api_key: str | None = None, max_results: int = 100):
        self.api_key = api_key or os.environ.get("SERPER_API_KEY", "")
        self.max_results = max_results

    def collect(self, brand_name: str, keywords: list[str], **kwargs) -> list[NormalizedItem]:
        if not self.api_key:
            logger.warning("Serper: No API key set (SERPER_API_KEY). Skipping.")
            return []

        all_items: list[NormalizedItem] = []
        seen_ids: set[str] = set()
        seen_urls: set[str] = set()

        # Search with brand name + key keyword variants (cap to save quota)
        queries = [brand_name] + keywords[:8]

        for query in queries:
            results = self._search(query)
            for result in results:
                title = result.get("title", "")
                snippet = result.get("snippet", "")
                url = result.get("link", "")

                if not url or not (title or snippet):
                    continue

                # Skip duplicate URLs
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                full_text = f"{title}. {snippet}".strip()
                if len(full_text) < 20:
                    continue

                item_id = generate_item_id(url, full_text[:500])
                if item_id in seen_ids:
                    continue
                seen_ids.add(item_id)

                item = NormalizedItem(
                    item_id=item_id,
                    source_platform=SourcePlatform.WEB,
                    source_url=url,
                    source_author="Web",
                    collected_at=self._now(),
                    content_text=full_text[:2000],
                    content_type=ContentType.ARTICLE,
                    platform_metadata=PlatformMetadata(),
                    collection_query=query,
                    collection_method="serper_google_search",
                )
                all_items.append(item)

            if len(all_items) >= self.max_results:
                break

        logger.info(f"Web Search (Serper): collected {len(all_items)} results for '{brand_name}'")
        return all_items[:self.max_results]

    def _search(self, query: str, num: int = 20) -> list[dict]:
        _RATE_LIMITER.wait()
        try:
            resp = requests.post(
                "https://google.serper.dev/search",
                headers={
                    "X-API-KEY": self.api_key,
                    "Content-Type": "application/json",
                },
                json={"q": query, "num": min(num, 100)},
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json().get("organic", [])
        except requests.RequestException as e:
            logger.error(f"Serper error: {e}")
            return []
