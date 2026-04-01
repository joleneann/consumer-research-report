"""NewsData.io collector for press coverage and industry news.

Provides news articles with full source attribution, author info,
and publication dates. Free tier: 200 credits/day.

Requires NEWSDATA_API_KEY environment variable.
"""

from __future__ import annotations

import logging
import os
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

_RATE_LIMITER = RateLimiter(max_calls=1, window_seconds=1.0)


class NewsCollector(BaseCollector):
    """Collects news articles from NewsData.io."""

    platform_name = "news"

    def __init__(
        self,
        api_key: str | None = None,
        language: str = "en",
        country: str = "",
        max_articles: int = 100,
    ):
        self.api_key = api_key or os.environ.get("NEWSDATA_API_KEY", "")
        self.language = language
        self.country = country
        self.max_articles = max_articles

    def collect(self, brand_name: str, keywords: list[str], **kwargs) -> list[NormalizedItem]:
        if not self.api_key:
            logger.warning("News: No API key set (NEWSDATA_API_KEY). Skipping.")
            return []

        all_items: list[NormalizedItem] = []
        seen_ids: set[str] = set()
        search_queries = [brand_name] + keywords

        for query in search_queries:
            articles = self._search_articles(query)
            for article in articles:
                title = article.get("title", "")
                description = article.get("description", "") or ""
                content = article.get("content", "") or ""
                full_text = f"{title}. {description} {content}".strip()

                if not full_text or len(full_text) < 20:
                    continue

                url = article.get("link", "")
                if not url:
                    continue

                item_id = generate_item_id(url, full_text[:500])
                if item_id in seen_ids:
                    continue
                seen_ids.add(item_id)

                pub_date = article.get("pubDate")
                timestamp = None
                if pub_date:
                    try:
                        timestamp = datetime.fromisoformat(
                            pub_date.replace("Z", "+00:00")
                        )
                    except ValueError:
                        pass

                creator = article.get("creator")
                author = creator[0] if isinstance(creator, list) and creator else "Unknown"

                item = NormalizedItem(
                    item_id=item_id,
                    source_platform=SourcePlatform.NEWS,
                    source_url=url,
                    source_author=author,
                    source_timestamp=timestamp,
                    collected_at=self._now(),
                    content_text=full_text[:2000],  # Cap text length
                    content_type=ContentType.ARTICLE,
                    platform_metadata=PlatformMetadata(),
                    collection_query=query,
                    collection_method="newsdata_api_search",
                )
                all_items.append(item)

            if len(all_items) >= self.max_articles:
                break

        logger.info(f"News: collected {len(all_items)} articles for '{brand_name}'")
        return all_items[:self.max_articles]

    def _search_articles(self, query: str) -> list[dict]:
        _RATE_LIMITER.wait()
        url = "https://newsdata.io/api/1/latest"
        params = {
            "apikey": self.api_key,
            "q": query,
            "language": self.language,
        }
        if self.country:
            params["country"] = self.country

        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") != "success":
                logger.error(f"NewsData API error: {data.get('results', {})}")
                return []
            return data.get("results", [])
        except requests.RequestException as e:
            logger.error(f"NewsData API error: {e}")
            return []
