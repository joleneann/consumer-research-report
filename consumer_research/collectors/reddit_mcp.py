"""Reddit data collector using Reddit's public JSON API.

This collector fetches posts and comments from Reddit without requiring
authentication by appending .json to Reddit URLs. It provides fully
traceable data with permalinks, scores, timestamps, and author info.

Rate limited to 1 request per 2 seconds to respect Reddit's guidelines
for unauthenticated access.
"""

from __future__ import annotations

import logging
import time
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

# Reddit's public JSON API rate limit: be conservative
_RATE_LIMITER = RateLimiter(max_calls=1, window_seconds=2.0)

_HEADERS = {
    "User-Agent": "ConsumerResearch/0.1 (research project; contact: research@example.com)"
}


class RedditCollector(BaseCollector):
    """Collects posts and comments from Reddit using the public JSON API."""

    platform_name = "reddit"

    def __init__(
        self,
        subreddits: list[str] | None = None,
        max_posts: int = 500,
        max_comments_per_post: int = 20,
        min_score: int = 3,
        sort: str = "relevance",
        time_filter: str = "year",
    ):
        self.subreddits = subreddits or []
        self.max_posts = max_posts
        self.max_comments_per_post = max_comments_per_post
        self.min_score = min_score  # Minimum upvotes to include
        self.sort = sort
        self.time_filter = time_filter

    def collect(self, brand_name: str, keywords: list[str], **kwargs) -> list[NormalizedItem]:
        """Collect Reddit posts and comments matching the brand/keywords.

        Searches each configured subreddit, then also does a site-wide search.
        For each post found, fetches the top comments.
        """
        all_items: list[NormalizedItem] = []
        seen_ids: set[str] = set()
        search_queries = [brand_name] + keywords

        # Build brand validation terms for post-level quality gate
        brand_lower = brand_name.lower()
        self._brand_terms = {brand_lower, brand_lower.replace(" ", "")}
        if "thums" in brand_lower:
            self._brand_terms.update(["thumbs up", "thumsup", "thumbsup", "thumps up", "thums up"])
        self._skipped_posts = 0

        for query in search_queries:
            # Site-wide search
            posts = self._search_posts(query, subreddit=None)
            all_items.extend(self._process_posts(posts, query, seen_ids))

            # Per-subreddit search
            for sub in self.subreddits:
                posts = self._search_posts(query, subreddit=sub)
                all_items.extend(self._process_posts(posts, query, seen_ids))

            if len(all_items) >= self.max_posts:
                break

        if self._skipped_posts:
            logger.info(f"Reddit: skipped {self._skipped_posts} posts with no brand mention (from broad queries)")
        logger.info(f"Reddit: collected {len(all_items)} items for '{brand_name}'")
        return all_items[:self.max_posts * 3]  # posts + comments can exceed post count

    def _search_posts(
        self, query: str, subreddit: str | None = None, limit: int = 25
    ) -> list[dict]:
        """Search Reddit for posts matching the query."""
        if subreddit:
            url = f"https://www.reddit.com/r/{subreddit}/search.json"
        else:
            url = "https://www.reddit.com/search.json"

        params = {
            "q": query,
            "sort": self.sort,
            "t": self.time_filter,
            "limit": min(limit, 100),
            "restrict_sr": "1" if subreddit else "0",
        }

        data = self._make_request(url, params)
        if not data:
            return []

        posts = []
        for child in data.get("data", {}).get("children", []):
            if child.get("kind") == "t3":
                posts.append(child["data"])
        return posts

    def _fetch_comments(self, permalink: str, limit: int = 50) -> list[dict]:
        """Fetch comments for a specific post."""
        url = f"https://www.reddit.com{permalink}.json"
        params = {"limit": limit, "sort": "top"}

        data = self._make_request(url, params)
        if not data or not isinstance(data, list) or len(data) < 2:
            return []

        comments = []
        self._extract_comments(data[1].get("data", {}).get("children", []), comments, limit)
        return comments

    def _extract_comments(self, children: list[dict], result: list[dict], limit: int, depth: int = 0) -> None:
        """Recursively extract comments from Reddit's nested structure."""
        for child in children:
            if len(result) >= limit:
                break
            if child.get("kind") != "t1":
                continue
            comment_data = child.get("data", {})
            if comment_data.get("body") and comment_data["body"] != "[deleted]":
                comment_data["_depth"] = depth
                result.append(comment_data)
            # Recurse into replies
            replies = comment_data.get("replies")
            if isinstance(replies, dict):
                reply_children = replies.get("data", {}).get("children", [])
                self._extract_comments(reply_children, result, limit, depth + 1)

    def _process_posts(
        self, posts: list[dict], query: str, seen_ids: set[str]
    ) -> list[NormalizedItem]:
        """Convert raw Reddit posts to NormalizedItems and fetch their comments."""
        items: list[NormalizedItem] = []
        low_engagement_dropped = 0

        for post in posts:
            post_url = f"https://www.reddit.com{post.get('permalink', '')}"
            post_text = f"{post.get('title', '')} {post.get('selftext', '')}".strip()

            if not post_text or len(post_text) < 10:
                continue

            # Quality gate: for non-brand queries (category terms), check that
            # the post actually mentions the brand. This prevents collecting
            # generic category posts from broad queries.
            post_lower = post_text.lower()
            query_lower = query.lower()
            query_has_brand = any(bt in query_lower for bt in self._brand_terms)
            post_has_brand = any(bt in post_lower for bt in self._brand_terms)
            # If the query doesn't contain the brand AND the post doesn't mention it,
            # skip - it's likely noise from a broad category search
            if not query_has_brand and not post_has_brand:
                self._skipped_posts += 1
                continue

            # Extract thread_id from Reddit post ID (t3_xxxxx)
            post_id = post.get("id", "")
            thread_id = post_id

            item_id = generate_item_id(post_url, post_text)
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)

            # Posts always included (they frame the discussion)
            created_utc = post.get("created_utc")
            timestamp = datetime.fromtimestamp(created_utc, tz=timezone.utc) if created_utc else None

            post_item = NormalizedItem(
                item_id=item_id,
                source_platform=SourcePlatform.REDDIT,
                source_url=post_url,
                source_author=post.get("author", "Unknown"),
                source_timestamp=timestamp,
                collected_at=self._now(),
                content_text=post_text,
                content_type=ContentType.POST,
                platform_metadata=PlatformMetadata(
                    score=post.get("score"),
                    subreddit=post.get("subreddit"),
                    num_comments=post.get("num_comments"),
                    thread_id=thread_id,
                    comment_depth=0,
                ),
                collection_query=query,
                collection_method="reddit_json_search",
            )
            items.append(post_item)

            # Fetch comments for this post
            if post.get("num_comments", 0) > 0 and post.get("permalink"):
                comments = self._fetch_comments(
                    post["permalink"], limit=self.max_comments_per_post
                )
                for comment in comments:
                    comment_text = comment.get("body", "").strip()
                    if not comment_text or len(comment_text) < 10:
                        continue

                    # Engagement filter: skip low-score comments
                    comment_score = comment.get("score", 0) or 0
                    if comment_score < self.min_score:
                        low_engagement_dropped += 1
                        continue

                    comment_permalink = comment.get("permalink", "")
                    comment_url = f"https://www.reddit.com{comment_permalink}" if comment_permalink else post_url
                    c_id = generate_item_id(comment_url, comment_text)

                    if c_id in seen_ids:
                        continue
                    seen_ids.add(c_id)

                    c_created = comment.get("created_utc")
                    c_timestamp = datetime.fromtimestamp(c_created, tz=timezone.utc) if c_created else None
                    depth = comment.get("_depth", 0)

                    comment_item = NormalizedItem(
                        item_id=c_id,
                        source_platform=SourcePlatform.REDDIT,
                        source_url=comment_url,
                        source_author=comment.get("author", "Unknown"),
                        source_timestamp=c_timestamp,
                        collected_at=self._now(),
                        content_text=comment_text,
                        content_type=ContentType.COMMENT,
                        platform_metadata=PlatformMetadata(
                            score=comment_score,
                            subreddit=post.get("subreddit"),
                            thread_id=thread_id,
                            comment_depth=depth,
                        ),
                        collection_query=query,
                        collection_method="reddit_json_comments",
                    )
                    items.append(comment_item)

        if low_engagement_dropped:
            logger.info(f"  Dropped {low_engagement_dropped} comments below min score {self.min_score}")

        return items

    def _make_request(self, url: str, params: dict) -> dict | list | None:
        """Make a rate-limited GET request to Reddit's JSON API."""
        _RATE_LIMITER.wait()
        try:
            resp = requests.get(url, params=params, headers=_HEADERS, timeout=15)
            if resp.status_code == 429:
                logger.warning("Reddit rate limited, waiting 10s...")
                time.sleep(10)
                resp = requests.get(url, params=params, headers=_HEADERS, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.error(f"Reddit API error: {e} (url: {url})")
            return None
        except ValueError as e:
            logger.error(f"Reddit JSON parse error: {e}")
            return None
