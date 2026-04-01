"""Google Trends data collector using PyTrends.

Fetches search interest over time, related queries, and interest by region
for the given brand. This provides a demand-side signal that complements
social conversation data.

Free, no API key required. Rate-limited with 60s delays to avoid blocks.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from consumer_research.collectors.base import BaseCollector
from consumer_research.models.schemas import (
    ContentType,
    NormalizedItem,
    PlatformMetadata,
    SourcePlatform,
)
from consumer_research.utils.hashing import generate_item_id

logger = logging.getLogger(__name__)


class TrendsCollector(BaseCollector):
    """Collects Google Trends data for search interest analysis."""

    platform_name = "trends"

    def __init__(self, geo: str = "", timeframe: str = "today 12-m"):
        self.geo = geo  # e.g., "IN" for India
        self.timeframe = timeframe

    def collect(self, brand_name: str, keywords: list[str], **kwargs) -> list[NormalizedItem]:
        try:
            from pytrends.request import TrendReq
        except ImportError:
            logger.error("pytrends not installed. Run: pip install pytrends")
            return []

        items: list[NormalizedItem] = []
        pytrends = TrendReq(hl="en-US", tz=330 if self.geo == "IN" else 0)

        all_kws = [brand_name] + keywords[:4]  # pytrends max 5 keywords

        # Interest over time
        try:
            logger.info(f"Trends: fetching interest over time for {all_kws}")
            pytrends.build_payload(all_kws, cat=0, timeframe=self.timeframe, geo=self.geo)
            iot = pytrends.interest_over_time()

            if not iot.empty and brand_name in iot.columns:
                for date_idx, row in iot.iterrows():
                    interest = int(row[brand_name])
                    date_str = str(date_idx.date())
                    url = f"https://trends.google.com/trends/explore?q={brand_name}&geo={self.geo}&date={self.timeframe}"

                    item_id = generate_item_id(url, f"interest_{date_str}_{interest}")
                    item = NormalizedItem(
                        item_id=item_id,
                        source_platform=SourcePlatform.TRENDS,
                        source_url=url,
                        source_author="Google Trends",
                        source_timestamp=date_idx.to_pydatetime().replace(tzinfo=timezone.utc),
                        collected_at=self._now(),
                        content_text=f"Google search interest for '{brand_name}': {interest}/100 on {date_str}",
                        content_type=ContentType.TREND_DATA,
                        platform_metadata=PlatformMetadata(
                            search_interest=interest,
                            region=self.geo or "global",
                        ),
                        collection_query=brand_name,
                        collection_method="pytrends_interest_over_time",
                    )
                    items.append(item)

                logger.info(f"Trends: {len(items)} data points for interest over time")
        except Exception as e:
            logger.error(f"Trends interest_over_time error: {e}")

        time.sleep(5)  # Delay between pytrends calls

        # Related queries
        try:
            logger.info(f"Trends: fetching related queries for '{brand_name}'")
            pytrends.build_payload([brand_name], cat=0, timeframe=self.timeframe, geo=self.geo)
            related = pytrends.related_queries()

            if brand_name in related:
                for query_type in ["top", "rising"]:
                    df = related[brand_name].get(query_type)
                    if df is not None and not df.empty:
                        for _, row in df.iterrows():
                            query_text = row.get("query", "")
                            value = row.get("value", 0)
                            url = f"https://trends.google.com/trends/explore?q={brand_name}&geo={self.geo}"

                            item_id = generate_item_id(url, f"related_{query_type}_{query_text}")
                            item = NormalizedItem(
                                item_id=item_id,
                                source_platform=SourcePlatform.TRENDS,
                                source_url=url,
                                source_author="Google Trends",
                                collected_at=self._now(),
                                content_text=f"Related {query_type} query for '{brand_name}': '{query_text}' (value: {value})",
                                content_type=ContentType.TREND_DATA,
                                platform_metadata=PlatformMetadata(
                                    search_interest=int(value) if isinstance(value, (int, float)) else None,
                                    region=self.geo or "global",
                                ),
                                collection_query=brand_name,
                                collection_method=f"pytrends_related_queries_{query_type}",
                            )
                            items.append(item)

                logger.info(f"Trends: total {len(items)} items including related queries")
        except Exception as e:
            logger.error(f"Trends related_queries error: {e}")

        return items
