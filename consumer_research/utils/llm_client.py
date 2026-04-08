"""Unified LLM client abstraction.

Supports both Anthropic Claude and Google Gemini as backends.
The pipeline code calls this client instead of the Anthropic SDK directly,
making it easy to swap providers.

Usage:
    client = create_llm_client()  # Auto-detects available provider
    response_text = client.generate(prompt, max_tokens=4096)
"""

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    """Abstract LLM client interface."""

    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 4096, temperature: float = 0.0) -> str:
        """Generate a response from the LLM.

        Args:
            prompt: The prompt text.
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature (0.0 = deterministic).

        Returns:
            The generated text response.
        """
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier being used."""
        ...


class ClaudeClient(LLMClient):
    """Anthropic Claude API client."""

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        import anthropic
        self._client = anthropic.Anthropic()
        self._model = model

    def generate(self, prompt: str, max_tokens: int = 4096, temperature: float = 0.0) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()

    @property
    def model_name(self) -> str:
        return self._model


class GeminiClient(LLMClient):
    """Google Gemini API client (using google-genai SDK)."""

    def __init__(self, model: str = "gemini-2.0-flash-001"):
        from google import genai
        api_key = os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        self._client = genai.Client(api_key=api_key)
        self._model_name = model

    def generate(self, prompt: str, max_tokens: int = 4096, temperature: float = 0.0) -> str:
        from google.genai import types
        response = self._client.models.generate_content(
            model=self._model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            ),
        )
        return response.text.strip()

    @property
    def model_name(self) -> str:
        return self._model_name


def create_llm_client(preferred_provider: str = "auto", model: str | None = None) -> LLMClient:
    """Create an LLM client, auto-detecting available providers.

    Priority: Claude (if ANTHROPIC_API_KEY set) → Gemini (if GOOGLE_API_KEY set)

    Args:
        preferred_provider: "claude", "gemini", or "auto" (default)
        model: Optional model name override. Passed to the client constructor.

    Returns:
        An LLMClient instance.
    """
    if preferred_provider == "claude":
        client = ClaudeClient(model=model) if model else ClaudeClient()
        logger.info(f"LLM provider: Claude ({client.model_name})")
        return client

    if preferred_provider == "gemini":
        client = GeminiClient(model=model) if model else GeminiClient()
        logger.info(f"LLM provider: Gemini ({client.model_name})")
        return client

    # Auto-detect — Claude first (primary provider), Gemini as fallback
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if anthropic_key:
        try:
            client = ClaudeClient(model=model) if model else ClaudeClient()
            logger.info(f"Using Claude ({client.model_name})")
            return client
        except Exception as e:
            logger.warning(f"Claude init failed: {e}")

    google_key = os.environ.get("GOOGLE_API_KEY", "")
    if google_key:
        try:
            client = GeminiClient(model=model) if model else GeminiClient()
            logger.info(f"Using Gemini ({client.model_name})")
            return client
        except Exception as e:
            logger.warning(f"Gemini init failed: {e}")

    raise RuntimeError(
        "No LLM provider available. Set ANTHROPIC_API_KEY or GOOGLE_API_KEY."
    )
