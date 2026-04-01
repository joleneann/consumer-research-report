"""YouTube data collector using the YouTube Data API v3.

Searches for videos related to the brand, then fetches top comments
from each video. Provides fully traceable data with video URLs,
comment permalinks, timestamps, and engagement metrics.

Requires a YouTube Data API key (set YOUTUBE_API_KEY env var).
Free tier provides 10,000 quota units/day.
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

_RATE_LIMITER = RateLimiter(max_calls=5, window_seconds=1.0)


class YouTubeCollector(BaseCollector):
    """Collects video metadata and comments from YouTube."""

    platform_name = "youtube"

    def __init__(
        self,
        api_key: str | None = None,
        max_videos: int = 50,
        max_comments_per_video: int = 100,
        min_likes: int = 2,
        region_code: str = "",
    ):
        self.api_key = api_key or os.environ.get("YOUTUBE_API_KEY", "")
        self.max_videos = max_videos
        self.max_comments_per_video = max_comments_per_video
        self.min_likes = min_likes
        self.region_code = region_code

    def collect(self, brand_name: str, keywords: list[str], **kwargs) -> list[NormalizedItem]:
        if not self.api_key:
            logger.warning("YouTube: No API key set (YOUTUBE_API_KEY). Skipping.")
            return []

        all_items: list[NormalizedItem] = []
        seen_ids: set[str] = set()
        search_queries = [brand_name] + keywords

        # Build brand validation terms from brand name and its variants
        brand_lower = brand_name.lower()
        brand_terms = {brand_lower, brand_lower.replace(" ", "")}
        # Add common misspellings
        if "thums" in brand_lower:
            brand_terms.update(["thumbs up", "thumsup", "thumbsup", "thumps up", "thums up"])
        skipped_videos = 0

        for query in search_queries:
            videos = self._search_videos(query)
            for video in videos:
                video_id = video.get("id", {}).get("videoId")
                if not video_id:
                    continue

                snippet = video.get("snippet", {})
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                video_title = snippet.get("title", "")
                video_desc = snippet.get("description", "")

                # Quality gate: skip videos whose title+description don't mention
                # the brand. This prevents fetching comments from irrelevant videos
                # found via broad category queries.
                title_desc_lower = f"{video_title} {video_desc}".lower()
                if not any(bt in title_desc_lower for bt in brand_terms):
                    # Also check the original query - if the query IS brand-specific,
                    # trust YouTube's relevance ranking
                    query_lower = query.lower()
                    if not any(bt in query_lower for bt in brand_terms):
                        skipped_videos += 1
                        continue

                comments = self._fetch_comments(video_id)
                for comment in comments:
                    comment_snippet = comment.get("snippet", {}).get(
                        "topLevelComment", {}
                    ).get("snippet", {})
                    text = comment_snippet.get("textOriginal", "").strip()
                    if not text or len(text) < 10:
                        continue

                    # Engagement filter
                    like_count = comment_snippet.get("likeCount", 0) or 0
                    if like_count < self.min_likes:
                        continue

                    comment_id = comment.get("snippet", {}).get(
                        "topLevelComment", {}
                    ).get("id", "")
                    comment_url = f"{video_url}&lc={comment_id}" if comment_id else video_url

                    item_id = generate_item_id(comment_url, text)
                    if item_id in seen_ids:
                        continue
                    seen_ids.add(item_id)

                    published = comment_snippet.get("publishedAt")
                    timestamp = None
                    if published:
                        try:
                            timestamp = datetime.fromisoformat(
                                published.replace("Z", "+00:00")
                            )
                        except ValueError:
                            pass

                    item = NormalizedItem(
                        item_id=item_id,
                        source_platform=SourcePlatform.YOUTUBE,
                        source_url=comment_url,
                        source_author=comment_snippet.get(
                            "authorDisplayName", "Unknown"
                        ),
                        source_timestamp=timestamp,
                        collected_at=self._now(),
                        content_text=text,
                        content_type=ContentType.COMMENT,
                        platform_metadata=PlatformMetadata(
                            video_id=video_id,
                            thread_id=video_id,  # Thread = video for YouTube
                            video_title=video_title,
                            like_count=comment_snippet.get("likeCount"),
                        ),
                        collection_query=query,
                        collection_method="youtube_api_v3_comments",
                    )
                    all_items.append(item)

            if len(all_items) >= self.max_videos * self.max_comments_per_video:
                break

        if skipped_videos:
            logger.info(f"YouTube: skipped {skipped_videos} videos with no brand mention in title/description")
        logger.info(f"YouTube: collected {len(all_items)} comments for '{brand_name}'")
        return all_items

    def _search_videos(self, query: str) -> list[dict]:
        _RATE_LIMITER.wait()
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": min(self.max_videos, 50),
            "order": "relevance",
            "key": self.api_key,
        }
        if self.region_code:
            params["regionCode"] = self.region_code

        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json().get("items", [])
        except requests.RequestException as e:
            logger.error(f"YouTube search error: {e}")
            return []

    def _fetch_comments(self, video_id: str) -> list[dict]:
        _RATE_LIMITER.wait()
        url = "https://www.googleapis.com/youtube/v3/commentThreads"
        params = {
            "part": "snippet",
            "videoId": video_id,
            "maxResults": min(self.max_comments_per_video, 100),
            "order": "relevance",
            "key": self.api_key,
        }

        try:
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 403:
                # Comments may be disabled
                return []
            resp.raise_for_status()
            return resp.json().get("items", [])
        except requests.RequestException as e:
            logger.error(f"YouTube comments error for {video_id}: {e}")
            return []
