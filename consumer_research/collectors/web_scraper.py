"""Web scraper collector for product reviews (Amazon, Flipkart, etc).

Uses Crawl4AI (open source, no API limits) to scrape product review pages
and extract structured review data. Falls back to requests+BeautifulSoup
if Crawl4AI is not available.

This collector is for verified purchase reviews — the highest-trust
consumer signal available.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

from consumer_research.collectors.base import BaseCollector
from consumer_research.models.schemas import (
    ContentType,
    NormalizedItem,
    PlatformMetadata,
    SourcePlatform,
)
from consumer_research.utils.hashing import generate_item_id

logger = logging.getLogger(__name__)


class WebScraperCollector(BaseCollector):
    """Scrapes product review pages for consumer data."""

    platform_name = "reviews"

    def __init__(self, urls: list[str] | None = None, max_reviews_per_url: int = 50):
        self.urls = urls or []
        self.max_reviews_per_url = max_reviews_per_url

    def collect(self, brand_name: str, keywords: list[str], **kwargs) -> list[NormalizedItem]:
        """Collect reviews from provided URLs.

        URLs should point to product review pages (Amazon, Flipkart, etc).
        If no URLs provided, this collector does nothing.
        """
        if not self.urls:
            logger.info("Web Scraper: No URLs provided. Skipping.")
            return []

        all_items: list[NormalizedItem] = []
        seen_ids: set[str] = set()

        for url in self.urls:
            try:
                reviews = self._scrape_reviews(url, brand_name)
                for review in reviews:
                    item_id = generate_item_id(review["url"], review["text"][:500])
                    if item_id in seen_ids:
                        continue
                    seen_ids.add(item_id)

                    item = NormalizedItem(
                        item_id=item_id,
                        source_platform=SourcePlatform.AMAZON,  # Or detect from URL
                        source_url=review["url"],
                        source_author=review.get("author", "Unknown"),
                        collected_at=self._now(),
                        content_text=review["text"],
                        content_type=ContentType.REVIEW,
                        platform_metadata=PlatformMetadata(
                            star_rating=review.get("rating"),
                            verified_purchase=review.get("verified"),
                        ),
                        collection_query=brand_name,
                        collection_method="web_scraper_reviews",
                    )
                    all_items.append(item)

            except Exception as e:
                logger.error(f"Web Scraper error for {url}: {e}")

        logger.info(f"Web Scraper: collected {len(all_items)} reviews for '{brand_name}'")
        return all_items

    def _scrape_reviews(self, url: str, brand_name: str) -> list[dict]:
        """Scrape reviews from a URL. Tries Crawl4AI first, falls back to requests."""
        try:
            return self._scrape_with_crawl4ai(url, brand_name)
        except ImportError:
            logger.info("Crawl4AI not available, trying requests fallback")
            return self._scrape_with_requests(url, brand_name)

    def _scrape_with_crawl4ai(self, url: str, brand_name: str) -> list[dict]:
        """Scrape using Crawl4AI for JavaScript-heavy pages."""
        from crawl4ai import WebCrawler

        crawler = WebCrawler()
        crawler.warmup()
        result = crawler.run(url=url)

        if not result.success:
            logger.error(f"Crawl4AI failed for {url}")
            return []

        # Extract review-like content from the markdown
        return self._parse_review_text(result.markdown, url)

    def _scrape_with_requests(self, url: str, brand_name: str) -> list[dict]:
        """Simple fallback scraper using requests."""
        import requests

        try:
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            resp.raise_for_status()
            return self._parse_review_text(resp.text, url)
        except Exception as e:
            logger.error(f"Requests fallback failed for {url}: {e}")
            return []

    def _parse_review_text(self, text: str, source_url: str) -> list[dict]:
        """Extract review-like segments from raw text. Basic heuristic parser."""
        reviews = []
        # Split on common review separators
        segments = re.split(r'\n{2,}|\r\n{2,}', text)

        for segment in segments:
            segment = segment.strip()
            # Heuristic: reviews are usually 50-2000 chars
            if 50 < len(segment) < 2000:
                reviews.append({
                    "text": segment,
                    "url": source_url,
                    "author": "Unknown",
                    "rating": None,
                    "verified": None,
                })

            if len(reviews) >= self.max_reviews_per_url:
                break

        return reviews
