"""
OpenRouter LLM client for AURUM AI.

Uses the openai SDK pointed at the OpenRouter base URL.  Acts as the last-resort
fallback in the multi-provider chain — free-tier models only, no cost incurred.
"""

import logging
from typing import Optional

from openai import OpenAI, RateLimitError as OpenAIRateLimitError

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class RateLimitError(Exception):
    """Raised when the provider returns a 429 rate-limit response."""
    pass


class OpenRouterClient:
    """OpenRouter client backed by the openai SDK.

    Args:
        api_key: OpenRouter API key.
    """

    DEFAULT_MODEL = "meta-llama/llama-3.1-8b-instruct:free"
    DEEP_MODEL = "google/gemma-2-9b-it:free"

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("OpenRouter API key must not be empty.")
        self._client = OpenAI(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL,
        )

    def _messages_to_dicts(self, messages: list) -> list[dict]:
        """Normalise messages to plain dicts for the openai SDK."""
        result = []
        for msg in messages:
            # Already a plain dict — pass through
            if isinstance(msg, dict):
                result.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
                continue
            # LangChain message objects expose .type and .content
            role_map = {
                "human": "user",
                "ai": "assistant",
                "system": "system",
            }
            role = role_map.get(getattr(msg, "type", "human"), "user")
            result.append({"role": role, "content": msg.content})
        return result

    def invoke(
        self,
        messages: list,
        model: str = DEFAULT_MODEL,
    ) -> str:
        """Invoke an OpenRouter model and return the response text.

        Args:
            messages: List of message dicts (role/content) or LangChain messages.
            model: OpenRouter model path, e.g. ``"meta-llama/llama-3.1-8b-instruct:free"``.

        Returns:
            The assistant's response as a plain string.

        Raises:
            RateLimitError: If the API returns a 429 error.
            Exception: For other API errors.
        """
        normalised = self._messages_to_dicts(messages)
        try:
            completion = self._client.chat.completions.create(
                model=model,
                messages=normalised,
                temperature=0.2,
            )
            return completion.choices[0].message.content or ""
        except OpenAIRateLimitError as exc:
            logger.warning("OpenRouter rate limit hit for model %s: %s", model, exc)
            raise RateLimitError(f"OpenRouter rate limit exceeded: {exc}") from exc
        except Exception as exc:
            exc_str = str(exc).lower()
            if "429" in exc_str or "rate limit" in exc_str or "rate_limit" in exc_str:
                logger.warning("OpenRouter rate limit hit for model %s: %s", model, exc)
                raise RateLimitError(f"OpenRouter rate limit exceeded: {exc}") from exc
            logger.error("OpenRouter invocation error (model=%s): %s", model, exc)
            raise

    def invoke_deep(self, messages: list) -> str:
        """Invoke the deeper free model (Gemma-2 9B).

        Args:
            messages: List of message dicts or LangChain messages.

        Returns:
            The assistant's response as a plain string.

        Raises:
            RateLimitError: If the API returns a 429 error.
        """
        return self.invoke(messages, model=self.DEEP_MODEL)
