"""Deterministic ID generation for corpus items.

Uses SHA-256 hashing of source_url + content_text to ensure
the same content always produces the same item_id, making
the pipeline reproducible.
"""

import hashlib


def generate_item_id(source_url: str, content_text: str) -> str:
    """Generate a deterministic ID for a corpus item.

    Args:
        source_url: The permalink/URL of the source content.
        content_text: The text content of the item.

    Returns:
        A hex SHA-256 hash string (first 16 chars for readability).
    """
    raw = f"{source_url}|{content_text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
