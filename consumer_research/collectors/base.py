"""Base collector interface that all data collectors must implement."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from consumer_research.models.schemas import NormalizedItem


class BaseCollector(ABC):
    """Abstract base class for all data collectors.

    Every collector must:
    1. Collect raw data from its source
    2. Return a list of NormalizedItem objects conforming to the unified schema
    3. Preserve all source provenance (URLs, timestamps, authors)
    """

    @abstractmethod
    def collect(self, brand_name: str, keywords: list[str], **kwargs) -> list[NormalizedItem]:
        """Collect data for the given brand/keywords.

        Args:
            brand_name: The brand to research.
            keywords: Search terms to use.
            **kwargs: Collector-specific parameters.

        Returns:
            List of NormalizedItem objects with full provenance.
        """
        ...

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform identifier for this collector."""
        ...

    def _now(self) -> datetime:
        return datetime.utcnow()
